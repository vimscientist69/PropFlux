"""
Scrapy settings for real estate scraper project.
"""

BOT_NAME = 'real_estate_scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

# Crawl responsibly by identifying yourself
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Configure a delay for requests
DOWNLOAD_DELAY = 1
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_IP = 4

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Enable or disable spider middlewares
# SPIDER_MIDDLEWARES = {
#    'scraper.middlewares.ScraperSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# DOWNLOADER_MIDDLEWARES = {
#    'scraper.middlewares.ScraperDownloaderMiddleware': 543,
# }

# Enable or disable extensions
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
ITEM_PIPELINES = {
    'scraper.pipelines.DeduplicationPipeline': 100,
    'scraper.pipelines.NormalizationPipeline': 200,
    'scraper.pipelines.ExportPipeline': 300,
}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 408, 429]
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/scraper.log'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

# Custom settings
FEEDS = {
    'output/%(name)s_%(time)s.json': {
        'format': 'json',
        'encoding': 'utf8',
        'store_empty': False,
        'indent': 2,
    },
}
