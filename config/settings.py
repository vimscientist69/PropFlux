import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file at the project root
load_dotenv()

class Settings:
    # Environment & Overrides
    ENV = os.getenv("SCRAPER_ENV", "development")
    # Default to None (no limit) if not set or invalid
    try:
        DEV_LIMIT = int(os.getenv("SCRAPER_DEV_LIMIT")) if os.getenv("SCRAPER_DEV_LIMIT") else None
    except (ValueError, TypeError):
        DEV_LIMIT = None
    
    # API Keys & Proxies (Secrets)
    NOPECHA_API_KEY = os.getenv("NOPECHA_API_KEY")
    PROXY_URL = os.getenv("PROXY_URL")
    
    # Site Constants (Non-secrets)
    PROPERTY24_RECAPTCHA_SITEKEY = "6LcGHUEUAAAAAAfppsl05ypEC9L5KgUG3JYkpoF7"
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / "output"

settings = Settings()
