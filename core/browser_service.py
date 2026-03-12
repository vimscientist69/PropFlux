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

def _human_scroll(driver: webdriver.Chrome, element):
    """Scroll to an element using variable speed and small steps to mimic a human."""
    target_y = element.location['y'] - 200 # Leave some space at the top
    current_y = driver.execute_script("return window.pageYOffset;")
    distance = target_y - current_y
    
    if distance > 0:
        steps = random.randint(5, 12)
        for i in range(steps):
            amount = (distance / steps) + random.uniform(-10, 10)
            driver.execute_script(f"window.scrollBy(0, {amount});")
            time.sleep(random.uniform(0.1, 0.3))

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
    # If we need extension for CAPTCHA, don't disable extensions
    # options.add_argument('--disable-extensions')
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
                        if isinstance(selector_config, dict):
                            show_btn_sel = selector_config.get('show_btn')
                            result_sel = selector_config.get('result')
                            
                            if show_btn_sel:
                                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, show_btn_sel)))
                                _human_scroll(driver, btn)
                                ActionChains(driver).move_to_element(btn).click().perform()
                                
                            result_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, result_sel)))
                            extracted_data[field] = result_el.text.strip()
                        
                        # Case 2: Direct extraction
                        else:
                            # Handle attribute vs text
                            if "::attr(" in selector_config:
                                base_sel, attr = selector_config.split("::attr(")
                                attr = attr.rstrip(")")
                                el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, base_sel)))
                                extracted_data[field] = el.get_attribute(attr)
                            elif "::text" in selector_config:
                                base_sel = selector_config.replace("::text", "")
                                el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, base_sel)))
                                extracted_data[field] = el.text.strip()
                            else:
                                el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector_config)))
                                extracted_data[field] = el.text.strip()
                                
                    except Exception as fe:
                        logger.warning(f"Browser Service: Failed to extract field '{field}': {fe}")

                return extracted_data

            finally:
                if driver: driver.quit()
                shutil.rmtree(temp_dir, ignore_errors=True)
