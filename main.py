#!/usr/bin/env python3
"""
Main Entry Point - NITE Exam Checker Bot System

This script orchestrates the entire bot system by running two independent
processes in parallel:
    1. Telegram Bot (telegram_bot.py) - Handles user registration and preferences
    2. Checker Bot (nite_check.py) - Monitors API and sends notifications

Architecture:
    Uses Python's multiprocessing module to run both bots simultaneously
    in separate processes. This allows:
        - Independent operation (one bot crash doesn't affect the other)
        - True parallelism (not limited by GIL)
        - Clean shutdown of both processes with Ctrl+C

Process Management:
    - Creates two Process objects with descriptive names
    - Starts both processes
    - Waits for completion (join) - blocks until Ctrl+C
    - Gracefully terminates both on KeyboardInterrupt
    - Ensures cleanup on any exception

Usage:
    python3 main.py  # Starts both bots
    Ctrl+C           # Stops both bots cleanly

Requirements:
    - TELEGRAM_TOKEN environment variable must be set
    - Database will be created automatically on first run
"""

import os
import sys
import logging
import multiprocessing
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging with process names for multi-process tracking
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(processName)s] %(message)s"
    filename="project.log",  # Creates log file
    filemode="a"
)
logger = logging.getLogger(__name__)


def run_client_bot():
    """
    Process target function for client bot.
    
    Imports and runs the client bot's main function.
    Runs in separate process named "ClientBot".
    
    Error Handling:
        Any exception causes process to exit with code 1.
        Exception details logged with full traceback.
    """
    try:
        from telegram_bot import main as client_main
        logger.info("Starting client bot...")
        client_main()  # Blocks until terminated
    except Exception as e:
        logger.error(f"Client bot crashed: {e}", exc_info=True)
        sys.exit(1)


def run_checker_bot():
    """
    Process target function for checker bot.
    
    Imports and runs the checker bot's main loop.
    Runs in separate process named "CheckerBot".
    
    Error Handling:
        Any exception causes process to exit with code 1.
        Exception details logged with full traceback.
    """
    try:
        from nite_check import run_checker
        logger.info("Starting checker bot...")
        run_checker()  # Blocks until terminated
    except Exception as e:
        logger.error(f"Checker bot crashed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """
    Main orchestration function - start and manage both bot processes.
    
    Pre-flight Checks:
        Validates TELEGRAM_TOKEN environment variable exists.
        Exits with error message if missing.
    
    Process Lifecycle:
        1. Create two Process objects with descriptive names
        2. Start both processes (non-blocking)
        3. Join both processes (blocks here, waiting for termination)
        4. Handle Ctrl+C gracefully:
           - Terminate both processes
           - Wait for cleanup (join)
           - Log successful shutdown
        5. Handle any other exception:
           - Terminate both processes
           - Exit with error code 1
    
    Process Naming:
        - "ClientBot": User management bot
        - "CheckerBot": Exam monitoring bot
        Visible in logs via %(processName)s formatter
    
    Blocking Behavior:
        This function blocks at join() calls until:
        - User presses Ctrl+C (KeyboardInterrupt)
        - A process crashes (should not happen with error handling)
        - Process is killed externally
    
    Exit Codes:
        0: Clean shutdown via Ctrl+C
        1: Environment variable missing or unexpected error
    """
    
    # Verify required environment variables before starting
    if not os.getenv("TELEGRAM_TOKEN"):
        logger.error("Missing TELEGRAM_TOKEN in environment variables!")
        logger.error("Please create a .env file with: TELEGRAM_TOKEN=your_token_here")
        sys.exit(1)
    
    # Log system startup
    logger.info("=" * 60)
    logger.info("NITE Exam Checker Bot System Starting...")
    logger.info("=" * 60)
    
    # Create process objects (not yet started)
    client_process = multiprocessing.Process(
        target=run_client_bot, 
        name="ClientBot"  # Visible in logs
    )
    checker_process = multiprocessing.Process(
        target=run_checker_bot, 
        name="CheckerBot"  # Visible in logs
    )
    
    try:
        # Start both processes (non-blocking, processes run independently)
        client_process.start()
        checker_process.start()
        
        logger.info("Both bots started successfully!")
        logger.info("Client bot for user management")
        logger.info("Checker bot for exam monitoring")
        logger.info("Press Ctrl+C to stop both bots")
        
        # Wait for processes to complete (blocks here until Ctrl+C or crash)
        client_process.join()
        checker_process.join()
        
    except KeyboardInterrupt:
        # User pressed Ctrl+C - graceful shutdown
        logger.info("\nShutting down bots...")
        client_process.terminate()  # Send SIGTERM
        checker_process.terminate()  # Send SIGTERM
        client_process.join()  # Wait for process to finish cleanup
        checker_process.join()  # Wait for process to finish cleanup
        logger.info("Both bots stopped successfully.")
    
    except Exception as e:
        # Unexpected error - emergency shutdown
        logger.error(f"Error in main: {e}", exc_info=True)
        client_process.terminate()
        checker_process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()
