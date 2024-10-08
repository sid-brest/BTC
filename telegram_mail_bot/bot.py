import os
import imaplib
import email
from email.header import decode_header
import telebot
from dotenv import load_dotenv
import time
import logging
import schedule

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
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Создание папки для сохранения изображений
PICTURES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Pictures")
if not os.path.exists(PICTURES_FOLDER):
    os.makedirs(PICTURES_FOLDER)

# Создание файла для хранения обработанных ID писем
PROCESSED_EMAILS_FILE = 'processed_emails.txt'

def get_processed_emails():
    if os.path.exists(PROCESSED_EMAILS_FILE):
        with open(PROCESSED_EMAILS_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()

def add_processed_email(email_id):
    with open(PROCESSED_EMAILS_FILE, 'a') as f:
        f.write(f"{email_id}\n")

def fetch_emails():
    logging.info("Начало проверки отправленной почты")
    processed_emails = get_processed_emails()

    try:
        # Подключение к почтовому серверу
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select('"[Gmail]/Отправленные"')  # Выбор папки с отправленными письмами

        # Поиск писем за последную минуту
        _, message_numbers = mail.search(None, 'SINCE', (email.utils.formatdate(time.time() - 60)))

        for num in message_numbers[0].split():
            _, msg = mail.fetch(num, "(RFC822)")
            email_body = msg[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Получение ID письма
            email_id = email_message['Message-ID']
            
            if email_id in processed_emails:
                continue

            # Получение темы письма
            subject, encoding = decode_header(email_message["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")

            logging.info(f"Обработка письма: {subject}")

            # Обработка вложений
            for part in email_message.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                if part.get("Content-Disposition") is None:
                    continue

                filename = part.get_filename()
                if filename:
                    # Декодирование имени файла, если необходимо
                    filename, encoding = decode_header(filename)[0]
                    if isinstance(filename, bytes):
                        filename = filename.decode(encoding or "utf-8")

                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        # Сохранение изображения
                        filepath = os.path.join(PICTURES_FOLDER, filename)
                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        
                        logging.info(f"Сохранено изображение: {filename}")
                        
                        # Отправка изображения в Telegram
                        with open(filepath, "rb") as photo:
                            bot.send_photo(CHAT_ID, photo, caption=f"Тема: {subject}")
                        
                        logging.info(f"Отправлено изображение в Telegram: {filename}")

            # Добавление ID обработанного письма
            add_processed_email(email_id)

        mail.logout()
        logging.info("Проверка отправленной почты завершена")
    except Exception as e:
        logging.error(f"Ошибка при проверке почты: {str(e)}")

# Функция для запуска проверки почты по расписанию
def scheduled_check():
    fetch_emails()

# Настройка расписания проверки почты каждую минуту
schedule.every(1).minutes.do(scheduled_check)

# Команда для ручной проверки новых писем
@bot.message_handler(commands=['check_mail'])
def check_mail(message):
    bot.reply_to(message, "Проверяю почту...")
    fetch_emails()
    bot.reply_to(message, "Проверка завершена.")

# Функция для запуска бота и планировщика
def run_bot():
    logging.info("Бот запущен")
    while True:
        try:
            schedule.run_pending()
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logging.error(f"Ошибка в работе бота: {str(e)}")
            time.sleep(1)

if __name__ == "__main__":
    run_bot()