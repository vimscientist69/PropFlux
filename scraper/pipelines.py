"""
Scrapy pipelines for processing scraped items.
"""
from typing import Dict, Any
from loguru import logger

from core.normalizer import Normalizer
from core.deduplicator import Deduplicator
from core.exporter import Exporter


class NormalizationPipeline:
    """Pipeline for normalizing scraped data."""
    
    def __init__(self):
        self.normalizer = Normalizer()
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """
        Normalize item data.
        
        Args:
            item: Scraped item
            spider: Spider instance
            
        Returns:
            Normalized item
        """
        normalized = self.normalizer.normalize_listing(item)
        logger.debug(f"Normalized item: {normalized.get('listing_url')}")
        return normalized


class DeduplicationPipeline:
    """Pipeline for removing duplicate items."""
    
    def __init__(self):
        self.deduplicator = Deduplicator()
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """
        Check for duplicates and filter them out.
        
        Args:
            item: Scraped item
            spider: Spider instance
            
        Returns:
            Item if unique, raises DropItem if duplicate
        """
        from scrapy.exceptions import DropItem
        
        if self.deduplicator.is_duplicate(item):
            raise DropItem(f"Duplicate item: {item.get('listing_url')}")
        
        return item
    
    def close_spider(self, spider):
        """Log deduplication stats when spider closes."""
        stats = self.deduplicator.get_stats()
        logger.info(f"Deduplication stats: {stats}")


class ExportPipeline:
    """Pipeline for exporting data to various formats."""
    
    def __init__(self):
        self.exporter = Exporter()
        self.items = []
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """
        Collect items for batch export.
        
        Args:
            item: Scraped item
            spider: Spider instance
            
        Returns:
            Item (unchanged)
        """
        self.items.append(dict(item))
        return item
    
    def close_spider(self, spider):
        """
        Export all collected items when spider closes.
        
        Args:
            spider: Spider instance
        """
        if not self.items:
            logger.warning("No items to export")
            return
        
        logger.info(f"Exporting {len(self.items)} items")
        
        # Export to all formats
        results = self.exporter.export_all(
            self.items,
            base_filename=spider.name
        )
        
        logger.info(f"Export complete: {results}")
