"""
Base service for channel business logic
All channel-specific services should inherit from this
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseChannelService(ABC):
    """Abstract base class for channel services"""
    
    def __init__(self):
        """Initialize the channel service"""
        self.channel_type = self.get_channel_type()
        self.client = self.get_client()
    
    @abstractmethod
    def get_channel_type(self) -> str:
        """Return the channel type (e.g., 'whatsapp', 'email', 'linkedin')"""
        pass
    
    @abstractmethod
    def get_client(self):
        """Return the channel-specific API client"""
        pass
    
    @abstractmethod
    async def process_webhook(
        self,
        event_type: str,
        data: Dict[str, Any],
        account_id: str
    ) -> Dict[str, Any]:
        """
        Process webhook events
        
        Args:
            event_type: Type of webhook event
            data: Webhook payload data
            account_id: Account ID from webhook
            
        Returns:
            Processing result
        """
        pass
    
    @abstractmethod
    async def sync_conversations(
        self,
        user: User,
        account_id: str,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Sync conversations for a user account
        
        Args:
            user: User instance
            account_id: Provider account ID
            force_sync: Force fresh sync ignoring cache
            
        Returns:
            Sync result with conversations
        """
        pass
    
    @abstractmethod
    async def sync_messages(
        self,
        user: User,
        account_id: str,
        conversation_id: str,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Sync messages for a conversation
        
        Args:
            user: User instance
            account_id: Provider account ID
            conversation_id: Conversation ID
            force_sync: Force fresh sync ignoring cache
            
        Returns:
            Sync result with messages
        """
        pass
    
    async def send_message(
        self,
        user: User,
        account_id: str,
        conversation_id: str,
        content: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send a message through the channel
        
        Args:
            user: User instance
            account_id: Provider account ID
            conversation_id: Conversation ID
            content: Message content
            attachments: Optional attachments
            
        Returns:
            Sent message details
        """
        # Common implementation that can be overridden
        try:
            # Validate user has access to this account
            if not await self.validate_user_access(user, account_id):
                return {'success': False, 'error': 'Access denied'}
            
            # Send through client
            result = await self.client.send_message(
                account_id=account_id,
                conversation_id=conversation_id,
                content=content,
                attachments=attachments
            )
            
            # Store locally if needed
            await self.store_sent_message(user, account_id, conversation_id, result)
            
            return {'success': True, 'message': result}
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {'success': False, 'error': str(e)}
    
    async def validate_user_access(self, user: User, account_id: str) -> bool:
        """
        Validate user has access to the account
        
        Args:
            user: User instance
            account_id: Provider account ID
            
        Returns:
            True if user has access
        """
        from communications.models import UserChannelConnection
        
        return UserChannelConnection.objects.filter(
            user=user,
            unipile_account_id=account_id,
            channel_type=self.channel_type,
            is_active=True
        ).exists()
    
    async def store_sent_message(
        self,
        user: User,
        account_id: str,
        conversation_id: str,
        message_data: Dict[str, Any]
    ) -> None:
        """
        Store sent message locally
        
        Args:
            user: User instance
            account_id: Provider account ID
            conversation_id: Conversation ID
            message_data: Message data from provider
        """
        # Default implementation - can be overridden
        logger.info(f"Storing sent message for conversation {conversation_id}")
        # Implementation would store in local database
        pass
    
    async def get_or_create_channel(self, account_id: str, user: User):
        """
        Get or create a channel instance
        
        Args:
            account_id: Provider account ID
            user: User instance
            
        Returns:
            Channel instance
        """
        from communications.models import Channel
        
        channel, created = await Channel.objects.aget_or_create(
            unipile_account_id=account_id,
            channel_type=self.channel_type,
            defaults={
                'name': f"{self.channel_type.title()} Channel",
                'created_by': user,
                'is_active': True,
                'auth_status': 'authenticated'
            }
        )
        
        if created:
            logger.info(f"Created new {self.channel_type} channel for account {account_id}")
        
        return channel