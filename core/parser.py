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
    
    def is_detail_page(self, response: Response) -> bool:
        """
        Check if the current response is a listing detail page.
        
        Logic: Returns True if the 'title' selector matches something,
        but the 'listing_links' or 'listing_container' selectors do not.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            True if it's a detail page, False otherwise
        """
        title_selector = self.selectors.get('title')
        container_selector = self.selectors.get('listing_container')
        
        # Must have a title to be a detail page
        if not title_selector or not response.css(title_selector).get():
            logger.info(f"No title selector or no title content found from html")
            return False
            
        # If listing_container is present, it's a search page
        if container_selector and response.css(container_selector):
            logger.info(f"Container selector present and it is found in html")
            return False

        return True
    
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
