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
    
    def start_requests(self):
        """Generate initial requests for listing pages."""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error
            )
    
    def parse(self, response):
        """Parse listing links from the search page."""
        self.current_page += 1
        from loguru import logger
        logger.info(f"Parsing page {self.current_page}: {response.url}")

        if self.current_page == 1:
            try:
                html_path = f"output/debug_property24_page{self.current_page}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info(f"Debug HTML saved to {html_path}")
            except Exception as e:
                logger.error(f"Failed to capture debug info: {e}")
        
        # Extract listing links
        listing_links = self.parser.parse_listing_links(response)
        
        # DEV LIMIT: only processing first 3 links
        listing_links = listing_links[:3]
        logger.info(f"Dev limit: only processing first {len(listing_links)} links")
        
        # Follow each listing link
        for link in listing_links:
            yield scrapy.Request(
                url=link,
                callback=self.parse_listing,
                errback=self.handle_error
            )
        
        # Follow pagination
        if self.current_page < self.max_pages:
            next_page = self.parser.parse_next_page(response)
            if next_page:
                logger.info(f"Following next page: {next_page}")
                yield scrapy.Request(
                    url=next_page,
                    callback=self.parse,
                    errback=self.handle_error
                )
            else:
                logger.info("No more pages found")
        else:
            logger.info(f"Reached max pages limit: {self.max_pages}")

