"""
Tracking-specific webhook handler - consolidates delivery and read tracking
"""
import logging
from typing import Dict, Any, Optional
from .base import BaseWebhookHandler

logger = logging.getLogger(__name__)


class TrackingWebhookHandler(BaseWebhookHandler):
    """
    Specialized handler for tracking webhook events
    Consolidates delivery tracking, read receipts, and analytics
    """
    
    def __init__(self):
        super().__init__('tracking')
    
    def get_supported_events(self) -> list[str]:
        """Tracking supported event types"""
        return [
            'delivery_status',
            'read_receipt',
            'tracking_pixel',
            'email_opened',
            'link_clicked',
            'attachment_downloaded',
            'bounce',
            'spam_report',
            'unsubscribe'
        ]
    
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract account ID from tracking webhook data"""
        # Tracking events may not always have account_id
        # They often have message_id instead
        possible_keys = ['account_id', 'accountId', 'account']
        
        for key in possible_keys:
            if key in data:
                return str(data[key])
        
        # For tracking events, we might need to look up account from message
        message_id = data.get('message_id')
        if message_id:
            try:
                from communications.models import Message
                message = Message.objects.filter(external_message_id=message_id).first()
                if message and message.channel:
                    return message.channel.unipile_account_id
            except Exception as e:
                self.logger.warning(f"Failed to lookup account from message {message_id}: {e}")
        
        return None
    
    def handle_message_received(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Tracking doesn't handle message received - delegate to provider handlers"""
        return {'success': False, 'error': 'Tracking handler does not process message_received events'}
    
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Tracking doesn't handle message sent - delegate to provider handlers"""
        return {'success': False, 'error': 'Tracking handler does not process message_sent events'}
    
    def handle_delivery_status(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delivery status tracking"""
        try:
            message_id = data.get('message_id')
            delivery_status = data.get('status', data.get('delivery_status'))
            
            if not message_id:
                return {'success': False, 'error': 'Missing message_id in delivery tracking'}
            
            # Trigger delivery tracking
            from communications.signals.tracking import handle_unipile_delivery_webhook
            
            tracking_data = {
                'event_type': 'delivery_status',
                'status': delivery_status,
                'timestamp': data.get('timestamp'),
                'provider': data.get('provider', 'unknown'),
                'delivery_details': data.get('details', {}),
                'webhook_data': data
            }
            
            handle_unipile_delivery_webhook(message_id, tracking_data)
            
            self.logger.info(f"Processed delivery status for message {message_id}: {delivery_status}")
            return {
                'success': True,
                'message_id': message_id,
                'delivery_status': delivery_status
            }
            
        except Exception as e:
            self.logger.error(f"Delivery status tracking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_read_receipt(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle read receipt tracking"""
        try:
            message_id = data.get('message_id')
            read_timestamp = data.get('timestamp', data.get('read_at'))
            
            if not message_id:
                return {'success': False, 'error': 'Missing message_id in read tracking'}
            
            # Trigger read tracking
            from communications.signals.tracking import handle_tracking_pixel_request
            
            tracking_data = {
                'message_id': message_id,
                'event_type': 'read_receipt',
                'timestamp': read_timestamp,
                'user_agent': data.get('user_agent', ''),
                'ip_address': data.get('ip_address', data.get('ip', '')),
                'location': data.get('location', {}),
                'device_info': data.get('device', {}),
                'provider': data.get('provider', 'unknown')
            }
            
            handle_tracking_pixel_request(tracking_data)
            
            self.logger.info(f"Processed read receipt for message {message_id}")
            return {
                'success': True,
                'message_id': message_id,
                'read_timestamp': read_timestamp
            }
            
        except Exception as e:
            self.logger.error(f"Read receipt tracking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_tracking_pixel(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tracking pixel events (email opens)"""
        try:
            # Tracking pixel indicates email was opened
            result = self.handle_read_receipt(account_id, {
                **data,
                'event_type': 'tracking_pixel'
            })
            
            # Also trigger email-specific tracking
            if result.get('success'):
                self._trigger_email_open_analytics(data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Tracking pixel handling failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_email_opened(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email opened event"""
        return self.handle_tracking_pixel(account_id, data)
    
    def handle_link_clicked(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle link click tracking"""
        try:
            message_id = data.get('message_id')
            link_url = data.get('url', data.get('link'))
            click_timestamp = data.get('timestamp')
            
            if not message_id or not link_url:
                return {'success': False, 'error': 'Missing message_id or link URL'}
            
            # Store link click analytics
            self._store_link_click_analytics(message_id, link_url, data)
            
            self.logger.info(f"Processed link click for message {message_id}: {link_url}")
            return {
                'success': True,
                'message_id': message_id,
                'link_url': link_url,
                'click_timestamp': click_timestamp
            }
            
        except Exception as e:
            self.logger.error(f"Link click tracking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_attachment_downloaded(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle attachment download tracking"""
        try:
            message_id = data.get('message_id')
            attachment_name = data.get('attachment_name', data.get('filename'))
            download_timestamp = data.get('timestamp')
            
            if not message_id:
                return {'success': False, 'error': 'Missing message_id'}
            
            # Store attachment download analytics
            self._store_attachment_download_analytics(message_id, attachment_name, data)
            
            self.logger.info(f"Processed attachment download for message {message_id}: {attachment_name}")
            return {
                'success': True,
                'message_id': message_id,
                'attachment_name': attachment_name,
                'download_timestamp': download_timestamp
            }
            
        except Exception as e:
            self.logger.error(f"Attachment download tracking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_bounce(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email bounce tracking"""
        try:
            message_id = data.get('message_id')
            bounce_type = data.get('bounce_type', 'hard')
            bounce_reason = data.get('reason', data.get('bounce_reason'))
            
            if not message_id:
                return {'success': False, 'error': 'Missing message_id in bounce tracking'}
            
            # Update message status and store bounce analytics
            self._handle_message_bounce(message_id, bounce_type, bounce_reason, data)
            
            self.logger.warning(f"Processed bounce for message {message_id}: {bounce_type} - {bounce_reason}")
            return {
                'success': True,
                'message_id': message_id,
                'bounce_type': bounce_type,
                'bounce_reason': bounce_reason
            }
            
        except Exception as e:
            self.logger.error(f"Bounce tracking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_spam_report(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle spam report tracking"""
        try:
            message_id = data.get('message_id')
            reporter_email = data.get('reporter_email')
            
            if not message_id:
                return {'success': False, 'error': 'Missing message_id in spam report'}
            
            # Store spam report for compliance and analytics
            self._store_spam_report(message_id, reporter_email, data)
            
            self.logger.warning(f"Processed spam report for message {message_id} from {reporter_email}")
            return {
                'success': True,
                'message_id': message_id,
                'reporter_email': reporter_email
            }
            
        except Exception as e:
            self.logger.error(f"Spam report tracking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_unsubscribe(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unsubscribe tracking"""
        try:
            message_id = data.get('message_id')
            unsubscribe_email = data.get('email')
            
            if not unsubscribe_email:
                return {'success': False, 'error': 'Missing email in unsubscribe tracking'}
            
            # Store unsubscribe for compliance
            self._handle_unsubscribe(message_id, unsubscribe_email, data)
            
            self.logger.info(f"Processed unsubscribe for email {unsubscribe_email}")
            return {
                'success': True,
                'message_id': message_id,
                'unsubscribe_email': unsubscribe_email
            }
            
        except Exception as e:
            self.logger.error(f"Unsubscribe tracking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_event(self, event_type: str, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process tracking-specific events"""
        # Custom handler mapping for tracking events
        tracking_handler_map = {
            'delivery_status': self.handle_delivery_status,
            'read_receipt': self.handle_read_receipt,
            'tracking_pixel': self.handle_tracking_pixel,
            'email_opened': self.handle_email_opened,
            'link_clicked': self.handle_link_clicked,
            'attachment_downloaded': self.handle_attachment_downloaded,
            'bounce': self.handle_bounce,
            'spam_report': self.handle_spam_report,
            'unsubscribe': self.handle_unsubscribe
        }
        
        handler = tracking_handler_map.get(event_type)
        if handler:
            return handler(account_id, data)
        
        # Fall back to base class for standard events
        return super().process_event(event_type, account_id, data)
    
    def _trigger_email_open_analytics(self, data: Dict[str, Any]):
        """Trigger email-specific open analytics"""
        try:
            # This could integrate with email marketing analytics
            pass
        except Exception as e:
            self.logger.warning(f"Failed to trigger email open analytics: {e}")
    
    def _store_link_click_analytics(self, message_id: str, link_url: str, data: Dict[str, Any]):
        """Store link click analytics data"""
        try:
            # This could store detailed click analytics
            pass
        except Exception as e:
            self.logger.warning(f"Failed to store link click analytics: {e}")
    
    def _store_attachment_download_analytics(self, message_id: str, attachment_name: str, data: Dict[str, Any]):
        """Store attachment download analytics"""
        try:
            # This could track attachment engagement
            pass
        except Exception as e:
            self.logger.warning(f"Failed to store attachment download analytics: {e}")
    
    def _handle_message_bounce(self, message_id: str, bounce_type: str, bounce_reason: str, data: Dict[str, Any]):
        """Handle message bounce and update status"""
        try:
            from communications.models import Message, MessageStatus
            
            message = Message.objects.filter(external_message_id=message_id).first()
            if message:
                message.status = MessageStatus.FAILED
                if not message.metadata:
                    message.metadata = {}
                message.metadata['bounce'] = {
                    'type': bounce_type,
                    'reason': bounce_reason,
                    'timestamp': data.get('timestamp')
                }
                message.save()
        except Exception as e:
            self.logger.warning(f"Failed to handle message bounce: {e}")
    
    def _store_spam_report(self, message_id: str, reporter_email: str, data: Dict[str, Any]):
        """Store spam report for compliance"""
        try:
            # This should integrate with compliance tracking
            pass
        except Exception as e:
            self.logger.warning(f"Failed to store spam report: {e}")
    
    def _handle_unsubscribe(self, message_id: str, email: str, data: Dict[str, Any]):
        """Handle unsubscribe request"""
        try:
            # This should integrate with email list management
            pass
        except Exception as e:
            self.logger.warning(f"Failed to handle unsubscribe: {e}")
    
    def validate_webhook_data(self, data: Dict[str, Any]) -> bool:
        """Validate tracking-specific webhook data"""
        if not isinstance(data, dict):
            return False
        
        # Tracking events must have either message_id or email
        if 'message_id' in data or 'email' in data:
            return True
        
        self.logger.error("Tracking webhook missing message_id or email")
        return False