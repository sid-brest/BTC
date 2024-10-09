import os
import telebot # type: ignore
from dotenv import load_dotenv # type: ignore
import logging
import schedule # type: ignore
import time
from imap_tools import MailBox, A # type: ignore
from datetime import datetime, timedelta
import sqlite3
import threading

# Load environment variables from .env file
load_dotenv()

# Email settings
IMAP_SERVER = "imap.gmail.com"
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")

# Telegram bot settings
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "").split(",")

# Initialize Telegram bot
bot = telebot.TeleBot(BOT_TOKEN)

# Configure logging
logging.basicConfig(filename='mail_bot.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    encoding='utf-8')

# Create folder for saving images
PICTURES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Pictures")
if not os.path.exists(PICTURES_FOLDER):
    os.makedirs(PICTURES_FOLDER)

# Initialize database
def init_db():
    # Connect to SQLite database
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    
    # Create table for processed emails if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails
                 (email_id TEXT PRIMARY KEY)''')
    
    # Check if authorized_chats table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='authorized_chats'")
    if c.fetchone() is None:
        # If table doesn't exist, create it with new structure
        c.execute('''CREATE TABLE authorized_chats
                     (chat_id INTEGER PRIMARY KEY, username TEXT)''')
    else:
        # If table exists, check for username column
        c.execute("PRAGMA table_info(authorized_chats)")
        columns = [col[1] for col in c.fetchall()]
        if 'username' not in columns:
            # If username column doesn't exist, add it
            c.execute("ALTER TABLE authorized_chats ADD COLUMN username TEXT")
    
    conn.commit()
    conn.close()

# Database functions
def is_email_processed(email_id):
    # Check if email has been processed
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,))
    result = c.fetchone() is not None
    conn.close()
    return result

def add_processed_email(email_id):
    # Add processed email to database
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO processed_emails (email_id) VALUES (?)", (email_id,))
    conn.commit()
    conn.close()

def get_authorized_chats():
    # Get list of authorized chat IDs
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("SELECT chat_id FROM authorized_chats")
    chats = [row[0] for row in c.fetchall()]
    conn.close()
    return chats

def add_authorized_chat(chat_id, username):
    # Add or update authorized chat
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO authorized_chats (chat_id, username) VALUES (?, ?)", (chat_id, username))
    conn.commit()
    conn.close()

def remove_authorized_chat(chat_id):
    # Remove authorized chat
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM authorized_chats WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def is_user_allowed(username):
    # Check if user is in the allowed users list
    return username in ALLOWED_USERS

def fetch_emails():
    logging.info("Starting to check sent mail")

    try:
        # Connect to the email server
        with MailBox(IMAP_SERVER).login(EMAIL, PASSWORD) as mailbox:
            # Set folder to sent mail
            mailbox.folder.set('[Gmail]/Отправленные')
            one_hour_ago = datetime.now() - timedelta(hours=1)
            # Fetch emails from the last hour
            for msg in mailbox.fetch(A(date_gte=one_hour_ago.date())):
                # Skip if email already processed
                if is_email_processed(msg.uid):
                    continue

                logging.info(f"Processing email: {msg.subject}")

                # Process attachments
                for att in msg.attachments:
                    if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        filepath = os.path.join(PICTURES_FOLDER, att.filename)
                        # Save attachment
                        with open(filepath, "wb") as f:
                            f.write(att.payload)
                        
                        logging.info(f"Saved image: {att.filename}")
                        
                        # Send image to all authorized chats
                        for chat_id in get_authorized_chats():
                            with open(filepath, "rb") as photo:
                                bot.send_photo(chat_id, photo, caption=f"Subject: {msg.subject}")
                        
                        logging.info(f"Sent image to Telegram: {att.filename}")

                # Mark email as processed
                add_processed_email(msg.uid)

        logging.info("Finished checking sent mail")
    except Exception as e:
        logging.error(f"Error while checking mail: {str(e)}", exc_info=True)

def scheduled_check():
    # Function to be called by scheduler
    fetch_emails()

@bot.message_handler(commands=['start'])
def handle_start(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if is_user_allowed(username):
        add_authorized_chat(message.chat.id, username)
        bot.reply_to(message, "You have successfully subscribed to notifications.")
        logging.info(f"User {username} (chat_id: {message.chat.id}) subscribed to notifications")
    else:
        bot.reply_to(message, "Sorry, you don't have permission to use this bot.")
        logging.warning(f"Unauthorized subscription attempt by user {username} (chat_id: {message.chat.id})")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    remove_authorized_chat(message.chat.id)
    bot.reply_to(message, "You have successfully unsubscribed from notifications.")
    username = f"@{message.from_user.username}" if message.from_user.username else None
    logging.info(f"User {username} (chat_id: {message.chat.id}) unsubscribed from notifications")

@bot.message_handler(func=lambda message: True)
def log_all_messages(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    logging.info(f"Received message from user {username} (chat_id: {message.chat.id}): {message.text}")

# Schedule email check every minute
schedule.every(1).minutes.do(scheduled_check)

def run_bot():
    logging.info("Bot started")
    init_db()
    # Start bot polling in a separate thread
    bot_thread = threading.Thread(target=bot.polling, args=(None, True))
    bot_thread.start()
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error in bot operation: {str(e)}")
            time.sleep(1)

if __name__ == "__main__":
    run_bot()
