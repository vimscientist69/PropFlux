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
    """Pipeline for exporting data to various formats incrementally."""
    
    def __init__(self):
        from config.settings import settings
        self.exporter = Exporter()
        self.items = []
        self.batch_size = settings.EXPORT_BATCH_SIZE
        self.total_count = 0
        self.csv_file = None
        self.jsonl_file = None
        self.base_name = None

    def open_spider(self, spider):
        """Initialize filenames at the start of the run."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_name = spider.name
        self.csv_file = f"{self.base_name}_{timestamp}.csv"
        self.jsonl_file = f"{self.base_name}_{timestamp}.jsonl"
        self.json_file = f"{self.base_name}_{timestamp}.json"
        logger.info(f"Incremental Export enabled: Batch size {self.batch_size}")

    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """
        Collect items and flush periodically.
        """
        self.items.append(dict(item))
        self.total_count += 1
        
        if len(self.items) >= self.batch_size:
            self._flush_items()
            
        return item
    
    def _flush_items(self):
        """Save buffered items to disk and clear memory."""
        if not self.items:
            return
            
        logger.info(f"Flushing {len(self.items)} items to disk (Total: {self.total_count})...")
        
        # 1. Append to CSV
        self.exporter.export_to_csv(self.items, filename=self.csv_file, append=True)
        
        # 2. Append to JSONL (temporary stream)
        self.exporter.export_to_jsonl(self.items, filename=self.jsonl_file)
        
        # 3. Append to SQLite
        self.exporter.export_to_sqlite(self.items, append=True)
        
        # 4. Clear memory
        self.items = []

    def close_spider(self, spider):
        """
        Final flush and convert JSONL to standard JSON.
        """
        # Final flush of remaining items
        if self.items:
            self._flush_items()
        
        if self.total_count == 0:
            logger.warning("No items were scraped, skipping export finalization.")
            return
            
        logger.info(f"Finalizing export for {self.total_count} items...")
        
        # Finalize JSON from JSONL
        final_json = self.exporter.finalize_json_from_jsonl(
            jsonl_filename=self.jsonl_file,
            json_filename=self.json_file
        )
        
        results = {
            'csv': str(self.exporter.output_dir / self.csv_file),
            'json': final_json,
            'sqlite': str(self.exporter.output_dir / "listings.db")
        }
        
        logger.info(f"Export complete: {results}")
