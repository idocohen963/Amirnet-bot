"""
Central configuration for NITE exam checker bot.
Single source of truth for city mappings and constants.

This module centralizes all configuration parameters used across the application,
ensuring consistency and making it easy to add or modify cities and API settings.
"""

# ========== CITY CONFIGURATION ==========
# Dictionary mapping NITE API city IDs to city information
# Keys (1,2,3,5) are city_id values returned from NITE API
# Each city has: name (Hebrew), db_column (database field), display_order (UI sort order)
CITIES = {
    1: {"name": "חיפה", "db_column": "haifa", "display_order": 4},
    2: {"name": "תל אביב", "db_column": "tel_aviv", "display_order": 1},
    3: {"name": "ירושלים", "db_column": "jerusalem", "display_order": 3},
    5: {"name": "באר שבע", "db_column": "beer_sheva", "display_order": 2}
}

def get_city_name(city_id: int) -> str:
    """
    Convert NITE API city_id to Hebrew city name.
    
    Args:
        city_id: City identifier from NITE API (1, 2, 3, or 5)
    
    Returns:
        Hebrew city name, or "עיר לא ידועה (id)" if city_id not found
    """
    city = CITIES.get(city_id)
    return city["name"] if city else f"עיר לא ידועה ({city_id})"

def get_city_column(city_id: int) -> str | None:
    """
    Get database column name for a given city ID.
    
    Args:
        city_id: City identifier from NITE API
    
    Returns:
        Database column name (e.g., 'tel_aviv'), or None if city not found
    """
    city = CITIES.get(city_id)
    return city["db_column"] if city else None

def get_city_options() -> list[str]:
    """
    Get list of city names sorted by display order for UI presentation.
    
    Returns:
        List of Hebrew city names sorted by display_order field
        Example: ['תל אביב', 'באר שבע', 'ירושלים', 'חיפה']
    """
    sorted_cities = sorted(CITIES.values(), key=lambda x: x["display_order"])
    return [city["name"] for city in sorted_cities]

def get_city_columns_map() -> dict[str, str]:
    """
    Create mapping from Hebrew city names to database column names.
    
    Returns:
        Dictionary mapping city names to DB columns
        Example: {'תל אביב': 'tel_aviv', 'חיפה': 'haifa', ...}
    """
    return {city["name"]: city["db_column"] for city in CITIES.values()}


# ========== DATABASE ==========
# SQLite database filename for storing exams, logs, and users
DB_FILE = "exams_data.db"

# ========== API ==========
# NITE (National Institute for Testing and Evaluation) API endpoints
NITE_MAIN_URL = "https://niteop.nite.org.il"  # Main website for session cookies
NITE_API_URL = "https://proxy.nite.org.il/net-registration/all-days?networkExamId=3"  # API endpoint for exam dates

# HTTP headers required for NITE API requests to avoid rejection
NITE_API_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://niteop.nite.org.il",
    "referer": "https://niteop.nite.org.il/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/139.0.0.0 Safari/537.36"
}

# ========== CHECKER ==========
# Time intervals for exam checking loop (in seconds)
CHECK_INTERVAL_MIN = 120  # Minimum wait time: 2 minutes
CHECK_INTERVAL_MAX = 240  # Maximum wait time: 4 minutes
# HTTP request timeout (in seconds)
REQUEST_TIMEOUT = 10
