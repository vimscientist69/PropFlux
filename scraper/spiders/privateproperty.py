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
        Parse listing links from the search page.
        """
        # Use base class logic to process links and pagination
        async for item in super().parse(response):
            yield item

    async def parse_listing(self, response):
        """
        Parse individual listing with extra logic for auction and agent name.
        """
        try:
            from twisted.internet.threads import deferToThread
            from scrapy.utils.defer import deferred_to_future
            from core.browser_service import BrowserService
            
            # Get base item from the parent class
            item = None
            async for base_item in super().parse_listing(response):
                item = base_item
                break
            
            if not item:
                return

            # --- Dynamic Data Extraction ---
            # PrivateProperty renders agent cards with JS, so we fetch these via Selenium
            try:
                dynamic_fields = ['agent_phone']
                if not item.get('agent_name'): dynamic_fields.append('agent_name')
                if not item.get('agency_name'): dynamic_fields.append('agency_name')
                
                if dynamic_fields:
                    dynamic_data = await deferred_to_future(deferToThread(
                        BrowserService().get_dynamic_data,
                        url=response.url,
                        site_key='privateproperty',
                        fields=dynamic_fields
                    ))
                    
                    if dynamic_data:
                        for field, val in dynamic_data.items():
                            if val: item[field] = val
                            
            except Exception as e:
                logger.error(f"Error in PrivateProperty dynamic extraction: {e}")

            item['is_private_seller'] = False

            # 1. Location Hierarchy (Province, City, Suburb) from URL
            try:
                url_parts = response.url.split('/')
                if 'for-sale' in url_parts:
                    fs_index = url_parts.index('for-sale')
                    id_index = len(url_parts) - 1
                    
                    if id_index > fs_index + 1:
                        item['province'] = url_parts[fs_index + 1].replace('-', ' ').title()
                        
                        region = url_parts[fs_index + 2].replace('-', ' ').title() if fs_index + 2 < id_index else None
                        area = url_parts[fs_index + 3].replace('-', ' ').title() if fs_index + 3 < id_index else None
                        suburb = url_parts[fs_index + 4].replace('-', ' ').title() if fs_index + 4 < id_index else None
                        
                        if suburb:
                            item['city'] = area if area else region
                            item['suburb'] = suburb
                        elif area:
                            item['city'] = region
                            item['suburb'] = area
                        elif region:
                            item['city'] = region
                            item['suburb'] = region
            except Exception as e:
                logger.error(f"Failed to parse location from URL {response.url}: {e}")

            # 2. Location fallback
            location = item.get('location', '') or ''
            if 'contact agent' in location.lower():
                sub = item.get('suburb', '')
                cty = item.get('city', '')
                if sub and cty and sub != cty:
                    item['location'] = f"{sub}, {cty}"
                elif cty:
                    item['location'] = cty

            # 3. Clean up Agent Name
            agent_name = item.get('agent_name')
            if agent_name and agent_name.startswith('Photo of '):
                item['agent_name'] = agent_name.replace('Photo of ', '').strip()

            # 4. Auction Detection
            desc = (item.get('description') or '').lower()
            title = (item.get('title') or '').lower()
            if 'auction' in desc or 'auction' in title:
                item['is_auction'] = True
            
            auction_links = response.css('a[href*="bid"], a[href*="auction"]').getall()
            if auction_links:
                item['is_auction'] = True

            yield item
            
        except Exception as master_e:
            logger.error(f"MASTER EXCEPTION in PrivateProperty parse_listing: {master_e}", exc_info=True)
            raise
