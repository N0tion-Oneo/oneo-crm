"""
Webhook field update handlers - ensures webhook data properly populates all fields
"""
import logging
from typing import Dict, Any
from django.utils import timezone

from communications.models import (
    UserChannelConnection, Conversation, Message, 
    Participant, ConversationParticipant, TenantUniPileConfig
)
from communications.services.field_manager import field_manager

logger = logging.getLogger(__name__)


class WebhookFieldUpdater:
    """Handles field updates from webhook data"""
    
    def process_auth_webhook(self, connection: UserChannelConnection, webhook_data: Dict[str, Any]):
        """Process authentication webhook and update connection fields"""
        
        # Extract token data
        if 'access_token' in webhook_data:
            field_manager.store_tokens(
                connection,
                access_token=webhook_data['access_token'],
                refresh_token=webhook_data.get('refresh_token'),
                expires_in=webhook_data.get('expires_in', 3600)
            )
        
        # Update account status based on webhook
        status_map = {
            'connected': 'active',
            'disconnected': 'disconnected',
            'expired': 'expired',
            'checkpoint_required': 'checkpoint_required',
            'failed': 'failed'
        }
        
        webhook_status = webhook_data.get('status', '').lower()
        if webhook_status in status_map:
            connection.account_status = status_map[webhook_status]
            connection.save(update_fields=['account_status'])
        
        # Store provider-specific config
        if 'provider_config' in webhook_data:
            connection.provider_config = webhook_data['provider_config']
            connection.save(update_fields=['provider_config'])
        
        # Update sync timestamps
        if connection.account_status == 'active':
            connection.record_sync_success()
        elif webhook_data.get('error'):
            connection.record_sync_failure(webhook_data['error'])
    
    def process_message_webhook(self, webhook_data: Dict[str, Any]):
        """Process message webhook and ensure all fields are populated"""
        
        # Extract message metadata
        message_data = webhook_data.get('message', webhook_data)
        
        # Determine message type and set subject for emails
        if message_data.get('subject'):
            # This is likely an email
            subject = message_data['subject']
        else:
            subject = None
        
        # Extract timestamps
        sent_at = None
        received_at = None
        
        if 'sent_at' in message_data:
            sent_at = timezone.datetime.fromisoformat(message_data['sent_at'])
        
        if 'received_at' in message_data:
            received_at = timezone.datetime.fromisoformat(message_data['received_at'])
        elif message_data.get('direction') == 'inbound':
            received_at = timezone.now()
        
        return {
            'subject': subject,
            'sent_at': sent_at,
            'received_at': received_at,
            'is_local_only': False  # Webhook messages are synced
        }
    
    def process_conversation_webhook(self, conversation: Conversation, webhook_data: Dict[str, Any]):
        """Process conversation webhook data"""
        
        # Extract conversation type hints
        conv_data = webhook_data.get('conversation', webhook_data)
        
        # Detect conversation type from webhook data
        if conv_data.get('type'):
            type_map = {
                'direct': 'direct',
                'group': 'group',
                'broadcast': 'broadcast',
                'channel': 'channel',
                'community': 'channel'
            }
            conv_type = type_map.get(conv_data['type'].lower())
            if conv_type:
                conversation.conversation_type = conv_type
                conversation.save(update_fields=['conversation_type'])
        
        # Update participant count if provided
        if 'participant_count' in conv_data:
            conversation.participant_count = conv_data['participant_count']
            conversation.save(update_fields=['participant_count'])
        
        # Set priority based on metadata
        if conv_data.get('is_urgent') or conv_data.get('priority') == 'high':
            field_manager.set_conversation_priority(conversation, 'high')
        
        # Mark as hot if it's frequently accessed
        if conv_data.get('message_count', 0) > 100:
            field_manager.mark_conversation_hot(conversation, True)
        
        # Update sync status
        field_manager.update_conversation_sync_status(
            conversation, 
            'synced',
            error=conv_data.get('sync_error')
        )
    
    def process_participant_webhook(self, participant: Participant, webhook_data: Dict[str, Any]):
        """Process participant data from webhook"""
        
        participant_data = webhook_data.get('participant', webhook_data)
        
        # Extract social handles
        social_handles = {}
        
        if participant_data.get('instagram'):
            social_handles['instagram'] = participant_data['instagram']
        
        if participant_data.get('facebook'):
            social_handles['facebook'] = participant_data['facebook']
        
        if participant_data.get('telegram'):
            social_handles['telegram'] = participant_data['telegram']
        
        if participant_data.get('twitter'):
            social_handles['twitter'] = participant_data['twitter']
        
        if social_handles:
            field_manager.set_participant_social_handles(participant, **social_handles)
        
        # Update avatar if provided
        if participant_data.get('avatar_url') and not participant.avatar_url:
            participant.avatar_url = participant_data['avatar_url']
            participant.save(update_fields=['avatar_url'])
        
        # Handle contact resolution data
        if participant_data.get('resolved_contact_id'):
            # This would need to fetch the actual Record
            # For now, just log it
            logger.info(f"Participant {participant.id} resolved to contact {participant_data['resolved_contact_id']}")
    
    def process_read_receipt_webhook(self, webhook_data: Dict[str, Any]):
        """Process read receipt webhook"""
        
        conversation_id = webhook_data.get('conversation_id')
        participant_id = webhook_data.get('participant_id')
        
        if conversation_id and participant_id:
            try:
                conv_participant = ConversationParticipant.objects.get(
                    conversation_id=conversation_id,
                    participant_id=participant_id
                )
                field_manager.mark_messages_read(conv_participant)
            except ConversationParticipant.DoesNotExist:
                logger.warning(f"ConversationParticipant not found for read receipt")
    
    def process_typing_indicator_webhook(self, webhook_data: Dict[str, Any]):
        """Process typing indicator webhook"""
        
        conversation_id = webhook_data.get('conversation_id')
        participant_id = webhook_data.get('participant_id')
        is_typing = webhook_data.get('is_typing', False)
        
        if conversation_id and participant_id:
            try:
                conv_participant = ConversationParticipant.objects.get(
                    conversation_id=conversation_id,
                    participant_id=participant_id
                )
                
                # This would need a new field for typing status
                # For now, just update metadata
                conv_participant.metadata['is_typing'] = is_typing
                conv_participant.metadata['typing_started_at'] = (
                    timezone.now().isoformat() if is_typing else None
                )
                conv_participant.save(update_fields=['metadata'])
                
            except ConversationParticipant.DoesNotExist:
                logger.warning(f"ConversationParticipant not found for typing indicator")
    
    def process_participant_left_webhook(self, webhook_data: Dict[str, Any]):
        """Process participant left conversation webhook"""
        
        conversation_id = webhook_data.get('conversation_id')
        participant_id = webhook_data.get('participant_id')
        
        if conversation_id and participant_id:
            try:
                conv_participant = ConversationParticipant.objects.get(
                    conversation_id=conversation_id,
                    participant_id=participant_id
                )
                field_manager.mark_participant_left(conv_participant)
                
                # Update conversation participant count
                conversation = conv_participant.conversation
                field_manager.detect_conversation_type(conversation)
                
            except ConversationParticipant.DoesNotExist:
                logger.warning(f"ConversationParticipant not found for participant left")
    
    def record_webhook_received(self):
        """Record successful webhook reception"""
        try:
            config = TenantUniPileConfig.get_or_create_for_tenant()
            field_manager.update_webhook_status(config, success=True)
        except Exception as e:
            logger.error(f"Failed to record webhook reception: {e}")


# Create singleton instance
webhook_field_updater = WebhookFieldUpdater()