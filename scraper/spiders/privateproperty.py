import scrapy
from loguru import logger
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

    async def parse(self, response):
        """
        Parse listing links and handle private seller detection from the list page.
        """
        # If it's a detail page (direct link), parse it directly
        if self.parser.is_detail_page(response):
            async for item in self.parse_listing(response):
                yield item
            return

        self.current_page += 1
        logger.info(f"Parsing page {self.current_page}: {response.url}")

        # Extract listing containers to check for private seller marker
        containers = response.css(self.site_config.get('selectors', {}).get('listing_container', '.featured-listing, .listing-result'))
        
        for container in containers:
            link = container.css(self.site_config.get('selectors', {}).get('listing_links', 'a::attr(href)')).get()
            if not link:
                continue
            
            absolute_url = response.urljoin(link)
            
            # is_private_seller can be left to default False for now
            is_private = False
            
            yield scrapy.Request(
                url=absolute_url,
                callback=self.parse_listing,
                errback=self.handle_error,
                meta={'is_private_seller': is_private}
            )

        # Pagination
        next_page = self.get_next_page_url(response)
        if next_page:
            yield scrapy.Request(
                url=next_page,
                callback=self.parse,
                errback=self.handle_error,
                meta={'search_base_url': response.meta.get('search_base_url')}
            )

    async def parse_listing(self, response):
        """
        Parse individual listing with extra logic for auction and agent name.
        """
        # Get base item from the parent class
        item = None
        async for base_item in super().parse_listing(response):
            item = base_item
            break
        
        if not item:
            return

        item['is_private_seller'] = False

        # 2. Auction Detection
        # Check description and links for auction keywords
        desc = (item.get('description') or '').lower()
        title = (item.get('title') or '').lower()
        if 'auction' in desc or 'auction' in title:
            item['is_auction'] = True
        
        # Check for external auction links
        auction_links = response.css('a[href*="bid"], a[href*="auction"]').getall()
        if auction_links:
            item['is_auction'] = True

        yield item
