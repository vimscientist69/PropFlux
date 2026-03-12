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
        link_selector = self.selectors.get('listing_links')
        container_selector = self.selectors.get('listing_container')
        
        if not link_selector:
            logger.warning("No listing_links selector configured")
            return []
        
        if container_selector:
            # Extract one link per container for better accuracy
            containers = response.css(container_selector)
            links = []
            for container in containers:
                link = container.css(link_selector).get()
                if link:
                    links.append(link)
        else:
            # Fallback to direct selection
            links = response.css(link_selector).getall()
            
        # Convert to absolute URLs and remove duplicates while preserving order
        absolute_links = []
        seen = set()
        for link in links:
            abs_link = response.urljoin(link)
            if abs_link not in seen:
                absolute_links.append(abs_link)
                seen.add(abs_link)
        
        logger.info(f"Found {len(absolute_links)} unique listing links")
        return absolute_links
    
    def parse_total_pages(self, pagination_config: Dict[str, Any], response: Response) -> int:
        """
        Extract total number of pages from pagination.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            Total number of pages (default 1 if not found)
        """
        # get selector from pagination config
        selector = pagination_config.get('total_pages_selector')
        if not selector:
            return 1
        
        total_pages = int(response.css(selector).get())

        return total_pages if total_pages > 1 else 1

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
            response: Response object
            
        Returns:
            Dictionary with extracted listing data
        """
        data = {
            'listing_url': response.url,
            'suburb': None,
            'city': None,
            'province': None
        }
        
        # Required fields
        required_fields = [
            'title', 'price', 'location', 'bedrooms', 
            'bathrooms', 'property_type', 'description'
        ]
        
        # Optional fields
        optional_fields = [
            'agent_name', 'agent_phone', 'agency_name', 'listing_id', 'date_posted',
            'erf_size', 'floor_size', 'rates_and_taxes', 'levies', 'garages', 
            'parking', 'backup_power', 'security', 'pets_allowed'
        ]

        # Initialize Data Quality flags (normalized later)
        data['is_auction'] = False
        data['is_private_seller'] = False
        try:
            # Extract both required and optional fields
            all_fields = required_fields + optional_fields
            for field in all_fields:
                selector = self.selectors.get(field)
                if selector:
                    value = self.extract_text(response, selector)

                    data[field] = value
                    if not value and field in required_fields:
                        logger.warning(f"Required field '{field}' is empty using selector: '{selector}' for listing '{response.url}'")
                else:
                    data[field] = None
                    if field in required_fields:
                        logger.warning(f"No selector configured for required field: '{field}' for listing '{response.url}'")
        except Exception as e:
            logger.error(f"Failed to parse listing detail: '{e}' for listing '{response.url}'")
            return None 
        
        return data

    def extract_text(self, response: Response, selector: str) -> Optional[str]:
        """
        Extract and clean text from a selector with fallback for nested text.
        Supports both CSS and XPath (if selector starts with '/').
        
        Logic:
        1. If selector starts with '/', treat as XPath.
        2. Else, try the selector as CSS.
        3. If CSS returns nothing and contains '::text', fall back to extracting 
           ALL nested text from the element (using XPath string(.)).
        
        Args:
            response: Response or Selector object
            selector: CSS or XPath selector string
            
        Returns:
            Cleaned text or None
        """
        # 1. Handle XPath
        if selector.startswith('/'):
            value = response.xpath(selector).get()
        else:
            # 2. Try provided CSS selector
            value = response.css(selector).get()

            value_empty = (value and not value.strip()) or not value

            # 3. Fallback for nested text if ::text failed
            if value_empty and "::text" in selector:
                base_selector = selector.replace("::text", "")
                # string(.) gets all nested text content concatenated
                value = response.css(base_selector).xpath("string(.)").get()
                if value:
                    logger.debug(f"Nested text fallback used for selector '{selector}'")
                
        return value.strip() if value else None
    
    def is_detail_page(self, response: Response) -> bool:
        """
        Check if the current response is a listing detail page.
        """
        title_selector = self.selectors.get('title')
        container_selector = self.selectors.get('listing_container')
        
        if not title_selector or not response.css(title_selector).get():
            return False
            
        if container_selector and response.css(container_selector):
            return False

        return True
