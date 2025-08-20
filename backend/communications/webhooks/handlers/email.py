"""
Email-specific webhook handler (Gmail, Outlook, etc.)
"""
import logging
from typing import Dict, Any, Optional
from .base import BaseWebhookHandler

logger = logging.getLogger(__name__)


class EmailWebhookHandler(BaseWebhookHandler):
    """Specialized handler for email webhook events (Gmail, Outlook) via UniPile"""
    
    def __init__(self):
        super().__init__('email')
    
    def get_supported_events(self) -> list[str]:
        """Email supported event types"""
        return [
            'mail_received',
            'mail_sent',
            'message.received',  # Email can use generic message events
            'message.sent',
            'message_delivered',
            'message_read',
            'account.connected',
            'account.disconnected', 
            'account.error'
        ]
    
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract email account ID from webhook data"""
        # Try different possible locations for account ID
        possible_keys = ['account_id', 'accountId', 'account', 'from_account_id']
        
        for key in possible_keys:
            if key in data:
                return str(data[key])
        
        # Check nested structures for email-specific formats
        if 'account' in data and isinstance(data['account'], dict):
            return str(data['account'].get('id'))
        
        if 'email' in data and isinstance(data['email'], dict):
            return str(data['email'].get('account_id'))
        
        if 'message' in data and isinstance(data['message'], dict):
            return str(data['message'].get('account_id'))
        
        return None
    
    def handle_message_received(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming email message"""
        try:
            from communications.webhooks.routing import account_router
            
            # Get user connection
            connection = account_router.get_user_connection(account_id)
            if not connection:
                return {'success': False, 'error': 'User connection not found'}
            
            # Validate it's an email connection
            if connection.channel_type not in ['gmail', 'outlook', 'mail', 'email']:
                return {'success': False, 'error': f'Invalid channel type for email: {connection.channel_type}'}
            
            # Use specialized email handler
            from communications.webhooks.email_handler import email_webhook_handler
            result = email_webhook_handler.handle_email_received(account_id, data)
            
            self.logger.info(f"Email message processed: {result.get('message_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Email message handling failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound email confirmation"""
        try:
            from communications.webhooks.email_handler import email_webhook_handler
            result = email_webhook_handler.handle_email_sent(account_id, data)
            
            self.logger.info(f"Email sent confirmation processed")
            return result
            
        except Exception as e:
            self.logger.error(f"Email sent confirmation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_delivered(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email delivery confirmation"""
        try:
            from communications.webhooks.email_handler import email_webhook_handler
            result = email_webhook_handler.handle_email_delivered(account_id, data)
            
            # Trigger delivery tracking for analytics
            self._trigger_delivery_tracking(data)
            
            self.logger.info(f"Email delivery confirmation processed")
            return result
            
        except Exception as e:
            self.logger.error(f"Email delivery confirmation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_read(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email read receipt"""
        try:
            from communications.webhooks.email_handler import email_webhook_handler
            result = email_webhook_handler.handle_email_read(account_id, data)
            
            # Trigger read tracking for analytics
            self._trigger_read_tracking(data)
            
            self.logger.info(f"Email read receipt processed")
            return result
            
        except Exception as e:
            self.logger.error(f"Email read receipt failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _trigger_delivery_tracking(self, webhook_data: Dict[str, Any]):
        """Trigger email delivery tracking analytics"""
        try:
            from communications.signals.tracking import handle_unipile_delivery_webhook
            
            message_id = webhook_data.get('message_id') or webhook_data.get('id')
            if message_id:
                handle_unipile_delivery_webhook(message_id, {
                    'event_type': 'message_delivered',
                    'provider': 'email',
                    'timestamp': webhook_data.get('timestamp'),
                    'webhook_data': webhook_data
                })
        except Exception as e:
            self.logger.warning(f"Failed to trigger email delivery tracking: {e}")
    
    def _trigger_read_tracking(self, webhook_data: Dict[str, Any]):
        """Trigger email read tracking analytics"""
        try:
            from communications.signals.tracking import handle_tracking_pixel_request
            
            message_id = webhook_data.get('message_id') or webhook_data.get('id')
            if message_id:
                handle_tracking_pixel_request({
                    'message_id': message_id,
                    'event_type': 'email_read',
                    'provider': 'email',
                    'user_agent': webhook_data.get('user_agent', ''),
                    'ip_address': webhook_data.get('ip', ''),
                    'timestamp': webhook_data.get('timestamp')
                })
        except Exception as e:
            self.logger.warning(f"Failed to trigger email read tracking: {e}")
    
    def validate_webhook_data(self, data: Dict[str, Any]) -> bool:
        """Validate email-specific webhook data"""
        if not super().validate_webhook_data(data):
            return False
        
        # Email-specific validations
        email_indicators = ['subject', 'body', 'from', 'to', 'sender', 'recipient']
        if any(key in data for key in email_indicators):
            return True
        
        # Check for nested email data
        if 'message' in data and isinstance(data['message'], dict):
            message_data = data['message']
            if any(key in message_data for key in email_indicators):
                return True
        
        # Account-level events don't need email-specific data
        event_type = data.get('event_type', data.get('event', ''))
        if 'account' in event_type:
            return True
        
        self.logger.error("Email webhook missing required email data")
        return False