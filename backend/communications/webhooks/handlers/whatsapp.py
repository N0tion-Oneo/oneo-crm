"""
WhatsApp-specific webhook handler
"""
import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.utils import timezone as django_timezone
from asgiref.sync import async_to_sync
from .base import BaseWebhookHandler
from communications.utils.message_direction import determine_message_direction
from communications.services.participant_resolution import (
    ParticipantResolutionService, ConversationStorageDecider
)
from communications.models import Participant

logger = logging.getLogger(__name__)


class WhatsAppWebhookHandler(BaseWebhookHandler):
    """Specialized handler for WhatsApp webhook events via UniPile"""
    
    def __init__(self):
        super().__init__('whatsapp')
        self.resolution_service = ParticipantResolutionService()
        self.storage_decider = ConversationStorageDecider()
    
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
            from django.db import transaction
            
            # Log the incoming data structure for debugging
            logger.info(f"📥 WhatsApp webhook data type: {type(data)}")
            logger.info(f"📥 WhatsApp webhook data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict!'}")
            
            # Get user connection (we're already in tenant context)
            connection = account_router.get_user_connection(account_id)
            if not connection:
                return {'success': False, 'error': 'User connection not found'}
            
            # Validate it's a WhatsApp connection
            if connection.channel_type != 'whatsapp':
                return {'success': False, 'error': f'Invalid channel type: {connection.channel_type}'}
            
            # Extract message data directly from webhook
            # If data is not a dict, something is wrong
            if not isinstance(data, dict):
                logger.error(f"Expected dict for webhook data, got {type(data)}: {data}")
                return {'success': False, 'error': f'Invalid data type: {type(data)}'}
                
            # The webhook structure for WhatsApp via UniPile is:
            # {
            #   "event": "message_received",
            #   "message": "actual message text",  <-- This is the content
            #   "message_id": "xxx",
            #   "chat_id": "xxx",
            #   "sender": {...},
            #   ...
            # }
            
            # Extract message content - it's directly in data['message'] as a string
            content = ''
            if 'message' in data and data['message'] is not None:
                if isinstance(data['message'], str):
                    content = data['message']  # This is the actual message text
                    logger.info(f"📝 Extracted message content: '{content}'")
                elif isinstance(data['message'], dict):
                    # Different webhook format - message might be nested
                    content = data['message'].get('text', '') or data['message'].get('content', '')
                    logger.info(f"📝 Extracted message content from dict: '{content}'")
            else:
                # No message content - could be attachment-only message
                logger.info(f"📎 No text content - might be attachment-only message")
            
            # Extract IDs directly from data
            chat_id = (data.get('chat_id') or 
                      data.get('conversation_id') or 
                      data.get('thread_id'))
            message_id = (data.get('message_id') or 
                         data.get('id') or 
                         data.get('external_message_id'))
            
            # Extract sender information
            sender_info = data.get('sender', {})
            if not sender_info and 'from' in data:
                sender_info = data.get('from', {})
                
            sender_name = ''
            sender_id = ''
            if isinstance(sender_info, dict):
                sender_name = sender_info.get('attendee_name', '') or sender_info.get('name', '')
                sender_id = sender_info.get('attendee_id', '') or sender_info.get('id', '')
            
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
                conversation_name = f"WhatsApp Chat {chat_id[:8]}"
                
                # Try to extract better name from message sender
                # Use the direction utility to check if message is inbound (from customer)
                # Prepare webhook data with proper sender info for AccountOwnerDetector
                webhook_msg_data = {
                    **data,
                    'sender': sender_info,
                    'account_id': account_id,
                }
                msg_direction = determine_message_direction(
                    message_data=webhook_msg_data,
                    channel_type='whatsapp',
                    user_identifier=None,  # Let it get from channel
                    channel=channel
                )
                if sender_name and msg_direction == 'in':
                    conversation_name = sender_name
                
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
            
            # Check participant resolution and storage decision
            should_store = self._check_participant_resolution(
                data, connection, channel, conversation
            )
            
            # Always return message info but only store if should_store is True
            response_data = {
                'success': True,
                'conversation_id': str(conversation.id),
                'conversation_name': conversation.subject,
                'chat_id': chat_id,
                'storage_decision': {
                    'should_store': should_store,
                    'reason': 'contact_match' if should_store else 'no_contact_match'
                }
            }
            
            # If we shouldn't store, return early
            if not should_store:
                logger.info(f"📤 WhatsApp message not stored (no contact match) for chat {chat_id}")
                response_data['note'] = 'Message not stored - no contact match'
                return response_data
            
            # Check if message already exists (only if we should store)
            existing_message = None
            if message_id:
                existing_message = Message.objects.filter(
                    external_message_id=message_id,
                    channel=channel
                ).first()
            
            if existing_message:
                logger.info(f"✅ Message {message_id} already exists, status updated if needed")
                response_data.update({
                    'message_id': str(existing_message.id),
                    'note': 'Message already exists',
                    'approach': 'sync_webhook_processor'
                })
                return response_data
            
            # Determine message direction using unified utility
            # The webhook data structure should have sender info for proper comparison
            # Make sure the data has the proper structure for AccountOwnerDetector
            webhook_message_data = {
                **data,  # Include all original webhook data
                'sender': sender_info,  # Make sure sender info is available
                'account_id': account_id,  # Include the account ID
            }
            
            # Debug logging for direction determination
            logger.info(f"🔍 Direction determination - Account ID: {account_id}")
            logger.info(f"🔍 Direction determination - Sender info: {sender_info}")
            logger.info(f"🔍 Direction determination - Channel: {channel.unipile_account_id if channel else 'None'}")
            
            direction_str = determine_message_direction(
                message_data=webhook_message_data,
                channel_type='whatsapp', 
                user_identifier=None,  # Let it get from channel
                channel=channel  # Pass channel for automatic account detection
            )
            
            logger.info(f"🔍 Direction determined: {direction_str}")
            
            # Convert string direction to enum
            if direction_str == 'out':
                direction = MessageDirection.OUTBOUND
                status = MessageStatus.SENT
            else:
                direction = MessageDirection.INBOUND
                status = MessageStatus.DELIVERED
            
            # Check for attachments and generate display content if no text
            raw_attachments = data.get('attachments', [])
            attachments = []
            
            # Process attachments into the format expected by the download endpoint
            for att in raw_attachments:
                processed_att = {
                    'id': att.get('attachment_id'),  # Use attachment_id as the id
                    'attachment_id': att.get('attachment_id'),  # Keep original too
                    'type': att.get('attachment_type', 'file'),
                    'url': att.get('attachment_url'),
                    'size': att.get('attachment_size'),
                    'filename': att.get('attachment_name', 'attachment'),
                    'mime_type': self._get_mime_type(att.get('attachment_type', 'file')),
                    'unipile_data': att  # Store original data for fallback
                }
                attachments.append(processed_att)
            
            # If no text content but has attachments, create a descriptive message
            if not content and attachments:
                attachment_types = []
                for att in attachments:
                    att_type = att.get('type', 'file')
                    if att_type == 'img':
                        attachment_types.append('📷 Image')
                    elif att_type == 'video':
                        attachment_types.append('📹 Video')
                    elif att_type == 'audio':
                        attachment_types.append('🎵 Audio')
                    elif att_type == 'doc':
                        attachment_types.append('📄 Document')
                    else:
                        attachment_types.append('📎 File')
                
                if attachment_types:
                    content = ', '.join(attachment_types)
                    logger.info(f"📎 Generated attachment description: '{content}'")
            
            # Parse timestamps - webhook provides ISO format timestamp
            from dateutil import parser
            message_timestamp = django_timezone.now()
            if 'timestamp' in data:
                try:
                    ts = data['timestamp']
                    if isinstance(ts, str):
                        # Parse ISO format like "2025-08-25T20:02:12.000Z"
                        message_timestamp = parser.parse(ts)
                        if message_timestamp.tzinfo is None:
                            message_timestamp = django_timezone.make_aware(message_timestamp)
                    elif isinstance(ts, (int, float)):
                        # Handle Unix timestamp (seconds or milliseconds)
                        if ts > 10000000000:  # Milliseconds
                            ts = ts / 1000
                        message_timestamp = django_timezone.datetime.fromtimestamp(ts, tz=django_timezone.utc)
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp: {e}")
            
            # Create message with sync operations only
            logger.info(f"💾 Creating message with content: '{content}' (length: {len(content)})")
            message = Message.objects.create(
                channel=channel,
                conversation=conversation,
                external_message_id=message_id,
                content=content,
                direction=direction,
                status=status,
                created_at=message_timestamp,
                sent_at=message_timestamp if direction == MessageDirection.OUTBOUND else None,
                received_at=message_timestamp if direction == MessageDirection.INBOUND else None,
                metadata={
                    'webhook_data': data,
                    'sender_id': sender_id,
                    'sender_name': sender_name,
                    'chat_id': chat_id,
                    'provider': 'whatsapp',
                    'sync_created': True,
                    'attachments': attachments,
                    'has_attachments': len(attachments) > 0
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
                'attachment_count': len(attachments),
                'content_type': 'attachment_only' if not content and attachments else 'text_with_attachments' if content and attachments else 'text_only'
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
    
    def _get_mime_type(self, attachment_type: str) -> str:
        """Get MIME type from attachment type"""
        mime_map = {
            'img': 'image/jpeg',
            'image': 'image/jpeg',
            'video': 'video/mp4',
            'audio': 'audio/mpeg',
            'doc': 'application/pdf',
            'document': 'application/pdf',
            'pdf': 'application/pdf',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        return mime_map.get(attachment_type.lower(), 'application/octet-stream')
    
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
    
    def _check_participant_resolution(self, webhook_data: Dict[str, Any], 
                                     connection, channel, conversation) -> bool:
        """
        Check if WhatsApp message participants should trigger storage
        
        Returns:
            bool: True if message should be stored (has contact match)
        """
        try:
            from django.db import connection as db_connection
            
            # Get current tenant from the schema context
            # We're already in the right schema context from the webhook routing
            tenant = None
            if hasattr(db_connection, 'tenant'):
                tenant = db_connection.tenant
            
            # Initialize storage decider with tenant
            storage_decider = ConversationStorageDecider(tenant)
            
            # Extract attendees from webhook data
            attendees = []
            
            # Add sender
            sender_info = webhook_data.get('sender', {})
            if sender_info:
                attendees.append({
                    'phone_number': sender_info.get('phone_number', ''),
                    'name': sender_info.get('attendee_name', '') or sender_info.get('name', ''),
                    'attendee_id': sender_info.get('attendee_id', '') or sender_info.get('id', '')
                })
            
            # For WhatsApp, we typically have 1-on-1 chats or group chats
            # The webhook might not include all participants, but we need at least the sender
            conversation_data = {
                'attendees': attendees
            }
            
            # Use storage decider to check participants
            should_store, participants = async_to_sync(storage_decider.should_store_conversation)(
                conversation_data,
                'whatsapp'
            )
            
            # Link participants to conversation if storing
            if should_store and participants:
                from communications.models import ConversationParticipant
                for participant in participants:
                    async_to_sync(ConversationParticipant.objects.update_or_create)(
                        conversation=conversation,
                        participant=participant,
                        defaults={
                            'role': 'member',
                            'is_active': True
                        }
                    )
            
            return should_store
            
        except Exception as e:
            logger.warning(f"Error checking participant resolution for WhatsApp: {e}")
            # Default to storing on error to avoid data loss
            return True