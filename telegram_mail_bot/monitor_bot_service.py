#!/usr/bin/env python3

import os
import time
import subprocess
import logging

# Get the directory of the script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging
LOG_FILE = os.path.join(SCRIPT_DIR, 'telegram-mail-bot-monitor.log')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename=LOG_FILE)

# Path to the log file we're monitoring
MAIL_BOT_LOG_FILE = os.path.join(SCRIPT_DIR, 'mail_bot.log')

# The name of the service we're monitoring
SERVICE_NAME = 'telegram-mail-bot.service'

def get_service_start_time():
    """Get the start time of the service."""
    try:
        result = subprocess.run(['systemctl', 'show', SERVICE_NAME, '--property=ActiveEnterTimestamp'],
                                capture_output=True, text=True, check=True)
        timestamp = result.stdout.split('=')[1].strip()
        return int(time.mktime(time.strptime(timestamp, '%a %Y-%m-%d %H:%M:%S %Z')))
    except Exception as e:
        logging.error(f"Error getting service start time: {e}")
        return None

def get_last_log_time():
    """Get the timestamp of the last log entry."""
    try:
        return os.path.getmtime(MAIL_BOT_LOG_FILE)
    except FileNotFoundError:
        logging.error(f"Log file not found: {MAIL_BOT_LOG_FILE}")
        return None

def restart_service():
    """Restart the service."""
    try:
        subprocess.run(['sudo', 'systemctl', 'restart', SERVICE_NAME], check=True)
        logging.info(f"Restarted {SERVICE_NAME}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to restart {SERVICE_NAME}: {e}")

def main():
    logging.info("Monitor script started")
    while True:
        service_start_time = get_service_start_time()
        last_log_time = get_last_log_time()

        if service_start_time is None or last_log_time is None:
            time.sleep(60)  # Wait for a minute and try again
            continue

        current_time = time.time()
        time_since_log = current_time - last_log_time
        time_since_start = current_time - service_start_time

        if time_since_log > 600 and time_since_start > 600:  # 10 minutes
            logging.warning(f"No log activity for {time_since_log:.2f} seconds. Restarting service.")
            restart_service()
        
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()