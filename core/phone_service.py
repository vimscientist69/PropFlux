"""
Service for retrieving protected phone numbers from real estate sites.
"""
import requests
from typing import Optional
from loguru import logger
from core.captcha_resolver import CaptchaResolver
from config.settings import settings

class PhoneService:
    """Handles API requests to fetch protected phone numbers."""
    
    def __init__(self):
        self.resolver = CaptchaResolver()
        self.session = requests.Session()
        self.session.headers.update({
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json; charset=UTF-8',
            'x-requested-with': 'XMLHttpRequest',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_property24_phone(self, 
                             url: str, 
                             agent_id: int, 
                             contact_value: str, 
                             listing_number: int) -> Optional[str]:
        """
        Retrieve agent phone number for Property24.
        
        Args:
            url: The listing URL
            agent_id: The ID of the agent
            contact_value: The dynamic 'value' from js_agentDetails
            listing_number: The listing ID
            
        Returns:
            Cleaned phone number or None
        """
        site_key = settings.PROPERTY24_RECAPTCHA_SITEKEY
        if not site_key:
            logger.error("PROPERTY24_RECAPTCHA_SITEKEY not found in settings")
            return None

        # Solve CAPTCHA
        token = self.resolver.solve_recaptcha_v3(site_key, url)
        if not token:
            return None

        # Prepare request
        endpoint = "https://www.property24.com/contact/numbers"
        payload = {
            "value": contact_value,
            "agentId": agent_id,
            "countryId": 1,
            "isAdminLead": False,
            "hideAgentName": True,
            "listingNumber": {
                "isValid": True,
                "number": {
                    "number": listing_number,
                    "isValid": True
                }
            },
            "recaptchaToken": token
        }

        try:
            logger.info(f"Fetching phone number for agent {agent_id}...")
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                # The response structure might vary, but usually contains number or message
                # Based on typical Property24 responses
                logger.success(f"Successfully retrieved phone number info")
                # Usually it returns a message with the phone number or HTML
                return str(data) 
            else:
                logger.warning(f"API Error: {data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Failed to fetch phone number: {e}")
            return None
