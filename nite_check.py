
import time
import random
import logging
import requests

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
def process_new_dates(data, last_dates):
    messages = []
    current_dates = set(data.keys())
    new_dates = current_dates - last_dates

    for date in new_dates:
        cities = [CITY_MAPPING.get(c, f"עיר לא ידועה ({c})") for c in data[date]]
        city_names = ", ".join(cities)
        messages.append(f"📢 נוסף מבחן חדש ב-{city_names}, בתאריך {date}")

    return messages, current_dates

# ----------------
# לולאת הבדיקה
def run_checker():
    last_dates = set()
    logging.info("הבוט התחיל לעבוד")

    while True:
        data = fetch_dates()
        if not data:
            logging.warning("לא התקבלו נתונים")
        else:
            messages, current_dates = process_new_dates(data, last_dates)

            for msg in messages:
                logging.info(f"שולח הודעה: {msg}")
                send_telegram_message(msg)

            last_dates = current_dates

        # המתנה רנדומלית בין 2 ל־4 דקות
        wait_time = random.randint(15, 60)
        logging.info(f"המתנה {wait_time} שניות לסיבוב הבא...")
        time.sleep(wait_time)

# ----------------
if __name__ == "__main__":
    run_checker()
