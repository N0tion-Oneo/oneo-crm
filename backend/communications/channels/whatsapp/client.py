"""
WhatsApp Client using UniPile SDK
Handles all WhatsApp API operations through UniPile
"""
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings
from ..base import BaseChannelClient

logger = logging.getLogger(__name__)


class WhatsAppClient(BaseChannelClient):
    """WhatsApp client implementation using UniPile SDK"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize WhatsApp client
        
        Args:
            api_key: UniPile API key (defaults to settings)
        """
        super().__init__(api_key or settings.UNIPILE_API_KEY)
        
        # Initialize UniPile messaging client with proper parameters
        from communications.unipile import UnipileMessagingClient, UnipileClient
        
        # Get DSN from settings (UNIPILE_DSN is the correct setting)
        dsn = getattr(settings, 'UNIPILE_DSN', '')
        # if not dsn:
        #     # Fallback to UNIPILE_BASE_URL if exists
        #     dsn = getattr(settings, 'UNIPILE_BASE_URL', 'https://api1.unipile.com:13111')
        
        access_token = self.api_key
        
        logger.debug(f"Initializing UniPile client with DSN: {dsn}")
        
        self.unipile_client = UnipileClient(dsn=dsn, access_token=access_token)
        self.messaging_client = UnipileMessagingClient(self.unipile_client)
    
    def get_channel_type(self) -> str:
        """Return the channel type"""
        return 'whatsapp'
    
    async def get_conversations(
        self,
        account_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get WhatsApp chats for an account
        
        Args:
            account_id: UniPile account ID
            limit: Number of chats to retrieve
            cursor: Pagination cursor
            **kwargs: Additional parameters
            
        Returns:
            Dict with chats data and pagination info
        """
        try:
            # Use UniPile messaging client to get chats
            result = await self.messaging_client.get_all_chats(
                account_id=account_id,
                cursor=cursor,
                limit=limit,
                account_type='WHATSAPP'
            )
            
            # Transform to our format  
            # Note: UniPile doesn't return has_more, we infer it from cursor presence and item count
            conversations = result.get('items', [])
            cursor = result.get('cursor')
            
            # Determine has_more based on cursor presence
            # If there's a cursor, there are more conversations to fetch
            # UniPile uses cursor-based pagination, so cursor presence is the definitive indicator
            has_more = cursor is not None
            
            return {
                'success': True,
                'conversations': conversations,
                'cursor': cursor,
                'has_more': has_more,
                'total': result.get('total_count')
            }
            
        except Exception as e:
            logger.error(f"Failed to get WhatsApp conversations: {e}")
            return {
                'success': False,
                'error': str(e),
                'conversations': []
            }
    
    async def get_chats(
        self,
        account_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get WhatsApp chats (alias for get_conversations)
        
        Args:
            account_id: UniPile account ID
            limit: Number of chats to retrieve
            cursor: Pagination cursor
            **kwargs: Additional parameters
            
        Returns:
            Dict with chats data and pagination info
        """
        result = await self.get_conversations(account_id, limit, cursor, **kwargs)
        # Rename 'conversations' to 'chats' for compatibility
        if 'conversations' in result:
            result['chats'] = result.pop('conversations')
        return result
    
    async def get_messages(
        self,
        account_id: str,
        conversation_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get messages for a WhatsApp chat
        
        Args:
            account_id: UniPile account ID (not used for chat-specific endpoints)
            conversation_id: Chat ID
            limit: Number of messages to retrieve
            cursor: Pagination cursor
            **kwargs: Additional parameters
            
        Returns:
            Dict with messages data and pagination info
        """
        try:
            # Safety check: UniPile API has a maximum limit of ~250
            # We cap at 200 to be safe from API errors
            # The actual limit per conversation is controlled by sync config (typically 100)
            safe_limit = min(limit, 200)
            if limit > 200:
                logger.warning(f"Message limit {limit} exceeds API maximum, capping at 200")
            
            # Use UniPile messaging client to get messages
            # IMPORTANT: UniPile API returns 400 if account_id is passed with chat_id
            # When fetching messages for a specific chat, only use chat_id
            result = await self.messaging_client.get_all_messages(
                chat_id=conversation_id,
                cursor=cursor,
                limit=safe_limit
            )
            
            # Debug: Log raw API response structure
            logger.info(f"📝 Raw API response keys: {list(result.keys()) if result else 'None'}")
            logger.info(f"📝 Raw cursor value: {repr(result.get('cursor'))} (type: {type(result.get('cursor')).__name__})")
            
            # Transform to our format
            # Note: UniPile doesn't return has_more, we infer it from cursor presence and message count
            messages = result.get('items', [])
            cursor = result.get('cursor')
            
            # Determine has_more based on cursor presence
            # If there's a cursor, there are more messages to fetch
            # UniPile uses cursor-based pagination, so cursor presence is the definitive indicator
            has_more = cursor is not None
            
            # Log useful debugging info
            total_count = result.get('total_count')
            if total_count:
                logger.debug(f"API reports total_count: {total_count} messages for conversation")
            
            # Enhanced debugging for pagination issues
            logger.info(f"📊 Message pagination for {conversation_id[:20]}: got {len(messages)} messages, cursor={cursor}, has_more={has_more}")
            
            # Log the raw response for debugging
            if messages:
                # Log first and last message timestamps to understand the range
                first_msg = messages[0]
                last_msg = messages[-1]
                logger.info(f"  📅 Message range: first={first_msg.get('timestamp', 'unknown')[:19]}, last={last_msg.get('timestamp', 'unknown')[:19]}")
            
            if not has_more and len(messages) == safe_limit:
                logger.warning(f"⚠️ PAGINATION ISSUE: Got full batch ({safe_limit}) but no cursor - API may have more messages!")
            
            # Check if cursor is an empty string or empty dict vs None
            if cursor == '' or cursor == {}:
                logger.warning(f"⚠️ Cursor is empty ({repr(cursor)}) - treating as no more data")
                has_more = False
            
            # Special check: if we got exactly the limit and no cursor, there might be more
            if len(messages) == safe_limit and not cursor:
                logger.error(f"🚨 POTENTIAL API BUG: Got exactly {safe_limit} messages but no cursor! There may be more messages that the API isn't providing access to.")
            
            return {
                'success': True,
                'messages': messages,
                'cursor': cursor,
                'has_more': has_more,
                'total': total_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get WhatsApp messages: {e}")
            return {
                'success': False,
                'error': str(e),
                'messages': []
            }
    
    async def send_message(
        self,
        account_id: str,
        conversation_id: str,
        content: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message
        
        Args:
            account_id: UniPile account ID
            conversation_id: Chat ID
            content: Message text content
            attachments: Optional list of attachments
            **kwargs: Additional parameters
            
        Returns:
            Dict with sent message details
        """
        try:
            # Prepare message data for UniPile
            message_data = {
                'text': content
            }
            
            # Add attachments if provided
            if attachments:
                message_data['attachments'] = attachments
            
            # Send through UniPile
            result = await self.messaging_client.send_message(
                chat_id=conversation_id,
                account_id=account_id,
                **message_data
            )
            
            return {
                'success': True,
                'message': result,
                'message_id': result.get('id')
            }
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def mark_as_read(
        self,
        account_id: str,
        conversation_id: str,
        message_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Mark a WhatsApp message as read
        
        Args:
            account_id: UniPile account ID
            conversation_id: Chat ID
            message_id: Message ID to mark as read
            **kwargs: Additional parameters
            
        Returns:
            Dict with operation result
        """
        try:
            # UniPile mark as read endpoint
            result = await self.messaging_client.mark_message_as_read(
                account_id=account_id,
                chat_id=conversation_id,
                message_id=message_id
            )
            
            return {
                'success': True,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to mark WhatsApp message as read: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_attendees(self, account_id: str, chat_id: str) -> Dict[str, Any]:
        """
        Get attendees/participants for a WhatsApp chat
        
        Args:
            account_id: UniPile account ID
            chat_id: Chat ID
            
        Returns:
            Dict with attendees data
        """
        try:
            # Use the dedicated attendees endpoint
            result = await self.messaging_client.get_attendees_from_chat(chat_id)
            
            # Extract attendees from the result
            attendees = result.get('items', [])
            
            return {
                'success': True,
                'attendees': attendees,
                'count': len(attendees)
            }
            
        except Exception as e:
            logger.error(f"Failed to get WhatsApp attendees: {e}")
            return {
                'success': False,
                'error': str(e),
                'attendees': []
            }
    
    async def get_profile_picture(self, account_id: str, attendee_id: str) -> Optional[bytes]:
        """
        Get profile picture for a WhatsApp contact
        
        Args:
            account_id: UniPile account ID
            attendee_id: Attendee/contact ID
            
        Returns:
            Image bytes or None
        """
        try:
            # This would need to be implemented based on UniPile's API
            # For now, return None as placeholder
            logger.info(f"Getting profile picture for {attendee_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get profile picture: {e}")
            return None
    
    async def sync_chat_history(
        self,
        account_id: str,
        chat_id: str,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Sync historical messages for a WhatsApp chat
        
        Args:
            account_id: UniPile account ID
            chat_id: Chat ID
            days_back: Number of days to sync back
            
        Returns:
            Dict with sync operation details
        """
        try:
            # Calculate date range
            from datetime import datetime, timedelta
            since_date = datetime.now() - timedelta(days=days_back)
            
            # Get messages with date filter
            # NOTE: When chat_id is provided, do NOT pass account_id as it causes 400 errors
            result = await self.messaging_client.get_all_messages(
                chat_id=chat_id,
                # account_id=account_id,  # Don't include account_id when using chat_id endpoint
                since=since_date.isoformat()
            )
            
            return {
                'success': True,
                'messages_synced': len(result.get('items', [])),
                'days_back': days_back,
                'oldest_message': result.get('items', [])[-1] if result.get('items') else None
            }
            
        except Exception as e:
            logger.error(f"Failed to sync WhatsApp chat history: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def update_chat_metadata(
        self,
        account_id: str,
        chat_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update chat metadata (e.g., labels, archived status)
        
        Args:
            account_id: UniPile account ID
            chat_id: Chat ID
            metadata: Metadata to update
            
        Returns:
            Dict with update result
        """
        try:
            # This would need UniPile API support
            logger.info(f"Updating chat {chat_id} metadata: {metadata}")
            
            return {
                'success': True,
                'chat_id': chat_id,
                'updated': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to update chat metadata: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_account_info(self, account_id: str) -> Dict[str, Any]:
        """
        Get WhatsApp account information
        
        Args:
            account_id: UniPile account ID
            
        Returns:
            Dict with account details
        """
        try:
            # Use UniPile account client
            from communications.unipile import UnipileAccountClient
            account_client = UnipileAccountClient(self.unipile_client)
            
            account_info = await account_client.get_account(account_id)
            
            return {
                'success': True,
                'account': account_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get WhatsApp account info: {e}")
            return {
                'success': False,
                'error': str(e)
            }