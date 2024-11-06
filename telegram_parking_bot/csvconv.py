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

load_dotenv()

os.makedirs('./csvdata', exist_ok=True)
os.makedirs('./csvbymonth', exist_ok=True)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service-account-key.json'
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

def format_duration(minutes):
    """Convert minutes to days/hours/minutes format with floor rounding"""
    minutes = int(minutes)  # Floor rounding
    if minutes < 60:
        return f"{minutes} мин"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        return f"{hours} ч. {remaining_minutes} мин"
    
    days = hours // 24
    remaining_hours = hours % 24
    return f"{days} д. {remaining_hours} ч. {remaining_minutes} мин"

def load_plate_mappings(filename='plate_mapping.txt'):
    mappings = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    target, sources = line.strip().split('=')
                    sources = [p.strip() for p in sources.replace(';', ',').split(',')]
                    for plate in sources:
                        mappings[plate] = target.strip()
                    mappings[target.strip()] = target.strip()
    except FileNotFoundError:
        print(f"Warning: {filename} not found")
    return mappings

def setup_sheets_api():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def manage_sheet(service, sheet_name):
    try:
        metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        if not any(sheet['properties']['title'] == sheet_name for sheet in metadata.get('sheets', '')):
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {'title': sheet_name}
                    }
                }]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
        return True
    except Exception as e:
        print(f"Sheet management error ({sheet_name}): {e}")
        return False

def update_sheet_content(service, sheet_name, data):
    try:
        if 'Суммарное время (мин)' in data.columns:
            data['Суммарное время'] = data['Суммарное время (мин)'].apply(format_duration)
            data = data.drop('Суммарное время (мин)', axis=1)

        values = [data.columns.values.tolist()] + data.values.tolist()
        values = [['' if pd.isna(x) else x for x in row] for row in values]
        
        range_name = f'{sheet_name}!A1:Z'
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A1',
            valueInputOption='RAW',
            body={'values': values}
        ).execute()
        return True
    except Exception as e:
        print(f"Sheet update error ({sheet_name}): {e}")
        return False

def setup_email_db():
    conn = sqlite3.connect('processed_emails.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS processed_emails
        (message_id TEXT PRIMARY KEY, 
         subject TEXT,
         date TEXT,
         email_account TEXT)
    ''')
    conn.commit()
    return conn

def check_processed_email(conn, message_id):
    return conn.execute('SELECT 1 FROM processed_emails WHERE message_id = ?', 
                       (message_id,)).fetchone() is not None

def record_processed_email(conn, message_id, subject, date, account):
    conn.execute('INSERT INTO processed_emails VALUES (?, ?, ?, ?)',
                (message_id, subject, date, account))
    conn.commit()

def fetch_email_attachments(email_account, password):
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(email_account, password)
    mail.select('"[Gmail]/Sent Mail"')

    conn = setup_email_db()
    _, messages = mail.search(None, 'ALL')

    for num in messages[0].split():
        _, msg_data = mail.fetch(num, '(RFC822)')
        email_msg = email.message_from_bytes(msg_data[0][1])
        
        if check_processed_email(conn, email_msg['Message-ID']):
            continue

        for part in email_msg.walk():
            if part.get_content_maintype() == 'multipart' or not part.get('Content-Disposition'):
                continue

            filename = part.get_filename()
            if filename and filename.upper().endswith('.CSV'):
                if decode_header(filename)[0][1]:
                    filename = decode_header(filename)[0][0].decode(decode_header(filename)[0][1])

                with open(os.path.join('./csvdata', filename), 'wb') as f:
                    f.write(part.get_payload(decode=True))
                
                record_processed_email(conn, email_msg['Message-ID'], 
                                    email_msg['subject'], email_msg['date'], 
                                    email_account)

    mail.close()
    mail.logout()
    conn.close()

def identify_channel(filename):
    ip_match = re.search(r'192\.168\.4\.(\d+)', filename)
    return 'CH01' if ip_match and ip_match.group(1) == '103' else 'CH02' if ip_match and ip_match.group(1) == '104' else 'Unknown'

def process_intervals(df, plate_mappings):
    intervals_data = []
    
    df = df.copy()
    df['Original_Plate'] = df['Номерной знак']
    df['Номерной знак'] = df['Номерной знак'].map(lambda x: plate_mappings.get(x, x))
    
    for plate in df['Номерной знак'].unique():
        plate_events = df[df['Номерной знак'] == plate].sort_values('Время мом. снимка')
        
        intervals = []
        start_time = None
        
        for _, event in plate_events.iterrows():
            if event['Канал'] == 'CH01':
                if not start_time:
                    start_time = event['Время мом. снимка']
            elif event['Канал'] == 'CH02' and start_time:
                duration = (event['Время мом. снимка'] - start_time).total_seconds() / 60
                intervals.append({
                    'start': start_time,
                    'end': event['Время мом. снимка'],
                    'duration': int(duration)  # Floor rounding
                })
                start_time = None

        if intervals:
            total_minutes = sum(interval['duration'] for interval in intervals)
            
            intervals_details = ', '.join([
                f"({interval['start'].strftime('%Y-%m-%d %H:%M:%S')} -> "
                f"{interval['end'].strftime('%Y-%m-%d %H:%M:%S')}: "
                f"{format_duration(interval['duration'])})"
                for interval in intervals
            ])
            
            intervals_data.append({
                'Номерной знак': plate,
                'Количество проездов': len(intervals),
                'Суммарное время (мин)': total_minutes,
                'Детали проездов': intervals_details
            })
    
    return pd.DataFrame(intervals_data)

def update_sheets_with_intervals():
    service = setup_sheets_api()
    interval_files = [f for f in os.listdir('./csvbymonth') if f.startswith('intervals_')]
    
    for file in interval_files:
        if match := re.search(r'intervals_(\d{4}-\d{2})\.csv', file):
            sheet_name = datetime.strptime(match.group(1), '%Y-%m').strftime('%m.%Y')
            df = pd.read_csv(f'./csvbymonth/{file}', encoding='utf-8-sig')
            
            if manage_sheet(service, sheet_name):
                if update_sheet_content(service, sheet_name, df):
                    print(f"Updated sheet: {sheet_name}")
                else:
                    print(f"Failed to update: {sheet_name}")

def main():
    plate_mappings = load_plate_mappings()
    
    for account, password in [
        (os.getenv('EMAIL1'), os.getenv('EMAIL1_PASSWORD')),
        (os.getenv('EMAIL2'), os.getenv('EMAIL2_PASSWORD'))
    ]:
        if account and password:
            fetch_email_attachments(account, password)

    monthly_data = {}

    for file in [f for f in os.listdir('./csvdata') if f.endswith('.CSV')]:
        if date_match := re.search(r'(\d{4}-\d{2}-\d{2})', file):
            month_key = datetime.strptime(date_match.group(1), '%Y-%m-%d').strftime('%Y-%m')
            
            df = pd.read_csv(f'./csvdata/{file}', encoding='utf-8')
            df = df[df['Номерной знак'] != 'Не лицензировано']
            
            df = df[['Номерной знак', 'Белый список', 'Время мом. снимка', 'ТС спереди или сзади']].copy()
            df.insert(0, 'Канал', identify_channel(file))
            
            monthly_data[month_key] = pd.concat([monthly_data.get(month_key, pd.DataFrame()), df])

    for month_key, df in monthly_data.items():
        df['Время мом. снимка'] = pd.to_datetime(df['Время мом. снимка'])
        df_sorted = df.sort_values(['Номерной знак', 'Время мом. снимка'])
        
        base_path = f'./csvbymonth/data_{month_key}.csv'
        df_export = df_sorted.copy()
        df_export['Время мом. снимка'] = df_export['Время мом. снимка'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_export.to_csv(base_path, index=False, encoding='utf-8-sig')
        
        intervals = process_intervals(df_sorted, plate_mappings)
        intervals.to_csv(f'./csvbymonth/intervals_{month_key}.csv', index=False, encoding='utf-8-sig')

    update_sheets_with_intervals()
    print("Processing complete. Results available in csvbymonth folder and Google Sheets.")

if __name__ == "__main__":
    main()