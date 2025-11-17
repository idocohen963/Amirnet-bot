# 🎓 NITE Exam Checker Bot

A Telegram bot for monitoring NITE exams and sending notifications to registered users.

## 📋 Description

The project consists of two main components running in parallel:
1. **Client Bot** (`platforms/telegram/bot.py`) - Manages user registrations and city preferences through an inline keyboard interface
2. **Checker Bot** (`nite_check.py`) - Polls NITE system for changes every 2-4 minutes and sends notifications

Both bots run in separate processes via `main.py` using Python's `multiprocessing`.

## 🏗️ Project Structure

```
nite_checker/
├── main.py                    # ⭐ Entry point - runs both bots in parallel
├── config.py                  # Central configuration - city mappings, URLs, constants
├── nite_check.py              # Change scanner bot - main monitoring loop
├── nite_api.py                # NITE API client - connection and data retrieval
├── notifications.py           # Message sending layer (Telegram + WhatsApp placeholder)
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not in git!)
├── .gitignore                 # Files to ignore in git
├── .dockerignore              # Files to ignore in Docker build
├── exams_data.db              # SQLite database (created automatically)
│
│
├── database/
│   ├── __init__.py
│   └── db.py                  # Database layer - all SQLite operations
│
├── platforms/
│   ├── __init__.py
│   ├── telegram/
│   │   ├── __init__.py
│   │   └── bot.py             # Telegram bot for user management
│   └── whatsapp/
│       └── __init__.py        # WhatsApp placeholder (future)
│
└── docker/
    ├── Dockerfile             # Docker image definition
    ├── docker-compose.yml     # Docker Compose configuration
    └── DOCKER_DEPLOY.md       # Detailed deployment guide
```

## 🔧 Installation

### 1. Clone the project
```bash
git clone <repository-url>
cd nite_checker
```

### 2. Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the root directory:
```bash
TELEGRAM_TOKEN=your_bot_token_here
```

**Getting a bot token:**
1. Open a chat with [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot` and follow the instructions
3. Copy the received token to the `.env` file

## 🚀 Running

### 🐍 Direct Python execution (recommended for development)

```bash
# Make sure virtual environment is active
source .venv/bin/activate

# Run both bots
python3 main.py
```

**Stop:** `Ctrl+C`

### 🐳 Running with Docker (recommended for production)

**Quick start:**
```bash
cd docker
docker-compose up -d --build
```

**Check status:**
```bash
cd docker
docker-compose ps
docker-compose logs -f
```

**Stop the bot:**
```bash
cd docker
docker-compose down
```

**Update after changes:**
```bash
cd docker
git pull
docker-compose up -d --build
```

**For full Docker and cloud deployment details:** see `docker/DOCKER_DEPLOY.md`

## 🗺️ Central Configuration

### **City Mapping (`config.py`)**

All city information is centralized in `config.py`:

```python
CITIES = {
    1: {"name": "חיפה", "db_column": "haifa", "display_order": 4},
    2: {"name": "תל אביב", "db_column": "tel_aviv", "display_order": 1},
    3: {"name": "ירושלים", "db_column": "jerusalem", "display_order": 3},
    5: {"name": "באר שבע", "db_column": "beer_sheva", "display_order": 2}
}
```

**The keys (1, 2, 3, 5) are the city_id values from the NITE API!**

### Helper functions in `config.py`:

- `get_city_name(city_id)` - Get city name by ID
- `get_city_column(city_id)` - Get DB column name by ID
- `get_city_options()` - Returns sorted list of cities for bot
- `get_city_columns_map()` - Mapping of city names to DB columns


## 💾 Database

### Tables (`database/db.py`):

1. **exams** - Current active exams
   - `id`, `exam_date`, `city_id`, `first_seen`
   - UNIQUE constraint on `(exam_date, city_id)`

2. **exam_log** - Change history
   - `log_id`, `exam_date`, `city_id`, `event_type` (CREATED/DELETED), `event_timestamp`

3. **users** - Telegram users and city preferences
   - `user_id` (INTEGER), `tel_aviv`, `beer_sheva`, `jerusalem`, `haifa`

4. **whatsapp_users** - WhatsApp users and city preferences (future)
   - `user_id` (TEXT), `tel_aviv`, `beer_sheva`, `jerusalem`, `haifa`

### Query examples:

```bash
# Show all users
sqlite3 exams_data.db "SELECT * FROM users;"

# Show users registered for Tel Aviv
sqlite3 exams_data.db "SELECT user_id FROM users WHERE tel_aviv = 1;"

# Show active exams
sqlite3 exams_data.db "SELECT * FROM exams ORDER BY exam_date;"

# Show change history (last 20)
sqlite3 exams_data.db "SELECT * FROM exam_log ORDER BY event_timestamp DESC LIMIT 20;"

```

## 🔐 Security

- **Never upload `.env` file to git!**
- The `.gitignore` file is configured to block it
- If a token is exposed, revoke it immediately via [@BotFather](https://t.me/BotFather)
- The `.dockerignore` file prevents copying sensitive files to Docker image

## 📊 Bot Workflow

```
┌─────────────────────┐
│  NITE API           │
│  (every 2-4 min)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌──────────────────┐
│  nite_check.py      │────▶│  exams DB        │
│  (compares)         │     │  (current state) │
└──────────┬──────────┘     └──────────────────┘
           │
           ▼
    ┌─────────────┐
    │  New exam?  │
    └──────┬──────┘
           │ yes
           ▼
    ┌─────────────────────┐
    │ Query users by      │
    │ city from DB        │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ Send notifications  │
    │ (Telegram/WhatsApp) │
    └─────────────────────┘
```

## 🌐 Cloud Deployment

### Platform Support:

- **AWS** (ECS, EC2, Lightsail)
- **Google Cloud** (Cloud Run, Compute Engine)
- **Azure** (Container Instances, VMs)
- **DigitalOcean** (Droplets, App Platform)

**For detailed guide:** see `docker/DOCKER_DEPLOY.md`

## 🛠️ Troubleshooting

### Bot not responding?

**Python:**
```bash
# Verify the token is valid
cat .env | grep TELEGRAM_TOKEN

# Verify the bot is running
ps aux | grep python3

# Check logs
tail -f project.log
```

**Docker:**
```bash
cd docker

# Check container status
docker-compose ps

# Tail logs in real time
docker-compose logs -f

# Inspect processes in container
docker exec -it nite_checker_bot ps aux
```

### Not receiving notifications?

```bash
# Ensure there are registered users
sqlite3 exams_data.db "SELECT * FROM users;"

# Check via Docker
docker exec -it nite_checker_bot python3 -c "from database.db import get_connection; print(list(get_connection().execute('SELECT * FROM users')))"

# Verify the Checker bot is running
ps aux | grep nite_check  # or
docker-compose logs -f | grep CheckerBot
```

### Import error?

**Python:**
```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Ensure the virtual environment is active
which python3  # should point to .venv
```

**Docker:**
```bash
cd docker
docker-compose up -d --build  # rebuild the image
```

### Database issues?

```bash
# Check that the file exists
ls -lh exams_data.db

# Check permissions
chmod 666 exams_data.db

# Reinitialize the database (caution — deletes data!)
rm exams_data.db
python3 -c "from database.db import init_db; init_db()"
```

**In Docker:**
```bash
cd docker

# Check volume
docker volume ls | grep nite

# Remove volume and reinitialize (caution!)
docker-compose down -v
docker-compose up -d --build
```


## 📝 License

MIT License — use freely!

## 👨‍💻 Support

For issues or questions, open a GitHub issue or contact the project maintainer.

---

