#!/usr/bin/env python3
"""
Main runner script for PropFlux.

Usage:
    python runner.py --site property24
    python runner.py --site privateproperty --url "https://example.com/search"
"""
import argparse
import sys
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from loguru import logger
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from scraper.spiders.property24 import Property24Spider
from scraper.spiders.privateproperty import PrivatePropertySpider
from core.browser_service import setup_chrome_profile


# Map site names to spider classes
SPIDER_MAP = {
    'property24': Property24Spider,
    'privateproperty': PrivatePropertySpider,
}


def setup_logging(site_name: str = "general", verbose: bool = False):
    """
    Configure logging.
    
    Args:
        site_name: Name of the site being scraped
        verbose: Enable verbose logging
    """
    log_level = "DEBUG" if verbose else "INFO"
    
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
    )
    
    # Add file logger
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / f"{site_name}_{{time:YYYYMMDD_HHmmss}}.log",
        rotation="100 MB",
        retention="7 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    )


def run_spider(site_key: str, 
               url: Optional[str] = None, 
               max_pages: Optional[int] = None, 
               limit: Optional[int] = None, 
               skip_dynamic_fields: bool = False,
               verbose: bool = False,
               job_id: Optional[str] = None,
               settings_overrides: Optional[dict] = None):
    """
    Programmatically run a Scrapy spider.
    
    Args:
        site_key: Site to scrape (property24, privateproperty)
        url: Custom start URL
        max_pages: Maximum number of pages to scrape
        limit: Hard limit for total number of listings
        skip_dynamic_fields: Skip Selenium dynamic extraction
        verbose: Enable verbose logging
        job_id: Unique ID for this scrape job
        settings_overrides: Dictionary of Scrapy settings to override
    """
    # Setup logging
    setup_logging(site_key, verbose)
    
    # Auto-generate job_id if not provided
    if not job_id:
        import uuid
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        logger.info(f"Runner: Auto-generated Job ID: {job_id}")

    # Get spider class
    if site_key not in SPIDER_MAP:
        raise ValueError(f"Unknown site: {site_key}")
        
    spider_class = SPIDER_MAP[site_key]
    
    # Initialize exporter for job tracking
    from core.exporter import Exporter
    exporter = Exporter()
    
    logger.info(f"Starting scraper for: {site_key}")
    if job_id:
        logger.info(f"Job ID: {job_id}")
        # Create job entry in database
        job_config = {
            'url': url,
            'max_pages': max_pages,
            'limit': limit,
            'skip_dynamic_fields': skip_dynamic_fields,
            'settings_overrides': settings_overrides
        }
        exporter.create_job(job_id, site_key, job_config)
    
    try:
        # Get Scrapy settings
        settings = get_project_settings()
        if verbose:
            settings.set('LOG_LEVEL', 'DEBUG')
        
        # Apply settings overrides
        if settings_overrides:
            for key, value in settings_overrides.items():
                settings.set(key, value)
                logger.info(f"Overriding setting {key} = {value}")
        
        # Create crawler process
        process = CrawlerProcess(settings)
        
        # Prepare spider kwargs
        spider_kwargs = {
            'job_id': job_id,
            'skip_dynamic_fields': skip_dynamic_fields,
            'config_overrides': settings_overrides # Pass overrides to spider as well
        }
        
        if url:
            spider_kwargs['start_urls'] = [url]
            logger.info(f"Using custom start URL: {url}")
        
        if max_pages:
            spider_kwargs['max_pages'] = max_pages
            logger.info(f"Max pages set to: {max_pages}")
        
        if limit:
            spider_kwargs['limit'] = limit
            logger.info(f"Hard limit set to: {limit} listings")
        
        # Start crawling
        process.crawl(spider_class, **spider_kwargs)
        
        logger.info("Starting crawl...")
        process.start()
        
        logger.info("Scraping complete!")
        if job_id:
            exporter.update_job_status(job_id, "COMPLETED", ended_at=True)
        
    except Exception as e:
        logger.error(f"Fatal error in run_spider: {e}")
        if job_id:
            # Re-initialize exporter in case of error in main block
            try:
                from core.exporter import Exporter
                Exporter().update_job_status(job_id, "FAILED", ended_at=True)
            except Exception as nested_e:
                logger.error(f"Failed to update error status for job {job_id}: {nested_e}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PropFlux: Scalable Multi-Site Real Estate Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py --setup-chrome-profile
  python runner.py --site property24
  python runner.py --site privateproperty --url "https://example.com/search"
  python runner.py --site property24 --verbose
        """
    )

    parser.add_argument(
        '--setup-chrome-profile',
        action='store_true',
        help='Open a Chrome browser to set up the NopeCHA extension (one-time setup)'
    )
    
    parser.add_argument(
        '--site',
        type=str,
        required=False,
        choices=list(SPIDER_MAP.keys()),
        help='Site to scrape (property24, privateproperty)'
    )
    
    parser.add_argument(
        '--url',
        type=str,
        help='Custom start URL (optional, overrides config)'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum number of pages to scrape (optional)'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Hard limit for total number of listings to scrape (overrides max-pages and dev-limit)'
    )
    
    parser.add_argument(
        '--skip-dynamic-fields',
        action='store_true',
        help='Skip the Selenium phone extraction logic for faster debugging'
    )
    
    args = parser.parse_args()

    # Handle one-time Chrome profile setup
    if args.setup_chrome_profile:
        setup_chrome_profile()
        return

    if not args.site:
        parser.error('--site is required unless --setup-chrome-profile is used')

    # Run the spider
    job_id = str(uuid.uuid4().hex[:8])
    run_spider(
        site_key=args.site,
        url=args.url,
        max_pages=args.max_pages,
        limit=args.limit,
        skip_dynamic_fields=args.skip_dynamic_fields,
        verbose=args.verbose,
        job_id=job_id
    )


if __name__ == '__main__':
    main()
