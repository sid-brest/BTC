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
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails
                 (email_id TEXT PRIMARY KEY)''')
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='authorized_chats'")
    if c.fetchone() is None:
        c.execute('''CREATE TABLE authorized_chats
                     (chat_id INTEGER PRIMARY KEY, username TEXT, is_active INTEGER DEFAULT 1)''')
    else:
        c.execute("PRAGMA table_info(authorized_chats)")
        columns = [col[1] for col in c.fetchall()]
        if 'username' not in columns:
            c.execute("ALTER TABLE authorized_chats ADD COLUMN username TEXT")
        if 'is_active' not in columns:
            c.execute("ALTER TABLE authorized_chats ADD COLUMN is_active INTEGER DEFAULT 1")
    
    conn.commit()
    conn.close()

# Database functions
def is_email_processed(email_id):
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,))
    result = c.fetchone() is not None
    conn.close()
    return result

def add_processed_email(email_id):
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO processed_emails (email_id) VALUES (?)", (email_id,))
    conn.commit()
    conn.close()

def get_authorized_chats():
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("SELECT chat_id FROM authorized_chats WHERE is_active = 1")
    chats = [row[0] for row in c.fetchall()]
    conn.close()
    return chats

def add_authorized_chat(chat_id, username):
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO authorized_chats (chat_id, username, is_active) VALUES (?, ?, 1)", (chat_id, username))
    conn.commit()
    conn.close()

def is_user_allowed(username):
    return username in ALLOWED_USERS

def update_authorized_chats():
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    
    # Get all users from the authorized_chats table
    c.execute("SELECT chat_id, username, is_active FROM authorized_chats")
    db_users = c.fetchall()
    
    # Create a set of allowed usernames from the .env file
    allowed_usernames = set(ALLOWED_USERS)
    
    for chat_id, username, is_active in db_users:
        if username in allowed_usernames:
            # User is in ALLOWED_USERS, activate them
            if not is_active:
                c.execute("UPDATE authorized_chats SET is_active = 1 WHERE chat_id = ?", (chat_id,))
                logging.info(f"Reactivated user {username} (chat_id: {chat_id}) as they are now in ALLOWED_USERS")
        else:
            # User is not in ALLOWED_USERS, deactivate them
            if is_active:
                c.execute("UPDATE authorized_chats SET is_active = 0 WHERE chat_id = ?", (chat_id,))
                logging.info(f"Deactivated user {username} (chat_id: {chat_id}) as they are no longer in ALLOWED_USERS")
    
    # Add any new users from ALLOWED_USERS that are not in the database
    for username in allowed_usernames:
        c.execute("SELECT 1 FROM authorized_chats WHERE username = ?", (username,))
        if c.fetchone() is None:
            c.execute("INSERT INTO authorized_chats (username, is_active) VALUES (?, 1)", (username,))
            logging.info(f"Added new user {username} to authorized_chats as they are in ALLOWED_USERS")
    
    conn.commit()
    conn.close()

def fetch_emails():
    logging.info("Starting to check sent mail")

    try:
        with MailBox(IMAP_SERVER).login(EMAIL, PASSWORD) as mailbox:
            mailbox.folder.set('[Gmail]/Отправленные')
            one_hour_ago = datetime.now() - timedelta(hours=1)
            for msg in mailbox.fetch(A(date_gte=one_hour_ago.date())):
                if is_email_processed(msg.uid):
                    continue

                logging.info(f"Processing email: {msg.subject}")

                for att in msg.attachments:
                    if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        filepath = os.path.join(PICTURES_FOLDER, att.filename)
                        with open(filepath, "wb") as f:
                            f.write(att.payload)
                        
                        logging.info(f"Saved image: {att.filename}")
                        
                        for chat_id in get_authorized_chats():
                            with open(filepath, "rb") as photo:
                                bot.send_photo(chat_id, photo, caption=f"Subject: {msg.subject}")
                        
                        logging.info(f"Sent image to Telegram: {att.filename}")

                add_processed_email(msg.uid)

        logging.info("Finished checking sent mail")
    except Exception as e:
        logging.error(f"Error while checking mail: {str(e)}", exc_info=True)

def scheduled_check():
    update_authorized_chats()
    fetch_emails()

@bot.message_handler(commands=['start'])
def handle_start(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if is_user_allowed(username):
        add_authorized_chat(message.chat.id, username)
        bot.reply_to(message, "Вы успешно подписались на уведомления.")
        logging.info(f"User {username} (chat_id: {message.chat.id}) subscribed to notifications")
    else:
        bot.reply_to(message, "К сожалению, у Вас нет разрешения на использование этого бота.")
        logging.warning(f"Unauthorized subscription attempt by user {username} (chat_id: {message.chat.id})")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("UPDATE authorized_chats SET is_active = 0 WHERE chat_id = ?", (message.chat.id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, "Вы отписались от получения уведомлений.")
    username = f"@{message.from_user.username}" if message.from_user.username else None
    logging.info(f"User {username} (chat_id: {message.chat.id}) unsubscribed from notifications")

@bot.message_handler(func=lambda message: True)
def log_all_messages(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    logging.info(f"Received message from user {username} (chat_id: {message.chat.id}): {message.text}")

schedule.every(1).minutes.do(scheduled_check)

def run_bot():
    logging.info("Bot started")
    init_db()
    update_authorized_chats()  # Update authorized chats on startup
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