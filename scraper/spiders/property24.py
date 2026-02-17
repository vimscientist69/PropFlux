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
        """Generate initial requests with Playwright enabled for listing pages."""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,
                meta={
                    "playwright": True,
                    "playwright_include_page": False,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "networkidle",
                    },
                }
            )
    
    def parse(self, response):
        """Override parse to use Playwright for pagination."""
        self.current_page += 1
        from loguru import logger
        logger.info(f"Parsing page {self.current_page}: {response.url}")
        
        # Extract listing links
        listing_links = self.parser.parse_listing_links(response)
        
        # Follow each listing link (without Playwright - regular HTTP request)
        for link in listing_links:
            yield scrapy.Request(
                url=link,
                callback=self.parse_listing,
                errback=self.handle_error
            )
        
        # Follow pagination with Playwright
        if self.current_page < self.max_pages:
            next_page = self.parser.parse_next_page(response)
            if next_page:
                logger.info(f"Following next page: {next_page}")
                yield scrapy.Request(
                    url=next_page,
                    callback=self.parse,
                    errback=self.handle_error,
                    meta={
                        "playwright": True,
                        "playwright_include_page": False,
                        "playwright_page_goto_kwargs": {
                            "wait_until": "networkidle",
                        },
                    }
                )
            else:
                logger.info("No more pages found")
        else:
            logger.info(f"Reached max pages limit: {self.max_pages}")

