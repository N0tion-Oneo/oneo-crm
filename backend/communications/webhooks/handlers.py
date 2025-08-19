"""
UniPile webhook event handlers
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import connection as db_connection
from communications.models import UserChannelConnection, Message, Conversation, ChannelType, MessageDirection, MessageStatus
from communications.webhooks.routing import account_router
from communications.resolvers.contact_identifier import ContactIdentifier
from communications.resolvers.relationship_context import RelationshipContextResolver
from communications.services.unified_inbox import UnifiedInboxService

logger = logging.getLogger(__name__)


class UnipileWebhookHandler:
    """Handles different types of UniPile webhook events"""
    
    def __init__(self):
        # Initialize contact resolution services
        # Note: tenant_id will be set from request context when processing webhooks
        self.contact_identifier = None
        self.relationship_resolver = None
        self.event_handlers = {
            'message.received': self.handle_message_received,
            'message.sent': self.handle_message_sent,
            'message_received': self.handle_message_received,  # Handle both formats
            'message_sent': self.handle_message_sent,          # Handle both formats
            'message_delivered': self.handle_message_delivered, # Handle delivery status
            'message_read': self.handle_message_read,          # Handle read receipts
            'account.connected': self.handle_account_connected,
            'account.disconnected': self.handle_account_disconnected,
            'account.error': self.handle_account_error,
            'account.checkpoint': self.handle_account_checkpoint,
            # Enhanced UniPile account events
            'creation_success': self.handle_account_created,
            'creation_fail': self.handle_account_creation_failed,
            'credentials': self.handle_credentials_required,
            'permissions': self.handle_permissions_error,
            'error': self.handle_account_error,
            # Email specific events
            'mail_received': self.handle_message_received,  # Map email events to message handler
            'mail_sent': self.handle_message_sent,          # Map email events to message handler
        }
    
    def _initialize_resolvers(self, tenant_id: int):
        """Initialize contact and relationship resolvers with tenant context"""
        if not self.contact_identifier or not self.relationship_resolver:
            self.contact_identifier = ContactIdentifier(tenant_id=tenant_id)
            self.relationship_resolver = RelationshipContextResolver(tenant_id=tenant_id)
    
    def process_webhook(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a webhook event
        
        Args:
            event_type: Type of webhook event
            data: Event data from UniPile
            
        Returns:
            Dict[str, Any]: Processing result
        """
        logger.info(f"Processing webhook event: {event_type}")
        
        # Extract account ID from event data
        account_id = self.extract_account_id(data)
        if not account_id:
            logger.error(f"No account ID found in webhook data: {data}")
            return {'success': False, 'error': 'No account ID in webhook data'}
        
        # Get event handler
        handler = self.event_handlers.get(event_type)
        if not handler:
            logger.warning(f"No handler for event type: {event_type}")
            return {'success': False, 'error': f'Unsupported event type: {event_type}'}
        
        # Route to correct tenant and process
        result = account_router.process_with_tenant_context(
            account_id, 
            handler, 
            data
        )
        
        if result is None:
            return {'success': False, 'error': 'Failed to route to tenant'}
        
        return result
    
    def extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract account ID from webhook data"""
        # Ensure data is a dictionary
        if not isinstance(data, dict):
            logger.error(f"Expected dict but got {type(data)}: {data}")
            return None
        
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
        """Handle incoming message webhook with channel-specific routing"""
        try:
            # Ensure data is a dictionary
            if not isinstance(data, dict):
                logger.error(f"Expected dict in handle_message_received but got {type(data)}: {data}")
                return {'success': False, 'error': f'Invalid data type: {type(data)}'}
            
            # Get user connection (we're already in tenant context)
            connection = account_router.get_user_connection(account_id)
            if not connection:
                logger.error(f"No user connection found for account {account_id}")
                return {'success': False, 'error': 'User connection not found'}
            
            # Route to specialized handler based on channel type
            if connection.channel_type in ['gmail', 'outlook', 'mail', 'email']:
                logger.info(f"Routing email message to specialized email handler for account {account_id}")
                from communications.webhooks.email_handler import email_webhook_handler
                return email_webhook_handler.handle_email_received(account_id, data)
            
            # For non-email channels, continue with existing WhatsApp/social logic
            logger.info(f"Processing {connection.channel_type} message with standard handler for account {account_id}")
            
            # Simple approach: store raw webhook data and extract what we need
            from communications.utils.phone_extractor import (
                extract_whatsapp_phone_from_webhook,
                determine_whatsapp_direction,
                extract_whatsapp_conversation_id,
                extract_whatsapp_contact_name
            )
            
            # Extract basic info directly from raw webhook data
            external_message_id = data.get('id') or data.get('message_id')
            conversation_id = extract_whatsapp_conversation_id(data)
            phone_number = extract_whatsapp_phone_from_webhook(data)
            direction = determine_whatsapp_direction(data)
            contact_name = extract_whatsapp_contact_name(data)
            message_content = data.get('message', data.get('text', data.get('body', '')))
            
            # Create or get conversation
            conversation = self.get_or_create_conversation_simple(
                connection, 
                conversation_id,
                data
            )
            
            # Check if message already exists to prevent duplicates
            if external_message_id:
                existing_message = Message.objects.filter(
                    external_message_id=external_message_id,
                    conversation=conversation
                ).first()
                
                if existing_message:
                    logger.info(f"Message {external_message_id} already exists (ID: {existing_message.id}), skipping duplicate")
                    return {
                        'success': True,
                        'message_id': str(existing_message.id),
                        'conversation_id': str(conversation.id),
                        'note': 'Message already exists, skipped duplicate'
                    }
            
            # Create message record with raw data
            message, was_created = self.create_simple_message_record(
                connection,
                conversation,
                external_message_id,
                message_content,
                direction,
                phone_number,
                contact_name,
                data  # Store entire raw webhook data
            )
            
            if was_created:
                logger.info(f"Created new inbound message {message.id} for account {account_id}")
                
                # Trigger unified inbox real-time update
                self._trigger_unified_inbox_update(message, conversation, connection.user)
            else:
                logger.info(f"Message {message.id} already existed (race condition resolved)")
            
            # Auto-create contact if enabled and no contact is linked
            if was_created and not message.contact_record:
                self._attempt_auto_contact_resolution(message)
            
            return {
                'success': True,
                'message_id': str(message.id),
                'conversation_id': str(conversation.id),
                'was_created': was_created,
                'channel_type': connection.channel_type,
                'normalized': True
            }
            
        except Exception as e:
            logger.error(f"Error handling message received for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_sent(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound message confirmation webhook with channel routing"""
        try:
            # Ensure data is a dictionary
            if not isinstance(data, dict):
                logger.error(f"Expected dict in handle_message_sent but got {type(data)}: {data}")
                return {'success': False, 'error': f'Invalid data type: {type(data)}'}
            
            # Get user connection to determine channel type
            connection = account_router.get_user_connection(account_id)
            if connection and connection.channel_type in ['gmail', 'outlook', 'mail', 'email']:
                from communications.webhooks.email_handler import email_webhook_handler
                return email_webhook_handler.handle_email_sent(account_id, data)
            
            # UniPile webhook data structure has message content at the top level,
            # not nested under a 'message' object. So we use the entire data object.
            message_data = data
            
            external_message_id = message_data.get('message_id')
            
            if external_message_id:
                # Find existing message record
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if message:
                    message.status = MessageStatus.SENT
                    message.sent_at = timezone.now()
                    message.save()
                    
                    logger.info(f"Updated message {message.id} status to sent")
                    return {'success': True, 'message_id': str(message.id)}
            
            logger.warning(f"No message record found for external ID {external_message_id}")
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            logger.error(f"Error handling message sent for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_delivered(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message delivery confirmation webhook with channel routing"""
        try:
            # Ensure data is a dictionary
            if not isinstance(data, dict):
                logger.error(f"Expected dict in handle_message_delivered but got {type(data)}: {data}")
                return {'success': False, 'error': f'Invalid data type: {type(data)}'}
            
            # Get user connection to determine channel type
            connection = account_router.get_user_connection(account_id)
            if connection and connection.channel_type in ['gmail', 'outlook', 'mail', 'email']:
                from communications.webhooks.email_handler import email_webhook_handler
                return email_webhook_handler.handle_email_delivered(account_id, data)
            
            # UniPile webhook data structure has message content at the top level,
            # not nested under a 'message' object. So we use the entire data object.
            message_data = data
            
            external_message_id = message_data.get('message_id')
            
            if external_message_id:
                # Find existing message record
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if message:
                    message.status = MessageStatus.DELIVERED
                    message.save()
                    
                    logger.info(f"Updated message {message.id} status to delivered")
                    return {'success': True, 'message_id': str(message.id)}
            
            logger.warning(f"No message record found for external ID {external_message_id}")
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            logger.error(f"Error handling message delivered for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_message_read(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message read receipt webhook with channel routing"""
        try:
            # Get user connection to determine channel type
            connection = account_router.get_user_connection(account_id)
            if connection and connection.channel_type in ['gmail', 'outlook', 'mail', 'email']:
                from communications.webhooks.email_handler import email_webhook_handler
                return email_webhook_handler.handle_email_read(account_id, data)
            
            # Debug: Log the actual data structure for non-email channels
            logger.info(f"DEBUG: Read message webhook data: {data}")
            logger.info(f"DEBUG: Data type: {type(data)}")
            
            # UniPile webhook data structure has message content at the top level,
            # not nested under a 'message' object. So we use the entire data object.
            message_data = data
            
            external_message_id = message_data.get('message_id')
            
            if external_message_id:
                # Find existing message record and mark as read
                message = Message.objects.filter(
                    external_message_id=external_message_id
                ).first()
                
                if message:
                    # Update status to read (if it's an outbound message) or just log for inbound
                    if message.direction == MessageDirection.OUTBOUND:
                        message.status = MessageStatus.READ
                        message.save()
                        logger.info(f"Updated message {message.id} status to read")
                    else:
                        logger.info(f"Read receipt for inbound message {message.id} - no status update needed")
                    
                    return {'success': True, 'message_id': str(message.id)}
            
            logger.warning(f"No message record found for external ID {external_message_id}")
            return {'success': True, 'note': 'No local message record to update'}
            
        except Exception as e:
            logger.error(f"Error handling message read for account {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_connected(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account connection success webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.auth_status = 'authenticated'
                connection.last_sync_at = timezone.now()
                connection.sync_error_count = 0
                connection.last_error = ''
                connection.save()
                
                logger.info(f"Account {account_id} connected successfully")
                return {'success': True, 'status': 'connected'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling account connected for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_disconnected(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account disconnection webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.auth_status = 'failed'
                connection.last_error = data.get('reason', 'Account disconnected')
                connection.save()
                
                logger.warning(f"Account {account_id} disconnected: {connection.last_error}")
                return {'success': True, 'status': 'disconnected'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling account disconnected for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_error(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account error webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.auth_status = 'failed'
                connection.sync_error_count += 1
                connection.last_error = data.get('error', 'Unknown error')
                connection.save()
                
                logger.error(f"Account {account_id} error: {connection.last_error}")
                return {'success': True, 'status': 'error_recorded'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling account error for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_checkpoint(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account checkpoint (2FA) webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.auth_status = 'pending'
                # Store checkpoint data for frontend to handle
                checkpoint_data = {
                    'type': data.get('checkpoint_type', 'unknown'),
                    'message': data.get('message', 'Checkpoint required'),
                    'timestamp': timezone.now().isoformat()
                }
                connection.connection_config['checkpoint'] = checkpoint_data
                connection.save()
                
                logger.info(f"Account {account_id} requires checkpoint: {checkpoint_data['type']}")
                return {'success': True, 'status': 'checkpoint_required'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling account checkpoint for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_or_create_conversation_simple(self, connection: UserChannelConnection, conversation_id: str, webhook_data: Dict[str, Any]) -> Conversation:
        """Get or create conversation with simple approach"""
        if conversation_id:
            conversation = Conversation.objects.filter(
                external_thread_id=conversation_id
            ).first()
            if conversation:
                return conversation
        
        # Create new conversation
        from communications.models import Channel
        
        # Get or create channel for this connection
        channel, _ = Channel.objects.get_or_create(
            unipile_account_id=connection.unipile_account_id,
            channel_type=connection.channel_type,
            defaults={
                'name': f"{connection.channel_type.title()} - {connection.account_name}",
                'auth_status': connection.auth_status,
                'created_by': connection.user
            }
        )
        
        # Extract contact info using provider logic for better conversation subject
        from communications.utils.phone_extractor import (
            extract_whatsapp_contact_name,
            extract_whatsapp_phone_from_webhook,
            get_display_name_or_phone
        )
        
        contact_name = extract_whatsapp_contact_name(webhook_data)
        contact_phone = extract_whatsapp_phone_from_webhook(webhook_data)
        
        # Create a meaningful subject using contact name or formatted phone
        if contact_name:
            subject = f"WhatsApp - {contact_name}"
        elif contact_phone:
            # Use formatted phone as subject
            subject = f"WhatsApp - {contact_phone}"
        else:
            subject = "WhatsApp conversation"
        
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=conversation_id or f"msg_{webhook_data.get('id', 'unknown')}",
            subject=subject,
            status='active'
        )
        
        return conversation

    def get_or_create_conversation(self, connection: UserChannelConnection, message_data: Dict[str, Any]) -> Conversation:
        """Get or create conversation for message"""
        # Debug logging
        logger.debug(f"Getting conversation for message with keys: {list(message_data.keys())}")
        logger.debug(f"Conversation IDs - conversation_id: {message_data.get('conversation_id')}, thread_id: {message_data.get('thread_id')}, chat_id: {message_data.get('chat_id')}")
        
        # In UniPile webhook format, the chat_id is the conversation identifier
        external_thread_id = message_data.get('conversation_id') or message_data.get('thread_id') or message_data.get('chat_id')
        
        if external_thread_id:
            conversation = Conversation.objects.filter(
                external_thread_id=external_thread_id
            ).first()
            if conversation:
                return conversation
        
        # Create new conversation
        from communications.models import Channel
        
        # Get or create channel for this connection
        channel, _ = Channel.objects.get_or_create(
            unipile_account_id=connection.unipile_account_id,
            channel_type=connection.channel_type,
            defaults={
                'name': f"{connection.channel_type.title()} - {connection.account_name}",
                'auth_status': connection.auth_status,
                'created_by': connection.user
            }
        )
        
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=external_thread_id or f"msg_{message_data.get('message_id', timezone.now().timestamp())}",
            subject=f"WhatsApp conversation", 
            status='active'
        )
        
        return conversation
    
    def create_simple_message_record(self, connection: UserChannelConnection, conversation: Conversation, 
                                   external_message_id: str, content: str, direction: str, 
                                   phone_number: str, contact_name: str, raw_webhook_data: Dict[str, Any]) -> tuple[Message, bool]:
        """Create message record with simple raw data storage approach"""
        from django.db import transaction
        
        # Use database-level atomic transaction to prevent race conditions
        with transaction.atomic():
            # Try to get existing message first (with select_for_update to prevent race conditions)
            existing_message = Message.objects.select_for_update().filter(
                external_message_id=external_message_id,
                conversation=conversation
            ).first()
            
            if existing_message:
                # Message already exists - return without triggering real-time processing
                return existing_message, False
            
            # Create new message with raw webhook data stored in metadata
            message = Message.objects.create(
                channel=conversation.channel,
                conversation=conversation,
                external_message_id=external_message_id,
                direction=direction,
                content=content or '',
                subject='',  # WhatsApp doesn't have subjects
                contact_email='',  # WhatsApp uses phone numbers
                contact_phone=phone_number,
                status=MessageStatus.DELIVERED if direction == MessageDirection.INBOUND else MessageStatus.SENT,
                metadata={
                    'raw_webhook_data': raw_webhook_data,  # Store entire webhook response
                    'contact_name': contact_name,
                    'extracted_phone': phone_number,
                    'webhook_processed_at': timezone.now().isoformat(),
                    'processing_version': '2.0_simplified'
                },
                sent_at=timezone.now() if direction == MessageDirection.OUTBOUND else None,
                received_at=timezone.now() if direction == MessageDirection.INBOUND else None
            )
            
            logger.info(f"Created message {message.id}: {direction} from phone {phone_number}")
            return message, True
    
    def create_message_record_atomic(self, connection: UserChannelConnection, conversation: Conversation, 
                            message_data: Dict[str, Any], direction: str) -> tuple[Message, bool]:
        """Create message record atomically, preventing duplicates and only triggering real-time for new messages"""
        from django.db import transaction
        
        external_message_id = message_data.get('message_id')
        
        # Use database-level atomic transaction to prevent race conditions
        with transaction.atomic():
            # Try to get existing message first (with select_for_update to prevent race conditions)
            existing_message = Message.objects.select_for_update().filter(
                external_message_id=external_message_id,
                conversation=conversation
            ).first()
            
            if existing_message:
                # Message already exists - return without triggering real-time processing
                return existing_message, False
            
            # Create new message - this will trigger real-time processing
            message = self.create_message_record_internal(connection, conversation, message_data, direction)
            return message, True
    
    def create_message_record_internal(self, connection: UserChannelConnection, conversation: Conversation, 
                            message_data: Dict[str, Any], direction: str) -> Message:
        """Create message record from webhook data with real-time enhancements and contact resolution"""
        
        # Extract sender info from UniPile webhook format
        sender_info = message_data.get('sender', {})
        sender_email = sender_info.get('attendee_provider_id', '') if isinstance(sender_info, dict) else ''
        
        # CRITICAL: Determine correct direction and contact based on sender
        business_account = '27720720047@s.whatsapp.net'
        
        # If sender is business account, this is an OUTBOUND message TO a customer
        if sender_email == business_account:
            actual_direction = MessageDirection.OUTBOUND
            contact_email = ''  # For outbound, we don't set contact_email to business account
        else:
            # If sender is NOT business account, this is an INBOUND message FROM that customer
            actual_direction = MessageDirection.INBOUND
            contact_email = sender_email  # Customer's phone number
        
        # Override the direction parameter with our corrected logic
        direction = actual_direction
        
        # NEW: Contact resolution using pipeline relationship domain validation
        contact_record = None
        relationship_context = None
        
        if self.contact_identifier and actual_direction == MessageDirection.INBOUND:
            # Extract contact data for identification
            contact_data = {
                'email': sender_info.get('email') if isinstance(sender_info, dict) else None,
                'phone': sender_email if '@s.whatsapp.net' in sender_email else None,
                'name': sender_info.get('attendee_name', '') if isinstance(sender_info, dict) else '',
                'linkedin_url': message_data.get('linkedin_url'),  # May be None
                'website': message_data.get('website')  # May be None
            }
            
            # Filter out None values
            contact_data = {k: v for k, v in contact_data.items() if v}
            
            try:
                # Identify contact using duplicate rules with domain validation
                contact_record = self.contact_identifier.identify_contact(contact_data)
                
                if contact_record and self.relationship_resolver:
                    # Get relationship context with domain validation
                    relationship_context = self.relationship_resolver.get_relationship_context(
                        contact_record=contact_record,
                        message_email=contact_data.get('email')
                    )
                    
                    logger.info(f"Contact resolution for message: contact={contact_record.id}, domain_validated={relationship_context.get('domain_validated', True)}")
                
            except Exception as e:
                logger.warning(f"Error in contact resolution: {e}")
                # Continue without contact resolution if it fails
        
        # Extract message content and metadata 
        message_content = message_data.get('message', '')  # This is the actual text content
        
        # Get enhanced contact name from sender info
        contact_name = ''
        if isinstance(sender_info, dict):
            contact_name = sender_info.get('attendee_name', '')
        
        # Create enhanced metadata with contact name and resolution context
        enhanced_metadata = dict(message_data)  # Copy all webhook data
        if contact_name and contact_name != sender_email:
            enhanced_metadata['contact_name'] = contact_name
        
        # Add contact resolution metadata
        if contact_record:
            enhanced_metadata['contact_resolved'] = True
            enhanced_metadata['contact_record_id'] = contact_record.id
            enhanced_metadata['contact_pipeline_id'] = contact_record.pipeline.id
            enhanced_metadata['contact_pipeline_name'] = contact_record.pipeline.name
            
            if relationship_context:
                enhanced_metadata['relationship_context'] = relationship_context
                enhanced_metadata['domain_validated'] = relationship_context.get('domain_validated', True)
                
                # Flag potential domain mismatches for review
                if relationship_context.get('validation_status') == 'domain_mismatch_warning':
                    enhanced_metadata['needs_domain_review'] = True
                    enhanced_metadata['domain_mismatch_details'] = {
                        'message_domain': relationship_context.get('message_domain'),
                        'pipeline_context': relationship_context.get('pipeline_context', [])
                    }
        else:
            # No contact match found - add data for manual resolution
            if actual_direction == MessageDirection.INBOUND and contact_data:
                enhanced_metadata['unmatched_contact_data'] = contact_data
                enhanced_metadata['needs_manual_resolution'] = True
        
        # REAL-TIME ENHANCEMENT: Add attendee_id for profile picture fetching
        attendee_id = sender_info.get('attendee_id', '') if isinstance(sender_info, dict) else ''
        if attendee_id:
            enhanced_metadata['attendee_id'] = attendee_id
            # Trigger async profile picture fetch for real-time contact updates
            self._fetch_contact_profile_picture_async(connection, attendee_id, contact_email)
        
        # REAL-TIME ENHANCEMENT: Add attachment info for immediate download
        attachments = message_data.get('attachments', [])
        if attachments:
            enhanced_metadata['has_attachments'] = True
            enhanced_metadata['attachment_count'] = len(attachments)
            # Trigger async attachment processing for real-time media
            for attachment in attachments:
                self._process_attachment_async(connection, message_data.get('message_id'), attachment)

        message = Message.objects.create(
            channel=conversation.channel,
            conversation=conversation,
            contact_record=contact_record,  # NEW: Link to resolved contact
            external_message_id=message_data.get('message_id'),
            direction=direction,
            content=message_content,
            subject='',  # WhatsApp doesn't have subjects
            contact_email=contact_email,
            status=MessageStatus.DELIVERED if direction == MessageDirection.INBOUND else MessageStatus.SENT,
            metadata=enhanced_metadata,
            sent_at=timezone.now() if direction == MessageDirection.OUTBOUND else None,
            received_at=timezone.now() if direction == MessageDirection.INBOUND else None
        )
        
        # Update conversation with resolved contact context
        if contact_record and not conversation.primary_contact_record:
            conversation.primary_contact_record = contact_record
            
            # Add relationship context to conversation metadata
            if relationship_context:
                if not conversation.metadata:
                    conversation.metadata = {}
                conversation.metadata['relationship_context'] = relationship_context
                conversation.metadata['domain_validated'] = relationship_context.get('domain_validated', True)
            
            conversation.save(update_fields=['primary_contact_record', 'metadata'])
            logger.info(f"Updated conversation {conversation.id} with primary contact {contact_record.id}")
        
        # REAL-TIME ENHANCEMENT: Broadcast message with contact info immediately
        # This will only happen for actually created messages, not duplicates
        self._broadcast_message_with_contact_info(message, conversation, contact_name, attendee_id, connection)
        
        return message
    
    def auto_create_contact(self, message_data: Dict[str, Any], connection: UserChannelConnection):
        """Auto-create contact from message if enabled"""
        try:
            from communications.services import communication_service
            
            # Extract contact info from UniPile webhook format
            sender_info = message_data.get('sender', {})
            if isinstance(sender_info, dict):
                sender_email = sender_info.get('attendee_provider_id', '')
                sender_name = sender_info.get('attendee_name', '')
            else:
                sender_email = ''
                sender_name = ''
            
            if sender_email:
                # Try to create/resolve contact
                communication_service.resolve_or_create_contact(
                    recipient=sender_email,
                    name=sender_name if sender_name != sender_email else None,
                    additional_data={
                        'source': 'webhook',
                        'channel_type': connection.channel_type,
                        'attendee_id': sender_info.get('attendee_id', '') if isinstance(sender_info, dict) else ''
                    }
                )
                
        except Exception as e:
            logger.warning(f"Failed to auto-create contact: {e}")
    
    def handle_account_created(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful account creation webhook from UniPile"""
        try:
            # This is called when a hosted auth account is successfully created
            # The account_id is the new UniPile account ID
            provider = data.get('provider', '').lower()
            
            logger.info(f"Account created successfully: {account_id}, provider: {provider}")
            
            # Try to find pending connections that match this creation
            # Look for recent pending connections for this provider type
            recent_pending = UserChannelConnection.objects.filter(
                channel_type=provider,
                account_status='pending',
                unipile_account_id__isnull=True,
                created_at__gte=timezone.now() - timezone.timedelta(hours=1)
            ).order_by('-created_at')
            
            if recent_pending.exists():
                connection = recent_pending.first()
                
                # Update the connection with the new account ID
                connection.unipile_account_id = account_id
                connection.account_status = 'active'
                connection.auth_status = 'authenticated'
                connection.hosted_auth_url = ''
                connection.last_sync_at = timezone.now()
                
                # Store account metadata
                if 'account' in data:
                    connection.connection_config['account_info'] = data['account']
                
                connection.save()
                
                logger.info(f"Linked new account {account_id} to connection {connection.id}")
                
                return {
                    'success': True,
                    'linked_connection': str(connection.id),
                    'account_id': account_id
                }
            else:
                # No pending connection found - this might be a manual creation
                logger.warning(f"No pending connection found for new account {account_id} of type {provider}")
                return {
                    'success': True,
                    'note': 'Account created but no pending connection to link'
                }
            
        except Exception as e:
            logger.error(f"Error handling account creation for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_account_creation_failed(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed account creation webhook from UniPile"""
        try:
            provider = data.get('provider', '').lower()
            error_message = data.get('error', 'Account creation failed')
            
            logger.warning(f"Account creation failed for provider {provider}: {error_message}")
            
            # Find and update pending connections
            recent_pending = UserChannelConnection.objects.filter(
                channel_type=provider,
                account_status='pending',
                created_at__gte=timezone.now() - timezone.timedelta(hours=1)
            ).order_by('-created_at')
            
            if recent_pending.exists():
                connection = recent_pending.first()
                connection.account_status = 'failed'
                connection.auth_status = 'failed'
                connection.last_error = error_message
                connection.hosted_auth_url = ''
                connection.save()
                
                logger.info(f"Updated connection {connection.id} with creation failure")
                
                return {
                    'success': True,
                    'updated_connection': str(connection.id),
                    'error': error_message
                }
            
            return {'success': True, 'note': 'No pending connection to update'}
            
        except Exception as e:
            logger.error(f"Error handling account creation failure: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_credentials_required(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle credentials required webhook (checkpoint/2FA needed)"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.account_status = 'checkpoint_required'
                connection.auth_status = 'pending'
                
                # Store checkpoint information
                checkpoint_info = {
                    'type': data.get('checkpoint_type', 'credentials'),
                    'message': data.get('message', 'Credentials verification required'),
                    'timestamp': timezone.now().isoformat(),
                    'data': data
                }
                connection.checkpoint_data = checkpoint_info
                connection.save()
                
                logger.info(f"Account {account_id} requires credentials verification")
                return {'success': True, 'status': 'checkpoint_required'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling credentials required for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_permissions_error(self, account_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle permissions error webhook"""
        try:
            connection = account_router.get_user_connection(account_id)
            if connection:
                connection.account_status = 'failed'
                connection.auth_status = 'failed'
                connection.last_error = data.get('error', 'Permissions error - please re-authenticate')
                connection.save()
                
                logger.warning(f"Account {account_id} has permissions error")
                return {'success': True, 'status': 'permissions_error'}
            
            return {'success': False, 'error': 'Connection not found'}
            
        except Exception as e:
            logger.error(f"Error handling permissions error for {account_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _fetch_contact_profile_picture_async(self, connection: UserChannelConnection, attendee_id: str, contact_email: str):
        """Async fetch profile picture for real-time contact updates"""
        try:
            from communications.tasks import fetch_contact_profile_picture
            
            # Trigger Celery task for immediate profile picture fetch
            fetch_contact_profile_picture.delay(
                connection.unipile_account_id,
                attendee_id,
                contact_email
            )
            logger.info(f"Triggered async profile picture fetch for attendee {attendee_id}")
        except ImportError as e:
            logger.warning(f"Could not import profile picture task: {e}")
        except Exception as e:
            logger.warning(f"Failed to trigger profile picture fetch: {e}")
    
    def _process_attachment_async(self, connection: UserChannelConnection, message_id: str, attachment: Dict[str, Any]):
        """Async process attachment for real-time media handling"""
        try:
            from communications.tasks import process_message_attachment
            
            # Trigger Celery task for immediate attachment processing
            process_message_attachment.delay(
                connection.unipile_account_id,
                message_id,
                attachment.get('id', ''),
                attachment.get('type', ''),
                attachment.get('name', '')
            )
            logger.info(f"Triggered async attachment processing for message {message_id}")
        except ImportError as e:
            logger.warning(f"Could not import attachment processing task: {e}")
        except Exception as e:
            logger.warning(f"Failed to trigger attachment processing: {e}")
    
    def create_unified_message_record(self, connection: UserChannelConnection, conversation: Conversation, 
                                    normalized_message: Dict[str, Any], direction: str) -> tuple[Message, bool]:
        """Create unified message record using normalized data"""
        from django.db import transaction
        
        external_message_id = normalized_message.get('external_id') or normalized_message.get('id')
        
        # Use database-level atomic transaction to prevent race conditions
        with transaction.atomic():
            # Try to get existing message first (with select_for_update to prevent race conditions)
            existing_message = Message.objects.select_for_update().filter(
                external_message_id=external_message_id,
                conversation=conversation
            ).first()
            
            if existing_message:
                # Message already exists - return without triggering real-time processing
                return existing_message, False
            
            # Create new message using normalized data
            message = Message.objects.create(
                channel=conversation.channel,
                conversation=conversation,
                contact_record=normalized_message.get('contact_record'),
                external_message_id=external_message_id,
                direction=direction,
                content=normalized_message.get('content', ''),
                subject=normalized_message.get('subject', ''),
                contact_email=normalized_message.get('contact_email', ''),
                contact_phone=normalized_message.get('contact_phone', ''),
                status=normalized_message.get('status', MessageStatus.DELIVERED),
                metadata=normalized_message.get('metadata', {}),
                sent_at=normalized_message.get('sent_at') if direction == MessageDirection.OUTBOUND else None,
                received_at=normalized_message.get('created_at') if direction == MessageDirection.INBOUND else None
            )
            
            return message, True
    
    def _trigger_unified_inbox_update(self, message: Message, conversation: Conversation, user):
        """Trigger unified inbox real-time update"""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.debug("No channel layer available for unified inbox broadcasting")
                return
            
            # Get contact record if linked
            contact_record = message.contact_record
            
            # Prepare unified inbox update data
            unified_update = {
                'type': 'unified_inbox_update',
                'data': {
                    'message_id': str(message.id),
                    'conversation_id': str(conversation.id),
                    'channel_type': conversation.channel.channel_type if conversation.channel else 'unknown',
                    'direction': message.direction,
                    'content_preview': (message.content or '')[:100],
                    'timestamp': message.created_at.isoformat(),
                    'contact_record': {
                        'id': contact_record.id,
                        'title': contact_record.title,
                        'pipeline_name': contact_record.pipeline.name
                    } if contact_record else None,
                    'unread': message.direction == MessageDirection.INBOUND and message.status != 'read'
                }
            }
            
            # Broadcast to user's unified inbox room
            user_inbox_room = f"user_{user.id}_unified_inbox"
            async_to_sync(channel_layer.group_send)(user_inbox_room, unified_update)
            
            # If there's a contact record, also broadcast to record-specific room
            if contact_record:
                record_room = f"record_{contact_record.id}_timeline"
                async_to_sync(channel_layer.group_send)(record_room, unified_update)
            
            logger.info(f"Triggered unified inbox update for user {user.id}, message {message.id}")
            
        except ImportError as e:
            logger.warning(f"Could not import channels for unified inbox broadcasting: {e}")
        except Exception as e:
            logger.warning(f"Failed to trigger unified inbox update: {e}")
    
    def _extract_contact_data_for_resolution(self, message: Message) -> Dict[str, Any]:
        """Extract contact data from raw webhook data for contact resolution"""
        try:
            raw_data = message.metadata.get('raw_webhook_data', {}) if message.metadata else {}
            
            # Start with basic extracted fields
            contact_data = {
                'channel_type': message.channel.channel_type if message.channel else 'unknown',
                'email': message.contact_email or '',
                'phone': message.contact_phone or '',
                'name': message.metadata.get('contact_name', '') if message.metadata else ''
            }
            
            # Enhanced extraction from raw webhook data if needed
            if raw_data and isinstance(raw_data, dict):
                # WhatsApp-specific enhancements
                if contact_data['channel_type'] == 'whatsapp':
                    # Get provider_chat_id (the contact we're speaking to)
                    provider_chat_id = raw_data.get('provider_chat_id', '')
                    
                    # Method 1: Find contact info by matching provider_chat_id in attendees
                    if provider_chat_id and not (contact_data['phone'] and contact_data['name']):
                        attendees = raw_data.get('attendees', [])
                        if attendees and isinstance(attendees, list):
                            for attendee in attendees:
                                if isinstance(attendee, dict):
                                    attendee_provider_id = attendee.get('attendee_provider_id', '')
                                    if attendee_provider_id == provider_chat_id:
                                        # Found the contact we're speaking to
                                        if not contact_data['phone']:
                                            if '@s.whatsapp.net' in attendee_provider_id:
                                                contact_data['phone'] = attendee_provider_id.replace('@s.whatsapp.net', '')
                                        
                                        if not contact_data['name'] and attendee.get('attendee_name'):
                                            attendee_name = attendee['attendee_name']
                                            if not ('@s.whatsapp.net' in attendee_name or attendee_name.isdigit()):
                                                contact_data['name'] = attendee_name
                                        break
                    
                    # Method 2: Check if sender matches provider_chat_id (inbound message case)
                    if provider_chat_id and not (contact_data['phone'] and contact_data['name']):
                        sender = raw_data.get('sender', {})
                        if isinstance(sender, dict):
                            sender_provider_id = sender.get('attendee_provider_id', '')
                            if sender_provider_id == provider_chat_id:
                                # Sender is the contact (inbound message)
                                if not contact_data['phone']:
                                    if '@s.whatsapp.net' in sender_provider_id:
                                        contact_data['phone'] = sender_provider_id.replace('@s.whatsapp.net', '')
                                
                                if not contact_data['name'] and sender.get('attendee_name'):
                                    attendee_name = sender['attendee_name']
                                    if not ('@s.whatsapp.net' in attendee_name or attendee_name.isdigit()):
                                        contact_data['name'] = attendee_name
                    
                    # Fallback: Use provider_chat_id directly if available
                    if not contact_data['phone'] and provider_chat_id:
                        if '@s.whatsapp.net' in provider_chat_id:
                            contact_data['phone'] = provider_chat_id.replace('@s.whatsapp.net', '')
                
                # Email-specific enhancements (Gmail, Outlook)
                elif contact_data['channel_type'] in ['gmail', 'outlook', 'mail']:
                    sender = raw_data.get('sender', {})
                    if isinstance(sender, dict):
                        if not contact_data['email'] and sender.get('email'):
                            contact_data['email'] = sender['email']
                        if not contact_data['name'] and sender.get('name'):
                            contact_data['name'] = sender['name']
                
                # LinkedIn-specific enhancements
                elif contact_data['channel_type'] == 'linkedin':
                    sender = raw_data.get('sender', {})
                    if isinstance(sender, dict):
                        if not contact_data['name'] and sender.get('name'):
                            contact_data['name'] = sender['name']
                        # LinkedIn uses profile IDs instead of emails
                        if sender.get('profile_id'):
                            contact_data['linkedin_profile_id'] = sender['profile_id']
            
            # Clean and format phone number if present (includes country code)
            if contact_data['phone']:
                # Remove any remaining WhatsApp suffixes and clean
                clean_phone = contact_data['phone'].replace('@s.whatsapp.net', '')
                clean_phone = ''.join(c for c in clean_phone if c.isdigit())
                
                # Format with country code (add + prefix)
                if len(clean_phone) >= 7:
                    contact_data['phone'] = f"+{clean_phone}"
                else:
                    contact_data['phone'] = ''
            
            # Filter out None/empty values
            contact_data = {k: v for k, v in contact_data.items() if v and str(v).strip()}
            
            logger.debug(f"Extracted contact data for resolution: {contact_data}")
            return contact_data
            
        except Exception as e:
            logger.error(f"Error extracting contact data for resolution: {e}")
            return {}
    
    def _attempt_auto_contact_resolution(self, message: Message):
        """Attempt automatic contact resolution using stored raw webhook data"""
        try:
            if not self.contact_identifier:
                logger.debug("Contact identifier not available for auto-resolution")
                return
            
            # Extract contact data from message using new direct approach
            contact_data = self._extract_contact_data_for_resolution(message)
            
            # Filter out None/empty values
            contact_data = {k: v for k, v in contact_data.items() if v}
            
            if not contact_data:
                logger.debug("No contact data available for auto-resolution")
                return
            
            # Attempt to identify contact
            contact_record = self.contact_identifier.identify_contact(contact_data)
            
            if contact_record:
                # Link the message to the identified contact
                message.contact_record = contact_record
                message.save(update_fields=['contact_record'])
                
                # Update conversation if it doesn't have a primary contact
                if message.conversation and not message.conversation.primary_contact_record:
                    message.conversation.primary_contact_record = contact_record
                    message.conversation.save(update_fields=['primary_contact_record'])
                
                # Update message metadata to reflect successful resolution
                if not message.metadata:
                    message.metadata = {}
                message.metadata['auto_contact_resolved'] = True
                message.metadata['contact_record_id'] = contact_record.id
                message.metadata['resolution_timestamp'] = timezone.now().isoformat()
                message.save(update_fields=['metadata'])
                
                logger.info(f"Auto-resolved message {message.id} to contact record {contact_record.id}")
            else:
                logger.debug(f"No matching contact found for message {message.id}")
                
        except Exception as e:
            logger.warning(f"Error in auto contact resolution for message {message.id}: {e}")

    def _broadcast_message_with_contact_info(self, message, conversation, contact_name: str, attendee_id: str, connection):
        """Broadcast message with enhanced contact info for real-time updates"""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.debug("No channel layer available for broadcasting")
                return
            
            # Enhanced message data for real-time broadcast - match frontend Message interface
            message_data = {
                'type': 'message_update',
                'message': {
                    'id': str(message.id),
                    'type': 'whatsapp',  # Add message type
                    'content': message.content,
                    'direction': message.direction,
                    'contact_email': message.contact_email,
                    'sender': {
                        'name': contact_name or 'Unknown',
                        'email': message.contact_email,
                        'platform_id': attendee_id
                    },
                    'recipient': {
                        'name': 'Business',
                        'email': connection.user.email if hasattr(connection, 'user') else ''
                    },
                    'timestamp': message.created_at.isoformat(),
                    'is_read': False,
                    'is_starred': False,
                    'conversation_id': str(conversation.id),
                    'account_id': connection.unipile_account_id,
                    'external_id': message.external_message_id,
                    'metadata': {
                        'contact_name': contact_name,
                        'sender_attendee_id': attendee_id,
                        'chat_id': conversation.external_thread_id,
                        'from': message.contact_email,
                        'to': connection.user.email if hasattr(connection, 'user') else '',
                        'is_sender': 0 if message.direction == 'inbound' else 1,
                        'profile_picture': message.metadata.get('profile_picture', ''),
                        'seen': False,
                        'delivery_status': message.status
                    },
                    'channel': {
                        'name': conversation.channel.name,
                        'channel_type': 'whatsapp'
                    },
                    'attachments': message.metadata.get('attachments', []) if message.metadata.get('has_attachments', False) else []
                }
            }
            
            # Broadcast to conversation room for instant updates (using generic consumer naming)
            room_name = f"conversation_{conversation.id}"
            async_to_sync(channel_layer.group_send)(room_name, message_data)
            
            # Broadcast to channel overview for conversation list updates (using generic consumer naming)
            inbox_room = f"channel_{conversation.channel.id}"
            async_to_sync(channel_layer.group_send)(inbox_room, {
                'type': 'new_conversation',
                'conversation': {
                    'id': str(conversation.id),
                    'last_message': message_data['message'],
                    'contact_name': contact_name,
                    # For unread count: delivered messages that haven't been marked as read
                    'unread_count': conversation.messages.filter(
                        direction='inbound', 
                        status__in=['delivered', 'sent']  # Count delivered and sent inbound messages as unread
                    ).exclude(status='read').count(),
                    'type': 'whatsapp',  # Add conversation type
                    'updated_at': timezone.now().isoformat(),  # Add timestamp
                    'created_at': conversation.created_at.isoformat() if hasattr(conversation, 'created_at') else timezone.now().isoformat(),
                    # Add minimal participants array for frontend compatibility (optional since we made it optional)
                    'participants': [{
                        'name': contact_name or 'Unknown Contact',
                        'email': message.contact_email,
                        'platform': 'whatsapp'
                    }] if contact_name and message.contact_email else []
                }
            })
            
            logger.info(f"Broadcasted real-time WhatsApp message to rooms: {room_name}, {inbox_room}")
            
        except ImportError as e:
            logger.warning(f"Could not import channels for broadcasting: {e}")
        except Exception as e:
            logger.warning(f"Failed to broadcast real-time message: {e}")


# Global handler instance
webhook_handler = UnipileWebhookHandler()