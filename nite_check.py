"""
This script monitors exam schedules and notifies users via Telegram about changes.
It fetches data from an API, compares it with the current database state, and sends
notifications for new or removed exams.

Modules:
    - time: For sleep intervals between checks.
    - random: To randomize sleep intervals.
    - logging: For logging messages.
    - requests: To interact with the API and Telegram.
    - dotenv: To load environment variables.
    - os: To access environment variables.
    - db: Custom module for database operations.

Usage:
    Run the script directly to start monitoring exam schedules.
"""

import time
import random
import logging
import requests
from dotenv import load_dotenv
import os
from db import (
    init_db,
    get_current_exams,
    add_exam,
    remove_exam
)

# Load environment variables from .env file
load_dotenv()

# ----------------
# Configuration and Constants
# ----------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CITY_MAPPING = {
    1: "חיפה",
    2: "תל אביב",
    3: "ירושלים",
    5: "באר שבע"
}

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("Missing TELEGRAM_TOKEN or CHAT_ID environment variables")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ----------------
# Utility Functions
# ----------------

# Sends a message to a specified Telegram chat.
# Args:
#     text (str): The message text to send.
# Raises:
#     requests.RequestException: If the message fails to send.
def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        logging.info("Message successfully sent to Telegram.")
    except requests.RequestException as e:
        logging.error(f"Failed to send message to Telegram: {e}")

# Fetches exam dates from the NITE API.
# Returns:
#     dict: A dictionary where keys are exam dates and values are lists of city IDs.
# Raises:
#     requests.RequestException: If the API request fails.
def fetch_dates():
    session = requests.Session()
    try:
        main_url = "https://niteop.nite.org.il"
        session.get(main_url, timeout=10)
        api_url = "https://proxy.nite.org.il/net-registration/all-days?networkExamId=3"
        headers = {
            "accept": "application/json, text/plain, */*",
            "origin": "https://niteop.nite.org.il",
            "referer": "https://niteop.nite.org.il/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/139.0.0.0 Safari/537.36"
        }
        resp = session.get(api_url, headers=headers, timeout=10, verify=False)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch dates: {e}")
        return {}

# ----------------
# Main Checker Logic
# ----------------

# Main loop to monitor and handle exam schedule changes.
# This function initializes the database, fetches data from the API, compares it
# with the current database state, and sends notifications for new or removed exams.
# It repeats the process at random intervals between 2 to 4 minutes.
def run_checker():
    # Initialize the database tables if they do not exist
    init_db()

    logging.info("Bot initialized and connected to SQLite database.")

    while True:
        api_data = fetch_dates()
        if not api_data:
            logging.warning("No data retrieved from the API.")
        else:
            # Parse API data into a set of tuples (date, city_id)
            current_pairs = set()
            for date, cities in api_data.items():
                for city_id in cities:
                    current_pairs.add((date, city_id))

            # Retrieve the current state of exams from the database
            existing_pairs = get_current_exams()

            # Identify new and removed exams
            new_exams = current_pairs - existing_pairs
            removed_exams = existing_pairs - current_pairs

            # Handle newly added exams
            if new_exams:
                logging.info(f"Detected {len(new_exams)} new exams.")
                for date, city_id in sorted(list(new_exams)):
                    city_name = CITY_MAPPING.get(city_id, f"עיר לא ידועה ({city_id})")
                    msg = f"📢 מבחן חדש ב-{city_name}, בתאריך {date}"
                    send_telegram_message(msg)
                    add_exam(date, city_id)
            
            # Handle removed exams
            if removed_exams:
                logging.info(f"Detected {len(removed_exams)} removed exams.")
                for date, city_id in removed_exams:
                    remove_exam(date, city_id)

            if not new_exams and not removed_exams:
                logging.info("No changes in the exam schedule.")

        # Wait between 2 to 4 minutes before the next check
        wait_time = random.randint(120, 240)
        logging.info(f"Sleeping for {wait_time} seconds before the next check...")
        time.sleep(wait_time)
# ----------------
if __name__ == "__main__":
    run_checker()