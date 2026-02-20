"""
reCAPTCHA resolver using NopeCHA service.
"""
import os
import nopecha
from loguru import logger
from config.settings import settings

class CaptchaResolver:
    """Handles CAPTCHA solving using NopeCHA."""
    
    def __init__(self):
        self.api_key = settings.NOPECHA_API_KEY
        if not self.api_key:
            logger.error("NOPECHA_API_KEY not found in settings")
        nopecha.api_key = self.api_key

    def solve_recaptcha(self, site_key: str, url: str) -> str:
        """
        Solve reCAPTCHA v2/v3 and return the token.
        
        Args:
            site_key: The sitekey for the reCAPTCHA
            url: The page URL where the reCAPTCHA is located
            
        Returns:
            The solved reCAPTCHA token
        """
        logger.info(f"Solving reCAPTCHA for {url}...")
        try:
            token = nopecha.Token.solve(
                type='recaptcha2', # Property24 uses v2-like challenge often
                sitekey=site_key,
                url=url
            )
            logger.success("reCAPTCHA solved successfully")
            return token
        except Exception as e:
            logger.error(f"Failed to solve reCAPTCHA: {e}")
            return ""
