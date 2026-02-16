"""
Parser module for extracting data from HTML using CSS selectors.
"""
from typing import Dict, Any, Optional
from scrapy.http import Response
from loguru import logger


class Parser:
    """Handles parsing of HTML content using configured selectors."""
    
    def __init__(self, selectors: Dict[str, str]):
        """
        Initialize parser with site-specific selectors.
        
        Args:
            selectors: Dictionary mapping field names to CSS selectors
        """
        self.selectors = selectors
    
    def parse_listing_links(self, response: Response) -> list[str]:
        """
        Extract listing URLs from a search/listing page.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            List of absolute URLs to individual listings
        """
        selector = self.selectors.get('listing_links')
        if not selector:
            logger.warning("No listing_links selector configured")
            return []
        
        links = response.css(selector).getall()
        # Convert to absolute URLs
        absolute_links = [response.urljoin(link) for link in links]
        
        logger.info(f"Found {len(absolute_links)} listing links")
        return absolute_links
    
    def parse_next_page(self, response: Response) -> Optional[str]:
        """
        Extract next page URL from pagination.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            Absolute URL to next page, or None if no next page
        """
        selector = self.selectors.get('next_page')
        if not selector:
            return None
        
        next_page = response.css(selector).get()
        if next_page:
            return response.urljoin(next_page)
        return None
    
    def parse_listing_detail(self, response: Response) -> Dict[str, Any]:
        """
        Extract all fields from a listing detail page.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            Dictionary with extracted listing data
        """
        data = {
            'listing_url': response.url,
        }
        
        # Required fields
        required_fields = [
            'title', 'price', 'location', 'bedrooms', 
            'bathrooms', 'property_type', 'description'
        ]
        
        # Optional fields
        optional_fields = [
            'agent_name', 'agent_phone', 'listing_id', 'date_posted'
        ]
        
        # Extract required fields
        for field in required_fields:
            selector = self.selectors.get(field)
            if selector:
                value = response.css(selector).get()
                data[field] = value.strip() if value else None
            else:
                data[field] = None
                logger.warning(f"No selector configured for required field: {field}")
        
        # Extract optional fields
        for field in optional_fields:
            selector = self.selectors.get(field)
            if selector:
                value = response.css(selector).get()
                data[field] = value.strip() if value else None
            else:
                data[field] = None
        
        return data
    
    def extract_text(self, response: Response, selector: str) -> Optional[str]:
        """
        Helper method to extract and clean text from a selector.
        
        Args:
            response: Scrapy Response object
            selector: CSS selector string
            
        Returns:
            Cleaned text or None
        """
        value = response.css(selector).get()
        return value.strip() if value else None
