"""
UniPile Messaging Client
Handles chat and message operations
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class UnipileMessagingClient:
    """UniPile messaging client"""
    
    def __init__(self, client):
        self.client = client
    
    async def get_all_chats(
        self, 
        account_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20,
        account_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all chats with pagination
        
        Args:
            account_id: Optional account ID to filter by specific account
            cursor: Pagination cursor from previous request  
            limit: Number of chats to return (default 20)
            account_type: Channel type (WHATSAPP, LINKEDIN, MESSENGER, TELEGRAM, etc.)
        """
        try:
            params = {'limit': limit}
            if account_id:
                params['account_id'] = account_id
            if cursor:
                params['cursor'] = cursor
            if account_type:
                params['account_type'] = account_type
                
            response = await self.client._make_request('GET', 'chats', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get chats: {e}")
            raise
    
    async def get_chat(self, chat_id: str) -> Dict[str, Any]:
        """Get specific chat details"""
        try:
            response = await self.client._make_request('GET', f'chats/{chat_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to get chat {chat_id}: {e}")
            raise
    
    async def get_all_messages(
        self, 
        chat_id: Optional[str] = None,
        account_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
        since: Optional[str] = None,
        sender_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all messages with pagination
        
        Args:
            chat_id: Optional chat ID to get messages for specific chat
            account_id: Optional account ID to filter by specific account
            cursor: Pagination cursor from previous request
            limit: Number of messages to return (default 50)
            since: Optional timestamp to get messages since
            sender_id: Optional sender ID for message filtering (UniPile format)
        """
        try:
            params = {'limit': limit}
            
            # Use correct endpoint based on whether chat_id is provided
            if chat_id:
                # For specific chat: use /api/v1/chats/{chat_id}/messages
                endpoint = f'chats/{chat_id}/messages'
                # Don't include chat_id in params when it's in the URL path
                if account_id:
                    params['account_id'] = account_id
            else:
                # For all messages across chats: use /api/v1/messages
                endpoint = 'messages'
                if account_id:
                    params['account_id'] = account_id
                    
            if cursor:
                params['cursor'] = cursor
            if since:
                params['since'] = since
            if sender_id:
                params['sender_id'] = sender_id
                
            response = await self.client._make_request('GET', endpoint, params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            raise
    
    async def send_message(
        self, 
        chat_id: str, 
        text: str,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Send message to existing chat"""
        try:
            data = {
                'chat_id': chat_id,
                'text': text
            }
            if attachments:
                data['attachments'] = attachments
                
            response = await self.client._make_request('POST', f'chats/{chat_id}/messages', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    async def start_new_chat(
        self, 
        account_id: str, 
        attendees_ids: List[str], 
        text: str,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Start new chat with message"""
        try:
            data = {
                'account_id': account_id,
                'attendees_ids': attendees_ids,
                'text': text
            }
            if attachments:
                data['attachments'] = attachments
                
            response = await self.client._make_request('POST', 'chats/start', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to start new chat: {e}")
            raise
    
    async def get_all_attendees(
        self, 
        account_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get all chat attendees"""
        try:
            params = {'limit': limit}
            if account_id:
                params['account_id'] = account_id
            if cursor:
                params['cursor'] = cursor
                
            # Correct endpoint per Unipile API docs: GET /api/v1/chat_attendees
            response = await self.client._make_request('GET', 'chat_attendees', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to get attendees: {e}")
            raise