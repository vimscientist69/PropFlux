"""
Base spider class with common functionality.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Generator
import scrapy
from scrapy.http import Response
from loguru import logger

from core.parser import Parser
from core.normalizer import Normalizer
from config.settings import settings


class BaseRealEstateSpider(scrapy.Spider):
    """Base spider with common real estate scraping logic."""
    
    # Override in subclasses
    site_key = None
    
    def __init__(self, start_urls=None, max_pages=None, limit=None, skip_dynamic_fields=False, *args, **kwargs):
        """Initialize spider with configuration."""
        super().__init__(*args, **kwargs)
        
        # Load site configuration
        self.config = self._load_config()
        self.site_config = self.config['sites'].get(self.site_key, {})
        
        # Initialize parser and normalizer
        selectors = self.site_config.get('selectors', {})
        self.parser = Parser(selectors)
        self.normalizer = Normalizer()
        
        # Set start URLs if not already provided (e.g., via command line)
        if not self.start_urls:
            self.start_urls = start_urls or self.site_config.get('start_urls', [])
        
        self.pagination_config = self.site_config.get('pagination', {})
        self.max_pages = max_pages or self.pagination_config.get('max_pages', 50)
        
        self.current_page = 0
        self.total_pages = None
        self.items_requested = 0
        
        # Hard limit from runner
        self.limit = limit or kwargs.get('limit')
        if self.limit:
            # If hard limit is set, we ignore max_pages and dev_limit
            self.max_pages = 999999
            self.dev_limit = None
            logger.info(f"Hard limit of {self.limit} items enabled. Overriding page/dev limits.")
        else:
            self.dev_limit = settings.DEV_LIMIT
        
        self.skip_dynamic_fields = skip_dynamic_fields

        logger.info(f"Initialized {self.name} spider for {self.site_key}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load sites configuration from YAML."""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'sites.yaml'
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def start_requests(self) -> Generator:
        """Generate initial requests for listing pages."""
        for url in self.start_urls:
            raw_url = url.split('/p')[0] if '/p' in url else url
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,
                meta={'search_base_url': raw_url}
            )

    def get_next_page_url(self, response: Response) -> Optional[str]:
        """
        Get the URL for the next page based on patterns or link extraction.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            URL for next page, or None
        """
        if self.total_pages is None:
            self.total_pages = self.parser.parse_total_pages(self.pagination_config, response)
            if self.total_pages:
                logger.info(f"Total pages found: {self.total_pages}")
        
        next_page_num = self.current_page + 1
        
        # Check hard limits
        if next_page_num > self.max_pages:
            logger.info(f"Reached max_pages limit: {self.max_pages}")
            return None
            
        if next_page_num > self.total_pages:
            logger.info(f"Reached end of results (page {self.total_pages})")
            return None
            
        # Try pattern-based pagination first
        pag_type = self.pagination_config.get('type')
        if pag_type == 'pattern':
            template = self.pagination_config.get('url_template')
            if template:
                # Use the actual search results URL from this specific request chain
                base_url = response.meta.get('search_base_url', '').rstrip('/')
                return template.format(base_url=base_url, page=next_page_num)
        
        # Fallback to next link extraction
        return self.parser.parse_next_page(response)

    async def parse(self, response: Response) -> Generator:
        """
        Parse listing page and extract listing URLs.
        
        Args:
            response: Scrapy Response object
            
        Yields:
            Requests to listing detail pages and next page or listing data
        """

        # Check if this is a direct listing detail page
        if self.parser.is_detail_page(response):
            logger.info(f"Direct listing detail page detected: {response.url}")
            async for item in self.parse_listing(response):
                yield item
            return

        self.current_page += 1
        logger.info(f"Parsing page {self.current_page}: {response.url}")
        
        # Extract listing links
        listing_links = self.parser.parse_listing_links(response)
        
        # Apply development limit if set
        if self.dev_limit:
            listing_links = listing_links[:self.dev_limit]
            logger.info(f"Dev limit: only processing first {len(listing_links)} links")
        
        # Follow each listing link
        # Follow each listing link up to the limit
        for link in listing_links:
            if self.limit and self.items_requested >= self.limit:
                logger.info(f"Hard limit of {self.limit} requests reached. Stopping.")
                return # Stop processing this page and don't look for more
                
            self.items_requested += 1
            
            yield scrapy.Request(
                url=link,
                callback=self.parse_listing,
                errback=self.handle_error
            )
        
        # Pagination
        next_page = self.get_next_page_url(response)
        if next_page:
            # Check hard limit before continuing to next page
            if self.limit and self.items_requested >= self.limit:
                logger.info(f"Hard limit of {self.limit} reached. Not requesting next page.")
                return
            
            logger.debug(f"Following next page: {next_page}")
            yield scrapy.Request(
                    url=next_page,
                    callback=self.parse,
                    errback=self.handle_error,
                    meta={'search_base_url': response.meta.get('search_base_url')}
                )
    
    async def parse_listing(self, response: Response) -> Generator:
        """
        Parse individual listing detail page.
        
        Args:
            response: Scrapy Response object
            
        Yields:
            Normalized listing data
        """
        # No need for limit check here as it's handled in the discovery loop (parse)
        logger.debug(f"Parsing listing: {response.url}")
        # Extract raw data
        raw_data = self.parser.parse_listing_detail(response)
        
        # Item metadata (normalization happens in pipeline)
        raw_data['source_site'] = self.site_key
        raw_data['scraped_at'] = scrapy.utils.misc.load_object(
            'datetime.datetime'
        ).now().isoformat()
        
        yield raw_data
    
    def handle_error(self, failure):
        """
        Handle request errors.
        
        Args:
            failure: Twisted Failure object
        """
        logger.error(f"Request failed: {failure.request.url}")
        logger.error(f"Error: {failure.value}")
