"""
Base client for channel API interactions
All channel-specific clients should inherit from this
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseChannelClient(ABC):
    """Abstract base class for channel API clients"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the channel client
        
        Args:
            api_key: API key for the channel provider
        """
        self.api_key = api_key
        self.channel_type = self.get_channel_type()
    
    @abstractmethod
    def get_channel_type(self) -> str:
        """Return the channel type (e.g., 'whatsapp', 'email', 'linkedin')"""
        pass
    
    @abstractmethod
    async def get_conversations(
        self, 
        account_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get conversations/chats for an account
        
        Args:
            account_id: Provider account ID
            limit: Number of conversations to retrieve
            cursor: Pagination cursor
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict with conversations data and pagination info
        """
        pass
    
    @abstractmethod
    async def get_messages(
        self,
        account_id: str,
        conversation_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get messages for a conversation
        
        Args:
            account_id: Provider account ID
            conversation_id: Conversation/chat ID
            limit: Number of messages to retrieve
            cursor: Pagination cursor
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict with messages data and pagination info
        """
        pass
    
    @abstractmethod
    async def send_message(
        self,
        account_id: str,
        conversation_id: str,
        content: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message
        
        Args:
            account_id: Provider account ID
            conversation_id: Conversation/chat ID
            content: Message content
            attachments: Optional list of attachments
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict with sent message details
        """
        pass
    
    @abstractmethod
    async def mark_as_read(
        self,
        account_id: str,
        conversation_id: str,
        message_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Mark a message as read
        
        Args:
            account_id: Provider account ID
            conversation_id: Conversation/chat ID
            message_id: Message ID to mark as read
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict with operation result
        """
        pass
    
    async def get_account_info(self, account_id: str) -> Dict[str, Any]:
        """
        Get account information
        
        Args:
            account_id: Provider account ID
            
        Returns:
            Dict with account details
        """
        # Default implementation - can be overridden
        logger.info(f"Getting account info for {account_id}")
        return {'account_id': account_id, 'channel_type': self.channel_type}
    
    async def sync_history(
        self,
        account_id: str,
        conversation_id: Optional[str] = None,
        days_back: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync historical data
        
        Args:
            account_id: Provider account ID
            conversation_id: Optional specific conversation to sync
            days_back: Number of days to sync back
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict with sync operation details
        """
        # Default implementation - can be overridden
        logger.info(f"Syncing history for {account_id}, days_back={days_back}")
        return {'success': True, 'days_back': days_back}