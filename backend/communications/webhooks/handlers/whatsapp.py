"""
WhatsApp-specific webhook handler
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from django.utils import timezone as django_timezone
from .base import BaseWebhookHandler

logger = logging.getLogger(__name__)


class WhatsAppWebhookHandler(BaseWebhookHandler):
    """Specialized handler for WhatsApp webhook events via UniPile"""
    
    def __init__(self):
        super().__init__('whatsapp')
    
    def get_supported_events(self) -> list[str]:
        """WhatsApp supported event types"""
        return [
            'message.received',
            'message_received', 
            'message.sent',
            'message_sent',
            'message_delivered',
            'message_read',
            'account.connected',
            'account.disconnected',
            'account.error'
        ]
    
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract WhatsApp account ID from webhook data"""
        # Try different possible locations for account ID
        possible_keys = ['account_id', 'accountId', 'account', 'from_account_id']
        
        for key in possible_keys:
            if key in data:
                return str(data[key])
        
        # Check nested structures
        if 'account' in data and isinstance(data['account'], dict):
            return str(data['account'].get('id'))
        
        if 'message' in data and isinstance(data['message'], dict):
            return str(data['message'].get('account_id'))
        
        return None
    
    def handle_message_received(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming WhatsApp message using sync-only approach to preserve tenant context"""
        try:
            from communications.webhooks.routing import account_router
            from communications.models import Channel, Conversation, Message, ChatAttendee, MessageDirection, MessageStatus
            from communications.services.unified_processor import unified_processor
            from communications.services.conversation_naming import conversation_naming_service
            from communications.services.direction_detection import direction_detection_service
            from django.db import transaction
            
            # Get user connection (we're already in tenant context)
            connection = account_router.get_user_connection(account_id)
            if not connection:
                return {'success': False, 'error': 'User connection not found'}
            
            # Validate it's a WhatsApp connection
            if connection.channel_type != 'whatsapp':
                return {'success': False, 'error': f'Invalid channel type: {connection.channel_type}'}
            
            # Normalize webhook data using unified processor (sync method)
            normalized_message = unified_processor.normalize_message_data(data, 'webhook')
            normalized_conversation = unified_processor.normalize_conversation_data(data, 'webhook')
            
            chat_id = normalized_message.get('chat_id')
            message_id = normalized_message.get('external_message_id')
            
            if not chat_id:
                return {'success': False, 'error': 'Chat ID not found in webhook data'}
            
            # Debug: Check current schema context
            from django.db import connection as db_connection
            logger.info(f"🔍 Current schema during webhook processing: {db_connection.schema_name}")
            
            # Debug: Test if we can actually query the tables
            try:
                conversation_count = Conversation.objects.count()
                message_count = Message.objects.count()
                logger.info(f"🔍 Can query tables: {conversation_count} conversations, {message_count} messages")
            except Exception as query_error:
                logger.error(f"🔍 Cannot query tables: {query_error}")
                return {'success': False, 'error': f'Table query failed: {query_error}'}
            
            # Ensure we maintain schema context - avoid atomic transaction that may reset schema
            # Get or create channel
            channel, _ = Channel.objects.get_or_create(
                unipile_account_id=account_id,
                channel_type='whatsapp',
                defaults={
                    'name': f"WhatsApp Account {connection.account_name or account_id}",
                    'auth_status': 'authenticated',
                    'is_active': True,
                    'created_by': connection.user
                }
            )
            
            # Get or create conversation
            conversation = Conversation.objects.filter(
                channel=channel,
                external_thread_id=chat_id
            ).first()
            
            if not conversation:
                # Use sync conversation creation without async calls
                conversation_name = normalized_conversation.get('name') or f"WhatsApp Chat {chat_id[:8]}"
                
                # Try to extract better name from message sender
                sender_info = normalized_message.get('sender_info', {})
                if sender_info.get('name') and not sender_info.get('is_self', False):
                    conversation_name = sender_info['name']
                
                conversation = Conversation.objects.create(
                    channel=channel,
                    external_thread_id=chat_id,
                    subject=conversation_name,
                    status='active',
                    sync_status='completed',
                    last_message_at=django_timezone.now(),
                    metadata={
                        'conversation_name': conversation_name,
                        'conversation_type': 'whatsapp',
                        'created_by_user': str(channel.created_by.id if channel.created_by else 'unknown'),
                        'chat_id': chat_id,
                        'webhook_created': True
                    }
                )
                logger.info(f"✅ Created conversation '{conversation.subject}' for chat {chat_id}")
            
            # Check if message already exists
            existing_message = None
            if message_id:
                existing_message = Message.objects.filter(
                    external_message_id=message_id,
                    channel=channel
                ).first()
            
            if existing_message:
                logger.info(f"✅ Message {message_id} already exists, status updated if needed")
                return {
                    'success': True,
                    'message_id': str(existing_message.id),
                    'conversation_id': str(conversation.id),
                    'conversation_name': conversation.subject,
                    'note': 'Message already exists',
                    'approach': 'sync_webhook_processor'
                }
            
            # Determine message direction using sync method
            sender_id = normalized_message.get('sender_id')
            is_self = normalized_message.get('sender_info', {}).get('is_self', False)
            
            # Simple direction detection based on sender info
            if is_self:
                direction = MessageDirection.OUTBOUND
                status = MessageStatus.SENT
            else:
                direction = MessageDirection.INBOUND
                status = MessageStatus.DELIVERED
            
            # Create message with sync operations only
            message = Message.objects.create(
                channel=channel,
                conversation=conversation,
                external_message_id=message_id,
                content=normalized_message.get('content', ''),
                direction=direction,
                status=status,
                created_at=normalized_message.get('created_at', django_timezone.now()),
                sent_at=normalized_message.get('sent_at'),
                received_at=normalized_message.get('received_at', django_timezone.now()),
                metadata={
                    'webhook_data': data,
                    'normalized_data': normalized_message,
                    'sender_id': sender_id,
                    'chat_id': chat_id,
                    'provider': 'whatsapp',
                    'sync_created': True
                }
            )
            
            # Update conversation's last message timestamp
            conversation.last_message_at = message.created_at
            conversation.save(update_fields=['last_message_at'])
            
            logger.info(f"✅ Created WhatsApp message {message.id} in conversation '{conversation.subject}'")
            
            # Skip real-time WebSocket updates to avoid async_to_sync issues
            # Real-time updates can be handled by Django signals if needed
            
            return {
                'success': True,
                'message_id': str(message.id),
                'conversation_id': str(conversation.id),
                'conversation_name': conversation.subject,
                'approach': 'sync_webhook_processor',
                'attachment_count': len(normalized_message.get('attachments', [])),
                'content_type': 'attachment_only' if not normalized_message.get('content') and normalized_message.get('attachments') else 'text_with_attachments' if normalized_message.get('content') and normalized_message.get('attachments') else 'text_only'
            }
            
        except Exception as e:
            logger.error(f"WhatsApp message handling failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound WhatsApp message confirmation with sync-only approach"""
        try:
            from communications.models import Message, MessageStatus, Conversation, Channel
            from django.db import transaction
            
            external_message_id = data.get('message_id') or data.get('id')
            chat_id = data.get('chat_id') or data.get('conversation_id')
            
            # First try to find existing message by external ID
            message = None
            if external_message_id:
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
            
            # If message found, update status
            if message:
                message.status = MessageStatus.SENT
                message.sent_at = timezone.now()
                message.save(update_fields=['status', 'sent_at'])
                
                logger.info(f"✅ Updated WhatsApp message {message.id} status to sent")
                
                # Skip real-time WebSocket updates to avoid async_to_sync issues
                # Real-time updates can be handled by Django signals if needed
                
                return {
                    'success': True,
                    'message_id': str(message.id),
                    'conversation_id': str(message.conversation.id),
                    'approach': 'sync_webhook_processor'
                }
            
            # If no existing message found but we have chat context, ensure conversation exists
            elif chat_id:
                # Get channel for this account
                channel = Channel.objects.filter(
                    unipile_account_id=account_id,
                    channel_type='whatsapp'
                ).first()
                
                if channel:
                    # Get or create conversation with simplified approach
                    conversation, created = Conversation.objects.get_or_create(
                        channel=channel,
                        external_thread_id=chat_id,
                        defaults={
                            'subject': f"WhatsApp Chat {chat_id[:8]}",
                            'status': 'active',
                            'sync_status': 'pending',
                            'last_message_at': timezone.now(),
                            'metadata': {
                                'conversation_name': f"WhatsApp Chat {chat_id[:8]}",
                                'conversation_type': 'whatsapp',
                                'created_by_user': str(channel.created_by.id if channel.created_by else 'unknown'),
                                'chat_id': chat_id,
                                'webhook_created': True
                            }
                        }
                    )
                    
                    if created:
                        logger.info(f"✅ Created conversation for outbound message webhook: {conversation.subject}")
                    
                    return {
                        'success': True,
                        'conversation_id': str(conversation.id),
                        'conversation_name': conversation.subject,
                        'note': 'Outbound message webhook handled with sync processing',
                        'approach': 'sync_webhook_processor'
                    }
            
            logger.warning(f"No WhatsApp message record found for external ID {external_message_id}")
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            logger.error(f"WhatsApp sent confirmation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_delivered(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WhatsApp message delivery confirmation"""
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
                    
                    # Trigger tracking webhook for delivery analytics
                    self._trigger_delivery_tracking(message, data)
                    
                    self.logger.info(f"Updated WhatsApp message {message.id} status to delivered")
                    return {'success': True, 'message_id': str(message.id)}
            
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            self.logger.error(f"WhatsApp delivery confirmation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_read(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WhatsApp message read receipt"""
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
                        
                        # Trigger real-time update
                        self._trigger_read_tracking(message, data)
                        
                        self.logger.info(f"Updated WhatsApp message {message.id} status to read")
                    else:
                        self.logger.info(f"Read receipt for inbound WhatsApp message {message.id}")
                    
                    return {'success': True, 'message_id': str(message.id)}
            
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            self.logger.error(f"WhatsApp read receipt failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _trigger_delivery_tracking(self, message, webhook_data: Dict[str, Any]):
        """Trigger delivery tracking analytics"""
        try:
            from communications.signals.tracking import handle_unipile_delivery_webhook
            handle_unipile_delivery_webhook(message.external_message_id, {
                'event_type': 'message_delivered',
                'provider': 'whatsapp',
                'timestamp': timezone.now().isoformat(),
                'webhook_data': webhook_data
            })
        except Exception as e:
            self.logger.warning(f"Failed to trigger delivery tracking: {e}")
    
    def _trigger_read_tracking(self, message, webhook_data: Dict[str, Any]):
        """Trigger read tracking analytics (sync-only to preserve tenant context)"""
        try:
            # Skip real-time WebSocket updates to avoid async_to_sync issues in ASGI
            # Real-time updates can be handled by Django signals if needed
            logger.info(f"Read receipt processed for message {message.id} (WebSocket updates disabled for sync compatibility)")
        except Exception as e:
            logger.warning(f"Failed to process read tracking: {e}")
    
    def validate_webhook_data(self, data: Dict[str, Any]) -> bool:
        """Validate WhatsApp-specific webhook data"""
        if not super().validate_webhook_data(data):
            return False
        
        # WhatsApp-specific validations
        if 'message' in data or 'id' in data or 'message_id' in data:
            return True
        
        # Check for nested message data
        if 'data' in data and isinstance(data['data'], dict):
            nested_data = data['data']
            if 'message' in nested_data or 'id' in nested_data or 'message_id' in nested_data:
                return True
        
        # Account-level events don't need message data
        event_type = data.get('event_type', data.get('event', ''))
        if 'account' in event_type:
            return True
        
        self.logger.error("WhatsApp webhook missing required message data")
        return False