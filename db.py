"""
This module handles all database operations for managing exam schedules.
It provides utility functions to initialize the database, fetch current exams,
add new exams, and remove exams while maintaining a log of changes.

Modules:
    - sqlite3: For database operations.
    - logging: For logging messages.
    - datetime: To handle timestamps.

Functions:
    - get_connection: Creates and returns a connection to the database.
    - init_db: Initializes the database tables if they do not exist.
    - get_current_exams: Fetches all currently active exams.
    - add_exam: Adds a new exam and logs the event.
    - remove_exam: Removes an exam and logs the event.

"""

import sqlite3
import logging
from datetime import datetime

DB_FILE = "exams_data.db"

# ----------------------------
# Utility Functions
# ----------------------------

# Creates and returns a connection to the database.
def get_connection():
    return sqlite3.connect(DB_FILE)

# ----------------------------
# Database Initialization
# ----------------------------

# Initializes the database tables if they do not exist.
def init_db():
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
        conn.commit()
    logging.info("Database initialized successfully.")

# ----------------------------
# Bot Management Functions
# ----------------------------

# Fetches all currently active exams from the database.
# Returns:
#     set: A set of tuples (exam_date, city_id) representing active exams.
def get_current_exams():
    with get_connection() as conn:
        rows = conn.execute("SELECT exam_date, city_id FROM exams").fetchall()
        return set(rows)

# Adds a new exam to the current state table and logs the event.
# Args:
#     date (str): The date of the exam.
#     city_id (int): The ID of the city where the exam is held.
def add_exam(date: str, city_id: int):
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

# Removes an exam from the current state table and logs the event.
# Args:
#     date (str): The date of the exam.
#     city_id (int): The ID of the city where the exam is held.
def remove_exam(date: str, city_id: int):
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