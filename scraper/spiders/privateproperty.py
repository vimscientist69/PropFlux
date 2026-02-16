"""
Private Property spider.
"""
from .base_spider import BaseRealEstateSpider


class PrivatePropertySpider(BaseRealEstateSpider):
    """Spider for Private Property website."""
    
    name = 'privateproperty'
    site_key = 'privateproperty'
    
    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
    }
