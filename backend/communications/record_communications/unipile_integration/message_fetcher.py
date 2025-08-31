"""
Message Fetcher - Retrieves messages for specific attendees

Handles fetching historical message data from UniPile for record-specific attendees.
Supports WhatsApp, LinkedIn, Telegram, Instagram, etc.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone
from .message_enricher import MessageEnricher

logger = logging.getLogger(__name__)


class MessageFetcher:
    """Fetches messages for specific attendees from UniPile"""
    
    def __init__(self, unipile_client):
        """
        Initialize with UniPile client
        
        Args:
            unipile_client: Instance of UnipileClient with messaging capabilities
        """
        self.unipile_client = unipile_client
        self.message_enricher = MessageEnricher()
    
    def fetch_messages_for_attendees(
        self,
        attendee_map: Dict[str, Dict[str, Any]],
        account_id: str,
        channel_type: str,
        days_back: int = 30,
        max_messages_per_attendee: int = 500
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch historical messages for specific attendees
        
        Args:
            attendee_map: Dict mapping provider_id to attendee info
            account_id: UniPile account ID
            channel_type: Type of messaging channel
            days_back: Number of days of history to fetch (0 = all)
            max_messages_per_attendee: Maximum messages to fetch per attendee
            
        Returns:
            Dict mapping attendee_id to their conversations and messages:
            {
                'attendee_123': {
                    'attendee_info': {...},
                    'conversations': [
                        {
                            'chat_id': 'chat_456',
                            'chat_data': {...},
                            'messages': [...]
                        }
                    ]
                }
            }
        """
        message_data = {}
        
        # Calculate date filter (0 = no date filter, fetch all history)
        after_date = None
        if days_back > 0:
            after_date = (timezone.now() - timedelta(days=days_back)).isoformat()
        
        for provider_id, attendee_info in attendee_map.items():
            attendee_id = attendee_info.get('attendee_id')
            
            if not attendee_id:
                logger.warning(f"No attendee_id for provider {provider_id}")
                continue
            
            try:
                # Fetch conversations and messages for this attendee
                conversations = self._fetch_attendee_conversations(
                    attendee_id,
                    account_id,
                    channel_type,
                    after_date,
                    max_messages_per_attendee
                )
                
                message_data[attendee_id] = {
                    'attendee_info': attendee_info,
                    'conversations': conversations
                }
                
                logger.info(
                    f"Fetched {len(conversations)} conversations for attendee {attendee_id}"
                )
                
            except Exception as e:
                logger.error(f"Failed to fetch messages for attendee {attendee_id}: {e}")
                message_data[attendee_id] = {
                    'attendee_info': attendee_info,
                    'conversations': []
                }
        
        return message_data
    
    def _fetch_attendee_conversations(
        self,
        attendee_id: str,
        account_id: str,
        channel_type: str,
        after_date: Optional[str],
        max_messages: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch conversations and messages for a specific attendee
        
        For WhatsApp: Use provider_id to get 1-on-1 chats
        For LinkedIn: Special flow to get 1-on-1 chats
        
        Args:
            attendee_id: UniPile attendee ID or provider_id for WhatsApp
            account_id: UniPile account ID
            channel_type: Channel type for filtering
            after_date: Optional date filter
            max_messages: Maximum messages to fetch
            
        Returns:
            List of conversation dictionaries with messages
        """
        from asgiref.sync import async_to_sync
        
        # Special handling for LinkedIn - use 1-to-1 chats endpoint
        if channel_type == 'linkedin':
            return self._fetch_linkedin_conversations(
                attendee_id, 
                account_id, 
                after_date, 
                max_messages
            )
        
        # Special handling for WhatsApp - use provider_id to get 1-on-1 chats
        if channel_type == 'whatsapp':
            return self._fetch_whatsapp_conversations(
                attendee_id,  # This is actually the provider_id for WhatsApp
                account_id,
                after_date,
                max_messages
            )
        
        # For other channels, use the original flow
        messages = self._fetch_messages_for_attendee(
            attendee_id,
            account_id,
            after_date,
            max_messages
        )
        
        # Group messages by conversation/chat
        conversations_map = {}
        
        for message in messages:
            chat_id = message.get('chat_id') or message.get('conversation_id')
            
            if not chat_id:
                logger.warning(f"Message {message.get('id')} has no chat_id")
                continue
            
            if chat_id not in conversations_map:
                # Fetch chat details
                chat_data = self._fetch_chat_details(chat_id, account_id)
                
                conversations_map[chat_id] = {
                    'chat_id': chat_id,
                    'chat_data': chat_data,
                    'messages': []
                }
            
            conversations_map[chat_id]['messages'].append(message)
        
        # Convert to list and sort by most recent message
        conversations = list(conversations_map.values())
        conversations.sort(
            key=lambda c: self._get_latest_message_time(c['messages']),
            reverse=True
        )
        
        return conversations
    
    def _fetch_messages_for_attendee(
        self,
        attendee_id: str,
        account_id: str,
        after_date: Optional[str],
        max_messages: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages for a specific attendee using the dedicated endpoint
        
        Uses: GET /api/v1/chat_attendees/{attendee_id}/messages
        
        Args:
            attendee_id: UniPile attendee ID
            account_id: UniPile account ID
            after_date: Optional date filter
            max_messages: Maximum messages to fetch
            
        Returns:
            List of message dictionaries
        """
        from asgiref.sync import async_to_sync
        
        messages = []
        cursor = None
        total_fetched = 0
        
        while total_fetched < max_messages:
            try:
                # Build request parameters
                params = {
                    'limit': min(250, max_messages - total_fetched)  # Allow more messages per request
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                if after_date:
                    params['after'] = after_date
                
                # Add account_id if the API requires it
                params['account_id'] = account_id
                
                # Call the attendee-specific message endpoint
                # Note: This endpoint might not exist in the current UnipileMessagingClient
                # We need to add it or use a direct API call
                
                # Option 1: If the method exists
                # response = async_to_sync(self.unipile_client.messaging.get_messages_for_attendee)(
                #     attendee_id=attendee_id,
                #     **params
                # )
                
                # Option 2: Direct API call (if method doesn't exist)
                endpoint = f'chat_attendees/{attendee_id}/messages'
                response = async_to_sync(self.unipile_client._make_request)(
                    'GET',
                    endpoint,
                    params=params
                )
                
                if not response or 'items' not in response:
                    break
                
                messages.extend(response['items'])
                total_fetched += len(response['items'])
                
                # Check for more pages
                cursor = response.get('cursor')
                if not cursor:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching messages for attendee {attendee_id}: {e}")
                break
        
        logger.info(f"Fetched {len(messages)} messages for attendee {attendee_id}")
        return messages
    
    def _fetch_chat_details(
        self,
        chat_id: str,
        account_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch details of a specific chat/conversation
        
        Args:
            chat_id: UniPile chat ID
            account_id: Optional UniPile account ID
            
        Returns:
            Chat data or None
        """
        from asgiref.sync import async_to_sync
        
        try:
            # Fetch chat details
            chat = async_to_sync(self.unipile_client.messaging.get_chat)(
                chat_id=chat_id
            )
            
            return chat
            
        except Exception as e:
            logger.error(f"Failed to fetch chat details for {chat_id}: {e}")
            return None
    
    def _get_latest_message_time(self, messages: List[Dict[str, Any]]) -> datetime:
        """
        Get the timestamp of the most recent message
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Datetime of the most recent message
        """
        if not messages:
            return datetime.min.replace(tzinfo=dt_timezone.utc)
        
        latest_time = datetime.min.replace(tzinfo=dt_timezone.utc)
        
        for message in messages:
            # Try different timestamp fields
            timestamp_str = (
                message.get('timestamp') or 
                message.get('created_at') or
                message.get('sent_at')
            )
            
            if timestamp_str:
                try:
                    # Parse ISO format timestamp
                    if isinstance(timestamp_str, str):
                        timestamp = datetime.fromisoformat(
                            timestamp_str.replace('Z', '+00:00')
                        )
                    else:
                        timestamp = timestamp_str
                    
                    if timestamp > latest_time:
                        latest_time = timestamp
                        
                except Exception as e:
                    logger.debug(f"Failed to parse timestamp: {e}")
        
        return latest_time
    
    def _fetch_linkedin_conversations(
        self,
        attendee_id: str,
        account_id: str,
        after_date: Optional[str],
        max_messages: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch LinkedIn conversations using the 1-to-1 chats endpoint
        
        LinkedIn requires using the chat_attendees endpoint to get 1-to-1 chats,
        then fetching messages for each chat.
        
        Args:
            attendee_id: Provider ID of the LinkedIn user
            account_id: UniPile account ID
            after_date: Optional date filter
            max_messages: Maximum messages to fetch
            
        Returns:
            List of conversation dictionaries with messages
        """
        from asgiref.sync import async_to_sync
        
        conversations = []
        
        try:
            logger.info(f"Fetching LinkedIn 1-to-1 chats for attendee: {attendee_id}")
            
            # Fetch ALL chats with pagination
            all_chats = []
            cursor = None
            page = 1
            
            while True:
                # Use the proper API endpoint to get chats for this attendee
                params = {
                    'attendee_id': attendee_id,  # For LinkedIn, this is the provider_id from profile
                    'account_id': account_id,
                    'limit': 100  # Max batch size
                }
                if cursor:
                    params['cursor'] = cursor
                
                response = async_to_sync(self.unipile_client.messaging.get_chats_from_attendee)(**params)
                
                if not response or 'items' not in response:
                    if page == 1:
                        logger.warning(f"No chats found for LinkedIn attendee: {attendee_id}")
                    break
                
                chats_batch = response.get('items', [])
                all_chats.extend(chats_batch)
                
                # Check for more pages
                cursor = response.get('cursor')
                if not cursor:
                    break
                    
                page += 1
            
            relevant_chats = all_chats
            logger.info(f"Found {len(relevant_chats)} chats for LinkedIn attendee across {page} pages")
            
            # Step 3: For each relevant chat, fetch messages
            messages_fetched = 0
            fetch_all = (max_messages == 0)  # 0 means fetch all
            
            for chat in relevant_chats:
                # Only check limit if we're not fetching all
                if not fetch_all and messages_fetched >= max_messages:
                    break
                
                chat_id = chat.get('id')
                if not chat_id:
                    continue
                
                # Get messages for this chat
                if fetch_all:
                    chat_limit = 0  # 0 means fetch all messages from this chat
                else:
                    chat_limit = min(250, max_messages - messages_fetched)
                
                chat_messages = self._fetch_messages_for_chat(
                    chat_id,
                    account_id,
                    after_date,
                    chat_limit
                )
                
                if chat_messages:
                    # Enrich messages with inferred sender information
                    enriched_messages = self.message_enricher.enrich_messages(
                        chat_messages,
                        'linkedin',
                        attendee_id  # Use the attendee_id as account identifier
                    )
                    
                    conversations.append({
                        'chat_id': chat_id,
                        'chat_data': chat,
                        'messages': enriched_messages
                    })
                    messages_fetched += len(enriched_messages)
                    
                    logger.info(f"Fetched {len(enriched_messages)} messages from LinkedIn chat {chat_id}")
            
            # Sort conversations by most recent message
            conversations.sort(
                key=lambda c: self._get_latest_message_time(c['messages']),
                reverse=True
            )
            
            logger.info(f"Successfully fetched {len(conversations)} LinkedIn conversations")
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn conversations for {attendee_id}: {e}")
        
        return conversations
    
    def _fetch_messages_for_chat(
        self,
        chat_id: str,
        account_id: str,
        after_date: Optional[str],
        max_messages: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages for a specific chat with pagination
        
        Args:
            chat_id: UniPile chat ID
            account_id: UniPile account ID
            after_date: Optional date filter
            max_messages: Maximum messages to fetch (0 = no limit, fetch all)
            
        Returns:
            List of message dictionaries
        """
        from asgiref.sync import async_to_sync
        
        messages = []
        cursor = None
        total_fetched = 0
        page = 1
        
        # If max_messages is 0, fetch everything
        fetch_all = (max_messages == 0)
        
        while fetch_all or total_fetched < max_messages:
            try:
                # Prepare parameters for this request
                if fetch_all:
                    batch_size = 100  # Use max batch size when fetching all
                else:
                    batch_size = min(100, max_messages - total_fetched)
                
                logger.debug(f"Fetching page {page} of chat {chat_id} (batch size: {batch_size})")
                
                # Get messages from the chat with pagination
                response = async_to_sync(self.unipile_client.messaging.get_all_messages)(
                    chat_id=chat_id,
                    limit=batch_size,
                    cursor=cursor
                )
                
                if not response or 'items' not in response:
                    break
                
                batch_messages = response.get('items', [])
                messages.extend(batch_messages)
                total_fetched += len(batch_messages)
                
                logger.debug(f"Page {page}: Got {len(batch_messages)} messages (total: {total_fetched})")
                
                # Check for more pages via cursor
                cursor = response.get('cursor')
                if not cursor:
                    logger.debug(f"No cursor returned - all messages fetched")
                    break
                
                # If we're not fetching all and hit the limit, stop
                if not fetch_all and total_fetched >= max_messages:
                    break
                    
                page += 1
                    
            except Exception as e:
                logger.error(f"Error fetching messages for chat {chat_id} on page {page}: {e}")
                break
        
        logger.info(f"Fetched {total_fetched} messages from chat {chat_id} across {page} pages")
        return messages
    
    def _fetch_whatsapp_conversations(
        self,
        provider_id: str,
        account_id: str,
        after_date: Optional[str],
        max_messages: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch WhatsApp conversations using 1-on-1 chats with provider ID
        
        WhatsApp flow:
        1. Use provider_id (phone@s.whatsapp.net) to get 1-on-1 chats
        2. Get messages from those chats
        
        Args:
            provider_id: WhatsApp provider ID (phone@s.whatsapp.net)
            account_id: UniPile account ID
            after_date: Optional date filter
            max_messages: Maximum messages to fetch
            
        Returns:
            List of conversation dictionaries with messages
        """
        from asgiref.sync import async_to_sync
        
        conversations = []
        
        try:
            logger.info(f"Fetching WhatsApp 1-on-1 chats for provider: {provider_id}")
            
            # Fetch ALL chats with pagination
            all_chats = []
            cursor = None
            page = 1
            
            while True:
                # Use the proper API endpoint to get chats for this attendee/provider_id
                params = {
                    'attendee_id': provider_id,  # For WhatsApp, this is phone@s.whatsapp.net
                    'account_id': account_id,
                    'limit': 100  # Max batch size
                }
                if cursor:
                    params['cursor'] = cursor
                
                response = async_to_sync(self.unipile_client.messaging.get_chats_from_attendee)(**params)
                
                if not response or 'items' not in response:
                    if page == 1:
                        logger.warning(f"No WhatsApp chats found for provider: {provider_id}")
                    break
                
                chats_batch = response.get('items', [])
                all_chats.extend(chats_batch)
                
                # Check for more pages
                cursor = response.get('cursor')
                if not cursor:
                    break
                    
                page += 1
            
            relevant_chats = all_chats
            logger.info(f"Found {len(relevant_chats)} WhatsApp chats for provider across {page} pages")
            
            # Step 2: For each relevant chat, fetch messages
            messages_fetched = 0
            fetch_all = (max_messages == 0)  # 0 means fetch all
            
            for chat in relevant_chats:
                # Only check limit if we're not fetching all
                if not fetch_all and messages_fetched >= max_messages:
                    break
                
                chat_id = chat.get('id')
                if not chat_id:
                    continue
                
                # Get messages for this chat
                if fetch_all:
                    chat_limit = 0  # 0 means fetch all messages from this chat
                else:
                    chat_limit = min(250, max_messages - messages_fetched)
                
                chat_messages = self._fetch_messages_for_chat(
                    chat_id,
                    account_id,
                    after_date,
                    chat_limit
                )
                
                if chat_messages:
                    # Enrich messages with inferred sender information
                    enriched_messages = self.message_enricher.enrich_messages(
                        chat_messages,
                        'whatsapp',
                        provider_id  # Use the provider_id as account identifier
                    )
                    
                    conversations.append({
                        'chat_id': chat_id,
                        'chat_data': chat,
                        'messages': enriched_messages
                    })
                    messages_fetched += len(enriched_messages)
                    
                    logger.info(f"Fetched {len(enriched_messages)} messages from WhatsApp chat {chat_id}")
            
            # Sort conversations by most recent message
            conversations.sort(
                key=lambda c: self._get_latest_message_time(c['messages']),
                reverse=True
            )
            
            logger.info(f"Successfully fetched {len(conversations)} WhatsApp conversations")
            
        except Exception as e:
            logger.error(f"Error fetching WhatsApp conversations for {provider_id}: {e}")
        
        return conversations
    
    def fetch_single_message(
        self,
        message_id: str,
        account_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single message by ID
        
        Args:
            message_id: UniPile message ID
            account_id: Optional UniPile account ID
            
        Returns:
            Message data or None
        """
        from asgiref.sync import async_to_sync
        
        try:
            # Fetch single message
            message = async_to_sync(self.unipile_client.messaging.get_message)(
                message_id=message_id
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to fetch message {message_id}: {e}")
            return None