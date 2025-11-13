# מדריך מימוש - Refactoring Guide
## Practical Implementation Guide

מדריך זה מציג דוגמאות קוד קונקרטיות למימוש הארכיטקטורה המודולרית.

---

## 📁 שלב 1: יצירת מבנה תיקיות

```bash
mkdir -p platforms/telegram platforms/whatsapp platforms/email
mkdir -p services db/repositories core config
```

---

## 🔧 שלב 2: Base Classes

### `platforms/base.py`

```python
"""Abstract base classes for all messaging platforms"""
from abc import ABC, abstractmethod
from typing import Optional

class PlatformClient(ABC):
    """
    Base class for interactive bots (user registration, commands)
    Each platform (Telegram, WhatsApp) implements this interface
    """
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform identifier: 'telegram', 'whatsapp', etc."""
        pass
    
    @abstractmethod
    def start_bot(self) -> None:
        """Start listening for user messages"""
        pass
    
    @abstractmethod
    def stop_bot(self) -> None:
        """Gracefully stop the bot"""
        pass


class PlatformMessenger(ABC):
    """
    Base class for one-way messaging (notifications only)
    Simpler than PlatformClient - no user interaction needed
    """
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        pass
    
    @abstractmethod
    def send_notification(self, platform_user_id: str, message: str) -> bool:
        """
        Send notification to user
        
        Args:
            platform_user_id: User ID as known by the platform (e.g., Telegram chat_id)
            message: Message text to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
```

---

## 📱 שלב 3: יישום Telegram

### `platforms/telegram/client.py`

```python
"""Telegram platform client - handles user registration and commands"""
import os
import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, 
    CallbackQueryHandler, ContextTypes
)

from platforms.base import PlatformClient
from services.user_service import UserService
from config import get_city_options

logger = logging.getLogger(__name__)

START, CHOOSING_CITIES = range(2)

class TelegramClient(PlatformClient):
    """Telegram bot for user registration and city selection"""
    
    def __init__(self, token: str, user_service: UserService):
        if not token:
            raise ValueError("Telegram token is required")
        
        self.token = token
        self.user_service = user_service
        self.application: Optional[Application] = None
        self.city_options = get_city_options()
    
    @property
    def platform_name(self) -> str:
        return "telegram"
    
    def start_bot(self) -> None:
        """Initialize and start Telegram bot"""
        self.application = Application.builder().token(self.token).build()
        
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self._handle_start)],
            states={
                CHOOSING_CITIES: [CallbackQueryHandler(self._handle_callback)]
            },
            fallbacks=[CommandHandler("cancel", self._handle_cancel)],
        )
        
        self.application.add_handler(conv_handler)
        logger.info("Telegram bot started")
        self.application.run_polling()
    
    def stop_bot(self) -> None:
        """Stop Telegram bot gracefully"""
        if self.application:
            self.application.stop()
            logger.info("Telegram bot stopped")
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command"""
        user = update.effective_user
        platform_user_id = str(user.id)
        
        # Register user via service (platform-agnostic)
        self.user_service.register_user(
            platform=self.platform_name,
            platform_user_id=platform_user_id
        )
        
        context.user_data['selected_cities'] = set()
        
        await update.message.reply_text("ברוך הבא לבוט שלי 👋")
        await update.message.reply_text(
            "בחר ערים שעליהן תרצה לקבל התראות:",
            reply_markup=self._build_city_keyboard()
        )
        
        return CHOOSING_CITIES
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        selected_cities = context.user_data.setdefault('selected_cities', set())
        
        if data.startswith("city_"):
            city = data[5:]
            if city in selected_cities:
                selected_cities.remove(city)
            else:
                selected_cities.add(city)
            await query.edit_message_reply_markup(
                reply_markup=self._build_city_keyboard(selected_cities)
            )
        
        elif data == "continue":
            if not selected_cities:
                await query.edit_message_text("לא נבחרו ערים. אנא בחר לפחות עיר אחת.")
                return CHOOSING_CITIES
            
            # Update preferences via service
            platform_user_id = str(update.effective_user.id)
            self.user_service.update_user_preferences(
                platform=self.platform_name,
                platform_user_id=platform_user_id,
                city_names=list(selected_cities)
            )
            
            await query.edit_message_text(
                f"הערים שנבחרו: {', '.join(selected_cities)}.\nההגדרות נשמרו בהצלחה ✅"
            )
            return ConversationHandler.END
        
        return CHOOSING_CITIES
    
    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command"""
        await update.message.reply_text("הפעולה בוטלה.")
        return ConversationHandler.END
    
    def _build_city_keyboard(self, selected_cities: set = None) -> InlineKeyboardMarkup:
        """Build city selection keyboard"""
        selected_cities = selected_cities or set()
        keyboard = [
            [InlineKeyboardButton(
                f"{'✅ ' if c in selected_cities else ''}{c}",
                callback_data=f"city_{c}"
            )]
            for c in self.city_options
        ]
        keyboard.append([InlineKeyboardButton("המשך", callback_data="continue")])
        return InlineKeyboardMarkup(keyboard)
```

### `platforms/telegram/messenger.py`

```python
"""Telegram messenger - handles one-way notifications"""
import os
import logging
import requests
from typing import Optional

from platforms.base import PlatformMessenger

logger = logging.getLogger(__name__)

class TelegramMessenger(PlatformMessenger):
    """Send Telegram notifications (no user interaction)"""
    
    def __init__(self, token: str):
        if not token:
            raise ValueError("Telegram token is required")
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    @property
    def platform_name(self) -> str:
        return "telegram"
    
    def send_notification(self, platform_user_id: str, message: str) -> bool:
        """
        Send notification via Telegram Bot API
        
        Args:
            platform_user_id: Telegram chat_id (as string)
            message: Message text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"chat_id": platform_user_id, "text": message}
            resp = requests.post(self.api_url, data=payload, timeout=10)
            resp.raise_for_status()
            logger.debug(f"Telegram message sent to {platform_user_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message to {platform_user_id}: {e}")
            return False
```

---

## 🗄️ שלב 4: Repository Pattern

### `db/repositories/user_repository.py`

```python
"""User data access layer"""
import sqlite3
import logging
from typing import Optional, List, Dict
from config import DB_FILE

logger = logging.getLogger(__name__)

class UserRepository:
    """Repository for user data operations"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_file)
    
    def add_user(self, platform: str, platform_user_id: str) -> int:
        """
        Add user or return existing user's internal ID
        
        Args:
            platform: Platform name ('telegram', 'whatsapp', etc.)
            platform_user_id: User ID from platform
            
        Returns:
            Internal user_id (primary key)
        """
        with self._get_connection() as conn:
            # Try to get existing user
            cursor = conn.execute(
                "SELECT id FROM users WHERE platform = ? AND platform_user_id = ?",
                (platform, platform_user_id)
            )
            row = cursor.fetchone()
            
            if row:
                return row[0]
            
            # Create new user
            cursor = conn.execute(
                "INSERT INTO users (platform, platform_user_id) VALUES (?, ?)",
                (platform, platform_user_id)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_user_id(self, platform: str, platform_user_id: str) -> Optional[int]:
        """Get internal user_id from platform-specific ID"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM users WHERE platform = ? AND platform_user_id = ?",
                (platform, platform_user_id)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    def get_user_platform_info(self, user_id: int) -> Dict[str, str]:
        """Get platform and platform_user_id for a user"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT platform, platform_user_id FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {"platform": row[0], "platform_user_id": row[1]}
            return {}
```

### `db/repositories/subscription_repository.py`

```python
"""Subscription data access layer"""
import sqlite3
import logging
from typing import List, Dict
from config import DB_FILE, get_city_columns_map

logger = logging.getLogger(__name__)

class SubscriptionRepository:
    """Repository for user subscription operations"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
    
    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_file)
    
    def update_user_subscriptions(self, user_id: int, city_names: List[str]) -> None:
        """
        Update user's city subscriptions
        
        Args:
            user_id: Internal user ID
            city_names: List of Hebrew city names to subscribe to
        """
        # Get city_id for each city name
        city_columns_map = get_city_columns_map()
        from config import CITIES
        
        # Map city names to city_ids
        city_ids = []
        for city_name in city_names:
            for city_id, city_info in CITIES.items():
                if city_info["name"] == city_name:
                    city_ids.append(city_id)
                    break
        
        with self._get_connection() as conn:
            # Remove all existing subscriptions
            conn.execute("DELETE FROM user_subscriptions WHERE user_id = ?", (user_id,))
            
            # Add new subscriptions
            for city_id in city_ids:
                conn.execute(
                    "INSERT INTO user_subscriptions (user_id, city_id) VALUES (?, ?)",
                    (user_id, city_id)
                )
            
            conn.commit()
    
    def get_users_by_city(self, city_id: int) -> List[Dict[str, str]]:
        """
        Get all users subscribed to a city
        
        Returns:
            List of dicts with 'user_id', 'platform', 'platform_user_id'
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT u.id, u.platform, u.platform_user_id
                FROM users u
                INNER JOIN user_subscriptions us ON u.id = us.user_id
                WHERE us.city_id = ?
            """, (city_id,))
            
            return [
                {
                    "user_id": row[0],
                    "platform": row[1],
                    "platform_user_id": row[2]
                }
                for row in cursor.fetchall()
            ]
```

---

## 🎯 שלב 5: Service Layer

### `services/user_service.py`

```python
"""User management business logic"""
import logging
from typing import List
from db.repositories.user_repository import UserRepository
from db.repositories.subscription_repository import SubscriptionRepository

logger = logging.getLogger(__name__)

class UserService:
    """Business logic for user operations"""
    
    def __init__(
        self,
        user_repo: UserRepository,
        subscription_repo: SubscriptionRepository
    ):
        self.user_repo = user_repo
        self.subscription_repo = subscription_repo
    
    def register_user(self, platform: str, platform_user_id: str) -> int:
        """
        Register new user or return existing user ID
        
        Args:
            platform: Platform identifier
            platform_user_id: User ID from platform
            
        Returns:
            Internal user_id
        """
        user_id = self.user_repo.add_user(platform, platform_user_id)
        logger.info(f"User registered: {platform}:{platform_user_id} -> user_id={user_id}")
        return user_id
    
    def update_user_preferences(
        self,
        platform: str,
        platform_user_id: str,
        city_names: List[str]
    ) -> bool:
        """
        Update user's city subscription preferences
        
        Args:
            platform: Platform identifier
            platform_user_id: User ID from platform
            city_names: List of Hebrew city names
            
        Returns:
            True if successful
        """
        user_id = self.user_repo.get_user_id(platform, platform_user_id)
        if not user_id:
            logger.warning(f"User not found: {platform}:{platform_user_id}")
            return False
        
        self.subscription_repo.update_user_subscriptions(user_id, city_names)
        logger.info(f"Updated preferences for user_id={user_id}: {city_names}")
        return True
```

### `services/notification_service.py`

```python
"""Centralized notification service"""
import logging
from typing import Dict
from platforms.base import PlatformMessenger
from db.repositories.subscription_repository import SubscriptionRepository
from db.repositories.user_repository import UserRepository
from config import get_city_name

logger = logging.getLogger(__name__)

class NotificationService:
    """Send notifications across all platforms"""
    
    def __init__(
        self,
        messengers: Dict[str, PlatformMessenger],
        subscription_repo: SubscriptionRepository,
        user_repo: UserRepository
    ):
        self.messengers = messengers
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo
    
    def notify_users_about_exam(self, city_id: int, exam_date: str) -> None:
        """
        Notify all users subscribed to a city about a new exam
        
        Args:
            city_id: NITE API city ID
            exam_date: Exam date (YYYY-MM-DD)
        """
        city_name = get_city_name(city_id)
        message = f"📢 מבחן חדש ב-{city_name}, בתאריך {exam_date}"
        
        # Get all users subscribed to this city
        users = self.subscription_repo.get_users_by_city(city_id)
        
        if not users:
            logger.info(f"No users subscribed to city_id={city_id} ({city_name})")
            return
        
        # Send notification via appropriate platform
        success_count = 0
        for user_info in users:
            platform = user_info["platform"]
            platform_user_id = user_info["platform_user_id"]
            
            messenger = self.messengers.get(platform)
            if not messenger:
                logger.warning(f"No messenger available for platform: {platform}")
                continue
            
            if messenger.send_notification(platform_user_id, message):
                success_count += 1
        
        logger.info(
            f"Notified {success_count}/{len(users)} users about exam "
            f"in {city_name} on {exam_date}"
        )
```

---

## 🔄 שלב 6: Core Checker (ללא תלות בפלטפורמה)

### `core/checker.py`

```python
"""Core exam monitoring logic (platform-agnostic)"""
import time
import random
import logging
from services.notification_service import NotificationService
from db.repositories.exam_repository import ExamRepository
from config import (
    CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX,
    NITE_MAIN_URL, NITE_API_URL, NITE_API_HEADERS, REQUEST_TIMEOUT
)
import requests

logger = logging.getLogger(__name__)

class ExamChecker:
    """Monitor NITE API and notify about changes"""
    
    def __init__(
        self,
        exam_repo: ExamRepository,
        notification_service: NotificationService
    ):
        self.exam_repo = exam_repo
        self.notification_service = notification_service
    
    def fetch_exam_data(self) -> dict:
        """Fetch current exam schedule from NITE API"""
        session = requests.Session()
        try:
            session.get(NITE_MAIN_URL, timeout=REQUEST_TIMEOUT)
            resp = session.get(
                NITE_API_URL,
                headers=NITE_API_HEADERS,
                timeout=REQUEST_TIMEOUT,
                verify=False
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch exam data: {e}")
            return {}
    
    def check_for_changes(self) -> None:
        """Check API for changes and notify users"""
        api_data = self.fetch_exam_data()
        if not api_data:
            logger.warning("No data retrieved from API")
            return
        
        # Parse API data
        current_pairs = set()
        for date, cities in api_data.items():
            for city_id in cities:
                current_pairs.add((date, city_id))
        
        # Get existing exams from DB
        existing_pairs = self.exam_repo.get_current_exams()
        
        # Find differences
        new_exams = current_pairs - existing_pairs
        removed_exams = existing_pairs - current_pairs
        
        # Handle new exams
        for date, city_id in sorted(new_exams):
            self.notification_service.notify_users_about_exam(city_id, date)
            self.exam_repo.add_exam(date, city_id)
            logger.info(f"Added new exam: {date}, city_id={city_id}")
        
        # Handle removed exams
        for date, city_id in removed_exams:
            self.exam_repo.remove_exam(date, city_id)
            logger.info(f"Removed exam: {date}, city_id={city_id}")
        
        if not new_exams and not removed_exams:
            logger.info("No changes detected")
    
    def run(self) -> None:
        """Main monitoring loop"""
        logger.info("Exam checker started")
        
        while True:
            try:
                self.check_for_changes()
            except Exception as e:
                logger.error(f"Error in check cycle: {e}", exc_info=True)
            
            wait_time = random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX)
            logger.info(f"Sleeping for {wait_time} seconds...")
            time.sleep(wait_time)
```

---

## 🚀 שלב 7: Main Entry Point (עדכון)

### `main.py` (עדכון)

```python
"""Main entry point - orchestrates all services and platforms"""
import os
import sys
import logging
import multiprocessing
from dotenv import load_dotenv

# Import services
from services.user_service import UserService
from services.notification_service import NotificationService

# Import repositories
from db.repositories.user_repository import UserRepository
from db.repositories.subscription_repository import SubscriptionRepository
from db.repositories.exam_repository import ExamRepository

# Import platforms
from platforms.telegram.client import TelegramClient
from platforms.telegram.messenger import TelegramMessenger

# Import core
from core.checker import ExamChecker
from db import init_db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(processName)s] %(message)s"
)
logger = logging.getLogger(__name__)


def run_client_bots():
    """Run all platform client bots"""
    # Initialize repositories
    user_repo = UserRepository()
    subscription_repo = SubscriptionRepository()
    
    # Initialize services
    user_service = UserService(user_repo, subscription_repo)
    
    # Initialize platform clients
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    if not telegram_token:
        raise ValueError("TELEGRAM_TOKEN not set")
    
    telegram_client = TelegramClient(telegram_token, user_service)
    
    # Start all clients (currently just Telegram)
    # In future: add WhatsApp, etc.
    try:
        telegram_client.start_bot()
    except Exception as e:
        logger.error(f"Client bot crashed: {e}", exc_info=True)
        sys.exit(1)


def run_checker_bot():
    """Run exam checker with notification service"""
    # Initialize repositories
    exam_repo = ExamRepository()
    subscription_repo = SubscriptionRepository()
    user_repo = UserRepository()
    
    # Initialize messengers
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    messengers = {
        "telegram": TelegramMessenger(telegram_token)
        # Future: add WhatsAppMessenger, EmailMessenger, etc.
    }
    
    # Initialize services
    notification_service = NotificationService(
        messengers, subscription_repo, user_repo
    )
    
    # Initialize and run checker
    checker = ExamChecker(exam_repo, notification_service)
    try:
        checker.run()
    except Exception as e:
        logger.error(f"Checker bot crashed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main orchestration"""
    if not os.getenv("TELEGRAM_TOKEN"):
        logger.error("Missing TELEGRAM_TOKEN")
        sys.exit(1)
    
    # Initialize database
    init_db()
    
    logger.info("=" * 60)
    logger.info("NITE Exam Checker Bot System Starting...")
    logger.info("=" * 60)
    
    # Create processes
    client_process = multiprocessing.Process(
        target=run_client_bots,
        name="ClientBots"
    )
    checker_process = multiprocessing.Process(
        target=run_checker_bot,
        name="CheckerBot"
    )
    
    try:
        client_process.start()
        checker_process.start()
        
        logger.info("All bots started successfully!")
        logger.info("Press Ctrl+C to stop")
        
        client_process.join()
        checker_process.join()
    
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        client_process.terminate()
        checker_process.terminate()
        client_process.join()
        checker_process.join()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
```

---

## ✅ סיכום

הקוד החדש:
- ✅ **מודולרי:** כל פלטפורמה בקובץ נפרד
- ✅ **נבדק:** קל ליצור Mocks לבדיקות
- ✅ **גמיש:** הוספת פלטפורמה = קלאס אחד חדש
- ✅ **נקי:** הפרדת אחריות ברורה

**הצעה:** להתחיל עם Base Classes, אחר כך Telegram, ואז מסד נתונים.

