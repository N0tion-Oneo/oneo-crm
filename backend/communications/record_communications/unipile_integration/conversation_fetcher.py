"""
Conversation Fetcher - Retrieves all conversations with chat-specific attendees

Fetches all conversations from a channel and enriches them with chat-specific
attendee information for proper name resolution.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class ConversationFetcher:
    """Fetches all conversations with their attendees from UniPile"""
    
    def __init__(self, unipile_client):
        """
        Initialize with UniPile client
        
        Args:
            unipile_client: Instance of UnipileClient with messaging capabilities
        """
        self.unipile_client = unipile_client
    
    def fetch_all_conversations_with_attendees(
        self,
        account_id: str,
        channel_type: str,
        days_back: int = 30,
        max_conversations: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch all conversations with their specific attendees
        
        This method:
        1. Fetches all chats for the account
        2. For each chat, fetches the chat-specific attendees
        3. Fetches messages for each chat
        4. Returns enriched conversation data
        
        Args:
            account_id: UniPile account ID
            channel_type: Type of messaging channel (whatsapp, linkedin, etc.)
            days_back: Number of days of history to fetch (0 = all)
            max_conversations: Maximum conversations to process
            
        Returns:
            List of conversation dictionaries with attendees and messages:
            [
                {
                    'chat_id': 'chat_456',
                    'chat_data': {...},
                    'attendees': {...},  # Chat-specific attendees with names
                    'messages': [...]
                }
            ]
        """
        from asgiref.sync import async_to_sync
        
        conversations = []
        
        # Calculate date filter
        after_date = None
        if days_back > 0:
            after_date = (timezone.now() - timedelta(days=days_back)).isoformat()
        
        try:
            # Step 1: Fetch all chats for this account
            logger.info(f"Fetching all {channel_type} chats for account {account_id}")
            
            all_chats = []
            cursor = None
            
            while len(all_chats) < max_conversations:
                params = {
                    'account_id': account_id,
                    'limit': min(50, max_conversations - len(all_chats))
                }
                if cursor:
                    params['cursor'] = cursor
                
                # Add channel type filter if supported
                if channel_type == 'whatsapp':
                    params['account_type'] = 'WHATSAPP'
                elif channel_type == 'linkedin':
                    params['account_type'] = 'LINKEDIN'
                
                response = async_to_sync(self.unipile_client.messaging.get_all_chats)(**params)
                
                if not response or 'items' not in response:
                    break
                
                all_chats.extend(response['items'])
                
                cursor = response.get('cursor')
                if not cursor or not response.get('has_more', False):
                    break
            
            logger.info(f"Found {len(all_chats)} {channel_type} chats")
            
            # Step 2: For each chat, fetch attendees and messages
            for chat in all_chats[:max_conversations]:
                chat_id = chat.get('id')
                if not chat_id:
                    continue
                
                try:
                    # Fetch attendees specific to this chat
                    attendees = self._fetch_chat_attendees(chat_id)
                    
                    # Fetch messages for this chat
                    messages = self._fetch_chat_messages(
                        chat_id,
                        account_id,
                        after_date
                    )
                    
                    if messages:
                        conversations.append({
                            'chat_id': chat_id,
                            'chat_data': chat,
                            'attendees': attendees,  # Chat-specific attendees
                            'messages': messages
                        })
                        
                        logger.info(
                            f"Fetched chat {chat_id} with {len(attendees)} attendees "
                            f"and {len(messages)} messages"
                        )
                
                except Exception as e:
                    logger.error(f"Error processing chat {chat_id}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(conversations)} {channel_type} conversations")
            return conversations
            
        except Exception as e:
            logger.error(f"Error fetching conversations for {channel_type}: {e}")
            return []
    
    def _fetch_chat_attendees(self, chat_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Fetch attendees for a specific chat
        
        Args:
            chat_id: UniPile chat ID
            
        Returns:
            Dict mapping attendee IDs to attendee info with names
        """
        from asgiref.sync import async_to_sync
        
        attendees = {}
        
        try:
            # Use the get_attendees_from_chat endpoint
            response = async_to_sync(self.unipile_client.messaging.get_attendees_from_chat)(
                chat_id=chat_id,
                limit=100
            )
            
            if response and 'items' in response:
                for attendee in response['items']:
                    attendee_id = attendee.get('id', '')
                    if attendee_id:
                        # Store by multiple keys for better matching
                        name = attendee.get('name', '')
                        provider_id = attendee.get('provider_id', '')
                        
                        attendee_info = {
                            'id': attendee_id,
                            'name': name,
                            'provider_id': provider_id,
                            'metadata': attendee
                        }
                        
                        # Store by attendee ID
                        attendees[attendee_id] = attendee_info
                        
                        # Also store by provider_id if available
                        if provider_id:
                            attendees[provider_id] = attendee_info
                            
                            # For WhatsApp, also store by phone number
                            if '@s.whatsapp.net' in provider_id:
                                phone = provider_id.replace('@s.whatsapp.net', '')
                                if phone:
                                    attendees[phone] = attendee_info
                
                logger.debug(f"Fetched {len(response['items'])} attendees for chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error fetching attendees for chat {chat_id}: {e}")
        
        return attendees
    
    def _fetch_chat_messages(
        self,
        chat_id: str,
        account_id: str,
        after_date: Optional[str],
        max_messages: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages for a specific chat
        
        Args:
            chat_id: UniPile chat ID
            account_id: UniPile account ID
            after_date: Optional date filter
            max_messages: Maximum messages to fetch
            
        Returns:
            List of message dictionaries
        """
        from asgiref.sync import async_to_sync
        
        messages = []
        cursor = None
        
        while len(messages) < max_messages:
            try:
                params = {
                    'limit': min(100, max_messages - len(messages))
                }
                
                if cursor:
                    params['cursor'] = cursor
                if after_date:
                    params['since'] = after_date
                
                # Use the chat-specific message endpoint
                response = async_to_sync(self.unipile_client.messaging.get_all_messages)(
                    chat_id=chat_id,
                    **params
                )
                
                if not response or 'items' not in response:
                    break
                
                messages.extend(response['items'])
                
                cursor = response.get('cursor')
                if not cursor or not response.get('has_more', False):
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching messages for chat {chat_id}: {e}")
                break
        
        return messages