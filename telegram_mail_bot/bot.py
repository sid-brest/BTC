import os
import telebot
from dotenv import load_dotenv
import logging
import schedule
import time
from imap_tools import MailBox, A
from datetime import datetime, timedelta

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройки для почты
IMAP_SERVER = "imap.gmail.com"
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")

# Настройки для Telegram бота
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telebot.TeleBot(BOT_TOKEN)

# Настройка логирования 
logging.basicConfig(filename='mail_bot.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    encoding='utf-8')

# Создание папки для сохранения изображений
PICTURES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Pictures")
if not os.path.exists(PICTURES_FOLDER):
    os.makedirs(PICTURES_FOLDER)

# Создание файла для хранения обработанных ID писем
PROCESSED_EMAILS_FILE = 'processed_emails.txt'

def get_processed_emails():
    if os.path.exists(PROCESSED_EMAILS_FILE):
        with open(PROCESSED_EMAILS_FILE, 'r', encoding='utf-8') as f:
            return set(f.read().splitlines())
    return set()

def add_processed_email(email_id):
    with open(PROCESSED_EMAILS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{email_id}\n")

def fetch_emails():
    logging.info("Начало проверки отправленной почты")
    processed_emails = get_processed_emails()

    try:
        with MailBox(IMAP_SERVER).login(EMAIL, PASSWORD) as mailbox:
            mailbox.folder.set('[Gmail]/Отправленные')
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            for msg in mailbox.fetch(A(date_gte=one_minute_ago.date())):
                if msg.uid in processed_emails:
                    continue

                logging.info(f"Обработка письма: {msg.subject}")

                for att in msg.attachments:
                    if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        filepath = os.path.join(PICTURES_FOLDER, att.filename)
                        with open(filepath, "wb") as f:
                            f.write(att.payload)
                        
                        logging.info(f"Сохранено изображение: {att.filename}")
                        
                        with open(filepath, "rb") as photo:
                            bot.send_photo(CHAT_ID, photo, caption=f"Тема: {msg.subject}")
                        
                        logging.info(f"Отправлено изображение в Telegram: {att.filename}")

                add_processed_email(msg.uid)

        logging.info("Проверка отправленной почты завершена")
    except Exception as e:
        logging.error(f"Ошибка при проверке почты: {str(e)}", exc_info=True)

def scheduled_check():
    fetch_emails()

# Настройка расписания проверки почты каждую минуту
schedule.every(1).minutes.do(scheduled_check)

def run_bot():
    logging.info("Бот запущен")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка в работе бота: {str(e)}")
            time.sleep(1)

if __name__ == "__main__":
    run_bot()