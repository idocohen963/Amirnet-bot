import requests

# נשתמש ב-Session כדי לשמור cookies אוטומטית
session = requests.Session()

# שלב 1: בקשה לאתר הראשי כדי לקבל cookies תקפים
main_url = "https://niteop.nite.org.il"
session.get(main_url)

# שלב 2: בקשה ל-API עם ה-cookies שנשמרו
api_url = "https://proxy.nite.org.il/net-registration/all-days?networkExamId=3"

headers = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://niteop.nite.org.il",
    "referer": "https://niteop.nite.org.il/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/139.0.0.0 Safari/537.36"
}

resp = session.get(api_url, headers=headers)

# שלב 3: בדיקה והצגת הטבלה
if resp.status_code == 200:
    data = resp.json()
    print("📅 טבלת התאריכים שהתקבלה:\n")
    for date, cities in data.items():
        print(f"{date}: {cities}")
else:
    print("שגיאה:", resp.status_code, resp.text)
