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
        
        # Set start URLs
        self.start_urls = self.site_config.get('start_urls', [])
        
        # Pagination settings
        self.pagination_config = self.site_config.get('pagination', {})
        self.max_pages = self.pagination_config.get('max_pages', 50)
        self.current_page = 0
        
        logger.info(f"Initialized {self.name} spider for {self.site_key}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load sites configuration from YAML."""
        config_path = Path(__file__).parent.parent / 'config' / 'sites.yaml'
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def parse(self, response: Response) -> Generator:
        """
        Parse listing page and extract listing URLs.
        
        Args:
            response: Scrapy Response object
            
        Yields:
            Requests to listing detail pages and next page
        """
        self.current_page += 1
        logger.info(f"Parsing page {self.current_page}: {response.url}")
        
        # Extract listing links
        listing_links = self.parser.parse_listing_links(response)
        
        # Follow each listing link
        for link in listing_links:
            yield scrapy.Request(
                url=link,
                callback=self.parse_listing,
                errback=self.handle_error
            )
        
        # Follow pagination if not at max pages
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
        
        # Normalize data
        normalized_data = self.normalizer.normalize_listing(raw_data)
        
        # Add metadata
        normalized_data['source_site'] = self.site_key
        normalized_data['scraped_at'] = scrapy.utils.misc.load_object(
            'datetime.datetime'
        ).now().isoformat()
        
        return normalized_data
    
    def handle_error(self, failure):
        """
        Handle request errors.
        
        Args:
            failure: Twisted Failure object
        """
        logger.error(f"Request failed: {failure.request.url}")
        logger.error(f"Error: {failure.value}")
