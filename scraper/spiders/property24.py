"""
Property24 spider.
"""
import scrapy
from .base_spider import BaseRealEstateSpider


class Property24Spider(BaseRealEstateSpider):
    """Spider for Property24 website."""
    
    name = 'property24'
    site_key = 'property24'
    
    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
    }
    
    def parse(self, response):
        """Parse listing links from the search page."""
        # Capture debug info on first page
        if self.current_page == 0:  # current_page starts at 0, becomes 1 in super().parse()
            try:
                import os
                os.makedirs("output", exist_ok=True)
                html_path = f"output/debug_property24_page1.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                from loguru import logger
                logger.info(f"Debug HTML saved to {html_path}")
            except Exception as e:
                from loguru import logger
                logger.error(f"Failed to capture debug info: {e}")
        
        # Use base class logic to process links and pagination
        yield from super().parse(response)

    def parse_listing(self, response):
        """
        Custom parse_listing for Property24 to include phone number retrieval.
        Using guard clauses to handle unhappy paths early and reduce nesting.
        """
        item = super().parse_listing(response)
        
        # Guard: Only proceed if phone is missing
        if item.get('agent_phone'):
            return item

        try:
            import re
            from core.phone_service import PhoneService
            from loguru import logger
            
            # Extract dynamic values
            agent_url = response.css(self.site_config['selectors'].get('agent_profile_url')).get()
            contact_val = response.css(self.site_config['selectors'].get('contact_value')).get()
            listing_id = item.get('listing_id')
            
            # Guard: Ensure all values are present
            if not all([agent_url, contact_val, listing_id]):
                return item

            # Guard: Extract agent ID from url like /Agent/Profile/413016
            agent_match = re.search(r'/Profile/(\d+)', agent_url)
            if not agent_match:
                return item
            
            # Fetch phone number
            service = PhoneService()
            phone_data = service.get_property24_phone(
                url=response.url,
                agent_id=int(agent_match.group(1)),
                contact_value=contact_val,
                listing_number=int(listing_id)
            )
            
            if phone_data:
                item['agent_phone'] = phone_data
                logger.info(f"Updated agent_phone for {listing_id}")
                
        except Exception as e:
            from loguru import logger
            logger.error(f"Error in Property24 custom phone extraction: {e}")
        
        return item

