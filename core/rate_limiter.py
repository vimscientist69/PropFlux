import time
import threading
from loguru import logger
from typing import Dict

class RateLimiter:
    """
    Thread-safe global rate limiter implementing a simple fixed-interval logic.
    Ensures that for any given domain, requests are spaced out by a minimum interval.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RateLimiter, cls).__new__(cls)
                cls._instance._last_request_time: Dict[str, float] = {}
                cls._instance._domain_locks: Dict[str, threading.Lock] = {}
        return cls._instance

    def wait_for_slot(self, domain: str, requests_per_minute: int):
        """
        Blocks until a slot is available for the given domain.
        
        Args:
            domain: The domain to rate limit (e.g., 'property24')
            requests_per_minute: Maximum requests allowed per minute
        """
        if requests_per_minute <= 0:
            return

        interval = 60.0 / requests_per_minute
        
        # Get or create a lock for this specific domain
        with self._lock:
            if domain not in self._domain_locks:
                self._domain_locks[domain] = threading.Lock()
            domain_lock = self._domain_locks[domain]

        with domain_lock:
            now = time.time()
            last_time = self._last_request_time.get(domain, 0)
            elapsed = now - last_time
            
            if elapsed < interval:
                wait_time = interval - elapsed
                logger.info(f"RateLimiter: Sleeping {wait_time:.2f}s for domain '{domain}'")
                time.sleep(wait_time)
                now = time.time()  # Update 'now' after sleeping
            
            self._last_request_time[domain] = now

# Global singleton instance
rate_limiter = RateLimiter()
