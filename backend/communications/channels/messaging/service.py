"""
Unified Messaging Service for WhatsApp and LinkedIn
Handles sending messages via UniPile's chat-based API
"""
import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone

logger = logging.getLogger(__name__)


class MessagingService:
    """Unified service for WhatsApp and LinkedIn messaging"""
    
    def __init__(self, channel_type: str):
        """
        Initialize messaging service
        
        Args:
            channel_type: Either 'whatsapp' or 'linkedin'
        """
        self.channel_type = channel_type
        self._client = None
    
    @property
    def client(self):
        """Lazy load UniPile client"""
        if not self._client:
            from communications.unipile.core.client import UnipileClient
            from django.conf import settings
            
            # Get UniPile credentials from settings
            dsn = getattr(settings, 'UNIPILE_DSN', 'https://api18.unipile.com:14890')
            access_token = getattr(settings, 'UNIPILE_API_KEY', None)
            
            if not access_token:
                raise ValueError("UNIPILE_API_KEY not configured in settings")
            
            self._client = UnipileClient(dsn=dsn, access_token=access_token)
        return self._client
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        attachments: Optional[List[Dict]] = None,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send message to existing chat
        
        Args:
            chat_id: UniPile chat ID
            text: Message content
            attachments: Optional list of attachments
            account_id: Optional account ID for validation
            
        Returns:
            Dict with success status and message_id
        """
        try:
            logger.info(f"📤 Sending {self.channel_type} message to chat {chat_id}")
            
            # Use the messaging client
            result = await self.client.messaging.send_message(
                chat_id=chat_id,
                text=text,
                attachments=attachments
            )
            
            # UniPile returns message_id on success
            if result and 'message_id' in result:
                logger.info(f"✅ Message sent successfully: {result['message_id']}")
                return {
                    'success': True,
                    'message_id': result['message_id']
                }
            else:
                logger.error(f"Failed to send message: {result}")
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Error sending {self.channel_type} message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def start_new_chat(
        self,
        account_id: str,
        attendee_ids: List[str],
        text: str,
        attachments: Optional[List[Dict]] = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start new chat and send first message
        
        Args:
            account_id: UniPile account ID
            attendee_ids: List of attendee IDs (phone@s.whatsapp.net or LinkedIn URN)
            text: Initial message text
            attachments: Optional attachments
            subject: Optional subject (for LinkedIn)
            
        Returns:
            Dict with success status and chat_id
        """
        try:
            logger.info(f"📤 Starting new {self.channel_type} chat with {attendee_ids}")
            
            # Build request data
            data = {
                'account_id': account_id,
                'attendees_ids': attendee_ids,
                'text': text
            }
            
            # Add subject for LinkedIn if provided
            if subject and self.channel_type == 'linkedin':
                data['subject'] = subject
            
            # Add LinkedIn-specific options if needed
            if self.channel_type == 'linkedin':
                # Could add inmail, recruiter options, etc.
                pass
            
            # Start new chat via UniPile
            result = await self.client.messaging.start_new_chat(
                account_id=account_id,
                attendees_ids=attendee_ids,
                text=text,
                attachments=attachments
            )
            
            # UniPile returns chat info on success
            # According to docs, response has 'object': 'ChatStarted', 'chat_id', 'message_id'
            if result and (result.get('object') == 'ChatStarted' or result.get('chat_id')):
                chat_id = result.get('chat_id')
                logger.info(f"✅ New chat created: {chat_id}")
                return {
                    'success': True,
                    'chat_id': chat_id,
                    'message_id': result.get('message_id')
                }
            else:
                logger.error(f"Failed to start chat: {result}")
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to start chat')
                }
                
        except Exception as e:
            logger.error(f"Error starting {self.channel_type} chat: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def find_or_create_chat(
        self,
        account_id: str,
        attendee_id: str,
        text: str = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Find existing chat with attendee or create a new one
        
        Args:
            account_id: UniPile account ID  
            attendee_id: Attendee ID to find/create chat with
            text: Initial message text if creating new chat
            attachments: Optional attachments for new chat
            
        Returns:
            Dict with chat_id and whether it was found or created
        """
        try:
            logger.info(f"🔍 Looking for existing {self.channel_type} chat with {attendee_id}")
            
            # First, try to find existing chats with this attendee
            result = await self.client.messaging.get_chats_from_attendee(
                attendee_id=attendee_id,
                account_id=account_id,
                limit=10
            )
            
            if result and 'items' in result:
                chats = result['items']
                if chats and len(chats) > 0:
                    # Found existing chat(s), use the first (most recent) one
                    chat = chats[0]
                    chat_id = chat.get('id')
                    logger.info(f"✅ Found existing chat: {chat_id}")
                    return {
                        'success': True,
                        'chat_id': chat_id,
                        'found': True,
                        'created': False
                    }
            
            # No existing chat found, create a new one if text is provided
            if text:
                logger.info(f"📝 No existing chat found, creating new {self.channel_type} chat")
                result = await self.start_new_chat(
                    account_id=account_id,
                    attendee_ids=[attendee_id],
                    text=text,
                    attachments=attachments
                )
                
                if result.get('success'):
                    return {
                        'success': True,
                        'chat_id': result.get('chat_id'),
                        'message_id': result.get('message_id'),
                        'found': False,
                        'created': True
                    }
                else:
                    return result
            else:
                # No existing chat and no text to create new one
                return {
                    'success': True,
                    'found': False,
                    'created': False,
                    'error': 'No existing chat found and no message provided to create new chat'
                }
            
        except Exception as e:
            logger.error(f"Error in find_or_create_chat: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def format_phone_for_whatsapp(self, phone: str) -> str:
        """
        Format phone number for WhatsApp attendee ID
        
        Args:
            phone: Phone number in various formats
            
        Returns:
            Formatted phone@s.whatsapp.net
        """
        import re
        
        # Remove all non-digits except +
        phone = re.sub(r'[^\d+]', '', phone)
        
        # Add country code if missing
        if not phone.startswith('+'):
            # Assume US if 10 digits
            if len(phone) == 10:
                phone = f'+1{phone}'
            else:
                phone = f'+{phone}'
        
        # Remove the + for WhatsApp format
        phone = phone.replace('+', '')
        
        return f"{phone}@s.whatsapp.net"
    
    async def resolve_attendee(
        self,
        identifier: str,
        account_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolve an identifier (phone, email, name) to attendee ID
        
        Args:
            identifier: Phone number, email, or name
            account_id: Optional account ID for context
            
        Returns:
            Attendee ID suitable for UniPile API
        """
        if self.channel_type == 'whatsapp':
            # For WhatsApp, format phone number
            return self.format_phone_for_whatsapp(identifier)
        
        elif self.channel_type == 'linkedin':
            # For LinkedIn, might need to search if not a URN
            if identifier.startswith('urn:li:'):
                return identifier
            
            # Could implement search by name/email here
            # For now, assume it's provided correctly
            return identifier
        
        return None