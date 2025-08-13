"""
IP Geolocation utilities for sharing analytics
"""
import requests
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_location_from_ip(ip_address, timeout=3):
    """
    Get location information from IP address using a free geolocation service
    
    Args:
        ip_address: IP address to lookup
        timeout: Request timeout in seconds
        
    Returns:
        dict: Location data with 'city', 'country', 'country_code' keys
              Returns empty dict if lookup fails
    """
    if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
        return {}
    
    # Check cache first (cache for 24 hours)
    cache_key = f"geo_location:{ip_address}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        # Use ip-api.com (free service, no API key required)
        # Limit: 1000 requests per hour from same IP
        url = f"http://ip-api.com/json/{ip_address}?fields=status,country,countryCode,city"
        
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 'success':
            location_data = {
                'city': data.get('city', ''),
                'country': data.get('country', ''),
                'country_code': data.get('countryCode', '')
            }
            
            # Cache successful results for 24 hours
            cache.set(cache_key, location_data, timeout=86400)
            
            logger.info(f"Geolocation lookup successful for {ip_address}: {location_data}")
            return location_data
        else:
            logger.warning(f"Geolocation lookup failed for {ip_address}: {data}")
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Geolocation request failed for {ip_address}: {e}")
    except Exception as e:
        logger.error(f"Unexpected geolocation error for {ip_address}: {e}")
    
    # Cache empty result for 1 hour to avoid repeated failed lookups
    cache.set(cache_key, {}, timeout=3600)
    return {}


def format_location_string(city, country, ip_address=None):
    """
    Format location string from city, country, and IP address
    
    Args:
        city: City name (can be empty)
        country: Country name (can be empty)
        ip_address: IP address (fallback if city/country empty)
        
    Returns:
        str: Formatted location string
    """
    location_parts = []
    
    if city:
        location_parts.append(city)
    if country:
        location_parts.append(country)
    
    if location_parts:
        return ', '.join(location_parts)
    elif ip_address:
        return f"IP: {ip_address}"
    else:
        return 'Unknown location'