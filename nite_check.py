import time
import random
import logging
import requests
import json
import os

# ----------------
# פרטי טלגרם (קשיחים בקוד כמו שביקשת)
TELEGRAM_TOKEN = "token"
CHAT_ID = "1152610979"

# ----------------
# לוגים
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ----------------
# קובץ סטייט
STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"שגיאה בקריאת state.json: {e}")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"שגיאה בכתיבה ל-state.json: {e}")

# ----------------
# שליחת הודעה לטלגרם
def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        logging.info("נשלחה הודעה לטלגרם בהצלחה")
    except requests.RequestException as e:
        logging.error(f"שגיאה בשליחת הודעה לטלגרם: {e}")

# ----------------
# שליפת נתונים מהאתר
def fetch_dates():
    session = requests.Session()
    try:
        # שלב 1 – פתיחת האתר כדי לקבל cookies
        main_url = "https://niteop.nite.org.il"
        session.get(main_url, timeout=10)

        # שלב 2 – בקשה ל־API עם ה־cookies
        api_url = "https://proxy.nite.org.il/net-registration/all-days?networkExamId=3"
        headers = {
            "accept": "application/json, text/plain, */*",
            "origin": "https://niteop.nite.org.il",
            "referer": "https://niteop.nite.org.il/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/139.0.0.0 Safari/537.36"
        }

        resp = session.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as e:
        logging.error(f"שגיאה בשליפת נתונים: {e}")
        return {}

# ----------------
# מיפוי ערים
CITY_MAPPING = {
    1: "חיפה",
    2: "תל אביב",
    3: "ירושלים",
    5: "באר שבע"
}

# ----------------
# עיבוד נתונים
def process_new_data(current_data, last_data):
    messages = []

    for date, cities in current_data.items():
        old_cities = set(last_data.get(date, []))
        new_cities = set(cities) - old_cities

        if date not in last_data:
            # תאריך חדש לגמרי
            city_names = ", ".join(CITY_MAPPING.get(c, f"עיר לא ידועה ({c})") for c in cities)
            messages.append(f"📢 נוסף מבחן חדש ב-{city_names}, בתאריך {date}")
        elif new_cities:
            # תאריך קיים אבל נוספו בו ערים חדשות
            city_names = ", ".join(CITY_MAPPING.get(c, f"עיר לא ידועה ({c})") for c in new_cities)
            messages.append(f"📢 נוספו ערים חדשות למבחן בתאריך {date}: {city_names}")

    return messages

# ----------------
# לולאת הבדיקה
def run_checker():
    last_data = load_state()
    logging.info("הבוט התחיל לעבוד")

    while True:
        current_data = fetch_dates()
        if not current_data:
            logging.warning("לא התקבלו נתונים")
        else:
            messages = process_new_data(current_data, last_data)

            for msg in messages:
                logging.info(f"שולח הודעה: {msg}")
                send_telegram_message(msg)

            if current_data != last_data:
                save_state(current_data)
                last_data = current_data

        # המתנה רנדומלית בין 2 ל־4 דקות
        wait_time = random.randint(120, 240)
        logging.info(f"המתנה {wait_time} שניות לסיבוב הבא...")
        time.sleep(wait_time)

# ----------------
if __name__ == "__main__":
    run_checker()
