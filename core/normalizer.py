"""
Normalizer module for cleaning and standardizing extracted data.
"""
import re
import dateparser
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger


class Normalizer:
    """Handles data normalization and cleaning."""
    
    # Common real estate terms for hidden or non-standard pricing
    NON_NUMERIC_PRICE_TERMS = {
        'POA', 'PRICE ON APPLICATION', 'PRICE UPON APPLICATION',
        'AUCTION', 'TENDER', 'NEGOTIABLE', 'OFFERS', 'PRICE ON REQUEST',
        'FROM', 'REQUEST PRICE', 'TBD', 'TBC'
    }
    
    @staticmethod
    def normalize_price(price_str: Any) -> Optional[float]:
        """
        Convert price string to numeric format.
        
        Examples:
            "R 1,200,000" -> 1200000.0
            "$1.2M" -> 1200000.0
            "1 200 000" -> 1200000.0
        
        Args:
            price_str: Raw price string or already normalized numeric value
            
        Returns:
            Numeric price or None if parsing fails
        """
        if price_str is None:
            return None
            
        if isinstance(price_str, (int, float)):
            return float(price_str)
        
        try:
            # First, check if it's a known non-numeric term
            # Clean up the string for comparison
            string_val = str(price_str).strip().upper()
            # Remove punctuation for matching (e.g. "P.O.A." -> "POA")
            match_val = re.sub(r'[.\-]', '', string_val)
            
            if match_val in Normalizer.NON_NUMERIC_PRICE_TERMS:
                return None
            
            # Check if any non-numeric term is contained in the string
            for term in Normalizer.NON_NUMERIC_PRICE_TERMS:
                if term in match_val:
                    return None

            # Remove currency symbols and common prefixes
            cleaned = re.sub(r'[R$€£,\s]', '', string_val)
            
            # Handle M (millions) and K (thousands) suffixes
            if 'M' in cleaned.upper():
                cleaned = cleaned.upper().replace('M', '')
                multiplier = 1_000_000
            elif 'K' in cleaned.upper():
                cleaned = cleaned.upper().replace('K', '')
                multiplier = 1_000
            else:
                multiplier = 1
            
            # Convert to float
            price = float(cleaned) * multiplier
            return price
            
        except (ValueError, AttributeError, TypeError) as e:
            # Only warn if it's not a known status term we should ignore
            # (Double check in case the regex/loop missed something)
            logger.warning(f"Failed to normalize price '{price_str}': {e}")
            return None
    
    @staticmethod
    def normalize_location(location_str: Optional[str]) -> Optional[str]:
        """
        Standardize location text.
        
        Args:
            location_str: Raw location string
            
        Returns:
            Cleaned location string
        """
        if not location_str:
            return None
        
        # Remove extra whitespace
        cleaned = ' '.join(str(location_str).split())
        
        # Remove common noise words/characters
        cleaned = cleaned.strip(',').strip()
        
        return cleaned if cleaned else None
    
    @staticmethod
    def normalize_integer(value_str: Any) -> Optional[int]:
        """
        Parse value as an integer. For fields guaranteed to always be whole numbers
        (bedrooms, garages, en_suite, lounges, parking, etc.).
        
        Examples:
            "4" -> 4
            "6.0" -> 6
        """
        val = Normalizer.normalize_numeric(value_str)
        if val is None:
            return None
        return int(val)
    
    @staticmethod
    def normalize_numeric(value_str: Any) -> Optional[float]:
        """
        Extract numeric value from string (for bedrooms, bathrooms, etc.).
        Supports decimals (e.g., "0.5" for studios).
        
        Examples:
            "3 Bedrooms" -> 3.0
            "0.5" -> 0.5
            "1.5 Bathrooms" -> 1.5
        
        Args:
            value_str: Raw string containing number or already normalized numeric value
            
        Returns:
            Float value or None
        """
        if value_str is None:
            return None
            
        if isinstance(value_str, (int, float)):
            return float(value_str)
        
        try:
            # Extract first number found (including decimals)
            # Use raw string for regex
            match = re.search(r'\d+(\.\d+)?', str(value_str))
            if match:
                return float(match.group())
            return None
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to normalize numeric '{value_str}': {e}")
            return None

    @staticmethod
    def normalize_area(area_str: Any) -> Optional[float]:
        """
        Normalize area strings (e.g., erf size, floor size) to float in square meters.
        
        Examples:
            "1 626 m²" -> 1626.0
            "585 m²" -> 585.0
            "0.5 ha" -> 5000.0
        """
        if not area_str:
            return None
            
        if isinstance(area_str, (int, float)):
            return float(area_str)
            
        try:
            val_str = str(area_str).lower().replace('\xa0', ' ').replace(',', '.')
            # Extract number
            match = re.search(r'([\d\s.]+)', val_str)
            if not match:
                return None
                
            num_part = match.group(1).replace(' ', '')
            value = float(num_part)
            
            # Handle units
            if 'ha' in val_str:
                value *= 10000
            elif 'acre' in val_str:
                value *= 4046.86
                
            return value
        except Exception as e:
            logger.warning(f"Failed to normalize area '{area_str}': {e}")
            return None

    @staticmethod
    def normalize_date(date_str: Any) -> Optional[str]:
        """
        Normalize date string to ISO format YYYY-MM-DD.
        
        Examples:
            "10 February 2026" -> "2026-02-10"
            "2026/03/01" -> "2026-03-01"
        """
        if not date_str:
            return None
            
        try:
            # Use dateparser to handle various natural language formats
            dt = dateparser.parse(str(date_str))
            if dt:
                return dt.strftime('%Y-%m-%d')
            return str(date_str)
        except Exception as e:
            logger.warning(f"Failed to normalize date '{date_str}': {e}")
            return str(date_str)
    
    @staticmethod
    def normalize_property_type(prop_type: Optional[str]) -> Optional[str]:
        """
        Standardize property type naming.
        
        Args:
            prop_type: Raw property type string
            
        Returns:
            Standardized property type
        """
        if not prop_type:
            return None
        
        # Convert to title case and clean
        cleaned = ' '.join(prop_type.split()).title()
        
        # Map common variations to standard names
        type_mapping = {
            'Apt': 'Apartment',
            'Flat': 'Apartment',
            'Townhouse': 'Townhouse',
            'Town House': 'Townhouse',
            'Penthouse': 'Penthouse',
            'House': 'House',
            'Villa': 'Villa',
            'Studio': 'Studio',
            'Duplex': 'Duplex',
        }
        
        for key, value in type_mapping.items():
            if key.lower() in cleaned.lower():
                return value
        
        return cleaned
    
    @staticmethod
    def normalize_listing(listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all fields in a listing.
        
        Args:
            listing: Raw listing data
            
        Returns:
            Normalized listing data
        """
        normalized = listing.copy()
        
        # Initialize flags if missing
        if 'is_auction' not in normalized:
            normalized['is_auction'] = False
        if 'is_private_seller' not in normalized:
            normalized['is_private_seller'] = False

        # 1. Auction Detection
        # Check title and price for auction keywords
        title_text = str(normalized.get('title', '')).upper()
        price_text = str(normalized.get('price', '')).upper()
        if 'AUCTION' in title_text or 'AUCTION' in price_text:
            normalized['is_auction'] = True

        # 2. Private Seller Detection & Agent Cleaning
        agent_name = normalized.get('agent_name')
        if agent_name:
            agent_name_clean = str(agent_name).strip()
            if agent_name_clean.upper() == "SELLER":
                normalized['is_private_seller'] = True
                normalized['agent_name'] = None
            else:
                normalized['agent_name'] = ' '.join(agent_name_clean.split())

        agency_name = normalized.get('agency_name')
        if agency_name:
            agency_name_clean = str(agency_name).strip()
            normalized['agency_name'] = ' '.join(agency_name_clean.split())        

        # Normalize price
        if 'price' in normalized:
            normalized['price'] = Normalizer.normalize_price(normalized['price'])
        
        # Normalize location
        if 'location' in normalized:
            normalized['location'] = Normalizer.normalize_location(normalized['location'])
        
        # Normalize integer-only fields (whole numbers guaranteed)
        for int_field in ['bedrooms', 'garages', 'parking', 'en_suite', 'lounges']:
            if int_field in normalized:
                normalized[int_field] = Normalizer.normalize_integer(normalized[int_field])
        
        # Normalize float-allowed numeric fields (half values possible)
        for num_field in ['bathrooms']:
            if num_field in normalized:
                normalized[num_field] = Normalizer.normalize_numeric(normalized[num_field])
        
        # Normalize area fields
        for area_field in ['erf_size', 'floor_size']:
            if area_field in normalized and normalized[area_field]:
                normalized[area_field] = Normalizer.normalize_area(normalized[area_field])

        # Normalize currency-like fields
        for currency_field in ['rates_and_taxes', 'levies']:
            if currency_field in normalized:
                normalized[currency_field] = Normalizer.normalize_price(normalized[currency_field])

        def normalize_yes_no_bool(value: Any) -> Optional[bool]:
            """
            Coerce values into strict boolean-or-null for feature flags.
            Rules (string values only):
              - "yes" (case-insensitive) -> True
              - "no" (case-insensitive)  -> False
              - any other string value   -> True
            If value is falsy/empty or None -> None.
            If value is already boolean -> keep it.
            """
            if value is None:
                return None

            if isinstance(value, bool):
                return value

            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned == "":
                    return None
                lowered = cleaned.lower()
                if lowered == "yes":
                    return True
                if lowered == "no":
                    return False
                return True

            # Non-string types: treat any non-null truthy value as True.
            return True if value else None

        # Force strict boolean-or-null for these fields.
        for bool_field in ["pets_allowed", "security", "backup_power"]:
            if bool_field in normalized:
                normalized[bool_field] = normalize_yes_no_bool(normalized.get(bool_field))

        # Other presence-based feature flags: keep existing behavior.
        for bool_field in [
            "alarm",
            "electric_fencing",
            "pool",
            "laundry",
            "study",
            "garden",
        ]:
            val = normalized.get(bool_field)
            if isinstance(val, bool):
                pass  # already a proper boolean, leave it
            elif val:
                normalized[bool_field] = " ".join(str(val).split())

        # Normalize property type
        if 'property_type' in normalized:
            normalized['property_type'] = Normalizer.normalize_property_type(normalized['property_type'])
            
        # Normalize date
        if 'date_posted' in normalized:
            normalized['date_posted'] = Normalizer.normalize_date(normalized['date_posted'])
        
        # Clean title and description
        for field in ['title', 'description']:
            if field in normalized and normalized[field]:
                normalized[field] = ' '.join(str(normalized[field]).split())
        
        return normalized