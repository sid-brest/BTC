import os
import pandas as pd
from datetime import datetime
import re
import sqlite3
import email
import imaplib
import email.header
from email.header import decode_header
from dotenv import load_dotenv
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
import numpy as np

# Load environment variables
load_dotenv()

# Create directories if they don't exist
os.makedirs('./csvdata', exist_ok=True)
os.makedirs('./csvbymonth', exist_ok=True)

# Google Sheets API setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service-account-key.json'
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

def initialize_sheets_api():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    return service

def get_or_create_sheet(service, sheet_name):
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', '')
        sheet_exists = False
        
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                sheet_exists = True
                break
                
        if not sheet_exists:
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=request_body
            ).execute()
            
    except Exception as e:
        print(f"Error with sheet {sheet_name}: {str(e)}")
        return False
    return True

def update_sheet_data(service, sheet_name, data):
    try:
        values = [data.columns.values.tolist()] + data.values.tolist()
        values = [['' if isinstance(x, float) and np.isnan(x) else x for x in row] for row in values]
        
        body = {
            'values': values
        }
        
        range_name = f'{sheet_name}!A1:Z'
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return True
    except Exception as e:
        print(f"Error updating sheet {sheet_name}: {str(e)}")
        return False

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('processed_emails.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS processed_emails
        (message_id TEXT PRIMARY KEY, 
         subject TEXT,
         date TEXT,
         email_account TEXT)
    ''')
    conn.commit()
    return conn

def is_email_processed(conn, message_id):
    c = conn.cursor()
    c.execute('SELECT 1 FROM processed_emails WHERE message_id = ?', (message_id,))
    return c.fetchone() is not None

def mark_email_processed(conn, message_id, subject, date, email_account):
    c = conn.cursor()
    c.execute('INSERT INTO processed_emails (message_id, subject, date, email_account) VALUES (?, ?, ?, ?)',
              (message_id, subject, date, email_account))
    conn.commit()

def download_attachments(email_account, password):
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(email_account, password)
    mail.select('"[Gmail]/Sent Mail"')

    result, messages = mail.search(None, 'ALL')
    
    if result != 'OK':
        print(f"Error accessing emails for {email_account}")
        return

    conn = init_db()

    for num in messages[0].split():
        result, msg_data = mail.fetch(num, '(RFC822)')
        if result != 'OK':
            continue

        email_body = msg_data[0][1]
        message = email.message_from_bytes(email_body)
        message_id = message['Message-ID']

        if is_email_processed(conn, message_id):
            continue

        for part in message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if filename and filename.upper().endswith('.CSV'):
                if decode_header(filename)[0][1] is not None:
                    filename = decode_header(filename)[0][0].decode(decode_header(filename)[0][1])

                filepath = os.path.join('./csvdata', filename)
                
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                
                mark_email_processed(conn, message_id, message['subject'],
                                  message['date'], email_account)

    mail.close()
    mail.logout()
    conn.close()

def get_channel(filename):
    ip_match = re.search(r'192\.168\.4\.(\d+)', filename)
    if ip_match:
        ip_last_octet = ip_match.group(1)
        if ip_last_octet == '103':
            return 'CH01'
        elif ip_last_octet == '104':
            return 'CH02'
    return 'Unknown'

def calculate_time_intervals(df):
    results = []
    for plate, group in df.groupby('Номерной знак'):
        group = group.sort_values('Время мом. снимка')
        events = group.to_dict('records')
        i = 0
        intervals = []
        
        while i < len(events) - 1:
            if events[i]['Канал'] == 'CH01' and events[i + 1]['Канал'] == 'CH02':
                time_diff = (events[i + 1]['Время мом. снимка'] - events[i]['Время мом. снимка']).total_seconds() / 60
                intervals.append({
                    'start_time': events[i]['Время мом. снимка'].strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': events[i + 1]['Время мом. снимка'].strftime('%Y-%m-%d %H:%M:%S'),
                    'interval': round(time_diff, 2)
                })
            i += 1
        
        if intervals:
            total_minutes = sum(interval['interval'] for interval in intervals)
            total_days = round(total_minutes / 1440, 3)
            results.append({
                'Номерной знак': plate,
                'Количество проездов': len(intervals),
                'Суммарное время (дни)': total_days,
                'Детали проездов': ', '.join([
                    f"({interval['start_time']} -> {interval['end_time']}: {interval['interval']} мин)"
                    for interval in intervals
                ])
            })
    
    return pd.DataFrame(results)

def upload_intervals_to_sheets():
    service = initialize_sheets_api()
    interval_files = [f for f in os.listdir('./csvbymonth') if f.startswith('intervals_')]
    
    for file in interval_files:
        match = re.search(r'intervals_(\d{4}-\d{2})\.csv', file)
        if match:
            year_month = match.group(1)
            sheet_name = datetime.strptime(year_month, '%Y-%m').strftime('%m.%Y')
            
            df = pd.read_csv(f'./csvbymonth/{file}', encoding='utf-8-sig')
            
            if get_or_create_sheet(service, sheet_name):
                if update_sheet_data(service, sheet_name, df):
                    print(f"Successfully updated sheet {sheet_name}")
                else:
                    print(f"Failed to update sheet {sheet_name}")
            else:
                print(f"Failed to create/get sheet {sheet_name}")

def main():
    # Download attachments from both email accounts
    email_accounts = [
        (os.getenv('EMAIL1'), os.getenv('EMAIL1_PASSWORD')),
        (os.getenv('EMAIL2'), os.getenv('EMAIL2_PASSWORD'))
    ]

    for email_account, password in email_accounts:
        if email_account and password:
            download_attachments(email_account, password)

    # Process CSV files
    csv_files = [f for f in os.listdir('./csvdata') if f.endswith('.CSV')]
    monthly_dfs = {}

    for file in csv_files:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file)
        if date_match:
            file_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
            month_key = file_date.strftime('%Y-%m')
            
            df = pd.read_csv(f'./csvdata/{file}', encoding='utf-8')
            df = df[df['Номерной знак'] != 'Не лицензировано']
            
            selected_columns = ['Номерной знак', 'Белый список', 'Время мом. снимка', 'ТС спереди или сзади']
            df = df[selected_columns].copy()
            
            df.insert(0, 'Канал', get_channel(file))
            
            if month_key in monthly_dfs:
                monthly_dfs[month_key] = pd.concat([monthly_dfs[month_key], df], ignore_index=True)
            else:
                monthly_dfs[month_key] = df

    # Process and save files by month
    for month_key, df in monthly_dfs.items():
        df['Время мом. снимка'] = pd.to_datetime(df['Время мом. снимка'])
        df_sorted = df.sort_values(['Номерной знак', 'Время мом. снимка'])
        
        output_filename = f'./csvbymonth/data_{month_key}.csv'
        df_temp = df_sorted.copy()
        df_temp['Время мом. снимка'] = df_temp['Время мом. снимка'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_temp.to_csv(output_filename, index=False, encoding='utf-8-sig')
        
        intervals_df = calculate_time_intervals(df_sorted)
        intervals_filename = f'./csvbymonth/intervals_{month_key}.csv'
        intervals_df.to_csv(intervals_filename, index=False, encoding='utf-8-sig')

    # Upload interval data to Google Sheets
    upload_intervals_to_sheets()
    
    print("Processing completed. Check the csvbymonth folder and Google Sheets for results.")

if __name__ == "__main__":
    main()