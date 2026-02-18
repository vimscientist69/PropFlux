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
    
    def parse_total_pages(self, response: Response) -> int:
        """
        Extract total number of pages from pagination.
        
        Args:
            response: Scrapy Response object
            
        Returns:
            Total number of pages (default 1 if not found)
        """
        selector = self.selectors.get('total_pages_selector')
        if not selector:
            return 1
        
        total_text = response.css(selector).get()
        if total_text:
            try:
                # Extract digits from text like "Page 1 of 50" or just "50"
                import re
                match = re.search(r'(\d+)', total_text)
                if match:
                    return int(match.group(1))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse total pages from text: {total_text}")
        
        return 1

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
