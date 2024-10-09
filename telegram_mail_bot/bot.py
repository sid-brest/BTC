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
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables from .env file
load_dotenv()

# Email settings
IMAP_SERVER = "imap.gmail.com"
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")

# Telegram bot settings
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "").split(",")

# Initialize Telegram bot with increased timeout
bot = telebot.TeleBot(BOT_TOKEN, threaded=False, timeout=30)

# Configure logging
logging.basicConfig(filename='mail_bot.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    encoding='utf-8')

# Create folder for saving images
PICTURES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Pictures")
if not os.path.exists(PICTURES_FOLDER):
    os.makedirs(PICTURES_FOLDER)

def init_db():
    """Initialize the SQLite database and create necessary tables."""
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    
    # Create table for storing processed email IDs
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails
                 (email_id TEXT PRIMARY KEY)''')
    
    # Create table for storing authorized chat IDs and usernames
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='authorized_chats'")
    if c.fetchone() is None:
        c.execute('''CREATE TABLE authorized_chats
                     (chat_id INTEGER PRIMARY KEY, username TEXT)''')
    else:
        # Add username column if it doesn't exist (for backwards compatibility)
        c.execute("PRAGMA table_info(authorized_chats)")
        columns = [col[1] for col in c.fetchall()]
        if 'username' not in columns:
            c.execute("ALTER TABLE authorized_chats ADD COLUMN username TEXT")
    
    conn.commit()
    conn.close()

def is_email_processed(email_id):
    """Check if an email has already been processed."""
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,))
    result = c.fetchone() is not None
    conn.close()
    return result

def add_processed_email(email_id):
    """Mark an email as processed in the database."""
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO processed_emails (email_id) VALUES (?)", (email_id,))
    conn.commit()
    conn.close()

def get_authorized_chats():
    """Retrieve all authorized chat IDs from the database."""
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("SELECT chat_id FROM authorized_chats")
    chats = [row[0] for row in c.fetchall()]
    conn.close()
    return chats

def add_authorized_chat(chat_id, username):
    """Add or update an authorized chat in the database."""
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO authorized_chats (chat_id, username) VALUES (?, ?)", (chat_id, username))
    conn.commit()
    conn.close()

def remove_authorized_chat(chat_id):
    """Remove an authorized chat from the database."""
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM authorized_chats WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def is_user_allowed(username):
    """Check if a user is in the list of allowed users."""
    return username in ALLOWED_USERS

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=60))
def send_telegram_message(chat_id, message):
    """Send a text message via Telegram with retry mechanism."""
    try:
        bot.send_message(chat_id, message)
    except Exception as e:
        logging.error(f"Error sending Telegram message: {str(e)}")
        raise

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=60))
def send_telegram_photo(chat_id, photo, caption):
    """Send a photo message via Telegram with retry mechanism."""
    try:
        with open(photo, "rb") as photo_file:
            bot.send_photo(chat_id, photo_file, caption=caption)
    except Exception as e:
        logging.error(f"Error sending Telegram photo: {str(e)}")
        raise

def fetch_emails():
    """Fetch and process new emails from the last hour."""
    logging.info("Starting to check sent mail")

    try:
        # Connect to the email server
        with MailBox(IMAP_SERVER).login(EMAIL, PASSWORD) as mailbox:
            # Set the folder to "Sent" emails
            mailbox.folder.set('[Gmail]/Отправленные')
            # Get emails from the last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            for msg in mailbox.fetch(A(date_gte=one_hour_ago.date())):
                # Skip already processed emails
                if is_email_processed(msg.uid):
                    continue

                logging.info(f"Processing email: {msg.subject}")

                # Process attachments
                for att in msg.attachments:
                    if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        # Save the attachment
                        filepath = os.path.join(PICTURES_FOLDER, att.filename)
                        with open(filepath, "wb") as f:
                            f.write(att.payload)
                        
                        logging.info(f"Saved image: {att.filename}")
                        
                        # Send the image to all authorized chats
                        for chat_id in get_authorized_chats():
                            send_telegram_photo(chat_id, filepath, f"Subject: {msg.subject}")
                        
                        logging.info(f"Sent image to Telegram: {att.filename}")

                # Mark email as processed
                add_processed_email(msg.uid)

        logging.info("Finished checking sent mail")
    except Exception as e:
        logging.error(f"Error while checking mail: {str(e)}", exc_info=True)

def scheduled_check():
    """Function to be called by the scheduler."""
    fetch_emails()

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle the /start command."""
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if is_user_allowed(username):
        add_authorized_chat(message.chat.id, username)
        send_telegram_message(message.chat.id, "You have successfully subscribed to notifications.")
        logging.info(f"User {username} (chat_id: {message.chat.id}) subscribed to notifications")
    else:
        send_telegram_message(message.chat.id, "Sorry, you don't have permission to use this bot.")
        logging.warning(f"Unauthorized subscription attempt by user {username} (chat_id: {message.chat.id})")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    """Handle the /stop command."""
    remove_authorized_chat(message.chat.id)
    send_telegram_message(message.chat.id, "You have successfully unsubscribed from notifications.")
    username = f"@{message.from_user.username}" if message.from_user.username else None
    logging.info(f"User {username} (chat_id: {message.chat.id}) unsubscribed from notifications")

@bot.message_handler(func=lambda message: True)
def log_all_messages(message):
    """Log all received messages."""
    username = f"@{message.from_user.username}" if message.from_user.username else None
    logging.info(f"Received message from user {username} (chat_id: {message.chat.id}): {message.text}")

def run_bot():
    """Main function to run the bot."""
    logging.info("Bot started")
    init_db()
    
    # Add a startup delay
    time.sleep(10)  # Wait for 10 seconds before starting

    # Start bot polling in a separate thread
    bot_thread = threading.Thread(target=bot.polling, args=(None, True))
    bot_thread.start()

    # Schedule email check every minute
    schedule.every(1).minutes.do(scheduled_check)

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error in bot operation: {str(e)}")
            time.sleep(5)  # Wait for 5 seconds before retrying

if __name__ == "__main__":
    run_bot()# Initialize database