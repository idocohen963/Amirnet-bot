"""
NITE API Client - Website Connection and Data Fetching

This module handles all interactions with the NITE (National Institute for Testing and Evaluation)
website and API. It provides a clean interface for fetching exam schedule data.

Responsibilities:
    - Establishing session with NITE website
    - Fetching exam data from NITE API
    - Handling API errors and timeouts
    - Parsing API responses

Dependencies:
    - requests: HTTP client for API calls
    - logging: Error logging
    - config: API endpoints and headers configuration
"""

import logging
import requests
from config import (
    NITE_MAIN_URL,
    NITE_API_URL,
    NITE_API_HEADERS,
    REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)


def fetch_exam_dates():
    """
    Fetch current exam schedule from NITE API.
    
    Returns:
        Dictionary mapping exam dates to lists of city IDs.
        Example: {
            '2025-11-04': [3],  # Jerusalem
            '2025-11-05': [2, 5]  # Tel Aviv and Beer Sheva
        }
        Returns empty dict {} on failure.
    
    API Flow:
        1. GET main website to establish session cookies
        2. GET API endpoint with proper headers
        3. Parse JSON response
    
    Error Handling:
        Catches RequestException and returns empty dict.
        Logs errors but allows caller to continue.
    
    Note:
        Uses verify=False to bypass SSL verification issues.
        API requires specific headers to avoid rejection.
    """
    session = requests.Session()
    try:
        # Visit main site first to get session cookies
        session.get(NITE_MAIN_URL, timeout=REQUEST_TIMEOUT)
        
        # Fetch exam data with proper headers
        resp = session.get(
            NITE_API_URL,
            headers=NITE_API_HEADERS,
            timeout=REQUEST_TIMEOUT,
            verify=False
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch exam dates from NITE API: {e}")
        return {}

