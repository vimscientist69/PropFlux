"""
reCAPTCHA resolver using NopeCHA service.
"""
import os
import nopecha
from loguru import logger
from config.settings import settings
from nopecha.api.requests import RequestsAPIClient

class CaptchaResolver:
    """Handles CAPTCHA solving using NopeCHA."""
    
    def __init__(self):
        self.api_key = settings.NOPECHA_API_KEY
        if not self.api_key:
            logger.error("NOPECHA_API_KEY not found in settings")
        nopecha.api_key = self.api_key

    def solve_recaptcha_v3(self, site_key: str, url: str) -> str:
        """
        Solve reCAPTCHA v3 and return the token.
        
        Args:
            site_key: The sitekey for the reCAPTCHA
            url: The page URL where the reCAPTCHA is located
            
        Returns:
            The solved reCAPTCHA token
        """
        logger.info(f"Solving reCAPTCHA for {url}...")
        try:
            client = RequestsAPIClient(self.api_key)
            token = client.solve_recaptcha_v2(
                site_key,
                url,
            )
            # token = client.solve_recaptcha_v3(
            #     site_key,
            #     url,
            # )
            logger.success("reCAPTCHA solved successfully")
            return token
        except Exception as e:
            logger.error(f"Failed to solve reCAPTCHA: {e}")
            return ""