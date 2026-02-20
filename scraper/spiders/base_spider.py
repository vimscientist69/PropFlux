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


class BaseRealEstateSpider(scrapy.Spider):
    """Base spider with common real estate scraping logic."""
    
    # Override in subclasses
    site_key = None
    
    def __init__(self, *args, **kwargs):
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
            self.start_urls = self.site_config.get('start_urls', [])
        
        # Pagination settings
        self.pagination_config = self.site_config.get('pagination', {})
        self.max_pages = self.pagination_config.get('max_pages', 50)
        self.current_page = 0
        self.total_pages = None
        
        # Development limits
        self.dev_limit = 3  # Set to None for no limit
        
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
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error
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
            self.total_pages = self.parser.parse_total_pages(response)
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
                # Assuming base_url is configured and doesn't end with / if we add one
                base_url = self.site_config.get('base_url', '').rstrip('/')
                # If the start_url already has the query params we need, we might need a smarter merge
                # For now, let's assume the template is correct as per user request
                return template.format(base_url=base_url, page=next_page_num)
        
        # Fallback to next link extraction
        return self.parser.parse_next_page(response)

    def parse(self, response: Response) -> Generator:
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
            yield self.parse_listing(response)
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
        for link in listing_links:
            yield scrapy.Request(
                url=link,
                callback=self.parse_listing,
                errback=self.handle_error
            )
        
        # Follow pagination
        next_page = self.get_next_page_url(response)
        if next_page:
            logger.info(f"Following next page: {next_page}")
            yield scrapy.Request(
                url=next_page,
                callback=self.parse,
                errback=self.handle_error
            )
    
    def parse_listing(self, response: Response) -> Dict[str, Any]:
        """
        Parse individual listing detail page.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            Normalized listing data
        """
        logger.debug(f"Parsing listing: {response.url}")
        
        # Extract raw data
        raw_data = self.parser.parse_listing_detail(response)
        
        # Item metadata (normalization happens in pipeline)
        raw_data['source_site'] = self.site_key
        raw_data['scraped_at'] = scrapy.utils.misc.load_object(
            'datetime.datetime'
        ).now().isoformat()
        
        return raw_data
    
    def handle_error(self, failure):
        """
        Handle request errors.
        
        Args:
            failure: Twisted Failure object
        """
        logger.error(f"Request failed: {failure.request.url}")
        logger.error(f"Error: {failure.value}")
