"""
Selenium-based phone number retrieval using the NopeCHA browser extension
to automatically solve CAPTCHAs on Property24.
"""
import os
import io
import zipfile
import yaml
import requests as http_requests
from pathlib import Path
from typing import Optional
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.settings import settings

# Cache the extension to avoid re-downloading every run
EXT_DIR = Path("output/nopecha_ext")
NOPECHA_EXT_URL = "https://github.com/NopeCHALLC/nopecha-extension/releases/latest/download/chromium.zip"


def _load_phone_config(site_key: str) -> dict:
    """Load phone_retrieval selectors for a given site from sites.yaml."""
    config_path = Path(__file__).parent.parent / "config" / "sites.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    site = config.get("sites", {}).get(site_key, {})
    return site.get("phone_retrieval", {})


def _ensure_extension() -> str:
    """Download and cache the NopeCHA extension. Returns the path to the extracted dir."""
    if EXT_DIR.exists() and any(EXT_DIR.iterdir()):
        logger.info("Phone Service: Using cached NopeCHA extension")
        return str(EXT_DIR.resolve())

    logger.info("Phone Service: Downloading NopeCHA extension...")
    EXT_DIR.mkdir(parents=True, exist_ok=True)

    response = http_requests.get(NOPECHA_EXT_URL, timeout=30)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(path=str(EXT_DIR))

    logger.success("Phone Service: Extension downloaded and extracted")
    return str(EXT_DIR.resolve())


def _build_driver(ext_dir: str) -> webdriver.Chrome:
    """Build a Chrome driver with the NopeCHA extension loaded."""
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")  # Remove this line to watch the browser during debugging
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"--load-extension={ext_dir}")

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    return driver


class PhoneService:
    """Retrieves protected phone numbers using a Selenium session with the NopeCHA extension."""

    def get_property24_phone(self, url: str, **kwargs) -> Optional[str]:
        """
        Navigate to a Property24 listing, click 'Show Number', let NopeCHA
        auto-solve any CAPTCHA, and return the revealed phone number.
        """
        return self._get_phone(url=url, site_key='property24')

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

        ext_dir = _ensure_extension()
        driver = _build_driver(ext_dir)

        try:
            # 1. Configure NopeCHA with the API key
            logger.info("Phone Service: Configuring NopeCHA extension...")
            driver.get(f"https://nopecha.com/setup#{api_key}")

            # 2. Navigate to the listing page
            logger.info(f"Phone Service: Navigating to {url}")
            driver.get(url)

            # 3. Find and click the "Show Contact Number" button
            logger.info("Phone Service: Waiting for 'Show Number' button...")
            wait = WebDriverWait(driver, 20)
            show_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, show_btn_sel)))
            logger.info("Phone Service: Clicking 'Show Number' button...")
            driver.execute_script("arguments[0].click();", show_btn)

            # 4. Wait for the phone number (NopeCHA auto-solves the CAPTCHA)
            logger.info("Phone Service: Waiting for phone number (NopeCHA will auto-solve CAPTCHA)...")
            phone_el = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, phone_result_sel)))
            phone = phone_el.text.strip()

            if phone:
                logger.success(f"Phone Service: Got phone number: {phone}")
                return phone

            logger.warning("Phone Service: Phone element visible but text was empty")
            return None

        except TimeoutException:
            logger.error("Phone Service: Timed out waiting for button or phone number")
            return None
        except NoSuchElementException as e:
            logger.error(f"Phone Service: Element not found: {e}")
            return None
        except Exception as e:
            logger.error(f"Phone Service: Unexpected error: {e}")
            return None
        finally:
            driver.quit()
            logger.info("Phone Service: Driver closed")
