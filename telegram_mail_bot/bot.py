# Import necessary libraries
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
TO_EMAIL = os.getenv("TOEMAIL")  # New variable for the specified email address

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
    """
    Initialize the SQLite database and create necessary tables if they don't exist.
    """
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    
    # Create table for storing processed email IDs
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails
                 (email_id TEXT PRIMARY KEY)''')
    
    # Create table for storing authorized chat information
    c.execute('''CREATE TABLE IF NOT EXISTS authorized_chats
                 (chat_id INTEGER PRIMARY KEY, username TEXT, is_active INTEGER DEFAULT 0)''')
    
    conn.commit()
    conn.close()

# Database functions
def is_email_processed(email_id):
    """
    Check if an email has already been processed.
    
    :param email_id: The unique identifier of the email
    :return: True if the email has been processed, False otherwise
    """
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,))
    result = c.fetchone() is not None
    conn.close()
    return result

def add_processed_email(email_id):
    """
    Mark an email as processed by adding its ID to the database.
    
    :param email_id: The unique identifier of the email
    """
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO processed_emails (email_id) VALUES (?)", (email_id,))
    conn.commit()
    conn.close()

def get_authorized_chats():
    """
    Retrieve a list of authorized chat IDs from the database.
    
    :return: A list of active chat IDs
    """
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("SELECT chat_id FROM authorized_chats WHERE is_active = 1")
    chats = [row[0] for row in c.fetchall()]
    conn.close()
    return chats

def add_or_update_chat(chat_id, username, is_active):
    """
    Add a new chat or update an existing chat's information in the database.
    
    :param chat_id: The unique identifier of the Telegram chat
    :param username: The username associated with the chat
    :param is_active: Boolean indicating whether the chat is active
    """
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO authorized_chats (chat_id, username, is_active) VALUES (?, ?, ?)", 
              (chat_id, username, is_active))
    conn.commit()
    conn.close()

def is_user_allowed(username):
    """
    Check if a user is allowed to use the bot.
    
    :param username: The username to check
    :return: True if the user is allowed, False otherwise
    """
    return username in ALLOWED_USERS

def update_authorized_chats():
    """
    Update the authorized chats in the database based on the ALLOWED_USERS list.
    Only adds new users, doesn't change status of existing users.
    """
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    
    c.execute("SELECT username FROM authorized_chats")
    db_usernames = set(row[0] for row in c.fetchall())
    
    allowed_usernames = set(ALLOWED_USERS)
    
    for username in allowed_usernames:
        if username not in db_usernames:
            c.execute("INSERT INTO authorized_chats (username, is_active) VALUES (?, 1)", (username,))
            logging.info(f"Added new allowed user {username} to database")
    
    conn.commit()
    conn.close()

def fetch_emails():
    """
    Fetch new emails from the sent mail folder, process attachments, and send them to authorized Telegram chats.
    """
    logging.info("Starting to check sent mail")

    try:
        with MailBox(IMAP_SERVER).login(EMAIL, PASSWORD) as mailbox:
            mailbox.folder.set('[Gmail]/Отправленные')
            one_hour_ago = datetime.now() - timedelta(hours=1)
            for msg in mailbox.fetch(A(date_gte=one_hour_ago.date())):
                if is_email_processed(msg.uid):
                    continue

                # Check if the specified email address is in the "To" field
                if TO_EMAIL not in msg.to:
                    continue

                logging.info(f"Processing email: {msg.subject}")

                has_image_attachment = False
                for att in msg.attachments:
                    if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        has_image_attachment = True
                        filepath = os.path.join(PICTURES_FOLDER, att.filename)
                        with open(filepath, "wb") as f:
                            f.write(att.payload)
                        
                        logging.info(f"Saved image: {att.filename}")
                        
                        # Format the sent date
                        sent_date = msg.date.strftime("%Y-%m-%d %H:%M:%S")
                        
                        for chat_id in get_authorized_chats():
                            try:
                                with open(filepath, "rb") as photo:
                                    bot.send_photo(chat_id, photo, caption=f"Изображение отправлено: {sent_date}")
                                logging.info(f"Sent image to Telegram: {att.filename} (chat_id: {chat_id})")
                            except telebot.apihelper.ApiTelegramException as e:
                                if e.error_code == 400 and "chat not found" in e.description:
                                    logging.warning(f"Chat not found for chat_id: {chat_id}. Deactivating in database.")
                                    add_or_update_chat(chat_id, None, 0)
                                else:
                                    logging.error(f"Error sending image to chat_id {chat_id}: {str(e)}")

                # Mark email as processed regardless of whether it has image attachments
                add_processed_email(msg.uid)

        logging.info("Finished checking sent mail")
    except Exception as e:
        logging.error(f"Error while checking mail: {str(e)}", exc_info=True)

def scheduled_check():
    """
    Perform a scheduled check of emails and update authorized chats.
    """
    update_authorized_chats()
    fetch_emails()

@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Handle the /start command for the Telegram bot.
    """
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if is_user_allowed(username):
        conn = sqlite3.connect('mail_bot.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO authorized_chats (chat_id, username, is_active) VALUES (?, ?, 1)", 
                  (message.chat.id, username))
        conn.commit()
        conn.close()
        bot.reply_to(message, "Вы успешно подписались на уведомления.")
        logging.info(f"User {username} (chat_id: {message.chat.id}) subscribed to notifications")
    else:
        bot.reply_to(message, "К сожалению, у Вас нет разрешения на использование этого бота.")
        logging.warning(f"Unauthorized subscription attempt by user {username} (chat_id: {message.chat.id})")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    """
    Handle the /stop command for the Telegram bot.
    """
    username = f"@{message.from_user.username}" if message.from_user.username else None
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("UPDATE authorized_chats SET is_active = 0 WHERE chat_id = ?", (message.chat.id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, "Вы отписались от получения уведомлений.")
    logging.info(f"User {username} (chat_id: {message.chat.id}) unsubscribed from notifications")

@bot.message_handler(func=lambda message: True)
def log_all_messages(message):
    """
    Log all received messages for debugging purposes.
    """
    username = f"@{message.from_user.username}" if message.from_user.username else None
    logging.info(f"Received message from user {username} (chat_id: {message.chat.id}): {message.text}")

# Schedule the email check to run every minute
schedule.every(1).minutes.do(scheduled_check)

def run_bot():
    """
    Main function to run the bot and handle scheduled tasks.
    """
    logging.info("Bot started")
    init_db()
    update_authorized_chats()
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