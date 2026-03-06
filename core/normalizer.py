"""
Normalizer module for cleaning and standardizing extracted data.
"""
import re
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
        Extract integer from string (for bedrooms, bathrooms, etc.).
        
        Examples:
            "3 Bedrooms" -> 3
            "2.5" -> 2
            "Two" -> None (text numbers not supported yet)
        
        Args:
            value_str: Raw string containing number or already normalized numeric value
            
        Returns:
            Integer value or None
        """
        if value_str is None:
            return None
            
        if isinstance(value_str, (int, float)):
            return int(value_str)
        
        try:
            # Extract first number found
            match = re.search(r'\d+', str(value_str))
            if match:
                return int(match.group())
            return None
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to normalize integer '{value_str}': {e}")
            return None
    
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
            'House': 'House',
            'Villa': 'Villa',
            'Penthouse': 'Penthouse',
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
        
        # Normalize price
        if 'price' in normalized:
            normalized['price'] = Normalizer.normalize_price(normalized['price'])
        
        # Normalize location
        if 'location' in normalized:
            normalized['location'] = Normalizer.normalize_location(normalized['location'])
        
        # Normalize bedrooms
        if 'bedrooms' in normalized:
            normalized['bedrooms'] = Normalizer.normalize_integer(normalized['bedrooms'])
        
        # Normalize bathrooms
        if 'bathrooms' in normalized:
            normalized['bathrooms'] = Normalizer.normalize_integer(normalized['bathrooms'])
        
        # Normalize property type
        if 'property_type' in normalized:
            normalized['property_type'] = Normalizer.normalize_property_type(normalized['property_type'])
        
        # Clean text fields (title, description)
        for field in ['title', 'description', 'agent_name']:
            if field in normalized and normalized[field]:
                normalized[field] = ' '.join(str(normalized[field]).split())
        
        return normalized
