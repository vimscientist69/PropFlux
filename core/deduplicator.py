"""
Deduplicator module for removing duplicate listings.
"""
from typing import List, Dict, Any, Set
from loguru import logger


class Deduplicator:
    """Handles deduplication of listings."""
    
    def __init__(self):
        """Initialize deduplicator with tracking sets."""
        self.seen_ids: Set[str] = set()
        self.seen_urls: Set[str] = set()
        self.duplicate_count = 0
    
    def is_duplicate(self, listing: Dict[str, Any]) -> bool:
        """
        Check if a listing is a duplicate.
        
        Priority:
        1. Check listing_id if available
        2. Fall back to URL
        
        Args:
            listing: Listing data dictionary
            
        Returns:
            True if duplicate, False if unique
        """
        # Try listing_id first (most reliable)
        listing_id = listing.get('listing_id')
        if listing_id:
            if listing_id in self.seen_ids:
                self.duplicate_count += 1
                logger.debug(f"Duplicate found by ID: {listing_id}")
                return True
            self.seen_ids.add(listing_id)
            return False
        
        # Fall back to URL
        url = listing.get('listing_url')
        if url:
            if url in self.seen_urls:
                self.duplicate_count += 1
                logger.debug(f"Duplicate found by URL: {url}")
                return True
            self.seen_urls.add(url)
            return False
        
        # If no ID or URL, can't determine duplicates
        logger.warning("Listing has no ID or URL for deduplication")
        return False
    
    def deduplicate_batch(self, listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicates from a batch of listings.
        
        Args:
            listings: List of listing dictionaries
            
        Returns:
            List of unique listings
        """
        unique_listings = []
        
        for listing in listings:
            if not self.is_duplicate(listing):
                unique_listings.append(listing)
        
        logger.info(
            f"Deduplication complete: {len(unique_listings)} unique, "
            f"{self.duplicate_count} duplicates removed"
        )
        
        return unique_listings
    
    def reset(self):
        """Reset the deduplicator state."""
        self.seen_ids.clear()
        self.seen_urls.clear()
        self.duplicate_count = 0
        logger.info("Deduplicator reset")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get deduplication statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            'unique_ids': len(self.seen_ids),
            'unique_urls': len(self.seen_urls),
            'duplicates_removed': self.duplicate_count
        }
