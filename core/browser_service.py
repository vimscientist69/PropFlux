"""
Selenium-based dynamic data retrieval (phone numbers, agent names, etc.) 
using the NopeCHA browser extension to automatically solve CAPTCHAs.

Requires a one-time Chrome profile setup:
  python runner.py --setup-chrome-profile
"""
import time
import yaml
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any
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
    SELENIUM_WIRE_AVAILABLE = False
    SELENIUM_WIRE_ERROR = str(e)

def _load_site_config(site_key: str) -> dict:
    """Load configuration for a given site from sites.yaml."""
    config_path = Path(__file__).parent.parent / "config" / "sites.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config.get("sites", {}).get(site_key, {})

def _wait_for_rate_limit(site_key: str) -> None:
    """
    Retrieves the RPM limit for the site and waits for a slot from the global rate limiter.
    """
    site_config = _load_site_config(site_key)
    rpm = site_config.get("rate_limit", {}).get("requests_per_minute", 3)

    # Wait for global slot
    logger.info(f"Browser Service: Waiting for global rate limit slot (Target RPM: {rpm})")
    rate_limiter.wait_for_slot(site_key, rpm)

def _get_sessionized_proxy_url(base_proxy_url: str) -> str:
    """
    Injects a unique sessid into the proxy URL for DataImpulse-style sticky sessions.
    Format: http://user__sessid.RANDOM:pass@host:port
    """
    if not base_proxy_url:
        return base_proxy_url
    
    if "://" not in base_proxy_url:
        base_proxy_url = f"http://{base_proxy_url}"

    parsed = urlparse(base_proxy_url)
    if not parsed.username:
        return base_proxy_url
    
    sessid = random.getrandbits(32)
    new_username = f"{parsed.username}__sessid.{sessid}"
    
    auth = new_username
    if parsed.password:
        auth += f":{parsed.password}"
    
    new_netloc = f"{auth}@{parsed.hostname}"
    if parsed.port:
        new_netloc += f":{parsed.port}"
        
    return urlunparse(parsed._replace(netloc=new_netloc))

def _human_scroll(driver: webdriver.Chrome, target: Any):
    """
    Scroll to an element or a pixel amount using variable speed and small steps 
    to mimic a human. target can be an int (pixels to scroll) or a WebElement.
    """
    current_y = driver.execute_script("return window.pageYOffset;")
    
    if isinstance(target, (int, float)):
        target_y = current_y + target
    else:
        # Assume it's an element
        try:
            target_y = target.location['y'] - 200 # Leave some space at the top
        except (AttributeError, KeyError):
            logger.warning("Browser Service: target passed to _human_scroll is neither int nor element")
            return
        
    distance = target_y - current_y
    if abs(distance) < 5:
        return
    
    steps = random.randint(6, 12)
    for i in range(steps):
        # Re-verify current position to avoid cumulative drift
        now_y = driver.execute_script("return window.pageYOffset;")
        remaining = target_y - now_y
        
        if abs(remaining) < 5:
            break
            
        # Move a portion of the remaining distance with some jitter
        step_dist = (remaining / (steps - i)) + random.uniform(-10, 10)
        driver.execute_script(f"window.scrollBy(0, {step_dist});")
        time.sleep(random.uniform(0.1, 0.25))

def _build_driver(ua: Optional[str] = None, proxy: Optional[str] = None, user_data_dir: Optional[str] = None, headless: bool = True) -> webdriver.Chrome:
    """Build a Chrome driver using the provided profile path."""
    options = webdriver.ChromeOptions()
    
    if user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
    
    if ua:
        options.add_argument(f'--user-agent={ua}')
 
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--mute-audio')
    
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
 
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
            logger.warning("Proxy configured but selenium-wire not available. Using direct connection.")
        driver = webdriver.Chrome(options=options)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
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


class BrowserService:
    """Retrieves dynamic data using a Selenium session."""
    
    _browser_semaphore = threading.Semaphore(settings.MAX_CONCURRENT_BROWSERS)

    def get_dynamic_data(self, url: str, site_key: str, fields: List[str], **kwargs) -> Dict[str, Any]:
        """
        Navigate to a listing and extract specified fields with retries.
        """
        max_retries = kwargs.get('retries', getattr(settings, 'RETRY_TIMES', 3))

        for attempt in range(max_retries):
            try:
                result = self._extract_data(url=url, site_key=site_key, fields=fields, **kwargs)
                if result == 'NOT_FOUND':
                    logger.warning(f"Browser Service: Listing not found (404) for {url}")
                    return {}
                if result:
                    return result
                logger.warning(f"Browser Service: Attempt {attempt + 1} failed for {url}")
            except Exception as e:
                logger.error(f"Browser Service: Attempt {attempt + 1} crashed: {e}")
            
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(1, 3)
                logger.info(f"Browser Service: Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
        return {}

    def _extract_data(self, url: str, site_key: str, fields: List[str], **kwargs) -> Optional[Dict[str, Any]]:
        """Core Selenium logic to extract multiple fields."""
        site_config = _load_site_config(site_key)
        dynamic_selectors = site_config.get('dynamic_selectors', {})
        
        if not dynamic_selectors:
            logger.error(f"Browser Service: No dynamic_selectors configured for site '{site_key}'")
            return None

        if not CHROME_PROFILE_DIR.exists():
            logger.error("Browser Service: Chrome profile not found.")
            return None

        ua = get_random_ua()
        proxy_base = settings.STICKY_PROXY_URL
        proxy = _get_sessionized_proxy_url(proxy_base) if proxy_base else None
        
        _wait_for_rate_limit(site_key)

        with self._browser_semaphore:
            logger.info(f"Browser Service: Acquired slot for {url}")
            temp_dir = tempfile.mkdtemp(prefix="chrome_profile_")
            source_profile = CHROME_PROFILE_DIR
            
            driver = None
            try:
                if source_profile.exists():
                    shutil.copytree(source_profile, temp_dir, dirs_exist_ok=True,
                                  ignore=shutil.ignore_patterns('Singleton*', 'Lock', 'RunningChromeVersion'))
                
                headless = kwargs.get('headless', settings.HEADLESS)
                driver = _build_driver(ua=ua, proxy=proxy, user_data_dir=temp_dir, headless=headless)
                
                if hasattr(driver, 'header_overrides'):
                    # Default headers
                    driver.header_overrides = {
                        'Referer': f"{site_config.get('base_url', '')}/",
                        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Upgrade-Insecure-Requests': '1'
                    }

                logger.info(f"Browser Service: Navigating to {url}")
                driver.get(url)

                # Check 404
                if "404" in driver.title or "Not Found" in driver.title:
                    return 'NOT_FOUND'

                extracted_data = {}
                wait = WebDriverWait(driver, 15)

                for field in fields:
                    selector_config = dynamic_selectors.get(field)
                    if not selector_config:
                        logger.warning(f"Browser Service: No selector for field '{field}'")
                        continue
                    
                    try:
                        # Case 1: Complex interaction (like phone click)
                        if isinstance(selector_config, dict) and field == 'agent_phone':
                            show_btn_sel = selector_config.get('show_btn')
                            result_sel = selector_config.get('result')
                            
                            if show_btn_sel:
                                logger.info(f"Browser Service: Waiting for '{field}' show button...")
                                # scroll down a bit to make sure the button is visible
                                _human_scroll(driver, 200)
                                
                                try:
                                    # Filter for visible buttons with physical size
                                    show_buttons = driver.find_elements(By.CSS_SELECTOR, show_btn_sel)
                                    show_btn = [btn for btn in show_buttons if btn.size['height'] > 0 and btn.size['width'] > 0][0]

                                    # 4.1 Human-like scrolling
                                    _human_scroll(driver, show_btn)
                                    time.sleep(random.uniform(0.8, 1.5))
                                    
                                    # 4.2 Human-like mouse movements
                                    logger.info(f"Browser Service: Clicking '{field}' button with ActionChains jitter...")
                                    actions = ActionChains(driver)
                                    
                                    # Hover with a bit of "jitter"
                                    actions.move_to_element_with_offset(show_btn, random.randint(-5, 5), random.randint(-5, 5))
                                    actions.pause(random.uniform(0.5, 1.2))
                                    
                                    # Click with slight offset
                                    actions.click_and_hold(show_btn)
                                    actions.pause(random.uniform(0.1, 0.2)) # Brief hold
                                    actions.release()
                                    actions.perform()
                                    
                                except Exception as click_e:
                                    logger.warning(f"Browser Service: Resilient click failed for {field}, trying JS fallback: {click_e}")
                                    try:
                                        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, show_btn_sel)))
                                        driver.execute_script("arguments[0].click();", btn)
                                    except:
                                        pass
                                
                            logger.info(f"Browser Service: Waiting for {field} result (NopeCHA may auto-solve CAPTCHA)...")
                            agent_phone_wait = WebDriverWait(driver, 200)
                            result_el = agent_phone_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, result_sel)))
                            val = result_el.text.strip()
                            
                            if val:
                                logger.success(f"Browser Service: Got {field}: {val}")
                                extracted_data[field] = val
                            else:
                                logger.warning(f"Browser Service: {field} element visible but text was empty")
                        
                        # Case 2: Direct extraction
                        else:
                            # Handle attribute vs text
                            if "::attr(" in selector_config:
                                base_sel, attr = selector_config.split("::attr(")
                                attr = attr.rstrip(")")
                                el = driver.find_element(By.CSS_SELECTOR, base_sel)
                                extracted_data[field] = el.get_attribute(attr)
                            elif "::text" in selector_config:
                                base_sel = selector_config.replace("::text", "")
                                el = driver.find_element(By.CSS_SELECTOR, base_sel)
                                extracted_data[field] = el.text.strip()
                            else:
                                el = driver.find_element(By.CSS_SELECTOR, selector_config)
                                extracted_data[field] = el.text.strip()
                                
                    except Exception as fe:
                        logger.warning(f"Browser Service: Failed to extract field '{field}': {fe}")

                return extracted_data

            finally:
                if driver: driver.quit()
                shutil.rmtree(temp_dir, ignore_errors=True)
