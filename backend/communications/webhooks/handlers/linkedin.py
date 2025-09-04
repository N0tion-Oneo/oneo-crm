"""
LinkedIn-specific webhook handler
"""
import logging
from typing import Dict, Any, Optional
from .base import BaseWebhookHandler
from communications.record_communications.storage.participant_link_manager import ParticipantLinkManager

logger = logging.getLogger(__name__)


class LinkedInWebhookHandler(BaseWebhookHandler):
    """Specialized handler for LinkedIn webhook events via UniPile"""
    
    def __init__(self):
        super().__init__('linkedin')
        self.link_manager = ParticipantLinkManager()
    
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
            from communications.models import (
                Channel, Conversation, Message, MessageStatus, MessageDirection,
                Participant, ConversationParticipant
            )
            from communications.utils.message_direction import determine_message_direction
            from django.utils import timezone
            from django.db import transaction
            from dateutil import parser
            
            # Get user connection
            connection = account_router.get_user_connection(account_id)
            if not connection:
                return {'success': False, 'error': 'User connection not found'}
            
            # Validate it's a LinkedIn connection
            if connection.channel_type != 'linkedin':
                return {'success': False, 'error': f'Invalid channel type: {connection.channel_type}'}
            
            # Extract message data
            message_content = data.get('message', '')
            message_id = data.get('message_id') or data.get('id')
            chat_id = data.get('chat_id') or data.get('provider_chat_id')
            sender_info = data.get('sender', {})
            
            if not chat_id:
                return {'success': False, 'error': 'Chat ID not found in webhook data'}
            
            # Get or create channel
            channel, _ = Channel.objects.get_or_create(
                unipile_account_id=account_id,
                channel_type='linkedin',
                defaults={
                    'name': f"LinkedIn - {connection.account_name or account_id}",
                    'auth_status': 'authenticated',
                    'is_active': True,
                    'created_by': connection.user
                }
            )
            
            # Get or create conversation
            conversation, created = Conversation.objects.get_or_create(
                channel=channel,
                external_thread_id=chat_id,
                defaults={
                    'subject': 'LinkedIn Conversation',
                    'status': 'active'
                }
            )
            
            # Determine message direction
            webhook_msg_data = {
                **data,
                'sender': sender_info,
                'account_id': account_id,
            }
            msg_direction = determine_message_direction(
                message_data=webhook_msg_data,
                channel_type='linkedin',
                user_identifier=None,
                channel=channel
            )
            
            # Convert string direction to enum
            if msg_direction == 'out':
                direction = MessageDirection.OUTBOUND
                status = MessageStatus.SENT
            else:
                direction = MessageDirection.INBOUND
                status = MessageStatus.DELIVERED
            
            # Parse timestamp
            message_timestamp = timezone.now()
            if 'timestamp' in data:
                try:
                    ts = data['timestamp']
                    if isinstance(ts, str):
                        message_timestamp = parser.parse(ts)
                        if message_timestamp.tzinfo is None:
                            message_timestamp = timezone.make_aware(message_timestamp)
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp: {e}")
            
            # Set timestamps based on direction
            sent_timestamp = message_timestamp if direction == MessageDirection.OUTBOUND else None
            received_timestamp = message_timestamp if direction == MessageDirection.INBOUND else None
            
            # Get or create sender participant
            sender_participant = None
            if sender_info:
                sender_name = sender_info.get('attendee_name', '')
                sender_provider_id = sender_info.get('attendee_provider_id', '')
                
                if sender_provider_id:
                    # Use linkedin_member_urn field for LinkedIn IDs
                    sender_participant, created = Participant.objects.get_or_create(
                        linkedin_member_urn=sender_provider_id,
                        defaults={'name': sender_name}
                    )
                    # Update name if changed
                    if sender_name and sender_participant.name != sender_name:
                        sender_participant.name = sender_name
                        sender_participant.save(update_fields=['name'])
                    
                    # Link participant to record if not already linked
                    if not sender_participant.contact_record and sender_provider_id:
                        try:
                            from communications.record_communications.services import RecordIdentifierExtractor
                            from django.utils import timezone
                            identifier_extractor = RecordIdentifierExtractor()
                            
                            # Find records by LinkedIn URN
                            identifiers = {'linkedin': [sender_provider_id]}
                            matching_records = identifier_extractor.find_records_by_identifiers(identifiers)
                            
                            if matching_records and len(matching_records) == 1:
                                # Use ParticipantLinkManager for consistent linking
                                if self.link_manager.link_participant_to_record(
                                    participant=sender_participant,
                                    record=matching_records[0],
                                    confidence=0.85,
                                    method='linkedin_webhook'
                                ):
                                    logger.info(f"✅ Linked participant {sender_participant.id} to record {matching_records[0].id} via LinkedIn URN")
                        except Exception as e:
                            logger.warning(f"Failed to link participant to record: {e}")
            
            # Extract recipient information from attendees
            attendees = data.get('attendees', [])
            recipient_name = None
            account_owner_name = None
            contact_name = None
            
            # Determine who is the recipient based on direction
            if direction == MessageDirection.OUTBOUND:
                # For outbound, sender is the account owner, recipient is the contact
                account_owner_name = sender_name if sender_name else connection.account_name
                # Find the recipient in attendees (not the sender)
                for attendee in attendees:
                    if attendee.get('attendee_provider_id') != sender_provider_id:
                        contact_name = attendee.get('attendee_name', '')
                        break
            else:
                # For inbound, sender is the contact, recipient is the account owner
                contact_name = sender_name
                account_owner_name = connection.account_name
                # Or extract from attendees
                for attendee in attendees:
                    attendee_id = attendee.get('attendee_provider_id')
                    if attendee_id and attendee_id != sender_provider_id:
                        account_owner_name = attendee.get('attendee_name', connection.account_name)
                        break
            
            # Create message
            with transaction.atomic():
                message = Message.objects.create(
                    channel=channel,
                    conversation=conversation,
                    external_message_id=message_id,
                    content=message_content,
                    direction=direction,
                    status=status,
                    sender_participant=sender_participant,
                    created_at=message_timestamp,
                    sent_at=sent_timestamp,
                    received_at=received_timestamp,
                    metadata={
                        'webhook_data': data,
                        'sender_name': sender_info.get('attendee_name', ''),
                        'sender_id': sender_info.get('attendee_id', ''),
                        'provider': 'linkedin',
                        'account_owner_name': account_owner_name,
                        'contact_name': contact_name,
                        'recipient_user_name': account_owner_name if direction == MessageDirection.INBOUND else None
                    }
                )
                
                # Add sender to conversation if not already there
                if sender_participant:
                    ConversationParticipant.objects.get_or_create(
                        conversation=conversation,
                        participant=sender_participant,
                        defaults={'role': 'sender'}
                    )
                
                # Update conversation's last message timestamp
                conversation.last_message_at = message.created_at
                conversation.save(update_fields=['last_message_at'])
            
            logger.info(f"✅ Created LinkedIn message {message.id} in conversation '{conversation.subject}'")
            
            return {
                'success': True,
                'message_id': str(message.id),
                'conversation_id': str(conversation.id),
                'provider': 'linkedin'
            }
            
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
        
        # Check if this is a LinkedIn webhook by account_type
        if data.get('account_type') == 'LINKEDIN':
            return True
            
        # Check account_info for LinkedIn type
        account_info = data.get('account_info', {})
        if account_info.get('type') == 'LINKEDIN':
            return True
        
        # LinkedIn-specific validations
        linkedin_indicators = ['profile', 'connection', 'linkedin_id', 'profile_url', 
                              'attendee_profile_url', 'attendee_provider_id']
        if any(key in data for key in linkedin_indicators):
            return True
        
        # Check for nested LinkedIn data
        if 'sender' in data and isinstance(data['sender'], dict):
            sender_data = data['sender']
            if any(key in sender_data for key in linkedin_indicators):
                return True
            # Check for LinkedIn profile URL format
            if 'attendee_profile_url' in sender_data and 'linkedin.com' in str(sender_data.get('attendee_profile_url', '')):
                return True
        
        # Check attendees for LinkedIn data
        attendees = data.get('attendees', [])
        for attendee in attendees:
            if isinstance(attendee, dict):
                if any(key in attendee for key in linkedin_indicators):
                    return True
                if 'attendee_profile_url' in attendee and 'linkedin.com' in str(attendee.get('attendee_profile_url', '')):
                    return True
        
        # Account-level events don't need LinkedIn-specific data
        event_type = data.get('event_type', data.get('event', ''))
        if 'account' in event_type or 'connection' in event_type:
            return True
        
        self.logger.error("LinkedIn webhook missing required profile data")
        return False