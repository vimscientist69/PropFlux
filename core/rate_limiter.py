import time
import random
import threading
from loguru import logger
from typing import Dict

class RateLimiter:
    """
    Thread-safe global rate limiter with random jitter.
    Ensures requests to a domain are spaced based on `60/rpm` seconds,
    randomized within a +/- 15% range to avoid predictable patterns.
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

        base_interval = 60.0 / requests_per_minute
        
        # Get or create a lock for this specific domain
        with self._lock:
            if domain not in self._domain_locks:
                self._domain_locks[domain] = threading.Lock()
            domain_lock = self._domain_locks[domain]

        with domain_lock:
            # Create a randomized target interval for this specific request
            # e.g., if RPM=15 (4s interval), range is 3.4s to 4.6s
            target_interval = base_interval * random.uniform(0.85, 1.15)
            
            now = time.time()
            last_time = self._last_request_time.get(domain, 0)
            elapsed = now - last_time
            
            if elapsed < target_interval:
                wait_time = target_interval - elapsed
                logger.info(f"RateLimiter: Sleeping {wait_time:.2f}s for domain '{domain}' (Target: {target_interval:.2f}s)")
                time.sleep(wait_time)
                now = time.time()  # Update 'now' after sleeping
            
            self._last_request_time[domain] = now

# Global singleton instance
rate_limiter = RateLimiter()
