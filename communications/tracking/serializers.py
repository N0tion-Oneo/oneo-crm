"""
DRF Serializers for communication tracking system
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from ..models import Channel, Message, Conversation
from .models import (
    CommunicationTracking, DeliveryTracking, ReadTracking,
    ResponseTracking, CampaignTracking, PerformanceMetrics
)

User = get_user_model()


class CommunicationTrackingSerializer(serializers.ModelSerializer):
    """Serializer for communication tracking events"""
    
    message_subject = serializers.CharField(source='message.subject', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    
    class Meta:
        model = CommunicationTracking
        fields = [
            'id', 'message', 'message_subject', 'channel', 'channel_name', 'channel_type',
            'conversation', 'tracking_type', 'status', 'event_timestamp',
            'user_agent', 'ip_address', 'tracking_data', 'response_time_ms',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DeliveryTrackingSerializer(serializers.ModelSerializer):
    """Serializer for delivery tracking"""
    
    message_subject = serializers.CharField(source='message.subject', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    is_delivered = serializers.BooleanField(read_only=True)
    is_failed = serializers.BooleanField(read_only=True)
    delivery_rate_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = DeliveryTracking
        fields = [
            'id', 'message', 'message_subject', 'channel', 'channel_name',
            'attempt_count', 'max_attempts', 'first_attempt_at', 'delivered_at',
            'failed_at', 'last_error_code', 'last_error_message', 'error_history',
            'total_delivery_time_ms', 'external_tracking_id', 'provider_response',
            'is_delivered', 'is_failed', 'delivery_rate_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReadTrackingSerializer(serializers.ModelSerializer):
    """Serializer for read tracking"""
    
    message_subject = serializers.CharField(source='message.subject', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    read_rate_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ReadTracking
        fields = [
            'id', 'message', 'message_subject', 'channel', 'channel_name',
            'first_read_at', 'last_read_at', 'read_count', 'time_to_first_read_minutes',
            'total_read_time_seconds', 'read_devices', 'read_locations',
            'read_receipt_enabled', 'tracking_pixel_loaded',
            'is_read', 'read_rate_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ResponseTrackingSerializer(serializers.ModelSerializer):
    """Serializer for response tracking"""
    
    original_message_subject = serializers.CharField(source='original_message.subject', read_only=True)
    response_message_content = serializers.CharField(source='response_message.content', read_only=True)
    conversation_subject = serializers.CharField(source='conversation.subject', read_only=True)
    
    class Meta:
        model = ResponseTracking
        fields = [
            'id', 'original_message', 'original_message_subject', 'response_message',
            'response_message_content', 'conversation', 'conversation_subject',
            'response_time_minutes', 'response_received_at', 'response_sentiment',
            'response_category', 'response_length', 'contains_question',
            'contains_action_request', 'response_analysis',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CampaignTrackingSerializer(serializers.ModelSerializer):
    """Serializer for campaign tracking"""
    
    channels = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Channel.objects.all()
    )
    channel_names = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = CampaignTracking
        fields = [
            'id', 'name', 'description', 'campaign_type', 'channels', 'channel_names',
            'target_audience', 'status', 'scheduled_start', 'actual_start',
            'scheduled_end', 'actual_end', 'target_send_count', 'target_delivery_rate',
            'target_open_rate', 'target_response_rate', 'created_by', 'created_by_username',
            'is_active', 'duration_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'actual_start', 'actual_end']
    
    def get_channel_names(self, obj):
        """Get list of channel names"""
        return [channel.name for channel in obj.channels.all()]


class PerformanceMetricsSerializer(serializers.ModelSerializer):
    """Serializer for performance metrics"""
    
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    engagement_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    total_engagement_actions = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = PerformanceMetrics
        fields = [
            'id', 'date', 'hour', 'channel', 'channel_name', 'campaign', 'campaign_name',
            'messages_sent', 'messages_delivered', 'messages_failed', 'messages_read',
            'responses_received', 'delivery_rate', 'open_rate', 'response_rate',
            'bounce_rate', 'avg_response_time_minutes', 'avg_read_time_seconds',
            'sentiment_positive_count', 'sentiment_neutral_count', 'sentiment_negative_count',
            'engagement_score', 'total_engagement_actions', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


# === NESTED SERIALIZERS FOR DETAILED VIEWS ===

class MessageDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for messages with tracking info"""
    
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    conversation_subject = serializers.CharField(source='conversation.subject', read_only=True)
    
    # Related tracking data
    delivery_tracking = DeliveryTrackingSerializer(read_only=True)
    read_tracking = ReadTrackingSerializer(read_only=True)
    tracking_events = CommunicationTrackingSerializer(many=True, read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'external_message_id', 'channel', 'channel_name', 'conversation',
            'conversation_subject', 'contact_record', 'direction', 'content', 'subject',
            'contact_email', 'status', 'sent_at', 'received_at', 'metadata',
            'delivery_tracking', 'read_tracking', 'tracking_events',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ChannelPerformanceSerializer(serializers.Serializer):
    """Serializer for channel performance summary"""
    
    channel_id = serializers.UUIDField()
    channel_name = serializers.CharField()
    channel_type = serializers.CharField()
    period_days = serializers.IntegerField()
    total_messages_sent = serializers.IntegerField()
    total_messages_delivered = serializers.IntegerField()
    total_messages_read = serializers.IntegerField()
    total_responses_received = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    open_rate = serializers.FloatField()
    response_rate = serializers.FloatField()
    avg_response_time_minutes = serializers.FloatField()
    engagement_score = serializers.FloatField()


class CampaignPerformanceSerializer(serializers.Serializer):
    """Serializer for campaign performance summary"""
    
    campaign_id = serializers.UUIDField()
    campaign_name = serializers.CharField()
    campaign_type = serializers.CharField()
    status = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField(allow_null=True)
    duration_days = serializers.IntegerField(allow_null=True)
    total_messages_sent = serializers.IntegerField()
    total_messages_delivered = serializers.IntegerField()
    total_messages_read = serializers.IntegerField()
    total_responses_received = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    open_rate = serializers.FloatField()
    response_rate = serializers.FloatField()
    target_delivery_rate = serializers.FloatField()
    target_open_rate = serializers.FloatField()
    target_response_rate = serializers.FloatField()
    delivery_vs_target = serializers.FloatField()
    open_vs_target = serializers.FloatField()
    response_vs_target = serializers.FloatField()


class PerformanceInsightSerializer(serializers.Serializer):
    """Serializer for performance insights"""
    
    metric = serializers.CharField()
    current_value = serializers.FloatField()
    previous_value = serializers.FloatField()
    change_percentage = serializers.FloatField()
    trend = serializers.CharField()
    recommendation = serializers.CharField()


class ChannelComparisonSerializer(serializers.Serializer):
    """Serializer for channel comparison data"""
    
    channel_name = serializers.CharField()
    channel_type = serializers.CharField()
    delivery_rate = serializers.FloatField()
    open_rate = serializers.FloatField()
    response_rate = serializers.FloatField()
    engagement_score = serializers.FloatField()
    total_messages = serializers.IntegerField()
    ranking = serializers.IntegerField()