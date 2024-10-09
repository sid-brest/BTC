This script is a Telegram bot that monitors a Gmail account's sent folder for new emails with image attachments and forwards them to authorized Telegram users.
# Setting Up Mail Bot on Ubuntu Server
## 1. Create a Virtual Environment
Navigate to your project directory:
```bash
cd /path/to/your/project
```
Create a virtual environment:
```bash
python3 -m venv venv
```
Activate the virtual environment:
```bash
source venv/bin/activate
```
## 2. Install Required Modules
Install all necessary modules:
```bash
pip install python-dotenv pyTelegramBotAPI schedule imap_tools tenacity threading sqlite3 telebot
```
## 3. Set Up the .env File
Create a .env file in the same directory as the bot.py file:
```bash
touch .env
```
Fill the .env file with the following content:
```bash
EMAIL=youremailthere@gmail.com
EMAIL_PASSWORD=strongpassword
TELEGRAM_BOT_TOKEN=123456789:QWEEFHKFJFJJKLJKJFHHSF
ALLOWED_USERS=@telegramuser1,@telegramuser2
```
Make it secure:
```bash
chmod 600 .env
```
## 4. Run the Script as a Service on Ubuntu
Create a systemd service file:
```bash
sudo nano /etc/systemd/system/telegram-mail-bot.service 
```
Add the following content to the service file:
```bash
[Unit]
Description=Mail Bot Service
After=network.target

[Service]
ExecStart=/path/to/your/venv/bin/python /path/to/your/bot.py
WorkingDirectory=/path/to/your/project
User=your_username
Group=your_group
Restart=always

[Install]
WantedBy=multi-user.target
```
Save and exit the editor.
Reload systemd to recognize the new service:
```bash
sudo systemctl daemon-reload
```
Start the service:
```bash
sudo systemctl start telegram-mail-bot.service
```
Enable the service to start on boot:
```bash
sudo systemctl enable telegram-mail-bot.service
```
Check the status of the service:
```bash
sudo systemctl status telegram-mail-bot.service
```
To view logs:
```bash
journalctl -u telegram-mail-bot.service
```
## 5. Usage
Run the script:
```bash
systemctl start telegram-mail-bot.service
```
Start a chat with your Telegram bot and send the `/start` command to subscribe to notifications.
The bot will check for new emails every minute and forward any image attachments to subscribed users.
To stop receiving notifications, send the `/stop` command to the bot.
## 6. Features
- Monitors the Gmail sent folder for new emails
- Saves image attachments locally
- Forwards image attachments to authorized Telegram users
- Manages user subscriptions using SQLite database
- Logs activities for debugging and monitoring
## 7. Notes
- The script uses a SQLite database to store processed email IDs and authorized chat information.
- Ensure that your Gmail account has sufficient storage space for saving attachments.
- The bot will only process emails sent within the last hour to avoid duplicate processing.
## 8. Troubleshooting
If you encounter any issues, check the `mail_bot.log` file for error messages and debugging information.
# Telegram Mail Bot Monitor Script
This script monitors the activity of a Telegram mail bot service and restarts it if there's no log activity for 10 minutes.
## Setup
Save the script `telegram_mail_bot_monitor.py` into the same directory with previous script file.
Make the script executable:
```bash
chmod +x telegram_mail_bot_monitor.py
```
Ensure the `telegram-mail-bot.service` is properly configured in your system.

Create a systemd service file:
```bash
sudo nano /etc/systemd/system/telegram-mail-bot-monitor.service 
```

Add the following content to the service file:
```bash
[Unit]
Description=Mail Bot Service
After=network.target

[Service]
ExecStart=/path/to/your/venv/bin/python /path/to/your/bot.py
WorkingDirectory=/path/to/your/project
User=your_username
Group=your_group
Restart=always

[Install]
WantedBy=multi-user.target
```
Save and exit the editor.
Reload systemd to recognize the new service:
```bash
sudo systemctl daemon-reload
```
Start the service:
```bash
sudo systemctl start telegram-mail-bot-monitor.service
```
Enable the service to start on boot:
```bash
sudo systemctl enable telegram-mail-bot-monitor.service
```
Check the status of the service:
```bash
sudo systemctl status telegram-mail-bot-monitor.service
```
To view logs:
```bash
journalctl -u telegram-mail-bot-monitor.service
```
## Logs
The script generates logs in telegram-mail-bot-monitor.log in the same directory as the script.
Note
Ensure that the user running this script has the necessary permissions to restart the service and access the log files.