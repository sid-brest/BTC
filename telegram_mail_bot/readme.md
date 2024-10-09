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
bash

sudo nano /etc/systemd/system/mailbot.service

Add the following content to the service file:
ini

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

Save and exit the editor.

Reload systemd to recognize the new service:
bash

sudo systemctl daemon-reload

Start the service:
bash

sudo systemctl start mailbot

Enable the service to start on boot:
bash

sudo systemctl enable mailbot

Check the status of the service:
bash

sudo systemctl status mailbot

To view logs:
bash

journalctl -u mailbot

Note on Required Modules

Ensure your bot.py file includes these import statements:
python

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

These modules should all be installed by the pip command in step 2.