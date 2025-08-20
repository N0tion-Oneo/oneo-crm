"""
Base webhook handler interface for provider-specific implementations
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseWebhookHandler(ABC):
    """
    Abstract base class for provider-specific webhook handlers
    Ensures clean separation of concerns between different providers
    """
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = logging.getLogger(f'{__name__}.{provider_name}')
    
    @abstractmethod
    def get_supported_events(self) -> list[str]:
        """Return list of event types this handler supports"""
        pass
    
    @abstractmethod
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract account ID from webhook data"""
        pass
    
    @abstractmethod
    def handle_message_received(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming message webhook"""
        pass
    
    @abstractmethod
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound message confirmation webhook"""
        pass
    
    def handle_message_delivered(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message delivery confirmation - default implementation"""
        return {'success': True, 'note': 'Delivery tracking not implemented for this provider'}
    
    def handle_message_read(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message read receipt - default implementation"""
        return {'success': True, 'note': 'Read tracking not implemented for this provider'}
    
    def handle_account_connected(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account connection success - default implementation"""
        return {'success': True, 'note': 'Account connection handled by base handler'}
    
    def handle_account_disconnected(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account disconnection - default implementation"""
        return {'success': True, 'note': 'Account disconnection handled by base handler'}
    
    def handle_account_error(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account error - default implementation"""
        return {'success': True, 'note': 'Account error handled by base handler'}
    
    def process_event(self, event_type: str, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a webhook event using the appropriate handler method
        
        Args:
            event_type: Type of webhook event
            account_id: UniPile account ID
            data: Event data
            
        Returns:
            Processing result
        """
        # Map event types to handler methods
        handler_map = {
            'message.received': self.handle_message_received,
            'message_received': self.handle_message_received,
            'mail_received': self.handle_message_received,
            
            'message.sent': self.handle_message_sent,
            'message_sent': self.handle_message_sent,
            'mail_sent': self.handle_message_sent,
            
            'message_delivered': self.handle_message_delivered,
            'message.delivered': self.handle_message_delivered,
            
            'message_read': self.handle_message_read,
            'message.read': self.handle_message_read,
            
            'account.connected': self.handle_account_connected,
            'account_connected': self.handle_account_connected,
            
            'account.disconnected': self.handle_account_disconnected,
            'account_disconnected': self.handle_account_disconnected,
            
            'account.error': self.handle_account_error,
            'account_error': self.handle_account_error,
        }
        
        handler = handler_map.get(event_type)
        if not handler:
            self.logger.warning(f"No handler for event type: {event_type}")
            return {'success': False, 'error': f'Unsupported event type: {event_type}'}
        
        try:
            self.logger.info(f"Processing {event_type} for account {account_id}")
            result = handler(account_id, data)
            result['provider'] = self.provider_name
            result['event_type'] = event_type
            return result
        except Exception as e:
            self.logger.error(f"Error processing {event_type} for account {account_id}: {e}")
            return {
                'success': False, 
                'error': str(e),
                'provider': self.provider_name,
                'event_type': event_type
            }
    
    def validate_webhook_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate webhook data structure - can be overridden by providers
        
        Args:
            data: Webhook data to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, dict):
            self.logger.error(f"Invalid webhook data type: {type(data)}")
            return False
        
        account_id = self.extract_account_id(data)
        if not account_id:
            self.logger.error("No account ID found in webhook data")
            return False
        
        return True