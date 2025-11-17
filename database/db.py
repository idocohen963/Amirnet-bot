"""
Database layer for NITE exam checker bot.

This module handles all SQLite database operations for managing exam schedules,
user subscriptions, and event logging. It maintains four tables:
    - exams: Current active exams
    - exam_log: Historical record of all exam changes
    - users: Telegram user subscription preferences by city
    - whatsapp_users: WhatsApp user subscription preferences by city

Dependencies:
    - sqlite3: SQLite database operations
    - logging: Application logging
    - datetime: Timestamp generation
    - config: Centralized configuration (DB_FILE, city mappings)

Functions:
    - get_connection: Create database connection
    - init_db: Initialize database schema
    - get_current_exams: Retrieve all active exams
    - add_exam: Insert new exam and log creation
    - remove_exam: Delete exam and log removal
    - add_user: Register new Telegram user
    - update_user_cities: Update Telegram user's city subscriptions
    - get_users_by_city: Query Telegram users subscribed to specific city
    - add_whatsapp_user: Register new WhatsApp user
    - update_whatsapp_user_cities: Update WhatsApp user's city subscriptions
    - get_whatsapp_users_by_city: Query WhatsApp users subscribed to specific city
"""

import sqlite3
import logging
from datetime import datetime
from config import DB_FILE, get_city_columns_map

# ----------------------------
# Utility Functions
# ----------------------------

def get_connection():
    """
    Create and return a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection: Active database connection object
    
    Note:
        Connection should be used with context manager (with statement)
        to ensure proper closure and transaction handling.
    """
    return sqlite3.connect(DB_FILE)

# ----------------------------
# Database Initialization
# ----------------------------

def init_db():
    """
    Initialize database schema by creating all required tables.
    
    Creates four tables if they don't exist:
        1. exams: Stores current active exams with unique constraint on (exam_date, city_id)
        2. exam_log: Audit log of all exam additions and removals
        3. users: Telegram user subscriptions with boolean columns for each city
        4. whatsapp_users: WhatsApp user subscriptions with boolean columns for each city
    
    Table Structure:
        exams: id, exam_date, city_id, first_seen
        exam_log: log_id, exam_date, city_id, event_type, event_timestamp
        users: user_id (INTEGER), tel_aviv, beer_sheva, jerusalem, haifa
        whatsapp_users: user_id (TEXT), tel_aviv, beer_sheva, jerusalem, haifa
    
    Note:
        Safe to call multiple times - uses CREATE TABLE IF NOT EXISTS.
    """
    with get_connection() as conn:
        # Table 1: Current state of exams
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_date TEXT NOT NULL,
                city_id INTEGER NOT NULL,
                first_seen TIMESTAMP NOT NULL,
                UNIQUE(exam_date, city_id)
            )
        """)

        # Table 2: Event history (log)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exam_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_date TEXT NOT NULL,
                city_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,  -- 'CREATED' or 'DELETED'
                event_timestamp TIMESTAMP NOT NULL
            )
        """)

        # Table 3: users (Telegram)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                tel_aviv INTEGER DEFAULT 0,
                beer_sheva INTEGER DEFAULT 0,
                jerusalem INTEGER DEFAULT 0,
                haifa INTEGER DEFAULT 0
            )
        """)

        # Table 4: whatsapp_users (WhatsApp)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_users (
                user_id TEXT PRIMARY KEY,
                tel_aviv INTEGER DEFAULT 0,
                beer_sheva INTEGER DEFAULT 0,
                jerusalem INTEGER DEFAULT 0,
                haifa INTEGER DEFAULT 0
            )
        """)
        conn.commit()
    logging.info("Database initialized successfully.")

# ----------------------------
# Exam Management Functions
# ----------------------------

def get_current_exams():
    """
    Retrieve all currently active exams from the database.
    
    Returns:
        set: Set of tuples in format (exam_date, city_id)
             Example: {('2025-11-04', 3), ('2025-11-05', 2)}
    
    Note:
        Used by checker bot to compare API data with database state.
    """
    with get_connection() as conn:
        rows = conn.execute("SELECT exam_date, city_id FROM exams").fetchall()
        return set(rows)

def add_exam(date: str, city_id: int):
    """
    Add a new exam to the database and log the creation event.
    
    Args:
        date: Exam date in ISO format (YYYY-MM-DD)
        city_id: NITE API city identifier (1=חיפה, 2=תל אביב, 3=ירושלים, 5=באר שבע)
    
    Side Effects:
        - Inserts row into 'exams' table with current timestamp
        - Logs 'CREATED' event to 'exam_log' table
        - Commits transaction
    
    Note:
        Should only be called after confirming exam doesn't exist in DB.
    """
    now = datetime.now()
    with get_connection() as conn:
        # Add to the current state table
        conn.execute(
            "INSERT INTO exams (exam_date, city_id, first_seen) VALUES (?, ?, ?)",
            (date, city_id, now)
        )
        # Log the event
        conn.execute(
            """INSERT INTO exam_log (exam_date, city_id, event_type, event_timestamp)
               VALUES (?, ?, 'CREATED', ?)""",
            (date, city_id, now)
        )
        conn.commit()

def remove_exam(date: str, city_id: int):
    """
    Remove an exam from the database and log the deletion event.
    
    Args:
        date: Exam date in ISO format (YYYY-MM-DD)
        city_id: NITE API city identifier
    
    Side Effects:
        - Deletes matching row from 'exams' table
        - Logs 'DELETED' event to 'exam_log' table
        - Commits transaction
    
    Note:
        Called when exam no longer appears in API response (exam was cancelled/removed).
        Does not send notifications to users - handled by caller.
    """
    with get_connection() as conn:
        # Remove from the current state table
        conn.execute(
            "DELETE FROM exams WHERE exam_date = ? AND city_id = ?",
            (date, city_id)
        )
        # Log the event
        conn.execute(
            """INSERT INTO exam_log (exam_date, city_id, event_type, event_timestamp)
               VALUES (?, ?, 'DELETED', ?)""",
            (date, city_id, datetime.now())
        )
        conn.commit()

# ----------------------------
# User Management Functions
# ----------------------------

def add_user(user_id: int):
    """
    Register a new user in the database.
    
    Args:
        user_id: Telegram user ID (unique identifier)
    
    Side Effects:
        - Inserts new row into 'users' table with all city subscriptions set to 0
        - Uses INSERT OR IGNORE to prevent duplicate key errors
        - Commits transaction
    
    Note:
        Called when user first sends /start command to the bot.
        If user already exists, operation is silently ignored.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (user_id)
            VALUES (?)
            """,
            (user_id,)
        )
        conn.commit()

def update_user_cities(user_id: int, cities: list[str]):
    """
    Update user's city subscription preferences.
    
    Args:
        user_id: Telegram user ID
        cities: List of Hebrew city names user wants to subscribe to
                Example: ['תל אביב', 'חיפה']
    
    Side Effects:
        - Updates all city columns in 'users' table for given user_id
        - Sets matching cities to 1 (subscribed), others to 0 (unsubscribed)
        - Commits transaction
    
    Implementation:
        Uses get_city_columns_map() to convert Hebrew names to DB column names.
        Dynamically builds UPDATE query for all city columns.
    """
    city_columns = get_city_columns_map()

    # Create dict: {db_column: 1 or 0} based on whether city is in user's selection
    updates = {column: (1 if city in cities else 0) for city, column in city_columns.items()}

    with get_connection() as conn:
        conn.execute(
            f"""
            UPDATE users
            SET {', '.join(f'{col} = ?' for col in updates.keys())}
            WHERE user_id = ?
            """,
            (*updates.values(), user_id)
        )
        conn.commit()

def get_users_by_city(city_column: str) -> list[int]:
    """
    Retrieve all user IDs subscribed to a specific city.
    
    Args:
        city_column: Database column name for the city
                    Valid values: 'tel_aviv', 'beer_sheva', 'jerusalem', 'haifa'
    
    Returns:
        List of Telegram user IDs (integers) subscribed to the specified city
        Example: [1152610979, 987654321]
        Returns empty list if no users subscribed
    
    Usage:
        Used by checker bot to determine which users to notify about new exams.
        Column name should be obtained from get_city_column(city_id).
    
    Security Note:
        Uses f-string for column name (not user input) - safe from SQL injection
        as column names are validated through config.py.
    """
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT user_id FROM users WHERE {city_column} = 1"
        ).fetchall()
        return [row[0] for row in rows]

# ----------------------------
# WhatsApp User Management Functions
# ----------------------------

def add_whatsapp_user(user_id: str):
    """
    Register a new WhatsApp user in the database.
    
    Args:
        user_id: WhatsApp user ID (string identifier)
    
    Side Effects:
        - Inserts new row into 'whatsapp_users' table with all city subscriptions set to 0
        - Uses INSERT OR IGNORE to prevent duplicate key errors
        - Commits transaction
    
    Note:
        Called when user first sends /start command to the WhatsApp bot.
        If user already exists, operation is silently ignored.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO whatsapp_users (user_id)
            VALUES (?)
            """,
            (user_id,)
        )
        conn.commit()

def update_whatsapp_user_cities(user_id: str, cities: list[str]):
    """
    Update WhatsApp user's city subscription preferences.
    
    Args:
        user_id: WhatsApp user ID (string)
        cities: List of Hebrew city names user wants to subscribe to
                Example: ['תל אביב', 'חיפה']
    
    Side Effects:
        - Updates all city columns in 'whatsapp_users' table for given user_id
        - Sets matching cities to 1 (subscribed), others to 0 (unsubscribed)
        - Commits transaction
    
    Implementation:
        Uses get_city_columns_map() to convert Hebrew names to DB column names.
        Dynamically builds UPDATE query for all city columns.
    """
    city_columns = get_city_columns_map()

    # Create dict: {db_column: 1 or 0} based on whether city is in user's selection
    updates = {column: (1 if city in cities else 0) for city, column in city_columns.items()}

    with get_connection() as conn:
        conn.execute(
            f"""
            UPDATE whatsapp_users
            SET {', '.join(f'{col} = ?' for col in updates.keys())}
            WHERE user_id = ?
            """,
            (*updates.values(), user_id)
        )
        conn.commit()

def get_whatsapp_users_by_city(city_column: str) -> list[str]:
    """
    Retrieve all WhatsApp user IDs subscribed to a specific city.
    
    Args:
        city_column: Database column name for the city
                    Valid values: 'tel_aviv', 'beer_sheva', 'jerusalem', 'haifa'
    
    Returns:
        List of WhatsApp user IDs (strings) subscribed to the specified city
        Example: ['whatsapp_user_123', 'whatsapp_user_456']
        Returns empty list if no users subscribed
    
    Usage:
        Used by checker bot to determine which WhatsApp users to notify about new exams.
        Column name should be obtained from get_city_column(city_id).
    
    Security Note:
        Uses f-string for column name (not user input) - safe from SQL injection
        as column names are validated through config.py.
    """
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT user_id FROM whatsapp_users WHERE {city_column} = 1"
        ).fetchall()
        return [row[0] for row in rows]