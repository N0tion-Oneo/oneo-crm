"""
Serializers for record-centric communication API
"""
from rest_framework import serializers
from django.utils import timezone

from pipelines.models import Record
from communications.models import (
    Conversation, Message, Participant, MessageDirection
)
from communications.serializers import (
    ConversationListSerializer, MessageSerializer
)
from .models import (
    RecordCommunicationProfile, RecordCommunicationLink, RecordSyncJob,
    RecordAttendeeMapping
)


class RecordIdentifiersSerializer(serializers.Serializer):
    """Serializer for record communication identifiers"""
    email = serializers.ListField(child=serializers.EmailField(), required=False)
    phone = serializers.ListField(child=serializers.CharField(), required=False)
    linkedin = serializers.ListField(child=serializers.CharField(), required=False)
    domain = serializers.ListField(child=serializers.CharField(), required=False)
    other = serializers.ListField(child=serializers.CharField(), required=False)


class RecordCommunicationProfileSerializer(serializers.ModelSerializer):
    """Serializer for record communication profile"""
    communication_identifiers = RecordIdentifiersSerializer(read_only=True)
    
    class Meta:
        model = RecordCommunicationProfile
        fields = [
            'id', 'record', 'pipeline', 'communication_identifiers',
            'identifier_fields', 'sync_status', 'last_full_sync',
            'sync_in_progress', 'total_conversations', 'total_messages',
            'total_unread', 'last_message_at', 'auto_sync_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'record', 'pipeline', 'sync_in_progress',
            'total_conversations', 'total_messages', 'total_unread',
            'last_message_at', 'created_at', 'updated_at'
        ]


class ParticipantSerializer(serializers.ModelSerializer):
    """Serializer for communication participant"""
    display_name = serializers.SerializerMethodField()
    has_contact = serializers.SerializerMethodField()
    
    class Meta:
        model = Participant
        fields = [
            'id', 'name', 'display_name', 'email', 'phone',
            'avatar_url', 'has_contact', 'contact_record',
            'resolution_confidence', 'resolution_method'
        ]
    
    def get_display_name(self, obj):
        return obj.get_display_name()
    
    def get_has_contact(self, obj):
        return obj.contact_record is not None


class RecordConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations linked to a record"""
    channel_name = serializers.SerializerMethodField()
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)
    account_name = serializers.CharField(source='channel.name', read_only=True)  # Keep original account name too
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'subject', 'channel_name', 'channel_type', 'account_name',
            'participants', 'last_message', 'last_message_at',
            'message_count', 'unread_count', 'status', 'priority',
            'created_at', 'updated_at'
        ]
    
    def get_channel_name(self, obj):
        """Get the user's name for the channel instead of account name"""
        if obj.channel and obj.channel.unipile_account_id:
            from communications.models import UserChannelConnection
            connection = UserChannelConnection.objects.filter(
                unipile_account_id=obj.channel.unipile_account_id
            ).select_related('user').first()
            
            if connection and connection.user:
                user_name = connection.user.get_full_name() or connection.user.username
                # Include channel type for clarity
                return f"{user_name} ({obj.channel.channel_type.title()})"
        
        # Fallback to channel name
        return obj.channel.name if obj.channel else 'Unknown'
    
    def get_participants(self, obj):
        # Get participants for this conversation, excluding the account owner
        participants = Participant.objects.filter(
            conversation_memberships__conversation=obj
        ).distinct()
        
        # Filter out the account owner (user who owns the channel)
        if obj.channel and obj.channel.unipile_account_id:
            from communications.models import UserChannelConnection
            connection = UserChannelConnection.objects.filter(
                unipile_account_id=obj.channel.unipile_account_id
            ).select_related('user').first()
            
            if connection:
                # Exclude by email if available
                if connection.user and connection.user.email:
                    participants = participants.exclude(email=connection.user.email)
                
                # Exclude by user's actual name
                if connection.user:
                    owner_name = connection.user.get_full_name() or connection.user.username
                    if owner_name:
                        participants = participants.exclude(name=owner_name)
                
                # For LinkedIn and other platforms that use account_name as participant name
                if connection.account_name:
                    participants = participants.exclude(name=connection.account_name)
                
                # Also exclude the channel name itself (some platforms use this)
                if obj.channel.name:
                    participants = participants.exclude(name=obj.channel.name)
        
        return ParticipantSerializer(participants, many=True).data
    
    def get_last_message(self, obj):
        # Get the last message in this conversation
        last_message = Message.objects.filter(
            conversation=obj
        ).order_by('-created_at').first()
        
        if last_message:
            return {
                'id': str(last_message.id),
                'content': last_message.content[:100],  # Preview only
                'direction': last_message.direction,
                'sent_at': last_message.sent_at,
                'sender_name': last_message.sender_participant.get_display_name() if last_message.sender_participant else 'Unknown'
            }
        return None


class RecordMessageSerializer(serializers.ModelSerializer):
    """Serializer for messages in record timeline"""
    sender = ParticipantSerializer(source='sender_participant', read_only=True)
    conversation_subject = serializers.CharField(source='conversation.subject', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    html_content = serializers.SerializerMethodField()
    sender_name = serializers.SerializerMethodField()
    sender_email = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    metadata = serializers.JSONField(read_only=True)
    conversation_id = serializers.CharField(source='conversation.id', read_only=True)
    attachments = serializers.SerializerMethodField()
    
    def get_attachments(self, obj):
        """Extract attachments from metadata and format for frontend"""
        if obj.metadata and isinstance(obj.metadata, dict):
            attachments_data = obj.metadata.get('attachments', [])
            if attachments_data:
                # Format attachments for frontend
                formatted_attachments = []
                
                # Try to get the record ID for the download URL
                try:
                    from communications.record_communications.models import RecordCommunicationLink
                    link = RecordCommunicationLink.objects.filter(
                        conversation_id=obj.conversation_id
                    ).first()
                    record_id = link.record_id if link else None
                except:
                    record_id = None
                
                for att in attachments_data:
                    # Get the attachment ID - could be 'id', 'attachment_id', or generate one
                    attachment_id = att.get('id') or att.get('attachment_id') or f"att_{obj.id}_{len(formatted_attachments)}"
                    
                    # Check if attachment is pending (sent but webhook hasn't updated yet)
                    is_pending = att.get('pending', False)
                    
                    formatted_attachment = {
                        'id': attachment_id,
                        'filename': att.get('filename', 'attachment'),
                        'size': att.get('size', 0),
                        'mime_type': att.get('content_type', att.get('mime_type', 'application/octet-stream')),
                        'pending': is_pending
                    }
                    
                    # Only add download URL if we have a record_id and attachment is not pending
                    if record_id and not is_pending:
                        # Get the current request from serializer context
                        request = self.context.get('request')
                        if request:
                            # Build full URL using the request's host
                            host = request.get_host()
                            scheme = 'https' if request.is_secure() else 'http'
                            formatted_attachment['url'] = f"{scheme}://{host}/api/v1/communications/records/{record_id}/download-attachment?message_id={obj.id}&attachment_id={attachment_id}"
                        else:
                            # Relative URL as fallback
                            formatted_attachment['url'] = f"/api/v1/communications/records/{record_id}/download-attachment?message_id={obj.id}&attachment_id={attachment_id}"
                    else:
                        formatted_attachment['url'] = None  # No download until webhook updates
                    
                    formatted_attachments.append(formatted_attachment)
                    
                return formatted_attachments
        return []
    
    def get_html_content(self, obj):
        """Extract HTML content from metadata if available"""
        if obj.metadata and isinstance(obj.metadata, dict):
            return obj.metadata.get('html_content', '')
        return ''
    
    def get_sender_name(self, obj):
        """Get sender name based on message data"""
        # First priority: Check metadata for enriched names
        if obj.metadata and isinstance(obj.metadata, dict):
            # For outbound messages, use the user's name
            if obj.direction == 'outbound' and obj.metadata.get('account_owner_name'):
                return obj.metadata['account_owner_name']
            # For inbound messages, use contact name if available
            elif obj.direction == 'inbound' and obj.metadata.get('contact_name'):
                return obj.metadata['contact_name']
        
        # Second try: Use sender_participant if available and metadata didn't have names
        if obj.sender_participant:
            display_name = obj.sender_participant.get_display_name()
            # Don't return phone-number-like names for outbound messages if we can get better
            if obj.direction == 'outbound' and display_name and 'WhatsApp' in display_name:
                # Skip this and try other methods
                pass
            else:
                return display_name
            
            # Try 'from' field for emails
            from_data = obj.metadata.get('from')
            if isinstance(from_data, dict):
                name = from_data.get('name', '') or from_data.get('email', '')
                if name:
                    return name
            
            # Try sender_name field
            sender_name = obj.metadata.get('sender_name')
            if sender_name:
                return sender_name
        
        # For outbound messages, try to get the account owner's name using helper
        if obj.direction == 'outbound':
            from communications.utils.account_utils import get_account_owner_name
            if obj.channel:
                account_name = get_account_owner_name(channel=obj.channel)
                if account_name and account_name != 'Unknown Account':
                    return account_name
            
            # Try channel name as fallback
            if obj.channel and obj.channel.name:
                return obj.channel.name
        
        return 'Unknown'
    
    def get_sender_email(self, obj):
        """Get sender email if available"""
        if obj.sender_participant:
            return obj.sender_participant.email
        elif obj.metadata and isinstance(obj.metadata, dict):
            from_data = obj.metadata.get('from')
            if isinstance(from_data, dict):
                return from_data.get('email', '')
        return ''
    
    def get_contact_name(self, obj):
        """Get recipient name based on message direction and available data"""
        # First try: Check metadata for enriched contact names
        if obj.metadata and isinstance(obj.metadata, dict):
            # For inbound messages, the recipient is the user
            if obj.direction == 'inbound' and obj.metadata.get('recipient_user_name'):
                return obj.metadata['recipient_user_name']
            # For outbound messages, the recipient is the contact
            elif obj.direction == 'outbound' and obj.metadata.get('contact_name'):
                return obj.metadata['contact_name']
            
            # For emails, get from 'to' field
            to_data = obj.metadata.get('to')
            if isinstance(to_data, list) and to_data:
                first_recipient = to_data[0]
                if isinstance(first_recipient, dict):
                    name = first_recipient.get('name', '') or first_recipient.get('email', '')
                    if name:
                        return name
            # For messaging platforms, check the 'to' field directly
            elif isinstance(to_data, str) and to_data:
                return to_data
        
        # Second try: Get other participants from the conversation
        if obj.conversation:
            try:
                from communications.models import ConversationParticipant
                # For outbound: get recipients (exclude sender)
                # For inbound: get the account owner (the recipient)
                if obj.direction == 'outbound':
                    # Get participants that are not the sender
                    participant = ConversationParticipant.objects.filter(
                        conversation=obj.conversation
                    ).exclude(
                        participant=obj.sender_participant
                    ).select_related('participant').first()
                    
                    if participant and participant.participant:
                        return participant.participant.get_display_name()
                else:
                    # For inbound, try to find the account owner
                    # This would typically be marked with a specific role
                    participants = ConversationParticipant.objects.filter(
                        conversation=obj.conversation,
                        role__in=['recipient', 'member']
                    ).exclude(
                        participant=obj.sender_participant
                    ).select_related('participant')
                    
                    for p in participants:
                        if p.participant:
                            # Check if this might be the account owner
                            # (You might need additional logic here to identify the account owner)
                            return p.participant.get_display_name()
            except:
                pass
        
        # Third try: Use contact_email if available
        if hasattr(obj, 'contact_email') and obj.contact_email:
            return obj.contact_email
        
        # For inbound messages, try to get the account owner's name
        if obj.direction == 'inbound' and obj.channel:
            # Try to find the UserChannelConnection to get the actual user's name
            if obj.channel.unipile_account_id:
                try:
                    from communications.models import UserChannelConnection
                    user_connection = UserChannelConnection.objects.filter(
                        unipile_account_id=obj.channel.unipile_account_id
                    ).select_related('user').first()
                    
                    if user_connection and user_connection.user:
                        # Return the user's actual name, not the account name
                        return user_connection.user.get_full_name() or user_connection.user.username
                except:
                    pass
            
            # Fallback to channel name
            if obj.channel.name:
                return obj.channel.name
        
        return 'Unknown'
    
    class Meta:
        model = Message
        fields = [
            'id', 'content', 'subject', 'direction', 'sender',
            'conversation_subject', 'channel_type', 'channel_name',
            'sent_at', 'received_at', 'status',
            'contact_email', 'contact_phone', 'contact_name',
            'created_at', 'html_content', 'sender_name', 'sender_email',
            'metadata', 'conversation_id', 'attachments'
        ]


class RecordCommunicationLinkSerializer(serializers.ModelSerializer):
    """Serializer for record-conversation links"""
    conversation = RecordConversationSerializer(read_only=True)
    
    class Meta:
        model = RecordCommunicationLink
        fields = [
            'id', 'conversation', 'participant', 'match_type',
            'match_identifier', 'confidence_score', 'created_at',
            'is_primary'
        ]


class RecordSyncJobSerializer(serializers.ModelSerializer):
    """Serializer for sync job status"""
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = RecordSyncJob
        fields = [
            'id', 'job_type', 'status', 'progress_percentage',
            'current_step', 'total_accounts_to_sync', 'accounts_synced',
            'messages_found', 'conversations_found', 'new_links_created',
            'error_message', 'started_at', 'completed_at', 'duration',
            'created_at', 'triggered_by', 'trigger_reason'
        ]
    
    def get_duration(self, obj):
        if obj.started_at and obj.completed_at:
            delta = obj.completed_at - obj.started_at
            return delta.total_seconds()
        return None


class RecordCommunicationStatsSerializer(serializers.Serializer):
    """Serializer for record communication statistics"""
    total_conversations = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    total_unread = serializers.IntegerField()
    last_activity = serializers.DateTimeField()
    channels = serializers.ListField(child=serializers.CharField())
    participants_count = serializers.IntegerField()
    
    # Breakdown by channel
    channel_breakdown = serializers.DictField(
        child=serializers.DictField(),
        required=False
    )
    
    # Activity over time
    activity_timeline = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class SyncTriggerSerializer(serializers.Serializer):
    """Serializer for triggering sync"""
    force = serializers.BooleanField(
        default=False,
        help_text="Force sync even if recently synced"
    )
    channels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Specific channels to sync (email, whatsapp, etc.)"
    )


class QuickReplySerializer(serializers.Serializer):
    """Serializer for quick reply to record"""
    conversation_id = serializers.UUIDField(
        required=False,
        help_text="Reply to existing conversation"
    )
    channel_type = serializers.CharField(
        help_text="Channel to use (email, whatsapp, etc.)"
    )
    content = serializers.CharField(
        help_text="Message content"
    )
    subject = serializers.CharField(
        required=False,
        help_text="Subject for email"
    )
    to = serializers.CharField(
        required=False,
        help_text="Recipient identifier (email/phone) if starting new conversation"
    )


class RecordAttendeeMappingSerializer(serializers.ModelSerializer):
    """Serializer for record attendee mappings"""
    
    class Meta:
        model = RecordAttendeeMapping
        fields = [
            'id', 'record', 'profile', 'attendee_id', 'provider_id',
            'channel_type', 'matched_identifier', 'identifier_type',
            'attendee_name', 'attendee_data', 'discovered_at', 'last_verified'
        ]
        read_only_fields = [
            'id', 'discovered_at', 'last_verified'
        ]