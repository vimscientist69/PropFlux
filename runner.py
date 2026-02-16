#!/usr/bin/env python3
"""
Main runner script for the multi-site real estate scraper.

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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from scraper.spiders.property24 import Property24Spider
from scraper.spiders.privateproperty import PrivatePropertySpider


# Map site names to spider classes
SPIDER_MAP = {
    'property24': Property24Spider,
    'privateproperty': PrivatePropertySpider,
}


def setup_logging(verbose: bool = False):
    """
    Configure logging.
    
    Args:
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
        log_dir / "scraper_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-site real estate scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py --site property24
  python runner.py --site privateproperty --url "https://example.com/search"
  python runner.py --site property24 --verbose
        """
    )
    
    parser.add_argument(
        '--site',
        type=str,
        required=True,
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
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Get spider class
    spider_class = SPIDER_MAP[args.site]
    
    logger.info(f"Starting scraper for: {args.site}")
    logger.info(f"Spider: {spider_class.name}")
    
    # Get Scrapy settings
    settings = get_project_settings()
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Prepare spider kwargs
    spider_kwargs = {}
    
    if args.url:
        spider_kwargs['start_urls'] = [args.url]
        logger.info(f"Using custom start URL: {args.url}")
    
    if args.max_pages:
        spider_kwargs['max_pages'] = args.max_pages
        logger.info(f"Max pages set to: {args.max_pages}")
    
    # Start crawling
    process.crawl(spider_class, **spider_kwargs)
    
    logger.info("Starting crawl...")
    process.start()
    
    logger.info("Scraping complete!")


if __name__ == '__main__':
    main()
