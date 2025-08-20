"""
Smart conversation naming service
Generates meaningful conversation names based on contact information
"""
import logging
import re
from typing import Dict, Any, Optional, List
from django.db import models
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class ConversationNamingService:
    """
    Intelligent conversation naming based on contact data and context
    """
    
    def __init__(self):
        self.fallback_names = {
            'whatsapp': 'WhatsApp Contact',
            'email': 'Email Contact', 
            'linkedin': 'LinkedIn Contact',
            'sms': 'SMS Contact',
            'telegram': 'Telegram Contact',
            'instagram': 'Instagram Contact',
            'messenger': 'Messenger Contact',
            'twitter': 'Twitter Contact',
            'slack': 'Slack Contact'
        }
    
    def generate_conversation_name(
        self, 
        channel_type: str,
        contact_info: Dict[str, Any],
        message_content: Optional[str] = None,
        external_thread_id: Optional[str] = None
    ) -> str:
        """
        Generate a meaningful conversation name based on available information
        
        Args:
            channel_type: Type of communication channel
            contact_info: Contact information from message or webhook
            message_content: First message content for context
            external_thread_id: External thread ID as fallback
            
        Returns:
            Human-readable conversation name
        """
        try:
            # Try multiple naming strategies in order of preference
            name = (
                self._name_from_contact_profile(contact_info) or
                self._name_from_phone_number(contact_info) or
                self._name_from_email(contact_info) or
                self._name_from_username(contact_info, channel_type) or
                self._name_from_message_content(message_content, channel_type) or
                self._fallback_name(channel_type, external_thread_id)
            )
            
            # Clean and format the name
            clean_name = self._clean_conversation_name(name)
            
            logger.debug(f"Generated conversation name: '{clean_name}' for {channel_type}")
            return clean_name
            
        except Exception as e:
            logger.error(f"Error generating conversation name: {e}")
            return self._fallback_name(channel_type, external_thread_id)
    
    def _name_from_contact_profile(self, contact_info: Dict[str, Any]) -> Optional[str]:
        """Extract name from contact profile information"""
        try:
            # WhatsApp contact profile
            if 'contact' in contact_info and isinstance(contact_info['contact'], dict):
                profile = contact_info['contact'].get('profile', {})
                if isinstance(profile, dict):
                    name = profile.get('name')
                    if name and name.strip():
                        return name.strip()
            
            # Direct profile information
            if 'profile' in contact_info and isinstance(contact_info['profile'], dict):
                profile = contact_info['profile']
                name = profile.get('name') or profile.get('display_name') or profile.get('full_name')
                if name and name.strip():
                    return name.strip()
            
            # Direct name fields
            for name_field in ['name', 'display_name', 'full_name', 'contact_name', 'sender_name']:
                if name_field in contact_info:
                    name = contact_info[name_field]
                    if name and str(name).strip():
                        return str(name).strip()
            
            # Combined first/last name
            first_name = contact_info.get('first_name', '').strip()
            last_name = contact_info.get('last_name', '').strip()
            if first_name or last_name:
                return f"{first_name} {last_name}".strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting name from contact profile: {e}")
            return None
    
    def _name_from_phone_number(self, contact_info: Dict[str, Any]) -> Optional[str]:
        """Generate name from phone number"""
        try:
            # Look for phone numbers in various formats
            for phone_field in ['from', 'phone', 'phone_number', 'contact_phone', 'wa_id']:
                phone = contact_info.get(phone_field)
                if phone and str(phone).strip():
                    phone_str = str(phone).strip()
                    
                    # Clean phone number
                    clean_phone = re.sub(r'[^\d+]', '', phone_str)
                    
                    if clean_phone:
                        # Format phone number nicely
                        if clean_phone.startswith('+'):
                            formatted_phone = clean_phone
                        elif clean_phone.startswith('1') and len(clean_phone) == 11:
                            # US number
                            formatted_phone = f"+{clean_phone}"
                        elif len(clean_phone) >= 10:
                            formatted_phone = f"+{clean_phone}"
                        else:
                            formatted_phone = clean_phone
                        
                        return f"Contact {formatted_phone}"
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting name from phone: {e}")
            return None
    
    def _name_from_email(self, contact_info: Dict[str, Any]) -> Optional[str]:
        """Generate name from email address"""
        try:
            # Look for email addresses
            for email_field in ['from', 'email', 'sender', 'contact_email', 'email_address']:
                email = contact_info.get(email_field)
                if email and str(email).strip():
                    email_str = str(email).strip()
                    
                    # Validate email format
                    if '@' in email_str and '.' in email_str.split('@')[-1]:
                        # Extract name from email
                        local_part = email_str.split('@')[0]
                        
                        # Clean up the local part
                        clean_name = re.sub(r'[._-]', ' ', local_part)
                        clean_name = re.sub(r'\d+', '', clean_name).strip()
                        
                        if clean_name and len(clean_name) > 2:
                            # Capitalize words
                            return clean_name.title()
                        else:
                            # Use the email itself
                            return f"Contact {email_str}"
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting name from email: {e}")
            return None
    
    def _name_from_username(self, contact_info: Dict[str, Any], channel_type: str) -> Optional[str]:
        """Generate name from username or handle"""
        try:
            # Look for usernames
            for username_field in ['username', 'handle', 'screen_name', 'user_id', 'sender_id']:
                username = contact_info.get(username_field)
                if username and str(username).strip():
                    username_str = str(username).strip()
                    
                    # Clean username
                    clean_username = re.sub(r'[@#]', '', username_str)
                    
                    if clean_username and len(clean_username) > 2:
                        channel_prefix = channel_type.title()
                        return f"{channel_prefix} @{clean_username}"
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting name from username: {e}")
            return None
    
    def _name_from_message_content(self, message_content: Optional[str], channel_type: str) -> Optional[str]:
        """Generate name from first message content (last resort)"""
        try:
            if not message_content or not message_content.strip():
                return None
            
            content = message_content.strip()
            
            # Look for "Hi, I'm [Name]" patterns
            patterns = [
                r"hi[,\s]+i['\s]*m\s+([a-zA-Z\s]+)",
                r"hello[,\s]+i['\s]*m\s+([a-zA-Z\s]+)", 
                r"my\s+name\s+is\s+([a-zA-Z\s]+)",
                r"this\s+is\s+([a-zA-Z\s]+)",
                r"i['\s]*m\s+([a-zA-Z\s]+)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content.lower())
                if match:
                    name = match.group(1).strip().title()
                    if len(name) > 2 and len(name) < 50:
                        return name
            
            # If message is short and looks like a name
            if len(content) < 30 and len(content.split()) <= 3:
                # Check if it looks like a name (mostly letters)
                if re.match(r'^[a-zA-Z\s]+$', content):
                    return content.title()
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting name from message content: {e}")
            return None
    
    def _fallback_name(self, channel_type: str, external_thread_id: Optional[str]) -> str:
        """Generate fallback name when all else fails"""
        try:
            base_name = self.fallback_names.get(channel_type, f"{channel_type.title()} Contact")
            
            if external_thread_id:
                # Use a more user-friendly ID
                short_id = external_thread_id[-6:] if len(external_thread_id) > 6 else external_thread_id
                return f"{base_name} ({short_id})"
            
            return base_name
            
        except Exception as e:
            logger.error(f"Error generating fallback name: {e}")
            return "Unknown Contact"
    
    def _clean_conversation_name(self, name: str) -> str:
        """Clean and format conversation name"""
        try:
            if not name:
                return "Unknown Contact"
            
            # Remove extra whitespace
            clean_name = re.sub(r'\s+', ' ', name.strip())
            
            # Limit length
            if len(clean_name) > 50:
                clean_name = clean_name[:47] + "..."
            
            # Ensure it's not empty
            if not clean_name:
                return "Unknown Contact"
            
            return clean_name
            
        except Exception:
            return "Unknown Contact"
    
    async def update_conversation_names_from_contacts(self, channel_type: str, account_id: str):
        """
        Update conversation names by linking with contact records
        This can be called periodically to improve conversation names
        """
        try:
            from ..models import Conversation, Message
            from pipelines.models import Record
            
            # Get conversations that might need better names
            conversations = await sync_to_async(list)(
                Conversation.objects.filter(
                    channel__channel_type=channel_type,
                    channel__unipile_account_id=account_id,
                    subject__iregex=r'^(conversation|chat|whatsapp|email|contact)\s+[a-z0-9]{6,8}$'
                ).select_related('channel')[:50]
            )
            
            updated_count = 0
            
            for conversation in conversations:
                try:
                    # Get the first message to extract contact info
                    first_message = await sync_to_async(
                        lambda: conversation.messages.order_by('created_at').first()
                    )()
                    
                    if not first_message:
                        continue
                    
                    # Try to find linked contact record
                    contact_record = None
                    if first_message.contact_record:
                        contact_record = first_message.contact_record
                    elif first_message.contact_phone:
                        # Try to find contact by phone
                        contact_record = await sync_to_async(
                            lambda: Record.objects.filter(
                                data__phone=first_message.contact_phone
                            ).first()
                        )()
                    elif first_message.contact_email:
                        # Try to find contact by email
                        contact_record = await sync_to_async(
                            lambda: Record.objects.filter(
                                data__email=first_message.contact_email
                            ).first()
                        )()
                    
                    # Generate better name
                    if contact_record and contact_record.data:
                        # Use contact record data
                        new_name = self.generate_conversation_name(
                            channel_type=channel_type,
                            contact_info=contact_record.data,
                            message_content=first_message.content
                        )
                    else:
                        # Use message metadata
                        contact_info = {
                            'from': first_message.contact_phone or first_message.contact_email,
                            'contact_phone': first_message.contact_phone,
                            'contact_email': first_message.contact_email
                        }
                        
                        # Add metadata if available
                        if hasattr(first_message, 'metadata') and first_message.metadata:
                            contact_info.update(first_message.metadata)
                        
                        new_name = self.generate_conversation_name(
                            channel_type=channel_type,
                            contact_info=contact_info,
                            message_content=first_message.content,
                            external_thread_id=conversation.external_thread_id
                        )
                    
                    # Update if name is better
                    if new_name != conversation.subject and 'Contact' in new_name or any(name in new_name for name in ['@', '+', '.']):
                        conversation.subject = new_name
                        await sync_to_async(conversation.save)(update_fields=['subject'])
                        updated_count += 1
                        
                        logger.info(f"Updated conversation name: '{conversation.subject}' -> '{new_name}'")
                    
                except Exception as e:
                    logger.error(f"Error updating conversation {conversation.id}: {e}")
                    continue
            
            logger.info(f"Updated {updated_count} conversation names for {channel_type} account {account_id}")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating conversation names: {e}")
            return 0


# Global instance
conversation_naming_service = ConversationNamingService()