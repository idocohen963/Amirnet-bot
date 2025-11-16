# 🎓 NITE Exam Checker Bot

בוט טלגרם לניטור מבחני ניטע ושליחת התראות למשתמשים רשומים.

## 📋 תיאור

הפרויקט מורכב משני רכיבים עיקריים:
1. **בוט משתמשים** (`telegram_bot.py`) - מנהל רשימת משתמשים והעדפות ערים
2. **בוט מעקב** (`nite_check.py`) - סורק שינויים במערכת ניטע ושולח התראות

## 🏗️ מבנה הפרויקט

```
nite_checker/
├── main.py            # ⭐ נקודת כניסה - מריץ הכל
├── config.py          # קונפיגורציה מרכזית
├── db.py              # שכבת מסד נתונים
├── telegram_bot.py    # בוט Telegram לניהול משתמשים
├── nite_check.py      # בוט סריקת שינויים
├── nite_api.py        # לקוח API של NITE - משיכת מידע
├── notifications.py   # מודול שליחת התראות Telegram
├── requirements.txt   # תלויות Python
├── .env               # משתני סביבה (לא בגיט!)
└── exams_data.db      # מסד נתונים SQLite
```

## 🔧 התקנה

1. **שכפל את הפרויקט:**
```bash
git clone <repository-url>
cd nite_checker
```

2. **צור סביבה וירטואלית:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# או
.venv\Scripts\activate  # Windows
```

3. **התקן תלויות:**
```bash
pip install -r requirements.txt
```

4. **הגדר משתני סביבה:**
צור קובץ `.env` עם הטוקנים:
```
TELEGRAM_TOKEN=your_bot_token_here
```

## 🚀 הרצה

### 🐳 הרצה עם Docker (מומלץ לפרודקשן):

**הרצה מהירה:**
```bash
docker-compose up -d
```

**בדיקת סטטוס:**
```bash
docker-compose ps
docker-compose logs -f
```

**עצירת הבוט:**
```bash
docker-compose down
```

**בנייה מחדש אחרי שינויים:**
```bash
docker-compose up -d --build
```

### 🐍 הרצה ישירה עם Python:

**דרך מומלצת - הרצה אחת פשוטה:**
```bash
python3 main.py
```
זה מריץ את **שני הבוטים במקביל** (client + checker).

**דרך חלופית - הרצה נפרדת:**
אם אתה רוצה שליטה מלאה, הרץ כל בוט בטרמינל נפרד:

**טרמינל 1 - בוט משתמשים:**
```bash
python3 telegram_bot.py
```

**טרמינל 2 - בוט סריקה:**
```bash
python3 nite_check.py
```

## 🗺️ קונפיגורציה מרכזית

### **מיפוי ערים (`config.py`)**

כל המידע על ערים מרוכז בקובץ `config.py`:

```python
CITIES = {
    1: {"name": "חיפה", "db_column": "haifa", "display_order": 4},
    2: {"name": "תל אביב", "db_column": "tel_aviv", "display_order": 1},
    3: {"name": "ירושלים", "db_column": "jerusalem", "display_order": 3},
    5: {"name": "באר שבע", "db_column": "beer_sheva", "display_order": 2}
}
```

**המפתחות (1, 2, 3, 5) הם ה-city_id מה-API של ניטע!**

### פונקציות עזר:

- `get_city_name(city_id)` - מקבל שם עיר לפי ID
- `get_city_column(city_id)` - מקבל שם עמודה ב-DB לפי ID
- `get_city_options()` - מחזיר רשימה ממוינת של ערים לבוט
- `get_city_columns_map()` - מיפוי שמות ערים לעמודות DB


## 💾 מסד נתונים

### טבלאות:

1. **exams** - מבחנים פעילים נוכחיים
2. **exam_log** - היסטוריית שינויים (CREATED/DELETED)
3. **users** - משתמשים והעדפות ערים

### דוגמאות שאילתות:

```bash
# הצג את כל המשתמשים
sqlite3 exams_data.db "SELECT * FROM users;"

# הצג משתמשים שרשומים לתל אביב
sqlite3 exams_data.db "SELECT user_id FROM users WHERE tel_aviv = 1;"

# הצג מבחנים פעילים
sqlite3 exams_data.db "SELECT * FROM exams ORDER BY exam_date;"

# הצג היסטוריית שינויים
sqlite3 exams_data.db "SELECT * FROM exam_log ORDER BY event_timestamp DESC LIMIT 10;"
```

## 🔒 אבטחה

- **לעולם אל תעלה קובץ `.env` לגיט!**
- הקובץ `.gitignore` מוגדר לחסום אותו
- אם טוקן נחשף, בטל אותו מיד דרך BotFather

## 📊 תהליך הבוט

```
┌─────────────────┐
│  NITE API       │
│  (Every 2-4min) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  nite_api.py    │
│  (Fetches data) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  nite_check.py  │────▶│  exams DB    │
│  (Compares)     │     │  (State)     │
└────────┬────────┘     └──────────────┘
         │
         ▼
   ┌─────────────┐
   │  New exam?  │
   └──────┬──────┘
          │ Yes
          ▼
   ┌─────────────────┐
   │ Get users by    │
   │ city from DB    │
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ notifications.py│
   │ Send Telegram   │
   │ notifications   │
   └─────────────────┘
```

## 🏛️ ארכיטקטורה

הפרויקט מחולק למודולים עם אחריות ברורה:

- **`main.py`** - נקודת כניסה, מריץ שני תהליכים במקביל
- **`telegram_bot.py`** - בוט Telegram לניהול משתמשים והעדפות
- **`nite_check.py`** - לוגיקת ניטור והשוואה בין API למסד נתונים
- **`nite_api.py`** - לקוח API של NITE, אחראי על התחברות ומשיכת מידע
- **`notifications.py`** - מודול שליחת התראות Telegram
- **`db.py`** - שכבת מסד נתונים, כל הפעולות על SQLite
- **`config.py`** - הגדרות מרכזיות, מיפוי ערים וקונפיגורציה

## � פריסה בענן (Cloud Deployment)

**AWS (ECS/EC2):**
```bash
# Build and push to ECR
docker build -t nite-checker .
docker tag nite-checker:latest <aws-account>.dkr.ecr.region.amazonaws.com/nite-checker:latest
docker push <aws-account>.dkr.ecr.region.amazonaws.com/nite-checker:latest
```

### ⚠️ חשוב לפריסה בענן:
- וודא שקובץ `.env` קיים עם הטוקן
- השתמש ב-volumes לשמירת מסד הנתונים
- הגדר restart policy ל-`always` או `unless-stopped`
- הגדר monitoring ו-logging

## �🛠️ פתרון בעיות

### הבוט לא מגיב?
- **Docker**: `docker-compose logs -f` לבדיקת לוגים
- **Python**: בדוק שהטוקן ב-`.env` תקין
- ודא שהבוט רץ: `docker ps` או `ps aux | grep python`

### לא מגיעות התראות?
- בדוק שיש משתמשים רשומים: `sqlite3 exams_data.db "SELECT * FROM users;"`
- **Docker**: `docker exec -it nite_checker_bot python3 -c "from db import get_connection; print(list(get_connection().execute('SELECT * FROM users')))"`
- בדוק ש-`nite_check.py` רץ ברקע

### שגיאת import?
- ודא שכל הקבצים באותו תיקיה
- **Python**: `pip install -r requirements.txt`
- **Docker**: rebuild the image: `docker-compose up -d --build`

### בעיות עם מסד הנתונים?
- ודא שהתיקיה `data/` קיימת
- בדוק הרשאות: `chmod 777 data/`
- **Docker**: volume נוצר אוטומטית, בדוק עם `docker volume ls`

## 📝 רישיון

MIT License - השתמש בחופשיות!

## 👨‍💻 תמיכה

לבעיות או שאלות, פתח issue בגיטהאב.
