"""
WhatsApp-specific webhook handler
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
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
        """Handle incoming WhatsApp message with chat-centric approach"""
        try:
            from communications.webhooks.routing import account_router
            from communications.models import Channel, Conversation, Message, ChatAttendee, MessageDirection, MessageStatus
            from communications.services.conversation_naming import conversation_naming_service
            from communications.unipile_sdk import unipile_service
            from asgiref.sync import async_to_sync
            
            # Get user connection (we're already in tenant context)
            connection = account_router.get_user_connection(account_id)
            if not connection:
                return {'success': False, 'error': 'User connection not found'}
            
            # Validate it's a WhatsApp connection
            if connection.channel_type != 'whatsapp':
                return {'success': False, 'error': f'Invalid channel type: {connection.channel_type}'}
            
            # Extract message data from UniPile webhook structure
            # UniPile sends the message content as a string in 'message' field, not as nested object
            chat_id = data.get('chat_id') or data.get('provider_chat_id')
            message_id = data.get('message_id')  
            message_text = data.get('message', '')  # This is the actual message text string
            
            # Extract sender information from UniPile format
            sender_info = data.get('sender', {})
            if isinstance(sender_info, dict):
                sender_id = sender_info.get('attendee_id') or sender_info.get('attendee_provider_id')
            else:
                sender_id = data.get('from') or data.get('sender_id')
            
            if not chat_id:
                return {'success': False, 'error': 'Chat ID not found in webhook data'}
            
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
            
            # Check if we have the conversation and attendees
            conversation = Conversation.objects.filter(
                channel=channel,
                external_thread_id=chat_id
            ).first()
            
            chat_attendees = []
            if not conversation or not ChatAttendee.objects.filter(channel=channel).exists():
                # Chat-centric approach: Get attendees for this specific chat
                try:
                    client = unipile_service.get_client()
                    chat_attendees_data = async_to_sync(client.request.get)(
                        f'chats/{chat_id}/attendees'
                    )
                    
                    if isinstance(chat_attendees_data, dict) and 'items' in chat_attendees_data:
                        attendees_list = chat_attendees_data['items']
                    elif isinstance(chat_attendees_data, list):
                        attendees_list = chat_attendees_data
                    else:
                        attendees_list = []
                    
                    # Store attendees in database for future reference
                    for attendee_data in attendees_list:
                        attendee_id = attendee_data.get('id')
                        if attendee_id:
                            chat_attendee, created = ChatAttendee.objects.get_or_create(
                                external_attendee_id=attendee_id,
                                channel=channel,
                                defaults={
                                    'provider_id': attendee_data.get('provider_id', ''),
                                    'name': attendee_data.get('name', ''),
                                    'picture_url': attendee_data.get('picture_url', ''),
                                    'is_self': attendee_data.get('is_self', False),
                                    'metadata': attendee_data
                                }
                            )
                            chat_attendees.append(chat_attendee)
                            
                            if created:
                                logger.info(f"✅ Created ChatAttendee {attendee_id} for chat {chat_id}")
                    
                except Exception as attendee_error:
                    logger.warning(f"Failed to fetch chat attendees for {chat_id}: {attendee_error}")
                    # Continue processing without attendee context
            else:
                # Get existing attendees
                chat_attendees = list(ChatAttendee.objects.filter(channel=channel))
            
            # Create or update conversation with proper naming
            if not conversation:
                # Find sender attendee for naming
                sender_attendee = None
                for attendee in chat_attendees:
                    if attendee.external_attendee_id == sender_id or attendee.provider_id == sender_id:
                        sender_attendee = attendee
                        break
                
                # Generate conversation name using naming service
                contact_info = {}
                if sender_attendee:
                    contact_info = {
                        'name': sender_attendee.name,
                        'phone': sender_attendee.metadata.get('phone', ''),
                        'profile': sender_attendee.metadata
                    }
                
                conversation_name = conversation_naming_service.generate_conversation_name(
                    channel_type='whatsapp',
                    contact_info=contact_info,
                    message_content=message_text,
                    external_thread_id=chat_id
                )
                
                conversation = Conversation.objects.create(
                    channel=channel,
                    external_thread_id=chat_id,
                    subject=conversation_name,  # Using subject field instead of name
                    status='active',  # Using the actual field from ConversationStatus choices
                    sync_status='pending',
                    metadata={
                        'conversation_name': conversation_name,
                        'conversation_type': 'whatsapp',
                        'created_by_user': str(connection.user.id),
                        'chat_id': chat_id,
                        'webhook_created': True
                    }
                )
                logger.info(f"✅ Created conversation '{conversation_name}' for chat {chat_id}")
            
            # Check if message already exists (handle duplicates)
            existing_message = Message.objects.filter(
                external_message_id=message_id,
                channel=channel
            ).first()
            
            if existing_message:
                logger.info(f"✅ Message {message_id} already exists, updating if needed")
                # Update existing message status if needed
                if existing_message.status != MessageStatus.DELIVERED:
                    existing_message.status = MessageStatus.DELIVERED
                    existing_message.received_at = timezone.now()
                    existing_message.save(update_fields=['status', 'received_at'])
                
                conversation_name = conversation.subject or conversation.metadata.get('conversation_name', f'Chat {chat_id[:8]}')
                return {
                    'success': True,
                    'message_id': str(existing_message.id),
                    'conversation_id': str(conversation.id),
                    'conversation_name': conversation_name,
                    'note': 'Message already exists, updated status',
                    'approach': 'chat_centric_webhook'
                }
            
            # Enhanced contact identification using stored account data
            from communications.services.contact_identification import contact_identification_service
            contact_info = contact_identification_service.identify_whatsapp_contact(connection, data)
            
            # Determine message direction using enhanced detection service
            from communications.services.direction_detection import direction_detection_service
            direction, detection_metadata = direction_detection_service.determine_direction(
                connection=connection,
                message_data=data,
                event_type='message_received'
            )
            
            # Create new message with enhanced contact data
            message = Message.objects.create(
                channel=conversation.channel,
                conversation=conversation,
                external_message_id=message_id,
                content=message_text,
                direction=direction,
                contact_phone=contact_info.get('contact_phone', ''),  # Store contact phone in dedicated field
                status=MessageStatus.DELIVERED,
                received_at=timezone.now(),
                sync_status='synced',  # This came from webhook so it's synced
                metadata={
                    'sender_id': sender_id,
                    'webhook_data': data,
                    'chat_id': chat_id,
                    'webhook_received': True,
                    'direction_detection': detection_metadata,  # Store detection details
                    'contact_identification': contact_info,     # Store contact identification
                    'business_phone': contact_info.get('business_phone'),
                    'contact_phone': contact_info.get('contact_phone'),
                    'contact_name': contact_info.get('contact_name'),
                    'is_group_chat': contact_info.get('is_group_chat', False)
                }
            )
            
            conversation_name = conversation.subject or conversation.metadata.get('conversation_name', f'Chat {chat_id[:8]}')
            logger.info(f"✅ Created WhatsApp message {message.id} in conversation '{conversation_name}'")
            
            # Send real-time update
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"conversation_{conversation.id}",
                        {
                            'type': 'new_message',
                            'message': {
                                'id': str(message.id),
                                'content': message.content,
                                'direction': message.direction,
                                'status': message.status,
                                'created_at': message.created_at.isoformat(),
                                'conversation_id': str(conversation.id)
                            }
                        }
                    )
            except Exception as ws_error:
                logger.warning(f"Failed to send real-time update: {ws_error}")
            
            return {
                'success': True,
                'message_id': str(message.id),
                'conversation_id': str(conversation.id),
                'conversation_name': conversation.subject or conversation.metadata.get('conversation_name', f'Chat {chat_id[:8]}'),
                'attendees_synced': len(chat_attendees),
                'approach': 'chat_centric_webhook'
            }
            
        except Exception as e:
            logger.error(f"WhatsApp message handling failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound WhatsApp message confirmation with chat-centric approach"""
        try:
            from communications.models import Message, MessageStatus, Conversation, Channel, ChatAttendee
            from communications.unipile_sdk import unipile_service
            from asgiref.sync import async_to_sync
            
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
                
                # Send real-time update
                try:
                    from channels.layers import get_channel_layer
                    channel_layer = get_channel_layer()
                    if channel_layer:
                        async_to_sync(channel_layer.group_send)(
                            f"conversation_{message.conversation.id}",
                            {
                                'type': 'message_status_update',
                                'message_id': str(message.id),
                                'status': 'sent',
                                'sent_at': message.sent_at.isoformat()
                            }
                        )
                except Exception as ws_error:
                    logger.warning(f"Failed to send real-time status update: {ws_error}")
                
                return {
                    'success': True,
                    'message_id': str(message.id),
                    'conversation_id': str(message.conversation.id),
                    'approach': 'chat_centric_webhook'
                }
            
            # If no existing message found but we have chat context, handle as new outbound message
            elif chat_id:
                # This handles cases where outbound message webhook arrives before we created the local message
                try:
                    # Get channel for this account
                    channel = Channel.objects.filter(
                        unipile_account_id=account_id,
                        channel_type='whatsapp'
                    ).first()
                    
                    if channel:
                        # Get or create conversation
                        conversation = Conversation.objects.filter(
                            channel=channel,
                            external_thread_id=chat_id
                        ).first()
                        
                        if not conversation:
                            # If conversation doesn't exist, try to get attendees for proper naming
                            try:
                                client = unipile_service.get_client()
                                chat_attendees_data = async_to_sync(client.request.get)(
                                    f'chats/{chat_id}/attendees'
                                )
                                
                                attendees_list = chat_attendees_data.get('items', []) if isinstance(chat_attendees_data, dict) else []
                                
                                # Store attendees
                                for attendee_data in attendees_list:
                                    attendee_id = attendee_data.get('id')
                                    if attendee_id:
                                        ChatAttendee.objects.get_or_create(
                                            external_attendee_id=attendee_id,
                                            channel=channel,
                                            defaults={
                                                'provider_id': attendee_data.get('provider_id', ''),
                                                'name': attendee_data.get('name', ''),
                                                'picture_url': attendee_data.get('picture_url', ''),
                                                'is_self': attendee_data.get('is_self', False),
                                                'metadata': attendee_data
                                            }
                                        )
                                        
                                # Create conversation with basic naming
                                conversation_name = f"WhatsApp Chat {chat_id[:8]}"
                                if attendees_list:
                                    first_attendee = next((a for a in attendees_list if not a.get('is_self')), None)
                                    if first_attendee and first_attendee.get('name'):
                                        conversation_name = first_attendee['name']
                                
                                conversation = Conversation.objects.create(
                                    channel=channel,
                                    external_thread_id=chat_id,
                                    subject=conversation_name,
                                    status='active',
                                    sync_status='pending',
                                    metadata={
                                        'conversation_name': conversation_name,
                                        'conversation_type': 'whatsapp',
                                        'created_by_user': str(channel.created_by.id),
                                        'chat_id': chat_id,
                                        'webhook_created': True
                                    }
                                )
                                
                            except Exception as attendee_error:
                                logger.warning(f"Failed to fetch attendees for outbound message chat {chat_id}: {attendee_error}")
                                # Create conversation without attendee context
                                conversation = Conversation.objects.create(
                                    channel=channel,
                                    external_thread_id=chat_id,
                                    subject=f"WhatsApp Chat {chat_id[:8]}",
                                    status='active',
                                    sync_status='pending',
                                    metadata={
                                        'conversation_name': f"WhatsApp Chat {chat_id[:8]}",
                                        'conversation_type': 'whatsapp',
                                        'created_by_user': str(channel.created_by.id),
                                        'chat_id': chat_id,
                                        'webhook_created': True
                                    }
                                )
                        
                        # Log successful handling without creating duplicate message
                        logger.info(f"✅ Handled outbound message webhook for conversation '{conversation.subject or conversation.metadata.get('conversation_name', f'Chat {chat_id[:8]}')}'")
                        return {
                            'success': True,
                            'conversation_id': str(conversation.id),
                            'conversation_name': conversation.subject or conversation.metadata.get('conversation_name', f'Chat {chat_id[:8]}'),
                            'note': 'Outbound message webhook handled with chat context',
                            'approach': 'chat_centric_webhook'
                        }
                        
                except Exception as conv_error:
                    logger.error(f"Failed to handle outbound message with chat context: {conv_error}")
            
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
        """Trigger read tracking analytics"""
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
                        'read_at': timezone.now().isoformat(),
                        'provider': 'whatsapp'
                    }
                )
        except Exception as e:
            self.logger.warning(f"Failed to send read update: {e}")
    
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