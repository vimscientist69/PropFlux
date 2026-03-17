import re
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

    # Map of feature label text → item field name (boolean True if present)
    FEATURE_FLAG_MAP = {
        'pet friendly':     'pets_allowed',
        'alarm':            'alarm',
        'electric fencing': 'electric_fencing',
        'pool':             'pool',
        'laundry':          'laundry',
        'study':            'study',
        'garden':           'garden',
    }

    async def parse(self, response):
        """
        Parse listing links from the search page.
        """
        # Use base class logic to process links and pagination
        async for item in super().parse(response):
            yield item

    def _parse_location_from_url(self, url: str) -> dict:
        """
        Parse province, city, suburb from a Private Property listing URL.
        
        Works backwards from the listing ID (T######) which is always the last
        path segment, then strips street-address segments (those containing digits)
        to get clean place-name parts.
        
        Example:
            /for-sale/gauteng/johannesburg-metro/north-riding-to-lanseria/sundowner/38-brushwood-estate/79-drysdale-road/T5425001
            → province=Gauteng, city=Sundowner ([-2] before ID), suburb=Sundowner? 
            
        URL structure after for-sale:
            [province, region, city_area?, suburb?, address_parts..., T-ID]
        """
        result = {'province': None, 'city': None, 'suburb': None}
        try:
            parts = url.rstrip('/').split('/')
            if 'for-sale' not in parts:
                return result
            
            fs_index = parts.index('for-sale')
            geo_parts = parts[fs_index + 1:]
            
            # Find the listing ID (T######) and slice off from it
            id_index = next(
                (i for i, p in enumerate(geo_parts) if re.match(r'^T\d+$', p)),
                len(geo_parts)
            )
            geo_parts = geo_parts[:id_index]
            
            # Strip address segments: any segment containing a digit is a street name/number
            place_parts = [p for p in geo_parts if not re.search(r'\d', p)]
            
            # Convert slugs to title case
            place_parts = [p.replace('-', ' ').title() for p in place_parts]
            
            # Assign by position:
            # [0] = province, [1] = metro-region (skip), [-2] = city, [-1] = suburb
            # If only 3 parts: [0]=province, [1]=city, [2]=suburb
            # If only 2 parts: [0]=province, [1]=city, suburb=None
            if len(place_parts) >= 4:
                result['province'] = place_parts[0]
                result['city']     = place_parts[-2]
                result['suburb']   = place_parts[-1]
            elif len(place_parts) == 3:
                result['province'] = place_parts[0]
                result['city']     = place_parts[1]
                result['suburb']   = place_parts[2]
            elif len(place_parts) == 2:
                result['province'] = place_parts[0]
                result['city']     = place_parts[1]
                result['suburb']   = None
            elif len(place_parts) == 1:
                result['province'] = place_parts[0]
            
            # De-duplicate: clear suburb when it matches city
            if result.get('suburb') and result.get('city') and result['suburb'] == result['city']:
                result['suburb'] = None
                    
        except Exception as e:
            logger.error(f"Failed to parse location from URL {url}: {e}")
        
        return result

    def _scrape_feature_flags(self, response) -> dict:
        """
        Scrape boolean feature flags from the #property-features-list block.
        
        Looks at the label text of each feature <li> and maps known labels to
        boolean fields. Returns a dict of {field_name: True} for present features.
        """
        flags = {}
        feature_items = response.css('.property-features__list-item .property-features__name-value')
        for item in feature_items:
            # Get the visible label text (excluding the child value span)
            raw = item.xpath('normalize-space(text())').get() or ''
            label = raw.strip().lower()
            if label in self.FEATURE_FLAG_MAP:
                field = self.FEATURE_FLAG_MAP[label]
                flags[field] = True
        return flags

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

            item['is_private_seller'] = False

            # 1. Location Hierarchy (Province, City, Suburb) from URL
            location = self._parse_location_from_url(response.url)
            item.update(location)

            # 2. Location display field fallback
            location_text = item.get('location', '') or ''
            if 'contact agent' in location_text.lower():
                sub = item.get('suburb', '')
                cty = item.get('city', '')
                if sub and cty and sub != cty:
                    item['location'] = f"{sub}, {cty}"
                elif cty:
                    item['location'] = cty

            # 4. Boolean Feature Flags from property-features-list
            feature_flags = self._scrape_feature_flags(response)
            item.update(feature_flags)

            # --- Dynamic Data Extraction ---
            try:
                if self.skip_dynamic_fields:
                    # Final cleanup before yielding
                    agent_name = item.get('agent_name')
                    if agent_name and agent_name.startswith('Photo of '):
                        item['agent_name'] = agent_name.replace('Photo of ', '').strip()
                    yield item
                    return

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

            # 6. Final Clean up Agent Name (handles both static and dynamic)
            agent_name = item.get('agent_name')
            if agent_name and agent_name.startswith('Photo of '):
                item['agent_name'] = agent_name.replace('Photo of ', '').strip()

            yield item
            
        except Exception as master_e:
            logger.error(f"MASTER EXCEPTION in PrivateProperty parse_listing: {master_e}", exc_info=True)
            raise
