"""
Attendee Resolver - Maps identifiers to UniPile attendee IDs

Handles the two-step process for messaging channels:
1. Convert identifier to provider_id
2. Resolve provider_id to attendee_id via UniPile API
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..utils import ProviderIdBuilder

logger = logging.getLogger(__name__)


class AttendeeResolver:
    """Resolves record identifiers to UniPile attendee IDs"""
    
    def __init__(self, unipile_client):
        """
        Initialize with UniPile client
        
        Args:
            unipile_client: Instance of UnipileClient with messaging capabilities
        """
        self.unipile_client = unipile_client
        self._attendee_cache = {}  # Cache to avoid repeated API calls
    
    def resolve_email_attendees(self, email_addresses: List[str]) -> Dict[str, str]:
        """
        Resolve email addresses to attendee IDs
        
        For email, the address itself is often the identifier,
        but we may need to look up the attendee record.
        
        Args:
            email_addresses: List of email addresses
            
        Returns:
            Dict mapping email to attendee_id (if found)
        """
        attendee_map = {}
        
        for email in email_addresses:
            if email in self._attendee_cache:
                attendee_map[email] = self._attendee_cache[email]
                continue
            
            # For email, we typically don't need attendee resolution
            # Emails are fetched directly by address
            # But we'll keep this for consistency
            attendee_map[email] = email  # Email is its own identifier
            
        return attendee_map
    
    def resolve_messaging_attendees(
        self, 
        identifiers: Dict[str, List[str]], 
        channel_type: str,
        account_id: str,
        pre_fetched_names: Optional[Dict[str, str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Resolve messaging identifiers to UniPile attendee records
        
        This is the key method for WhatsApp, LinkedIn, etc.
        
        Args:
            identifiers: Dict with phone, linkedin, etc. lists
            channel_type: 'whatsapp', 'linkedin', 'telegram', etc.
            account_id: UniPile account ID for the channel
            
        Returns:
            Dict mapping provider_id to attendee info:
            {
                'provider_id': {
                    'attendee_id': 'unipile_attendee_id',
                    'name': 'Contact Name',
                    'metadata': {...}
                }
            }
        """
        attendee_map = {}
        
        # Special handling for LinkedIn - need to fetch profile first
        if channel_type == 'linkedin':
            return self._resolve_linkedin_attendees(identifiers, account_id)
        
        # Build provider IDs based on channel type using centralized builder
        provider_ids = ProviderIdBuilder.build_provider_ids(identifiers, channel_type)
        
        for provider_id in provider_ids:
            # Check cache first
            cache_key = f"{channel_type}:{provider_id}"
            if cache_key in self._attendee_cache:
                attendee_map[provider_id] = self._attendee_cache[cache_key]
                continue
            
            # Query UniPile API for attendee
            try:
                attendee_info = self._fetch_attendee_from_unipile(
                    provider_id, 
                    channel_type,
                    account_id,
                    pre_fetched_names
                )
                
                if attendee_info:
                    attendee_map[provider_id] = attendee_info
                    self._attendee_cache[cache_key] = attendee_info
                    
            except Exception as e:
                logger.error(f"Failed to resolve attendee for {provider_id}: {e}")
                continue
        
        return attendee_map
    
    def fetch_all_attendees_with_names(
        self,
        account_id: str,
        channel_type: str
    ) -> Dict[str, str]:
        """
        Fetch all attendees from UniPile and return a mapping of identifier to name
        
        This is used to pre-fetch all attendee names at the beginning of a sync
        to ensure participants are created with proper names.
        
        Args:
            account_id: UniPile account ID
            channel_type: Channel type (whatsapp, linkedin, etc.)
            
        Returns:
            Dict mapping identifier (phone/provider_id) to name
            For WhatsApp: {'+1234567890': 'John Doe', ...}
            For LinkedIn: {'ACoBxxx': 'Jane Smith', ...}
        """
        from asgiref.sync import async_to_sync
        
        attendee_names = {}
        
        try:
            logger.info(f"Fetching all attendees for {channel_type} account {account_id}")
            
            # Fetch all attendees with pagination
            cursor = None
            total_fetched = 0
            page_count = 0
            max_pages = 100  # Safety limit to prevent infinite loops
            
            while page_count < max_pages:
                # Call UniPile's get_all_attendees endpoint
                response = async_to_sync(self.unipile_client.messaging.get_all_attendees)(
                    account_id=account_id,
                    cursor=cursor,
                    limit=100  # Fetch in batches
                )
                
                page_count += 1
                
                if not response or 'items' not in response:
                    break
                
                attendees = response.get('items', [])
                
                # Process attendees based on channel type
                for attendee in attendees:
                    name = attendee.get('name', '')
                    if not name:
                        continue  # Skip if no name
                    
                    if channel_type == 'whatsapp':
                        # For WhatsApp, extract phone number from provider_id
                        provider_id = attendee.get('provider_id', '')
                        attendee_id = attendee.get('id', '')  # This is the attendee ID used in messages
                        
                        if provider_id and '@s.whatsapp.net' in provider_id:
                            phone = provider_id.replace('@s.whatsapp.net', '')
                            if phone:
                                attendee_names[phone] = name
                                # Also store with full provider_id
                                attendee_names[provider_id] = name
                        
                        # IMPORTANT: Also store by attendee_id which is what messages use
                        if attendee_id:
                            attendee_names[attendee_id] = name
                    
                    elif channel_type == 'linkedin':
                        # For LinkedIn, use the provider_id
                        provider_id = attendee.get('provider_id', '')
                        if provider_id:
                            attendee_names[provider_id] = name
                            # Also try attendee_id as fallback
                            attendee_id = attendee.get('id', '')
                            if attendee_id and attendee_id != provider_id:
                                attendee_names[attendee_id] = name
                    
                    else:
                        # Generic handling for other channels
                        # Try multiple identifier fields
                        for id_field in ['provider_id', 'id', 'phone', 'email']:
                            identifier = attendee.get(id_field, '')
                            if identifier:
                                attendee_names[identifier] = name
                
                total_fetched += len(attendees)
                
                # Check for next page
                cursor = response.get('cursor') or response.get('next_cursor')
                if not cursor or not response.get('has_more', False):
                    break
                
                # Log progress for large datasets
                if total_fetched > 0 and total_fetched % 1000 == 0:
                    logger.info(f"  Progress: Fetched {total_fetched} attendees so far...")
            
            if page_count >= max_pages:
                logger.warning(f"Reached maximum page limit ({max_pages}) while fetching attendees")
            
            logger.info(f"Fetched {total_fetched} attendees across {page_count} pages with {len(attendee_names)} unique names for {channel_type}")
            return attendee_names
            
        except Exception as e:
            logger.error(f"Failed to fetch attendees for {channel_type}: {e}")
            return attendee_names  # Return what we have so far
    
    def _fetch_attendee_from_unipile(
        self, 
        provider_id: str, 
        channel_type: str,
        account_id: str,
        pre_fetched_names: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch attendee information from UniPile API
        
        For WhatsApp: We use the provider_id directly to get 1-on-1 chats
        
        Args:
            provider_id: Provider-specific identifier
            channel_type: Channel type
            account_id: UniPile account ID
            
        Returns:
            Dict with attendee information or None
        """
        try:
            from asgiref.sync import async_to_sync
            
            # For WhatsApp, we don't need to fetch attendees first
            # We use the provider_id directly to get chats
            if channel_type == 'whatsapp':
                # Get name from pre-fetched names if available
                name = ''
                if pre_fetched_names:
                    # Try to extract phone number from provider_id
                    phone = provider_id.replace('@s.whatsapp.net', '') if '@s.whatsapp.net' in provider_id else provider_id
                    # Look up name by phone or provider_id
                    name = pre_fetched_names.get(phone, '') or pre_fetched_names.get(provider_id, '')
                
                # Return a simplified attendee info that will be used to fetch chats
                return {
                    'attendee_id': provider_id,  # Use provider_id as attendee_id for WhatsApp
                    'name': name,  # Use pre-fetched name
                    'provider_id': provider_id,
                    'metadata': {
                        'type': 'whatsapp',
                        'phone': ProviderIdBuilder.extract_phone_from_whatsapp_id(provider_id)
                    }
                }
            
            # For other channels, try to get attendees (fallback behavior)
            response = async_to_sync(self.unipile_client.messaging.get_all_attendees)(
                account_id=account_id,
                limit=100  # We'll need pagination for large lists
            )
            
            if not response or 'items' not in response:
                return None
            
            # Search for matching attendee
            for attendee in response['items']:
                # Check various fields where provider_id might appear
                attendee_provider_id = attendee.get('provider_id', '')
                attendee_external_id = attendee.get('external_id', '')
                attendee_phone = attendee.get('phone', '')
                
                # Check if this attendee matches our provider_id
                if provider_id in [attendee_provider_id, attendee_external_id]:
                    return {
                        'attendee_id': attendee.get('id'),
                        'name': attendee.get('name', ''),
                        'provider_id': provider_id,
                        'metadata': attendee
                    }
                
                # Special handling for WhatsApp phone matching
                if channel_type == 'whatsapp' and attendee_phone:
                    # Extract phone from provider_id for comparison
                    provider_phone = ProviderIdBuilder.extract_phone_from_whatsapp_id(provider_id)
                    # Clean the attendee phone for comparison
                    attendee_phone_clean = ''.join(filter(str.isdigit, attendee_phone))
                    if provider_phone == attendee_phone_clean:
                        return {
                            'attendee_id': attendee.get('id'),
                            'name': attendee.get('name', ''),
                            'provider_id': provider_id,
                            'metadata': attendee
                        }
            
            # If we need to handle pagination
            cursor = response.get('cursor')
            while cursor:
                response = async_to_sync(self.unipile_client.messaging.get_all_attendees)(
                    account_id=account_id,
                    cursor=cursor,
                    limit=100
                )
                
                if not response or 'items' not in response:
                    break
                
                for attendee in response['items']:
                    if provider_id in [attendee.get('provider_id'), attendee.get('external_id')]:
                        return {
                            'attendee_id': attendee.get('id'),
                            'name': attendee.get('name', ''),
                            'provider_id': provider_id,
                            'metadata': attendee
                        }
                
                cursor = response.get('cursor')
            
            logger.warning(f"No attendee found for provider_id: {provider_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching attendee from UniPile: {e}")
            return None
    
    def _resolve_linkedin_attendees(
        self,
        identifiers: Dict[str, List[str]],
        account_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Resolve LinkedIn attendees by first fetching user profiles
        
        LinkedIn requires a special flow:
        1. Fetch the user profile using the LinkedIn identifier
        2. Extract the provider_id from the profile
        3. Use the provider_id to find attendees and chats
        
        Args:
            identifiers: Dict with linkedin identifiers
            account_id: UniPile account ID for LinkedIn
            
        Returns:
            Dict mapping provider_id to attendee info
        """
        attendee_map = {}
        linkedin_identifiers = identifiers.get('linkedin', [])
        
        if not linkedin_identifiers:
            logger.info("No LinkedIn identifiers to resolve")
            return attendee_map
        
        from asgiref.sync import async_to_sync
        
        for linkedin_id in linkedin_identifiers:
            try:
                # Check cache first
                cache_key = f"linkedin:{linkedin_id}"
                if cache_key in self._attendee_cache:
                    cached_info = self._attendee_cache[cache_key]
                    attendee_map[cached_info['provider_id']] = cached_info
                    continue
                
                logger.info(f"Fetching LinkedIn profile for identifier: {linkedin_id}")
                
                # Step 1: Fetch the LinkedIn profile to get provider_id
                # The identifier should be the LinkedIn username (e.g., "chilchik")
                profile_response = async_to_sync(self.unipile_client.users.get_user_profile)(
                    user_id=linkedin_id,  # The LinkedIn username/identifier
                    account_id=account_id
                )
                
                if not profile_response:
                    logger.warning(f"No LinkedIn profile found for: {linkedin_id}")
                    continue
                
                # Extract provider_id from the profile
                provider_id = profile_response.get('provider_id') or profile_response.get('id')
                if not provider_id:
                    logger.warning(f"No provider_id in LinkedIn profile for: {linkedin_id}")
                    continue
                
                logger.info(f"Found LinkedIn provider_id: {provider_id} for {linkedin_id}")
                
                # Step 2: Now we have the provider_id, create attendee info
                attendee_info = {
                    'attendee_id': provider_id,  # For LinkedIn, we use provider_id as attendee_id
                    'name': profile_response.get('name', ''),
                    'provider_id': provider_id,
                    'linkedin_id': linkedin_id,
                    'metadata': {
                        'profile': profile_response,
                        'headline': profile_response.get('headline', ''),
                        'profile_url': profile_response.get('profile_url', ''),
                        'picture_url': profile_response.get('picture_url', '')
                    }
                }
                
                attendee_map[provider_id] = attendee_info
                self._attendee_cache[cache_key] = attendee_info
                
                logger.info(f"Successfully resolved LinkedIn attendee: {attendee_info['name']}")
                
            except Exception as e:
                logger.error(f"Failed to resolve LinkedIn profile for {linkedin_id}: {e}")
                continue
        
        return attendee_map
    
    def clear_cache(self):
        """Clear the attendee cache"""
        self._attendee_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cached_attendees': len(self._attendee_cache),
            'cache_size_bytes': sum(
                len(str(k)) + len(str(v)) 
                for k, v in self._attendee_cache.items()
            )
        }