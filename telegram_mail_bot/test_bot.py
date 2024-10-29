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
import imaplib
import socket

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

def init_db():
    """
    Initialize the SQLite database and create necessary tables if they don't exist.
    """
    try:
        conn = sqlite3.connect('mail_bot.db')
        c = conn.cursor()
        
        # Create table for storing processed email IDs
        c.execute('''CREATE TABLE IF NOT EXISTS processed_emails
                     (email_id TEXT PRIMARY KEY)''')
        
        # Create table for storing authorized chat information
        c.execute('''CREATE TABLE IF NOT EXISTS authorized_chats
                     (chat_id INTEGER PRIMARY KEY, username TEXT, is_active INTEGER DEFAULT 0)''')
        
        conn.commit()
    except Exception as e:
        logging.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def is_email_processed(email_id):
    """
    Check if an email has already been processed.
    """
    try:
        conn = sqlite3.connect('mail_bot.db')
        c = conn.cursor()
        c.execute("SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,))
        result = c.fetchone() is not None
        return result
    except Exception as e:
        logging.error(f"Error checking processed email: {str(e)}", exc_info=True)
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def add_processed_email(email_id):
    """
    Mark an email as processed by adding its ID to the database.
    """
    try:
        conn = sqlite3.connect('mail_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO processed_emails (email_id) VALUES (?)", (email_id,))
        conn.commit()
    except Exception as e:
        logging.error(f"Error adding processed email: {str(e)}", exc_info=True)
    finally:
        if 'conn' in locals():
            conn.close()

def get_authorized_chats():
    """
    Retrieve a list of authorized chat IDs from the database.
    """
    try:
        conn = sqlite3.connect('mail_bot.db')
        c = conn.cursor()
        c.execute("SELECT chat_id FROM authorized_chats WHERE is_active = 1")
        chats = [row[0] for row in c.fetchall()]
        return chats
    except Exception as e:
        logging.error(f"Error getting authorized chats: {str(e)}", exc_info=True)
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def add_or_update_chat(chat_id, username, is_active):
    """
    Add a new chat or update an existing chat's information in the database.
    """
    try:
        conn = sqlite3.connect('mail_bot.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO authorized_chats (chat_id, username, is_active) VALUES (?, ?, ?)", 
                  (chat_id, username, is_active))
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating chat: {str(e)}", exc_info=True)
    finally:
        if 'conn' in locals():
            conn.close()

def is_user_allowed(username):
    """
    Check if a user is allowed to use the bot.
    """
    return username in ALLOWED_USERS

def update_authorized_chats():
    """
    Update the authorized chats in the database based on the ALLOWED_USERS list.
    """
    try:
        conn = sqlite3.connect('mail_bot.db')
        c = conn.cursor()
        
        # Get current users from database
        c.execute("SELECT username, chat_id FROM authorized_chats")
        db_users = {row[0]: row[1] for row in c.fetchall()}
        
        # Remove users that are in database but not in ALLOWED_USERS
        for username in list(db_users.keys()):
            if username not in ALLOWED_USERS:
                c.execute("DELETE FROM authorized_chats WHERE username = ?", (username,))
                logging.info(f"Removed unauthorized user {username} from database")
        
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating authorized chats: {str(e)}", exc_info=True)
    finally:
        if 'conn' in locals():
            conn.close()

def fetch_emails(max_retries=3, retry_delay=5):
    """
    Fetch new emails from the sent mail folder with improved connection handling.
    """
    logging.info("Starting to check sent mail")
    mailbox = None
    
    for attempt in range(max_retries):
        try:
            # Create new connection for each attempt
            if mailbox:
                try:
                    mailbox.logout()
                except:
                    pass
            
            mailbox = MailBox(IMAP_SERVER)
            mailbox.login(EMAIL, PASSWORD, initial_folder='[Gmail]/Отправленные')
            
            one_hour_ago = datetime.now() - timedelta(hours=1)
            messages = list(mailbox.fetch(A(date_gte=one_hour_ago.date())))
            
            for msg in messages:
                if is_email_processed(msg.uid):
                    continue

                if TO_EMAIL not in msg.to:
                    continue

                logging.info(f"Processing email: {msg.subject}")

                try:
                    has_image_attachment = False
                    for att in msg.attachments:
                        if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            has_image_attachment = True
                            filepath = os.path.join(PICTURES_FOLDER, att.filename)
                            with open(filepath, "wb") as f:
                                f.write(att.payload)
                            
                            logging.info(f"Saved image: {att.filename}")
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
                    
                    add_processed_email(msg.uid)
                except Exception as e:
                    logging.error(f"Error processing message {msg.uid}: {str(e)}", exc_info=True)
                    continue
            
            logging.info("Finished checking sent mail successfully")
            break

        except (imaplib.IMAP4.abort, imaplib.IMAP4.error, ConnectionError, EOFError, socket.error) as e:
            logging.error(f"IMAP error on attempt {attempt + 1}/{max_retries}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            logging.error("Max retries reached, giving up")
        except Exception as e:
            logging.error(f"Unexpected error while checking mail: {str(e)}", exc_info=True)
        finally:
            if mailbox:
                try:
                    mailbox.logout()
                except Exception as e:
                    logging.error(f"Error during mailbox logout: {str(e)}")

@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Handle the /start command for the Telegram bot.
    """
    username = f"@{message.from_user.username}" if message.from_user.username else None
    
    if not username:
        bot.reply_to(message, "Для использования бота необходимо иметь username в Telegram.")
        logging.warning(f"User without username attempted to start bot (chat_id: {message.chat.id})")
        return
    
    if is_user_allowed(username):
        try:
            conn = sqlite3.connect('mail_bot.db')
            c = conn.cursor()
            
            c.execute("SELECT chat_id, is_active FROM authorized_chats WHERE username = ?", (username,))
            existing_user = c.fetchone()
            
            if existing_user:
                c.execute("UPDATE authorized_chats SET chat_id = ?, is_active = 1 WHERE username = ?",
                         (message.chat.id, username))
                bot.reply_to(message, "Вы успешно переподключились к боту.")
            else:
                c.execute("INSERT INTO authorized_chats (chat_id, username, is_active) VALUES (?, ?, 1)",
                         (message.chat.id, username))
                bot.reply_to(message, "Вы успешно подписались на уведомления.")
            
            conn.commit()
            logging.info(f"User {username} (chat_id: {message.chat.id}) subscribed to notifications")
        except Exception as e:
            logging.error(f"Error handling start command: {str(e)}", exc_info=True)
            bot.reply_to(message, "Произошла ошибка при обработке команды.")
        finally:
            if 'conn' in locals():
                conn.close()
    else:
        bot.reply_to(message, "К сожалению, у Вас нет разрешения на использование этого бота.")
        logging.warning(f"Unauthorized subscription attempt by user {username} (chat_id: {message.chat.id})")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    """
    Handle the /stop command for the Telegram bot.
    """
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if is_user_allowed(username):
        add_or_update_chat(message.chat.id, username, 0)
        bot.reply_to(message, "Вы отписались от получения уведомлений.")
        logging.info(f"User {username} (chat_id: {message.chat.id}) unsubscribed from notifications")
    else:
        bot.reply_to(message, "К сожалению, у Вас нет разрешения на использование этого бота.")
        logging.warning(f"Unauthorized unsubscribe attempt by user {username} (chat_id: {message.chat.id})")

@bot.message_handler(func=lambda message: True)
def log_all_messages(message):
    """
    Log all received messages for debugging purposes.
    """
    username = f"@{message.from_user.username}" if message.from_user.username else None
    logging.info(f"Received message from user {username} (chat_id: {message.chat.id}): {message.text}")

def scheduled_check():
    """
    Perform a scheduled check of emails and update authorized chats with error handling.
    """
    try:
        update_authorized_chats()
        fetch_emails()
    except Exception as e:
        logging.error(f"Error in scheduled check: {str(e)}", exc_info=True)

def run_bot():
    """
    Main function to run the bot with improved error handling and reconnection logic.
    """
    logging.info("Bot started")
    
    while True:
        try:
            init_db()
            update_authorized_chats()
            
            # Clear any existing jobs to prevent duplicates
            schedule.clear()
            
            # Schedule the email check to run every minute
            schedule.every(1).minutes.do(scheduled_check)
            
            bot_thread = threading.Thread(target=bot.polling, args=(None, True))
            bot_thread.daemon = True
            bot_thread.start()
            
            while True:
                schedule.run_pending()
                time.sleep(1)
                
                # Check if bot thread is still alive
                if not bot_thread.is_alive():
                    logging.error("Bot thread died, restarting...")
                    raise Exception("Bot thread died")
                
        except Exception as e:
            logging.critical(f"Critical error in bot operation: {str(e)}", exc_info=True)
            time.sleep(10)  # Wait before attempting restart

if __name__ == "__main__":
    run_bot()