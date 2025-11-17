"""
NITE Exam Checker Bot - Continuous Monitoring and Notification Service

This script continuously monitors the NITE (National Institute for Testing and Evaluation)
API for exam schedule changes and sends real-time notifications to subscribed users
via multiple platforms (Telegram, WhatsApp).

Architecture:
    1. Fetch exam data from NITE API every 2-4 minutes
    2. Compare with current database state
    3. Detect new exams (additions) and removed exams (cancellations)
    4. Send notifications to users subscribed to affected cities (Telegram and WhatsApp)
    5. Update database to reflect current state
    6. Log all changes to exam_log table

Monitoring Loop:
    - Runs indefinitely with random delays (120-240 seconds)
    - Handles API failures gracefully (continues on next iteration)
    - Logs all operations and errors

Dependencies:
    - time, random: Sleep interval management
    - logging: Operation logging
    - db: Database operations
    - config: Centralized configuration
    - nite_api: NITE API client for fetching exam data
    - notifications: Notification service (Telegram and WhatsApp)

Usage:
    python3 nite_check.py  # Run standalone
    python3 main.py        # Run with telegram bot (recommended)
"""

import time
import random
import logging
from database.db import (
    init_db,
    get_current_exams,
    add_exam,
    remove_exam,
    get_users_by_city,
    get_whatsapp_users_by_city
)
from config import (
    get_city_name,
    get_city_column,
    CHECK_INTERVAL_MIN,
    CHECK_INTERVAL_MAX
)
from nite_api import fetch_exam_dates
from notifications import send_telegram_message, send_whatsapp_message

# Configure logging for monitoring operations
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ----------------
# Main Checker Logic
# ----------------

def run_checker():
    """
    Main monitoring loop - continuously check for exam changes and notify users.
    
    Flow:
        1. Initialize database (create tables if needed)
        2. Enter infinite loop:
           a. Fetch current exam data from API
           b. Compare with database state
           c. Detect new exams (API has, DB doesn't)
           d. Detect removed exams (DB has, API doesn't)
           e. For new exams: notify subscribed users, update DB
           f. For removed exams: remove from DB (no notifications currently)
           g. Sleep random interval (120-240 seconds)
           h. Repeat
    
    New Exam Handling:
        - Get city name and DB column from config
        - Query Telegram and WhatsApp users subscribed to that city
        - Send notifications to each relevant user (Telegram and WhatsApp)
        - Add exam to database and log creation event
    
    Removed Exam Handling:
        - Remove from database
        - Log deletion event
        - Note: Does NOT notify users (potential enhancement)
    
    Error Resilience:
        - API failures return empty dict, logged but don't crash bot
        - Message send failures logged but don't stop processing
        - Loop continues indefinitely even after errors
    
    Performance:
        - Randomized sleep prevents predictable API polling patterns
        - Set comparison (O(n)) for efficient change detection
    
    Note:
        This function blocks indefinitely. Use Ctrl+C or process termination to stop.
    """
    # Initialize the database tables if they do not exist
    init_db()

    logger.info("Bot initialized and connected to SQLite database.")

    while True:
        api_data = fetch_exam_dates()
        if not api_data:
            logger.warning("No data retrieved from the API.")
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
                logger.info(f"Detected {len(new_exams)} new exams.")
                for date, city_id in sorted(list(new_exams)):
                    city_name = get_city_name(city_id)
                    city_column = get_city_column(city_id)

                    if not city_column:
                        logger.warning(f"City column not found for city: {city_name}")
                        continue

                    # Get users subscribed to this city (Telegram)
                    telegram_user_ids = get_users_by_city(city_column)
                    
                    # Get WhatsApp users subscribed to this city
                    whatsapp_user_ids = get_whatsapp_users_by_city(city_column)
                    
                    if not telegram_user_ids and not whatsapp_user_ids:
                        logger.info(f"No users subscribed to city: {city_name}")
                        continue

                    # Send notifications to Telegram users
                    msg = f"📢 מבחן חדש ב-{city_name}, בתאריך {date}"
                    for user_id in telegram_user_ids:
                        send_telegram_message(user_id, msg)
                    
                    # Send notifications to WhatsApp users
                    for user_id in whatsapp_user_ids:
                        send_whatsapp_message(user_id, msg)

                    # Add the exam to the database
                    add_exam(date, city_id)
            
            # Handle removed exams (cancelled/deleted from NITE system)
            if removed_exams:
                logger.info(f"Detected {len(removed_exams)} removed exams.")
                for date, city_id in removed_exams:
                    # Remove from DB and log deletion event
                    # Note: Currently does NOT notify users about cancellations
                    remove_exam(date, city_id)

            # Log when no changes detected (helps confirm bot is running)
            if not new_exams and not removed_exams:
                logger.info("No changes in the exam schedule.")

        # Wait random interval before next check to avoid predictable patterns
        wait_time = random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX)
        logger.info(f"Sleeping for {wait_time} seconds before the next check...")
        time.sleep(wait_time)

# ----------------
# Entry Point
# ----------------

if __name__ == "__main__":
    run_checker()