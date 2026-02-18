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

