"""
Base webhook handler for all channels
All channel-specific webhook handlers should inherit from this
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseWebhookHandler(ABC):
    """Abstract base class for webhook handlers"""
    
    def __init__(self, channel_type: str):
        """
        Initialize the webhook handler
        
        Args:
            channel_type: Type of channel (e.g., 'whatsapp', 'email', 'linkedin')
        """
        self.channel_type = channel_type
    
    @abstractmethod
    def get_supported_events(self) -> List[str]:
        """
        Get list of supported webhook event types
        
        Returns:
            List of event type strings
        """
        pass
    
    @abstractmethod
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract account ID from webhook data
        
        Args:
            data: Raw webhook payload
            
        Returns:
            Account ID or None if not found
        """
        pass
    
    def process_webhook(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main webhook processing entry point
        
        Args:
            event_type: Type of webhook event
            data: Webhook payload data
            
        Returns:
            Processing result
        """
        try:
            # Extract account ID
            account_id = self.extract_account_id(data)
            if not account_id:
                logger.warning(f"No account ID found in webhook data for {self.channel_type}")
                return {'success': False, 'error': 'No account ID found'}
            
            # Log webhook reception
            logger.info(f"Processing {self.channel_type} webhook: {event_type} for account {account_id}")
            
            # Check if event is supported
            if event_type not in self.get_supported_events():
                logger.warning(f"Unsupported event type: {event_type} for {self.channel_type}")
                return {'success': False, 'error': f'Unsupported event type: {event_type}'}
            
            # Route to appropriate handler
            handler_method = self._get_handler_method(event_type)
            if handler_method:
                return handler_method(account_id, data)
            else:
                return self.handle_default(account_id, event_type, data)
                
        except Exception as e:
            logger.error(f"Error processing {self.channel_type} webhook: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _get_handler_method(self, event_type: str):
        """
        Get handler method for event type
        
        Args:
            event_type: Event type string
            
        Returns:
            Handler method or None
        """
        # Convert event type to method name (e.g., 'message.received' -> 'handle_message_received')
        method_name = f"handle_{event_type.replace('.', '_').replace('-', '_')}"
        return getattr(self, method_name, None)
    
    def handle_default(self, account_id: str, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Default handler for unhandled events
        
        Args:
            account_id: Account ID
            event_type: Event type
            data: Webhook data
            
        Returns:
            Processing result
        """
        logger.info(f"Default handler for {self.channel_type} event {event_type}")
        return {'success': True, 'message': f'Event {event_type} received but not processed'}
    
    def validate_webhook_signature(self, headers: Dict[str, str], body: bytes) -> bool:
        """
        Validate webhook signature (if applicable)
        
        Args:
            headers: Request headers
            body: Raw request body
            
        Returns:
            True if valid or validation not required
        """
        # Default implementation - can be overridden by channels that require signature validation
        return True
    
    def normalize_timestamp(self, timestamp: Any) -> Optional[str]:
        """
        Normalize timestamp to ISO format
        
        Args:
            timestamp: Timestamp in various formats
            
        Returns:
            ISO formatted timestamp string
        """
        if not timestamp:
            return None
            
        try:
            # Handle different timestamp formats
            if isinstance(timestamp, str):
                # Already a string, assume it's formatted
                return timestamp
            elif isinstance(timestamp, (int, float)):
                # Unix timestamp
                from datetime import datetime
                dt = datetime.fromtimestamp(timestamp)
                return dt.isoformat()
            else:
                return str(timestamp)
        except Exception as e:
            logger.warning(f"Failed to normalize timestamp {timestamp}: {e}")
            return None
    
    def extract_sender_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract sender information from webhook data
        
        Args:
            data: Webhook data
            
        Returns:
            Dict with sender information
        """
        # Default implementation - should be overridden by specific channels
        return {
            'id': None,
            'name': 'Unknown',
            'email': None,
            'phone': None,
            'is_self': False
        }
    
    def get_user_connection(self, account_id: str):
        """
        Get user connection for the account
        
        Args:
            account_id: Provider account ID
            
        Returns:
            UserChannelConnection instance or None
        """
        from communications.models import UserChannelConnection
        
        try:
            return UserChannelConnection.objects.get(
                unipile_account_id=account_id,
                channel_type=self.channel_type,
                is_active=True
            )
        except UserChannelConnection.DoesNotExist:
            logger.warning(f"No active connection found for {self.channel_type} account {account_id}")
            return None
        except UserChannelConnection.MultipleObjectsReturned:
            logger.warning(f"Multiple connections found for {self.channel_type} account {account_id}")
            # Return the most recent one
            return UserChannelConnection.objects.filter(
                unipile_account_id=account_id,
                channel_type=self.channel_type,
                is_active=True
            ).order_by('-created_at').first()