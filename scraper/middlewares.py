from scrapy import signals
from urllib.parse import urlparse
from core.rate_limiter import rate_limiter
from loguru import logger

class UnifiedRateLimitMiddleware:
    """
    Middleware that intercepts all requests and ensures they respect 
    the global rate limit for their domain.
    """

    def process_request(self, request, spider):
        # Identify the domain (or site_key if available)
        # We prefer site_key from spider to match site-specific configs
        site_key = getattr(spider, 'site_key', None)
        if not site_key:
            domain = urlparse(request.url).netloc
            site_key = domain.replace('www.', '').split('.')[0]

        # Get the limit from spider config or default to a safe value
        # The spider already has site_config loaded in __init__
        site_config = getattr(spider, 'site_config', {})
        rpm = site_config.get('rate_limit', {}).get('requests_per_minute', 3)
        
        logger.debug(f"Middleware: Waiting for slot for '{site_key}' (Target RPM: {rpm})")
        
        # This will block the Scrapy downloader thread
        rate_limiter.wait_for_slot(site_key, rpm)
        
        return None  # Continue normal processing
