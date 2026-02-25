"""
Selenium-based phone number retrieval using the NopeCHA browser extension
to automatically solve CAPTCHAs on Property24.

Requires a one-time Chrome profile setup:
  python runner.py --setup-chrome-profile
"""
import time
import yaml
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth
from core.rate_limiter import rate_limiter
from core.user_agents import get_random_ua
from config.settings import settings
import random

# Optional selenium-wire for proxy auth
try:
    from seleniumwire import webdriver as wire_webdriver
    SELENIUM_WIRE_AVAILABLE = True
except ImportError:
    SELENIUM_WIRE_AVAILABLE = False

def _load_phone_config(site_key: str) -> dict:
    """Load phone_retrieval selectors for a given site from sites.yaml."""
    config_path = Path(__file__).parent.parent / "config" / "sites.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    site = config.get("sites", {}).get(site_key, {})
    return site.get("phone_retrieval", {})


def _wait_for_rate_limit(site_key: str) -> None:
    """
    Retrieves the RPM limit for the site and waits for a slot from the global rate limiter.
    """
    config_path = Path(__file__).parent.parent / "config" / "sites.yaml"
    with open(config_path) as f:
        full_config = yaml.safe_load(f)
    
    # Get RPM limit from config, default to 3 if not specified
    rpm = full_config.get("sites", {}).get(site_key, {}).get("rate_limit", {}).get("requests_per_minute", 3)

    # Wait for global slot
    logger.info(f"Phone Service: Waiting for global rate limit slot (Target RPM: {rpm})")
    rate_limiter.wait_for_slot(site_key, rpm)

def _get_sessionized_proxy_url(base_proxy_url: str) -> str:
    """
    Injects a unique sessid into the proxy URL for DataImpulse-style sticky sessions.
    Format: http://user__sessid.RANDOM:pass@host:port
    """
    parsed = urlparse(base_proxy_url)
    if not parsed.username:
        return base_proxy_url
    
    sessid = random.getrandbits(32)
    new_username = f"{parsed.username}__sessid.{sessid}"
    
    # Reconstruct the netloc with the new username
    # netloc is user:pass@host:port
    auth = new_username
    if parsed.password:
        auth += f":{parsed.password}"
    
    new_netloc = f"{auth}@{parsed.hostname}"
    if parsed.port:
        new_netloc += f":{parsed.port}"
        
    return urlunparse(parsed._replace(netloc=new_netloc))

def _build_driver(ua: Optional[str] = None, proxy: Optional[str] = None) -> webdriver.Chrome:
    """Build a Chrome driver using the persistent NopeCHA profile.
    
    Args:
        ua: User-agent string to use.
        proxy: Proxy URL (http://user:pass@host:port).
    """
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR.resolve()}")
    
    if ua:
        options.add_argument(f'--user-agent={ua}')
    
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")
    options.add_argument("--window-size=1280,900")

    seleniumwire_options = {}
    if proxy and SELENIUM_WIRE_AVAILABLE:
        seleniumwire_options = {
            'proxy': {
                'http': proxy,
                'https': proxy,
                'no_proxy': 'localhost,127.0.0.1'
            }
        }
        driver = wire_webdriver.Chrome(options=options, seleniumwire_options=seleniumwire_options)
    else:
        if proxy and not SELENIUM_WIRE_AVAILABLE:
            logger.warning("Proxy configured but selenium-wire not installed. Using direct connection.")
        driver = webdriver.Chrome(options=options)
    
    # Anti-bot detection: Stealth
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    # Allow MV3 service worker (NopeCHA) a moment to register
    time.sleep(random.uniform(2.5, 4.0))
    driver.implicitly_wait(5)
    return driver


CHROME_PROFILE_DIR = Path("chrome-profiles/nopecha-profile")
NOPECHA_WEBSTORE_URL = "https://chromewebstore.google.com/detail/nopecha-captcha-solver/dknlfmjaanfblgfdfebhijalfmhmjjjo"

def setup_chrome_profile() -> None:
    """
    Interactive one-time setup: opens Chrome with the persistent profile so a developer
    can install the NopeCHA extension and authenticate it with their API key.

    Run via:  python runner.py --setup-chrome-profile
    """
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR.resolve()}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    print()
    print("=" * 60)
    print(" NopeCHA Chrome Profile Setup")
    print("=" * 60)
    print()
    print("A Chrome window is opening with a dedicated profile.")
    print("Please follow these steps in the browser:")
    print()
    print("  STEP 1 — Install the NopeCHA extension:")
    print(f"    {NOPECHA_WEBSTORE_URL}")
    print()
    print("  STEP 2 — Authenticate with your API key:")
    print("    https://nopecha.com/setup#YOUR_API_KEY_HERE")
    print("    (replace YOUR_API_KEY_HERE with your actual key)")
    print()
    print("  STEP 3 — Once done, close the browser window.")
    print()
    print("The profile will be saved to:", CHROME_PROFILE_DIR.resolve())
    print("Add that directory to .gitignore so your API key is never committed.")
    print("=" * 60)
    print()

    driver = webdriver.Chrome(options=options)

    # Open the Chrome Web Store page for NopeCHA automatically
    driver.get(NOPECHA_WEBSTORE_URL)

    try:
        # Block until the user closes the browser manually
        while True:
            try:
                _ = driver.title  # raises if window is closed
                time.sleep(1)
            except Exception:
                break
    finally:
        try:
            driver.quit()
        except Exception:
            pass  # already closed by user

    print()
    print("Setup complete! You can now run the scraper normally.")
    print("  python runner.py --site property24")
    print()


class PhoneService:
    """Retrieves protected phone numbers using a Selenium session with the NopeCHA extension."""

    def get_property24_phone(self, url: str, **kwargs) -> Optional[str]:
        """
        Navigate to a Property24 listing with retries.
        """
        max_retries = kwargs.get('retries', 3)
        for attempt in range(max_retries):
            try:
                phone = self._get_phone(url=url, site_key='property24')
                if phone:
                    return phone
                logger.warning(f"Phone Service: Attempt {attempt + 1} failed for {url}")
            except Exception as e:
                logger.error(f"Phone Service: Attempt {attempt + 1} crashed: {e}")
            
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(1, 3)
                logger.info(f"Phone Service: Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
        return None

    def _get_phone(self, url: str, site_key: str) -> Optional[str]:
        """Core Selenium logic — navigates to the URL and extracts the phone number."""
        api_key = settings.NOPECHA_API_KEY
        if not api_key:
            logger.error("Phone Service: NOPECHA_API_KEY not set")
            return None

        phone_config = _load_phone_config(site_key)
        show_btn_sel = phone_config.get('show_number_btn')
        phone_result_sel = phone_config.get('phone_result')

        if not show_btn_sel or not phone_result_sel:
            logger.error(f"Phone Service: Missing phone_retrieval selectors for site '{site_key}'")
            return None

        if not CHROME_PROFILE_DIR.exists():
            logger.error(
                "Phone Service: Chrome profile not found. "
                "Run 'python runner.py --setup-chrome-profile' first."
            )
            return None

        ua = get_random_ua()
        proxy_base = settings.STICKY_PROXY_URL
        proxy = _get_sessionized_proxy_url(proxy_base) if proxy_base else None
        
        driver = _build_driver(ua=ua, proxy=proxy)

        try:
            # Respect global rate limit across Scrapy and Selenium
            _wait_for_rate_limit(site_key)

            # 2. Navigate to the listing page
            logger.info(f"Phone Service: Navigating to {url}")
            time.sleep(random.uniform(1.0, 2.5))  # Random jitter before navigation
            driver.get(url)

            # 3. Find and click the "Show Contact Number" button
            logger.info("Phone Service: Waiting for 'Show Number' button...")
            wait = WebDriverWait(driver, 200)

            logger.info("Phone Service: Clicking 'Show Number' button...")

            show_buttons = driver.find_elements(By.CSS_SELECTOR, show_btn_sel)
            show_btn = [btn for btn in show_buttons if btn.size['height'] > 0 and btn.size['width'] > 0][0]

            # scroll down until show_btn is visible
            driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", show_btn)
            time.sleep(random.uniform(1.0, 2.0))
            
            actions = ActionChains(driver)
            actions.move_to_element(show_btn)   # moves the actual cursor to the element
            actions.pause(random.uniform(0.4, 0.8))  # brief human-like pause
            actions.click(show_btn)
            actions.perform()

            # 4. Wait for the phone number (NopeCHA auto-solves the CAPTCHA)
            logger.info("Phone Service: Waiting for phone number (NopeCHA will auto-solve CAPTCHA)...")
            phone_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, phone_result_sel)))
            phone = phone_el.text.strip()

            if phone:
                logger.success(f"Phone Service: Got phone number: {phone}")
                return phone

            logger.warning("Phone Service: Phone element visible but text was empty")
            return None

        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Phone Service: Driver error at {url}: {e}")
            return None
        except NoSuchElementException as e:
            logger.error(f"Phone Service: Element not found at {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Phone Service: Unexpected error at {url}: {e}")
            return None
        finally:
            try:
                driver.quit()
                logger.info(f"Phone Service: Driver closed for {url}")
            except:
                pass
