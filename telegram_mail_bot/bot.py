import os
import telebot
from dotenv import load_dotenv
import logging
import schedule
import time
from imap_tools import MailBox, A
from datetime import datetime, timedelta
import sqlite3
import threading

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройки для почты
IMAP_SERVER = "imap.gmail.com"
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")

# Настройки для Telegram бота
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

# Настройка логирования 
logging.basicConfig(filename='mail_bot.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    encoding='utf-8')

# Создание папки для сохранения изображений
PICTURES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Pictures")
if not os.path.exists(PICTURES_FOLDER):
    os.makedirs(PICTURES_FOLDER)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails
                 (email_id TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS authorized_chats
                 (chat_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

# Функции для работы с базой данных
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
    c.execute("SELECT chat_id FROM authorized_chats")
    chats = [row[0] for row in c.fetchall()]
    conn.close()
    return chats

def add_authorized_chat(chat_id):
    conn = sqlite3.connect('mail_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO authorized_chats (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

def fetch_emails():
    logging.info("Начало проверки отправленной почты")

    try:
        with MailBox(IMAP_SERVER).login(EMAIL, PASSWORD) as mailbox:
            mailbox.folder.set('[Gmail]/Отправленные')
            one_hour_ago = datetime.now() - timedelta(hours=1)
            for msg in mailbox.fetch(A(date_gte=one_hour_ago.date())):
                if is_email_processed(msg.uid):
                    continue

                logging.info(f"Обработка письма: {msg.subject}")

                for att in msg.attachments:
                    if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        filepath = os.path.join(PICTURES_FOLDER, att.filename)
                        with open(filepath, "wb") as f:
                            f.write(att.payload)
                        
                        logging.info(f"Сохранено изображение: {att.filename}")
                        
                        for chat_id in get_authorized_chats():
                            with open(filepath, "rb") as photo:
                                bot.send_photo(chat_id, photo, caption=f"Тема: {msg.subject}")
                        
                        logging.info(f"Отправлено изображение в Telegram: {att.filename}")

                add_processed_email(msg.uid)

        logging.info("Проверка отправленной почты завершена")
    except Exception as e:
        logging.error(f"Ошибка при проверке почты: {str(e)}", exc_info=True)

def scheduled_check():
    fetch_emails()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    add_authorized_chat(message.chat.id)
    bot.reply_to(message, "Чат авторизован для получения уведомлений.")

# Настройка расписания проверки почты каждую минуту
schedule.every(1).minutes.do(scheduled_check)

def run_bot():
    logging.info("Бот запущен")
    init_db()
    bot_thread = threading.Thread(target=bot.polling, args=(None, True))
    bot_thread.start()
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка в работе бота: {str(e)}")
            time.sleep(1)

if __name__ == "__main__":
    run_bot()