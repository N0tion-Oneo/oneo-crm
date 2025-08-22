"""
UniPile Messaging Client
Handles chat and message operations
"""
import logging
from datetime import datetime
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
            # If we have attachments, use multipart/form-data
            if attachments:
                files = {}
                data = {
                    'chat_id': chat_id,
                    'text': text
                }
                
                # Prepare files for multipart upload
                for attachment in attachments:
                    if 'file_path' in attachment:
                        files['attachments'] = (
                            attachment['name'],
                            open(attachment['file_path'], 'rb'),
                            attachment['content_type']
                        )
                        # UniPile API docs show only one attachment per request
                        # For multiple files, we'd need multiple requests
                        break
                
                # Send with files
                response = await self.client._make_request(
                    'POST', 
                    f'chats/{chat_id}/messages', 
                    data=data, 
                    files=files
                )
                
                # Close file handles
                for file_tuple in files.values():
                    if hasattr(file_tuple[1], 'close'):
                        file_tuple[1].close()
                        
                return response
            else:
                # Regular text message
                data = {
                    'chat_id': chat_id,
                    'text': text
                }
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
            # If we have attachments, use multipart/form-data
            if attachments:
                files = {}
                data = {
                    'account_id': account_id,
                    'attendees_ids': ','.join(attendees_ids),  # Convert list to comma-separated string
                    'text': text
                }
                
                # Prepare files for multipart upload
                for attachment in attachments:
                    if 'file_path' in attachment:
                        files['attachments'] = (
                            attachment['name'],
                            open(attachment['file_path'], 'rb'),
                            attachment['content_type']
                        )
                        # UniPile API docs show only one attachment per request
                        break
                
                # Send with files
                response = await self.client._make_request(
                    'POST', 
                    'chats/start', 
                    data=data, 
                    files=files
                )
                
                # Close file handles
                for file_tuple in files.values():
                    if hasattr(file_tuple[1], 'close'):
                        file_tuple[1].close()
                        
                return response
            else:
                # Regular text message
                data = {
                    'account_id': account_id,
                    'attendees_ids': attendees_ids,
                    'text': text
                }
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
    
    # =========================================================================
    # ENHANCED PAGINATION METHODS FOR BACKGROUND SYNC
    # =========================================================================
    
    async def paginate_all_chats(
        self, 
        account_id: Optional[str] = None,
        account_type: Optional[str] = None,
        batch_size: int = 50,
        max_items: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Paginate through all chats with automatic cursor management
        Returns all chats in a single list for processing
        
        Args:
            account_id: Account to filter by
            account_type: Type of account (WHATSAPP, etc.)
            batch_size: Items per API request
            max_items: Maximum total items to return (None = unlimited)
        """
        all_chats = []
        cursor = None
        items_fetched = 0
        
        while True:
            response = await self.get_all_chats(
                account_id=account_id,
                cursor=cursor,
                limit=batch_size,
                account_type=account_type
            )
            
            items = response.get('items', [])
            if not items:
                break
                
            all_chats.extend(items)
            items_fetched += len(items)
            
            # Check if we've hit our max limit
            if max_items and items_fetched >= max_items:
                all_chats = all_chats[:max_items]
                break
            
            # Check for more pages
            cursor = response.get('next_cursor') or response.get('cursor')
            has_more = response.get('has_more', False)
            
            if not has_more or not cursor:
                break
                
        logger.info(f"Paginated {len(all_chats)} chats across multiple requests")
        return all_chats
    
    async def paginate_all_messages(
        self,
        chat_id: Optional[str] = None,
        account_id: Optional[str] = None,
        batch_size: int = 100,
        max_items: Optional[int] = None,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Paginate through all messages with automatic cursor management
        Returns all messages in a single list for processing
        
        Args:
            chat_id: Specific chat to get messages from
            account_id: Account to filter by 
            batch_size: Items per API request
            max_items: Maximum total items to return (None = unlimited)
            since: Get messages since this timestamp
        """
        all_messages = []
        cursor = None
        items_fetched = 0
        
        while True:
            response = await self.get_all_messages(
                chat_id=chat_id,
                account_id=account_id,
                cursor=cursor,
                limit=batch_size,
                since=since
            )
            
            items = response.get('items', [])
            if not items:
                break
                
            all_messages.extend(items)
            items_fetched += len(items)
            
            # Check if we've hit our max limit
            if max_items and items_fetched >= max_items:
                all_messages = all_messages[:max_items]
                break
            
            # Check for more pages
            cursor = response.get('next_cursor') or response.get('cursor')
            has_more = response.get('has_more', False)
            
            if not has_more or not cursor:
                break
                
        logger.info(f"Paginated {len(all_messages)} messages across multiple requests")
        return all_messages
    
    async def get_chats_batch(
        self,
        account_id: Optional[str] = None,
        account_type: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get a single batch of chats with enhanced pagination metadata
        Optimized for background sync task processing
        
        Returns:
            {
                'items': [...],
                'next_cursor': 'cursor_string',
                'has_more': True/False,
                'total_fetched': 50,
                'batch_info': {...}
            }
        """
        start_time = datetime.now()
        
        response = await self.get_all_chats(
            account_id=account_id,
            cursor=cursor,
            limit=limit,
            account_type=account_type
        )
        
        # Enhance response with batch metadata for sync tracking
        response.setdefault('batch_info', {})
        response['batch_info'].update({
            'request_time_ms': int((datetime.now() - start_time).total_seconds() * 1000),
            'batch_size': limit,
            'items_returned': len(response.get('items', [])),
            'cursor_used': cursor
        })
        
        return response
    
    async def get_messages_batch(
        self,
        chat_id: Optional[str] = None,
        account_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a single batch of messages with enhanced pagination metadata
        Optimized for background sync task processing
        """
        from datetime import datetime
        
        start_time = datetime.now()
        
        response = await self.get_all_messages(
            chat_id=chat_id,
            account_id=account_id,
            cursor=cursor,
            limit=limit,
            since=since
        )
        
        # Enhance response with batch metadata for sync tracking
        response.setdefault('batch_info', {})
        response['batch_info'].update({
            'request_time_ms': int((datetime.now() - start_time).total_seconds() * 1000),
            'batch_size': limit,
            'items_returned': len(response.get('items', [])),
            'cursor_used': cursor,
            'chat_id': chat_id
        })
        
        return response