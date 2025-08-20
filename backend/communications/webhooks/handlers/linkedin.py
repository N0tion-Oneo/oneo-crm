"""
LinkedIn-specific webhook handler
"""
import logging
from typing import Dict, Any, Optional
from .base import BaseWebhookHandler

logger = logging.getLogger(__name__)


class LinkedInWebhookHandler(BaseWebhookHandler):
    """Specialized handler for LinkedIn webhook events via UniPile"""
    
    def __init__(self):
        super().__init__('linkedin')
    
    def get_supported_events(self) -> list[str]:
        """LinkedIn supported event types"""
        return [
            'message.received',
            'message_received',
            'message.sent', 
            'message_sent',
            'message_delivered',
            'message_read',
            'connection_request',
            'connection_accepted',
            'account.connected',
            'account.disconnected',
            'account.error'
        ]
    
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract LinkedIn account ID from webhook data"""
        # Try different possible locations for account ID
        possible_keys = ['account_id', 'accountId', 'account', 'from_account_id']
        
        for key in possible_keys:
            if key in data:
                return str(data[key])
        
        # Check nested structures for LinkedIn-specific formats
        if 'account' in data and isinstance(data['account'], dict):
            return str(data['account'].get('id'))
        
        if 'linkedin' in data and isinstance(data['linkedin'], dict):
            return str(data['linkedin'].get('account_id'))
        
        if 'message' in data and isinstance(data['message'], dict):
            return str(data['message'].get('account_id'))
        
        return None
    
    def handle_message_received(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming LinkedIn message"""
        try:
            from communications.webhooks.routing import account_router
            
            # Get user connection
            connection = account_router.get_user_connection(account_id)
            if not connection:
                return {'success': False, 'error': 'User connection not found'}
            
            # Validate it's a LinkedIn connection
            if connection.channel_type != 'linkedin':
                return {'success': False, 'error': f'Invalid channel type: {connection.channel_type}'}
            
            # Use generic message handler with LinkedIn-specific processing
            from communications.webhooks.handlers import webhook_handler
            result = webhook_handler.handle_message_received(account_id, data)
            
            # Add LinkedIn-specific processing
            if result.get('success') and result.get('message_id'):
                self._process_linkedin_message_features(result['message_id'], data)
            
            self.logger.info(f"LinkedIn message processed: {result.get('message_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"LinkedIn message handling failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound LinkedIn message confirmation"""
        try:
            from communications.models import Message, MessageStatus
            from django.utils import timezone
            
            external_message_id = data.get('message_id') or data.get('id')
            
            if external_message_id:
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if message:
                    message.status = MessageStatus.SENT
                    message.sent_at = timezone.now()
                    message.save(update_fields=['status', 'sent_at'])
                    
                    self.logger.info(f"Updated LinkedIn message {message.id} status to sent")
                    return {'success': True, 'message_id': str(message.id)}
            
            self.logger.warning(f"No LinkedIn message record found for external ID {external_message_id}")
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            self.logger.error(f"LinkedIn sent confirmation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_delivered(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn message delivery confirmation"""
        try:
            from communications.models import Message, MessageStatus
            
            external_message_id = data.get('message_id') or data.get('id')
            
            if external_message_id:
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if message:
                    message.status = MessageStatus.DELIVERED
                    message.save(update_fields=['status'])
                    
                    # Trigger LinkedIn-specific delivery tracking
                    self._trigger_linkedin_delivery_tracking(message, data)
                    
                    self.logger.info(f"Updated LinkedIn message {message.id} status to delivered")
                    return {'success': True, 'message_id': str(message.id)}
            
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            self.logger.error(f"LinkedIn delivery confirmation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_read(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn message read receipt"""
        try:
            from communications.models import Message, MessageStatus, MessageDirection
            
            external_message_id = data.get('message_id') or data.get('id')
            
            if external_message_id:
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if message:
                    # Only update outbound messages to read status
                    if message.direction == MessageDirection.OUTBOUND:
                        message.status = MessageStatus.READ
                        message.save(update_fields=['status'])
                        
                        # Trigger LinkedIn-specific read tracking
                        self._trigger_linkedin_read_tracking(message, data)
                        
                        self.logger.info(f"Updated LinkedIn message {message.id} status to read")
                    else:
                        self.logger.info(f"Read receipt for inbound LinkedIn message {message.id}")
                    
                    return {'success': True, 'message_id': str(message.id)}
            
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            self.logger.error(f"LinkedIn read receipt failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_connection_request(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn connection request"""
        try:
            # Extract connection request data
            requester_profile = data.get('requester', {})
            message = data.get('message', '')
            
            self.logger.info(f"LinkedIn connection request from {requester_profile.get('name', 'Unknown')}")
            
            # Store connection request for later processing
            # This could trigger notifications or auto-acceptance workflows
            
            return {
                'success': True,
                'event_type': 'connection_request',
                'requester': requester_profile,
                'message': message
            }
            
        except Exception as e:
            self.logger.error(f"LinkedIn connection request handling failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_connection_accepted(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn connection acceptance"""
        try:
            # Extract connection data
            connection_profile = data.get('connection', {})
            
            self.logger.info(f"LinkedIn connection accepted with {connection_profile.get('name', 'Unknown')}")
            
            # This could trigger follow-up workflows or contact creation
            
            return {
                'success': True,
                'event_type': 'connection_accepted',
                'connection': connection_profile
            }
            
        except Exception as e:
            self.logger.error(f"LinkedIn connection acceptance handling failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_linkedin_message_features(self, message_id: str, webhook_data: Dict[str, Any]):
        """Process LinkedIn-specific message features"""
        try:
            from communications.models import Message
            
            message = Message.objects.get(id=message_id)
            
            # Add LinkedIn-specific metadata
            if not message.metadata:
                message.metadata = {}
            
            # Extract LinkedIn profile information
            sender_profile = webhook_data.get('sender', {})
            if sender_profile:
                message.metadata['linkedin_profile'] = {
                    'name': sender_profile.get('name'),
                    'headline': sender_profile.get('headline'),
                    'profile_url': sender_profile.get('profile_url'),
                    'company': sender_profile.get('company')
                }
            
            # Mark as LinkedIn message
            message.metadata['linkedin_specific'] = True
            message.save(update_fields=['metadata'])
            
        except Exception as e:
            self.logger.warning(f"Failed to process LinkedIn message features: {e}")
    
    def _trigger_linkedin_delivery_tracking(self, message, webhook_data: Dict[str, Any]):
        """Trigger LinkedIn-specific delivery tracking"""
        try:
            from communications.signals.tracking import handle_unipile_delivery_webhook
            
            handle_unipile_delivery_webhook(message.external_message_id, {
                'event_type': 'message_delivered',
                'provider': 'linkedin',
                'timestamp': webhook_data.get('timestamp'),
                'profile_data': webhook_data.get('recipient', {}),
                'webhook_data': webhook_data
            })
        except Exception as e:
            self.logger.warning(f"Failed to trigger LinkedIn delivery tracking: {e}")
    
    def _trigger_linkedin_read_tracking(self, message, webhook_data: Dict[str, Any]):
        """Trigger LinkedIn-specific read tracking"""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"conversation_{message.conversation.id}",
                    {
                        'type': 'message_read_update',
                        'message_id': str(message.id),
                        'external_message_id': message.external_message_id,
                        'status': 'read',
                        'read_at': webhook_data.get('timestamp'),
                        'provider': 'linkedin',
                        'profile_data': webhook_data.get('reader', {})
                    }
                )
        except Exception as e:
            self.logger.warning(f"Failed to send LinkedIn read update: {e}")
    
    def validate_webhook_data(self, data: Dict[str, Any]) -> bool:
        """Validate LinkedIn-specific webhook data"""
        if not super().validate_webhook_data(data):
            return False
        
        # LinkedIn-specific validations
        linkedin_indicators = ['profile', 'connection', 'linkedin_id', 'profile_url']
        if any(key in data for key in linkedin_indicators):
            return True
        
        # Check for nested LinkedIn data
        if 'sender' in data and isinstance(data['sender'], dict):
            sender_data = data['sender']
            if any(key in sender_data for key in linkedin_indicators):
                return True
        
        # Account-level events don't need LinkedIn-specific data
        event_type = data.get('event_type', data.get('event', ''))
        if 'account' in event_type or 'connection' in event_type:
            return True
        
        self.logger.error("LinkedIn webhook missing required profile data")
        return False