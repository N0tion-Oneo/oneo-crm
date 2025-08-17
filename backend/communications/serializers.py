"""
DRF Serializers for Communication System
Focused purely on communication functionality - channels, messages, conversations
"""
from rest_framework import serializers
from .models import (
    Channel, Conversation, Message, 
    CommunicationAnalytics, ChannelType, AuthStatus, MessageDirection
)
from authentication.models import CustomUser
from pipelines.models import Record


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
    """Serializer for messages"""
    
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    contact_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'channel', 'channel_name', 'conversation', 'direction',
            'content', 'subject', 'contact_email', 'contact_name',
            'status', 'external_message_id', 'sent_at', 'received_at',
            'metadata', 'created_at', 'updated_at'
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