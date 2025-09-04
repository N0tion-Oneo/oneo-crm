"""
DRF Serializers for Communication System
Focused purely on communication functionality - channels, messages, conversations
"""
from rest_framework import serializers
from .models import (
    Channel, Conversation, Message, Participant,
    CommunicationAnalytics, ChannelType, AuthStatus, MessageDirection
)
from authentication.models import CustomUser
from pipelines.models import Record, Pipeline


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer for communication channels"""
    
    created_by = serializers.StringRelatedField(read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'description', 'channel_type', 'is_active',
            'external_account_id', 'auth_status', 'connection_config',
            'sync_settings', 'created_by', 'created_at', 'updated_at',
            'message_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'auth_status']
    
    def validate_connection_config(self, value):
        """Validate connection configuration"""
        if not value:
            return value
        
        # Basic validation for required fields based on channel type
        channel_type = self.initial_data.get('channel_type')
        
        if channel_type == ChannelType.EMAIL:
            required_fields = ['smtp_server', 'smtp_port', 'username']
        elif channel_type in [ChannelType.LINKEDIN, ChannelType.WHATSAPP]:
            required_fields = ['api_key', 'account_id']
        else:
            return value
        
        missing_fields = [field for field in required_fields if field not in value]
        if missing_fields:
            raise serializers.ValidationError(f"Missing required fields: {missing_fields}")
        
        return value


class ChannelConnectionSerializer(serializers.Serializer):
    """Serializer for testing channel connections"""
    
    channel_id = serializers.UUIDField()
    test_message = serializers.CharField(max_length=500, required=False)


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for conversation list view"""
    
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    contact_name = serializers.SerializerMethodField()
    primary_contact = serializers.SerializerMethodField()
    last_message_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'subject', 'status', 'priority', 'channel_name',
            'contact_name', 'primary_contact', 'message_count', 'last_message_at',
            'created_at', 'updated_at'
        ]
    
    def get_contact_name(self, obj):
        """Get primary contact name"""
        if obj.primary_contact_record and obj.primary_contact_record.data:
            data = obj.primary_contact_record.data
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip()
            
            # Use full name, or company name, or email as fallback
            return full_name or data.get('company_name') or data.get('contact_email') or data.get('email', 'Unknown Contact')
        return 'Unknown'
    
    def get_primary_contact(self, obj):
        """Get primary contact details for frontend integration"""
        if obj.primary_contact_record and obj.primary_contact_record.data:
            data = obj.primary_contact_record.data
            contact_name = self.get_contact_name(obj)
            
            return {
                'id': str(obj.primary_contact_record.id),
                'name': contact_name,
                'email': data.get('email'),
                'pipeline_name': obj.primary_contact_record.pipeline.name if obj.primary_contact_record.pipeline else 'Unknown Pipeline'
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for conversation detail view"""
    
    channel = ChannelSerializer(read_only=True)
    primary_contact = serializers.SerializerMethodField()
    recent_messages = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'subject', 'status', 'priority', 'channel',
            'external_thread_id', 'primary_contact', 'message_count',
            'last_message_at', 'metadata', 'recent_messages',
            'created_at', 'updated_at'
        ]
    
    def get_primary_contact(self, obj):
        """Get primary contact details"""
        if obj.primary_contact_record:
            return {
                'id': str(obj.primary_contact_record.id),
                'data': obj.primary_contact_record.data
            }
        return None
    
    def get_recent_messages(self, obj):
        """Get recent messages in conversation"""
        recent_messages = obj.messages.order_by('-created_at')[:5]
        return MessageSerializer(recent_messages, many=True).data


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages with contact resolution information"""
    
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    contact_name = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    unmatched_contact_data = serializers.SerializerMethodField()
    needs_manual_resolution = serializers.SerializerMethodField()
    needs_domain_review = serializers.SerializerMethodField()
    domain_validated = serializers.SerializerMethodField()
    relationship_context = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'channel', 'channel_name', 'conversation', 'contact_record', 'direction',
            'content', 'subject', 'contact_email', 'contact_name', 'contact_info',
            'status', 'external_message_id', 'sent_at', 'received_at', 'date',
            'metadata', 'created_at', 'updated_at',
            # Contact resolution fields
            'unmatched_contact_data', 'needs_manual_resolution', 'needs_domain_review',
            'domain_validated', 'relationship_context'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_contact_name(self, obj):
        """Get contact name from associated record"""
        if obj.contact_record and obj.contact_record.data:
            data = obj.contact_record.data
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            return f"{first_name} {last_name}".strip() or obj.contact_email
        return obj.contact_email or 'Unknown'
    
    def get_contact_info(self, obj):
        """Get full contact information when resolved"""
        if obj.contact_record:
            return {
                'id': obj.contact_record.id,
                'title': obj.contact_record.title,
                'pipeline_id': obj.contact_record.pipeline.id,
                'pipeline_name': obj.contact_record.pipeline.name,
                'data': obj.contact_record.data
            }
        return None
    
    def get_unmatched_contact_data(self, obj):
        """Get unmatched contact data for manual resolution"""
        return obj.metadata.get('unmatched_contact_data') if obj.metadata else None
    
    def get_needs_manual_resolution(self, obj):
        """Check if message needs manual contact resolution"""
        return obj.metadata.get('needs_manual_resolution', False) if obj.metadata else False
    
    def get_needs_domain_review(self, obj):
        """Check if message needs domain validation review"""
        return obj.metadata.get('needs_domain_review', False) if obj.metadata else False
    
    def get_domain_validated(self, obj):
        """Get domain validation status"""
        return obj.metadata.get('domain_validated', True) if obj.metadata else True
    
    def get_relationship_context(self, obj):
        """Get relationship context for domain validation"""
        if obj.metadata and 'relationship_context' in obj.metadata:
            context = obj.metadata['relationship_context']
            # Return summarized context for API response
            return {
                'domain_validated': context.get('domain_validated', True),
                'validation_status': context.get('validation_status', 'unknown'),
                'message_domain': context.get('message_domain'),
                'pipeline_context': context.get('pipeline_context', [])
            }
        return None
    
    def get_date(self, obj):
        """Get the actual message timestamp from metadata (not the sync time)"""
        # Try to get the actual timestamp from raw_data metadata
        if obj.metadata and 'raw_data' in obj.metadata:
            raw_timestamp = obj.metadata['raw_data'].get('timestamp')
            if raw_timestamp:
                return raw_timestamp
        
        # Fallback: For outbound messages, use sent_at if available
        if obj.direction == 'outbound' and obj.sent_at:
            return obj.sent_at.isoformat()
        # Fallback: For inbound messages, use received_at if available  
        elif obj.direction == 'inbound' and obj.received_at:
            return obj.received_at.isoformat()
        # Final fallback to created_at (sync time)
        else:
            return obj.created_at.isoformat()


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    
    class Meta:
        model = Message
        fields = [
            'channel', 'conversation', 'direction', 'content', 'subject',
            'contact_email', 'contact_record', 'metadata'
        ]
    
    def validate(self, data):
        """Validate message data"""
        if not data.get('content') and not data.get('subject'):
            raise serializers.ValidationError("Message must have content or subject")
        
        if data.get('direction') == MessageDirection.OUTBOUND and not data.get('contact_email'):
            raise serializers.ValidationError("Outbound messages must have contact_email")
        
        return data


class MessageSendSerializer(serializers.Serializer):
    """Serializer for sending messages"""
    
    channel_id = serializers.UUIDField()
    content = serializers.CharField(max_length=10000)
    subject = serializers.CharField(max_length=500, required=False)
    contact_email = serializers.EmailField()
    contact_record_id = serializers.UUIDField(required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class BulkMessageSerializer(serializers.Serializer):
    """Serializer for bulk message sending"""
    
    channel_id = serializers.UUIDField()
    content = serializers.CharField(max_length=10000)
    subject = serializers.CharField(max_length=500, required=False)
    recipients = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=1000
    )
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_recipients(self, value):
        """Validate recipient list"""
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate recipients found")
        return value


class ParticipantSerializer(serializers.ModelSerializer):
    """Base participant serializer with linkage status"""
    
    contact_record_display = serializers.SerializerMethodField()
    is_linked = serializers.SerializerMethodField()
    conversation_count = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()
    primary_identifier = serializers.SerializerMethodField()
    channel_types = serializers.SerializerMethodField()
    
    class Meta:
        model = Participant
        fields = [
            'id', 'name', 'email', 'phone', 'linkedin_member_urn',
            'instagram_username', 'facebook_id', 'telegram_id', 'twitter_handle',
            'avatar_url', 'contact_record', 'contact_record_display',
            'secondary_record', 'is_linked', 'conversation_count',
            'last_activity', 'primary_identifier', 'channel_types',
            'resolution_confidence', 'resolution_method', 'resolved_at',
            'first_seen', 'last_seen'
        ]
        read_only_fields = ['id', 'first_seen', 'last_seen']
    
    def get_contact_record_display(self, obj):
        """Get display info for linked record"""
        if obj.contact_record:
            record = obj.contact_record
            data = record.data or {}
            
            # Try to get a display name from common fields
            display_name = (
                data.get('full_name') or 
                data.get('name') or
                f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or
                data.get('company_name') or
                data.get('email') or
                'Unknown'
            )
            
            return {
                'id': str(record.id),
                'display_name': display_name,
                'pipeline_id': str(record.pipeline_id),
                'pipeline_name': record.pipeline.name
            }
        return None
    
    def get_is_linked(self, obj):
        """Check if participant is linked to a record"""
        return obj.contact_record_id is not None or obj.secondary_record_id is not None
    
    def get_conversation_count(self, obj):
        """Get count of conversations this participant is in"""
        return obj.conversation_memberships.count()
    
    def get_last_activity(self, obj):
        """Get timestamp of most recent activity"""
        return obj.last_seen
    
    def get_primary_identifier(self, obj):
        """Get primary identifier for display"""
        return obj.get_primary_identifier()
    
    def get_channel_types(self, obj):
        """Get unique channel types this participant uses"""
        # Get unique channel types from conversations
        from communications.models import ConversationParticipant
        channel_types = set()
        
        participations = ConversationParticipant.objects.filter(
            participant=obj
        ).select_related('conversation__channel')
        
        for participation in participations:
            if participation.conversation.channel:
                channel_types.add(participation.conversation.channel.channel_type)
        
        return list(channel_types)


class ParticipantDetailSerializer(ParticipantSerializer):
    """Detailed participant view with conversations and available pipelines"""
    
    recent_conversations = serializers.SerializerMethodField()
    available_pipelines = serializers.SerializerMethodField()
    linked_record_count = serializers.SerializerMethodField()
    
    class Meta(ParticipantSerializer.Meta):
        fields = ParticipantSerializer.Meta.fields + [
            'recent_conversations', 'available_pipelines', 'linked_record_count',
            'metadata'
        ]
    
    def get_recent_conversations(self, obj):
        """Get recent conversations for this participant"""
        from communications.models import ConversationParticipant
        
        # Get last 10 conversations
        participations = ConversationParticipant.objects.filter(
            participant=obj
        ).select_related('conversation').order_by('-joined_at')[:10]
        
        conversations = [p.conversation for p in participations]
        return ConversationListSerializer(conversations, many=True).data
    
    def get_available_pipelines(self, obj):
        """Get pipelines where records can be created"""
        # Get pipelines user has access to create records in
        pipelines = Pipeline.objects.filter(
            is_active=True
        ).order_by('name')
        
        return [
            {
                'id': str(p.id),
                'name': p.name,
                'slug': p.slug,
                'description': p.description
            }
            for p in pipelines
        ]
    
    def get_linked_record_count(self, obj):
        """Get count of linked records - participant can only have one contact_record"""
        # A participant can only be linked to one record via contact_record field
        return 1 if obj.contact_record else 0


class CreateRecordFromParticipantSerializer(serializers.Serializer):
    """Serializer for creating a record from participant"""
    
    pipeline_id = serializers.UUIDField(required=True)
    field_overrides = serializers.JSONField(required=False, default=dict)
    link_to_conversations = serializers.BooleanField(default=True)
    
    def validate_pipeline_id(self, value):
        """Validate pipeline exists and user has access"""
        try:
            pipeline = Pipeline.objects.get(id=value, is_active=True)
        except Pipeline.DoesNotExist:
            raise serializers.ValidationError("Pipeline not found or inactive")
        return value


class LinkParticipantSerializer(serializers.Serializer):
    """Serializer for linking participant to existing record"""
    
    record_id = serializers.UUIDField(required=True)
    confidence = serializers.FloatField(default=1.0, min_value=0.0, max_value=1.0)
    link_conversations = serializers.BooleanField(default=True)
    
    def validate_record_id(self, value):
        """Validate record exists"""
        try:
            Record.objects.get(id=value)
        except Record.DoesNotExist:
            raise serializers.ValidationError("Record not found")
        return value


class BulkParticipantActionSerializer(serializers.Serializer):
    """Serializer for bulk participant actions"""
    
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    pipeline_id = serializers.UUIDField(required=False)  # For bulk create
    record_id = serializers.UUIDField(required=False)    # For bulk link
    
    def validate(self, attrs):
        """Validate based on action type"""
        if self.context.get('action') == 'create' and not attrs.get('pipeline_id'):
            raise serializers.ValidationError("pipeline_id is required for bulk create")
        if self.context.get('action') == 'link' and not attrs.get('record_id'):
            raise serializers.ValidationError("record_id is required for bulk link")
        return attrs


class CommunicationAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for communication analytics"""
    
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    
    class Meta:
        model = CommunicationAnalytics
        fields = [
            'id', 'date', 'channel', 'channel_name', 
            'messages_sent', 'messages_received', 'active_channels',
            'response_rate', 'engagement_score', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']