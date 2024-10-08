import os
import imaplib
import email
from email.header import decode_header
import telebot
from dotenv import load_dotenv

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

def fetch_emails():
    # Подключение к почтовому серверу
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    # Поиск непрочитанных писем
    _, message_numbers = mail.search(None, "UNSEEN")

    for num in message_numbers[0].split():
        _, msg = mail.fetch(num, "(RFC822)")
        email_body = msg[0][1]
        email_message = email.message_from_bytes(email_body)

        # Получение темы письма
        subject, encoding = decode_header(email_message["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")

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
                    with open(filename, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    
                    # Отправка изображения в Telegram
                    with open(filename, "rb") as photo:
                        bot.send_photo(CHAT_ID, photo, caption=f"Тема: {subject}")
                    
                    # Удаление временного файла
                    os.remove(filename)

    mail.logout()

# Команда для проверки новых писем
@bot.message_handler(commands=['check_mail'])
def check_mail(message):
    bot.reply_to(message, "Проверяю почту...")
    fetch_emails()
    bot.reply_to(message, "Проверка завершена.")

# Запуск бота
bot.polling()