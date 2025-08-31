"""
Provider ID Builder - Builds provider-specific IDs from identifiers

Converts record identifiers to provider-specific formats.
"""
import re
from typing import Dict, List


class ProviderIdBuilder:
    """Builds provider IDs for different communication channels"""
    
    @staticmethod
    def build_whatsapp_ids(phone_numbers: List[str]) -> List[str]:
        """
        Build WhatsApp provider IDs from phone numbers
        
        Args:
            phone_numbers: List of phone numbers
            
        Returns:
            List of WhatsApp provider IDs (format: number@s.whatsapp.net)
        """
        provider_ids = []
        
        for phone in phone_numbers:
            # Remove all non-digits
            clean_phone = re.sub(r'[^\d]', '', phone)
            
            if not clean_phone:
                continue
            
            # Add country code if missing (assuming US +1 for 10-digit numbers)
            if len(clean_phone) == 10 and not clean_phone.startswith('1'):
                clean_phone = '1' + clean_phone
            
            # Format for WhatsApp
            provider_ids.append(f"{clean_phone}@s.whatsapp.net")
        
        return provider_ids
    
    @staticmethod
    def build_linkedin_ids(linkedin_identifiers: List[str]) -> List[str]:
        """
        Build LinkedIn provider IDs from LinkedIn URLs or usernames
        
        Args:
            linkedin_identifiers: List of LinkedIn URLs or usernames
            
        Returns:
            List of LinkedIn provider IDs
        """
        provider_ids = []
        
        for identifier in linkedin_identifiers:
            if not identifier:
                continue
            
            # If it's a URL, extract the username
            if 'linkedin.com' in identifier:
                # Extract username from various LinkedIn URL formats
                patterns = [
                    r'linkedin\.com/in/([a-zA-Z0-9\-]+)',
                    r'linkedin\.com/company/([a-zA-Z0-9\-]+)',
                    r'linkedin\.com/sales/people/([a-zA-Z0-9\-,]+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, identifier, re.IGNORECASE)
                    if match:
                        provider_ids.append(match.group(1))
                        break
            else:
                # Direct username/ID
                provider_ids.append(identifier)
        
        return provider_ids
    
    @staticmethod
    def build_telegram_ids(identifiers: Dict[str, List[str]]) -> List[str]:
        """
        Build Telegram provider IDs from phone numbers or usernames
        
        Args:
            identifiers: Dict with phone and telegram username lists
            
        Returns:
            List of Telegram provider IDs
        """
        provider_ids = []
        
        # Add phone numbers
        for phone in identifiers.get('phone', []):
            clean_phone = re.sub(r'[^\d]', '', phone)
            if clean_phone:
                provider_ids.append(clean_phone)
        
        # Add Telegram usernames
        for username in identifiers.get('telegram', []):
            if username:
                # Remove @ if present
                clean_username = username.replace('@', '')
                provider_ids.append(clean_username)
        
        return provider_ids
    
    @staticmethod
    def build_instagram_ids(usernames: List[str]) -> List[str]:
        """
        Build Instagram provider IDs from usernames
        
        Args:
            usernames: List of Instagram usernames
            
        Returns:
            List of Instagram provider IDs
        """
        provider_ids = []
        
        for username in usernames:
            if username:
                # Remove @ if present
                clean_username = username.replace('@', '')
                provider_ids.append(clean_username)
        
        return provider_ids
    
    @staticmethod
    def build_provider_ids(
        identifiers: Dict[str, List[str]],
        channel_type: str
    ) -> List[str]:
        """
        Build provider IDs based on channel type
        
        Args:
            identifiers: Dict with identifier types and values
            channel_type: The communication channel type
            
        Returns:
            List of provider IDs
        """
        if channel_type == 'whatsapp':
            return ProviderIdBuilder.build_whatsapp_ids(
                identifiers.get('phone', [])
            )
        
        elif channel_type == 'linkedin':
            return ProviderIdBuilder.build_linkedin_ids(
                identifiers.get('linkedin', [])
            )
        
        elif channel_type == 'telegram':
            return ProviderIdBuilder.build_telegram_ids(identifiers)
        
        elif channel_type == 'instagram':
            return ProviderIdBuilder.build_instagram_ids(
                identifiers.get('instagram', [])
            )
        
        elif channel_type == 'email':
            # Email addresses are their own identifiers
            return identifiers.get('email', [])
        
        else:
            # Unknown channel type
            return []
    
    @staticmethod
    def extract_phone_from_whatsapp_id(whatsapp_id: str) -> str:
        """
        Extract phone number from WhatsApp provider ID
        
        Args:
            whatsapp_id: WhatsApp provider ID (format: number@s.whatsapp.net)
            
        Returns:
            Phone number
        """
        return whatsapp_id.replace('@s.whatsapp.net', '')