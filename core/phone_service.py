"""
Selenium-based phone number retrieval using the NopeCHA browser extension
to automatically solve CAPTCHAs on Property24.

Requires a one-time Chrome profile setup:
  python runner.py --setup-chrome-profile
"""
import time
import yaml
import shutil
import tempfile
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
import traceback
import threading

# Optional selenium-wire for proxy auth
try:
    from seleniumwire import webdriver as wire_webdriver
    SELENIUM_WIRE_AVAILABLE = True
except ImportError as e:
    # Use standard print or a temporary log if loguru isn't ready, 
    # but here we can just set a flag and log it later in the class or just use logger if it was imported above.
    # Actually logger is imported on line 15.
    SELENIUM_WIRE_AVAILABLE = False
    SELENIUM_WIRE_ERROR = str(e)

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
    if not base_proxy_url:
        return base_proxy_url
    
    # Ensure scheme exists for correct parsing
    if "://" not in base_proxy_url:
        base_proxy_url = f"http://{base_proxy_url}"

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

def _human_scroll(driver: webdriver.Chrome, element):
    """Scroll to an element using variable speed and small steps to mimic a human."""
    target_y = element.location['y'] - 200 # Leave some space at the top
    current_y = driver.execute_script("return window.pageYOffset;")
    distance = target_y - current_y
    
    if distance > 0:
        # Scroll down in chunks
        steps = random.randint(5, 12)
        for i in range(steps):
            amount = (distance / steps) + random.uniform(-10, 10)
            driver.execute_script(f"window.scrollBy(0, {amount});")
            time.sleep(random.uniform(0.1, 0.3))

def _build_driver(ua: Optional[str] = None, proxy: Optional[str] = None, user_data_dir: Optional[str] = None, headless: bool = True) -> webdriver.Chrome:
    """Build a Chrome driver using the provided profile path.
    
    Args:
        ua: Optional User-Agent string
        proxy: Optional proxy URL
        user_data_dir: Path to the Chrome user data directory (cloned for this session)
        headless: Whether to run in headless mode
    """
    options = webdriver.ChromeOptions()
    
    if user_data_dir:
        # Use the cloned profile
        options.add_argument(f"--user-data-dir={user_data_dir}")
    
    if ua:
        options.add_argument(f'--user-agent={ua}')
    
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080") # Set common desktop resolution

    seleniumwire_options = {}
    if proxy:
        seleniumwire_options = {
            'proxy': {
                'http': proxy,
                'https': proxy,
                'no_proxy': 'localhost,127.0.0.1'
            }
        }
    
    if SELENIUM_WIRE_AVAILABLE:
        driver = wire_webdriver.Chrome(options=options, seleniumwire_options=seleniumwire_options)
    else:
        if proxy:
            error_msg = f": {SELENIUM_WIRE_ERROR}" if 'SELENIUM_WIRE_ERROR' in globals() else ""
            logger.warning(f"Proxy configured but selenium-wire not available: {error_msg}. Using direct connection (auth may fail).")
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
    
    # Global semaphore to limit concurrent browser instances
    # This prevents Out of Memory (OOM) crashes on local machines.
    _browser_semaphore = threading.Semaphore(settings.MAX_CONCURRENT_BROWSERS)

    def get_property24_phone(self, url: str, **kwargs) -> Optional[str]:
        """
        Navigate to a Property24 listing with retries.
        """
        max_retries = kwargs.get('retries', 5)
        for attempt in range(max_retries):
            try:
                phone = self._get_phone(url=url, site_key='property24', **kwargs)
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

    def _get_phone(self, url: str, site_key: str, **kwargs) -> Optional[str]:
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
        
        # 1. Wait for global rate limit slot BEFORE doing anything expensive
        # This prevents spawning multiple idle Chrome instances that are just waiting for a slot.
        _wait_for_rate_limit(site_key)

        with self._browser_semaphore:
            logger.info(f"Phone Service: Acquired browser slot for {url}")
            
            # 2. Create a unique temp directory for this browser instance to avoid profile locking
            temp_dir = tempfile.mkdtemp(prefix="chrome_profile_")
            source_profile = Path(__file__).parent.parent / "chrome-profiles" / "nopecha-profile"
            
            driver = None
            try:
                if source_profile.exists():
                    # Copy the Entire profile to our temp folder
                    # We ignore lock files and sockets that causes errors during copying
                    shutil.copytree(
                        source_profile, 
                        temp_dir, 
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('Singleton*', 'Lock', 'RunningChromeVersion')
                    )
                    logger.debug(f"Phone Service: Cloned profile to {temp_dir}")
                else:
                    logger.warning(f"Phone Service: Source profile not found at {source_profile}")

                # Use global setting for headless, but allow override via kwargs
                headless = kwargs.get('headless', settings.HEADLESS)
                driver = _build_driver(ua=ua, proxy=proxy, user_data_dir=temp_dir, headless=headless)
                
                # Anti-bot: Verification of Proxy IP
                try:
                    driver.get("https://api.ipify.org")
                    logger.info(f"Phone Service: Browser External IP: {driver.find_element(By.TAG_NAME, 'body').text}")
                except Exception as e:
                    logger.warning(f"Phone Service: Could not verify External IP: {e}")

                # Stealth: Inject Realistic Headers via Selenium-Wire
                if hasattr(driver, 'header_overrides'):
                    # Mimic a real Chrome 120+ request with modern security headers
                    driver.header_overrides = {
                        'Referer': 'https://www.property24.com/',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Upgrade-Insecure-Requests': '1'
                    }
                
                # 3. Navigate to the listing page
                logger.info(f"Phone Service: Navigating to {url}")
                time.sleep(random.uniform(1.0, 2.5))  # Random jitter before navigation
                driver.get(url)

                # 3.1 Block Detection
                if "Server unavailable" in driver.page_source:
                    logger.error(f"Phone Service: Blocked! 'Server unavailable' detected at {url}")
                    # Save debug screenshot if blocked
                    try:
                        debug_path = Path("output/blocks")
                        debug_path.mkdir(parents=True, exist_ok=True)
                        screenshot_file = debug_path / f"block_{int(time.time())}.png"
                        driver.save_screenshot(str(screenshot_file))
                        logger.info(f"Phone Service: Saved block screenshot to {screenshot_file}")
                    except:
                        pass
                    return None

                # 4. Find and click the "Show Contact Number" button
                logger.info("Phone Service: Waiting for 'Show Number' button...")
                wait = WebDriverWait(driver, 200)

                logger.info("Phone Service: Clicking 'Show Number' button...")

                show_buttons = driver.find_elements(By.CSS_SELECTOR, show_btn_sel)
                show_btn = [btn for btn in show_buttons if btn.size['height'] > 0 and btn.size['width'] > 0][0]

                # 4.1 Human-like scrolling
                _human_scroll(driver, show_btn)
                time.sleep(random.uniform(0.8, 1.5))
                
                # 4.2 Human-like mouse movements
                actions = ActionChains(driver)
                
                # Hover with a bit of "jitter"
                actions.move_to_element_with_offset(show_btn, random.randint(-5, 5), random.randint(-5, 5))
                actions.pause(random.uniform(0.5, 1.2))
                
                # Click with slight offset
                actions.click_and_hold(show_btn)
                actions.pause(random.uniform(0.1, 0.2)) # Brief hold
                actions.release()
                actions.perform()

                # 5. Wait for the phone number (NopeCHA auto-solves the CAPTCHA)
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
                logger.error(traceback.format_exc())
                return None
            finally:
                if driver:
                    driver.quit()
                # 6. Cleanup the temporary profile directory
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Phone Service: Cleaned up temp profile {temp_dir}")
                except Exception as cleanup_err:
                    logger.warning(f"Phone Service: Failed to cleanup temp profile: {cleanup_err}")
                logger.info(f"Phone Service: Driver closed and slot released for {url}")
