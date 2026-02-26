"""
Property24 spider.
"""
import scrapy
from loguru import logger
from scrapy.utils.defer import deferred_to_future
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
    
    async def parse(self, response):
        """Parse listing links from the search page."""
        # Capture debug info on first page
        if self.current_page == 0:  # current_page starts at 0, becomes 1 in super().parse()
            try:
                import os
                os.makedirs("output", exist_ok=True)
                html_path = f"output/debug_property24_page1.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info(f"Debug HTML saved to {html_path}")
            except Exception as e:
                logger.error(f"Failed to capture debug info: {e}")
        
        # Use base class logic to process links and pagination
        async for item in super().parse(response):
            yield item

    async def parse_listing(self, response):
        """
        Custom parse_listing for Property24 to include phone number retrieval.
        Using async/await and deferToThread to run Selenium in parallel.
        """
        from twisted.internet.threads import deferToThread
        from core.phone_service import PhoneService
        
        # Get base item from the async generator
        item = None
        async for base_item in super().parse_listing(response):
            item = base_item
            break
        
        if not item:
            return

        # Guard: Only fetch phone if it's not already in the page's HTML
        if item.get('agent_phone'):
            yield item
            return

        try:
            # Run the blocking Selenium call in a separate thread
            # Wrap deferToThread in deferred_to_future for clean async/await in Scrapy
            phone = await deferred_to_future(deferToThread(PhoneService().get_property24_phone, response.url))
            if phone:
                item['agent_phone'] = phone
                logger.info(f"Updated agent_phone for {item.get('listing_id')}")

        except Exception as e:
            logger.error(f"Error in Property24 phone extraction: {e}")

        yield item
