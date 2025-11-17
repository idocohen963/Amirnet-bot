# NITE Exam Checker Bot - AI Coding Agent Instructions

## Architecture Overview

This is a **dual-bot monitoring system** for NITE (Israeli National Institute for Testing and Evaluation) exam schedules:

1. **Client Bot** (`platforms/telegram/bot.py`) - Handles Telegram user registration and city subscription preferences via inline keyboards
2. **Checker Bot** (`nite_check.py`) - Polls NITE API every 2-4 minutes, detects exam changes, and sends notifications to subscribed users

Both bots run **in parallel processes** orchestrated by `main.py` using Python's `multiprocessing`. The system uses SQLite for state persistence and supports multi-platform notifications (Telegram active, WhatsApp placeholder).

## Core Data Flow

```
NITE API → Checker compares with DB → New exams detected → Query users by city → Send notifications (Telegram/WhatsApp) → Update DB
```

## Critical Configuration: City Mappings

**ALL city data is centralized in `config.py`**. The `CITIES` dictionary maps NITE API city IDs to:
- `name`: Hebrew display name
- `db_column`: SQLite column name in users/whatsapp_users tables
- `display_order`: UI sort order

```python
CITIES = {
    1: {"name": "חיפה", "db_column": "haifa", "display_order": 4},
    2: {"name": "תל אביב", "db_column": "tel_aviv", "display_order": 1},
    # ...
}
```

**To add a new city:**
1. Add entry to `config.CITIES` with correct NITE API ID
2. Add column to `users` and `whatsapp_users` tables: `ALTER TABLE users ADD COLUMN <db_column> INTEGER DEFAULT 0;`
3. No other code changes required - all functions use `config.py` helpers

## Database Schema (`database/db.py`)

Four tables managed by `database/db.py`:
- **exams**: Current state (exam_date, city_id, first_seen) - unique constraint on (exam_date, city_id)
- **exam_log**: Audit trail (event_type: 'CREATED'/'DELETED', event_timestamp)
- **users**: Telegram user subscriptions (user_id INTEGER, city columns as INTEGER 0/1)
- **whatsapp_users**: WhatsApp user subscriptions (user_id TEXT, city columns as INTEGER 0/1)

**Pattern**: User IDs are platform-specific types (Telegram: int, WhatsApp: str).

## Running the System

**Development (local):**
```bash
python3 main.py  # Runs both bots via multiprocessing
```

**Production (Docker):**
```bash
cd docker
docker-compose up -d --build  # Runs main.py in container
docker-compose logs -f        # View combined logs from both bots
```

**Environment requirements:**
- `.env` file with `TELEGRAM_TOKEN=<bot_token>` (or `TELEGRAM_TOKEN_TEST` for testing)
- Database file `exams_data.db` auto-created on first run
- Uses `data/` directory for volume persistence in Docker

## Debugging Commands

```bash
# View users and subscriptions
sqlite3 exams_data.db "SELECT * FROM users;"

# Check active exams
sqlite3 exams_data.db "SELECT exam_date, city_id FROM exams ORDER BY exam_date;"

# Audit exam changes
sqlite3 exams_data.db "SELECT * FROM exam_log ORDER BY event_timestamp DESC LIMIT 20;"

# Test in Docker container
docker exec -it nite_checker_bot python3 -c "from database.db import get_connection; print(list(get_connection().execute('SELECT * FROM users')))"
```

## Code Patterns & Conventions

### Hebrew RTL Text
All user-facing messages are in Hebrew. Use Unicode Hebrew characters directly in strings:
```python
msg = f"📢 מבחן חדש ב-{city_name}, בתאריך {date}"
```

### Error Resilience Philosophy
- **API failures don't crash the bot** - `fetch_exam_dates()` returns `{}` on error, loop continues
- **Message send failures are logged but non-fatal** - one user's error doesn't block others
- **Database initialization is idempotent** - `CREATE TABLE IF NOT EXISTS` safe to call repeatedly

### Dynamic SQL with Config Validation
DB queries use f-strings for column names, but ONLY with config-validated values:
```python
# SAFE: city_column comes from get_city_column() which validates against CITIES dict
conn.execute(f"SELECT user_id FROM users WHERE {city_column} = 1")
```

### Logging with Process Names
Multiprocessing logs include `%(processName)s` to distinguish ClientBot vs CheckerBot output:
```python
logging.basicConfig(format="%(asctime)s [%(levelname)s] [%(processName)s] %(message)s")
```

### Conversation State in Telegram Bot
Uses `ConversationHandler` with states (`START`, `CHOOSING_CITIES`) and stores temporary data in `context.user_data['selected_cities']` as a set.

## NITE API Integration (`nite_api.py`)

**Critical sequence:**
1. GET `niteop.nite.org.il` to establish session cookies
2. GET `proxy.nite.org.il/net-registration/all-days?networkExamId=3` with specific headers
3. Returns `{date: [city_ids]}` structure

**Important:** Uses `verify=False` to bypass SSL issues. Headers must include `origin`, `referer`, and `user-agent` to avoid rejection.

## Platform Expansion Pattern

WhatsApp support is architected but not implemented:
- Database schema exists (`whatsapp_users` table)
- `notifications.py` has `send_whatsapp_message()` stub
- `nite_check.py` queries both platforms
- **To activate:** Implement WhatsApp API client in `notifications.py` and set API credentials

## Common Pitfalls

1. **City ID ≠ Display Order**: NITE API uses non-sequential IDs (1,2,3,5). Never hardcode city IDs.
2. **Process isolation**: Each bot has separate Python interpreter. Shared state MUST go through database.
3. **Docker files location**: All Docker-related files are in `docker/` subdirectory. Run docker-compose from that directory.
4. **Database module path**: Import database operations from `database.db` not just `db`.

## Testing & Development

**No automated tests exist** - testing is manual via:
- Send `/start` to bot → verify DB entry created
- Manually trigger exam in API response → verify notification sent
- Check logs for error traces: `docker-compose logs -f` or `tail -f project.log`

**Development workflow:**
1. Edit code locally
2. Test with `python3 main.py` (requires `.env` with token)
3. Deploy: `git pull && docker-compose up -d --build` on server
4. Monitor: `docker-compose logs -f`

## Key Files Reference

- `config.py` - Single source of truth for cities, API URLs, intervals
- `database/db.py` - All SQLite operations with extensive docstrings
- `main.py` - Process orchestration entry point
- `nite_check.py` - Monitoring loop and change detection logic
- `platforms/telegram/bot.py` - User interaction and subscription management
- `notifications.py` - Message sending abstraction layer
- `docker/` - Docker configuration files (Dockerfile, docker-compose.yml, DOCKER_DEPLOY.md)
