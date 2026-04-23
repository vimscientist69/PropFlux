import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file at the project root
load_dotenv()


def _int_env(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def _float_env(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default

class Settings:
    # Environment & Overrides
    ENV = os.getenv("SCRAPER_ENV", "development")
    # Default to None (no limit) if not set or invalid
    try:
        DEV_LIMIT = int(os.getenv("SCRAPER_DEV_LIMIT")) if os.getenv("SCRAPER_DEV_LIMIT") else None
    except (ValueError, TypeError):
        DEV_LIMIT = None
    
    # Headless mode (default to True for production, allow override for debugging)
    HEADLESS = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
    
    # API Keys & Proxies (Secrets)
    NOPECHA_API_KEY = os.getenv("NOPECHA_API_KEY")
    ROTATING_PROXY_URL = os.getenv("ROTATING_PROXY_URL")
    STICKY_PROXY_URL = os.getenv("STICKY_PROXY_URL")
    
    # Export Settings
    EXPORT_BATCH_SIZE = int(os.getenv("SCRAPER_EXPORT_BATCH_SIZE", "100"))
    
    # Concurrency Settings
    MAX_CONCURRENT_BROWSERS = _int_env("SCRAPER_MAX_CONCURRENT_BROWSERS", 2)

    # Retry Settings (mirrors scraper/settings.py — change both together)
    RETRY_TIMES = 3
    RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

    # Pagination retry backoff tuning (used only for failed search/page requests).
    PAGINATION_RETRY_BACKOFF_STEP_SECONDS = _int_env("SCRAPER_PAGINATION_RETRY_STEP_SECONDS", 50)
    PAGINATION_RETRY_MAX_BACKOFF_SECONDS = _int_env("SCRAPER_PAGINATION_RETRY_MAX_SECONDS", 500)
    PAGINATION_RETRY_JITTER_PERCENT = _float_env("SCRAPER_PAGINATION_RETRY_JITTER_PERCENT", 0.0)
    
    # Site Constants (Non-secrets)
    PROPERTY24_RECAPTCHA_SITEKEY = "6LcGHUEUAAAAAAfppsl05ypEC9L5KgUG3JYkpoF7"
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / "output"

settings = Settings()
