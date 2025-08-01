"""
Communication tracking models for performance analytics and monitoring
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from ..models import Channel, Message, Conversation, MessageDirection, MessageStatus

User = get_user_model()


class TrackingType(models.TextChoices):
    """Types of communication tracking"""
    DELIVERY = 'delivery', 'Delivery Tracking'
    READ = 'read', 'Read Receipt'
    CLICK = 'click', 'Link Click'
    RESPONSE = 'response', 'Response Received' 
    BOUNCE = 'bounce', 'Bounce/Failure'
    UNSUBSCRIBE = 'unsubscribe', 'Unsubscribe'


class TrackingStatus(models.TextChoices):
    """Status of tracking events"""
    PENDING = 'pending', 'Pending'
    TRACKED = 'tracked', 'Successfully Tracked'
    FAILED = 'failed', 'Tracking Failed'
    EXPIRED = 'expired', 'Tracking Expired'


class CampaignStatus(models.TextChoices):
    """Status of communication campaigns"""
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class CommunicationTracking(models.Model):
    """
    Base tracking model for all communication events
    Provides comprehensive tracking across all message types and channels
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core relationships
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='tracking_events')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='tracking_events')
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='tracking_events',
        null=True, blank=True
    )
    
    # Tracking details
    tracking_type = models.CharField(max_length=20, choices=TrackingType.choices)
    status = models.CharField(
        max_length=20, 
        choices=TrackingStatus.choices, 
        default=TrackingStatus.PENDING
    )
    
    # Event data
    event_timestamp = models.DateTimeField(default=timezone.now)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Tracking metadata
    tracking_data = models.JSONField(
        default=dict,
        help_text="Additional tracking data (click URLs, device info, etc.)"
    )
    
    # Performance data
    response_time_ms = models.IntegerField(
        null=True, blank=True,
        help_text="Response time in milliseconds for delivery events"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['message', 'tracking_type']),
            models.Index(fields=['channel', 'event_timestamp']),
            models.Index(fields=['tracking_type', 'status']),
            models.Index(fields=['event_timestamp']),
            models.Index(fields=['conversation', 'tracking_type']),
        ]
        
    def __str__(self):
        return f"{self.get_tracking_type_display()} - {self.message}"


class DeliveryTracking(models.Model):
    """
    Specialized tracking for message delivery performance
    Tracks delivery attempts, failures, and success rates
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core relationships
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='delivery_tracking')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='delivery_trackings')
    
    # Delivery attempts
    attempt_count = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    # Delivery status
    first_attempt_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    last_error_code = models.CharField(max_length=50, blank=True)
    last_error_message = models.TextField(blank=True)
    error_history = models.JSONField(
        default=list,
        help_text="History of delivery errors and attempts"
    )
    
    # Performance metrics
    total_delivery_time_ms = models.IntegerField(
        null=True, blank=True,
        help_text="Total time from send to delivery in milliseconds"
    )
    
    # External tracking
    external_tracking_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(
        default=dict,
        help_text="Response from external delivery provider (UniPile, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['channel', 'delivered_at']),
            models.Index(fields=['failed_at']),
            models.Index(fields=['attempt_count']),
            models.Index(fields=['external_tracking_id']),
        ]
        
    def __str__(self):
        return f"Delivery tracking for {self.message}"
    
    @property
    def is_delivered(self) -> bool:
        """Check if message was successfully delivered"""
        return self.delivered_at is not None
    
    @property
    def is_failed(self) -> bool:
        """Check if delivery permanently failed"""
        return self.failed_at is not None or self.attempt_count >= self.max_attempts
    
    @property
    def delivery_rate_percentage(self) -> float:
        """Calculate delivery success rate"""
        if self.attempt_count == 0:
            return 0.0
        return (1.0 if self.is_delivered else 0.0) * 100


class ReadTracking(models.Model):
    """
    Tracks message read receipts and engagement
    Monitors when messages are opened and read by recipients
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core relationships
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='read_tracking')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='read_trackings')
    
    # Read tracking
    first_read_at = models.DateTimeField(null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    read_count = models.IntegerField(default=0)
    
    # Engagement metrics
    time_to_first_read_minutes = models.IntegerField(
        null=True, blank=True,
        help_text="Minutes from delivery to first read"
    )
    total_read_time_seconds = models.IntegerField(
        null=True, blank=True,
        help_text="Total time spent reading message"
    )
    
    # Device and location tracking
    read_devices = models.JSONField(
        default=list,
        help_text="List of devices used to read the message"
    )
    read_locations = models.JSONField(
        default=list,
        help_text="Geographic locations where message was read"
    )
    
    # Read receipt details
    read_receipt_enabled = models.BooleanField(default=True)
    tracking_pixel_loaded = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['channel', 'first_read_at']),
            models.Index(fields=['first_read_at']),
            models.Index(fields=['read_count']),
        ]
        
    def __str__(self):
        return f"Read tracking for {self.message}"
    
    @property
    def is_read(self) -> bool:
        """Check if message has been read"""
        return self.first_read_at is not None
    
    @property
    def read_rate_percentage(self) -> float:
        """Calculate read rate (0 or 100 for individual messages)"""
        return 100.0 if self.is_read else 0.0


class ResponseTracking(models.Model):
    """
    Tracks responses to outbound messages
    Monitors conversation engagement and response patterns
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core relationships
    original_message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='response_trackings',
        help_text="The original outbound message"
    )
    response_message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='responses_to',
        help_text="The inbound response message"
    )
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='response_trackings')
    
    # Response timing
    response_time_minutes = models.IntegerField(
        help_text="Minutes from original message to response"
    )
    response_received_at = models.DateTimeField()
    
    # Response analysis
    response_sentiment = models.CharField(
        max_length=20,
        choices=[
            ('positive', 'Positive'),
            ('neutral', 'Neutral'),
            ('negative', 'Negative'),
            ('unknown', 'Unknown')
        ],
        default='unknown'
    )
    response_category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Categorization of response type (question, complaint, etc.)"
    )
    
    # Response metrics
    response_length = models.IntegerField(
        help_text="Character length of response"
    )
    contains_question = models.BooleanField(default=False)
    contains_action_request = models.BooleanField(default=False)
    
    # Additional analysis
    response_analysis = models.JSONField(
        default=dict,
        help_text="AI analysis of response content and intent"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['original_message', 'response_received_at']),
            models.Index(fields=['conversation', 'response_received_at']),
            models.Index(fields=['response_time_minutes']),
            models.Index(fields=['response_sentiment']),
        ]
        unique_together = ['original_message', 'response_message']
        
    def __str__(self):
        return f"Response to {self.original_message} in {self.response_time_minutes}min"


class CampaignTracking(models.Model):
    """
    Tracks communication campaigns and bulk message performance
    Provides aggregated analytics for marketing campaigns
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Campaign details
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    campaign_type = models.CharField(
        max_length=50,
        choices=[
            ('email_blast', 'Email Blast'),
            ('drip_campaign', 'Drip Campaign'),
            ('follow_up', 'Follow-up Sequence'),
            ('newsletter', 'Newsletter'),
            ('promotional', 'Promotional'),
            ('transactional', 'Transactional'),
            ('other', 'Other')
        ]
    )
    
    # Campaign configuration
    channels = models.ManyToManyField(Channel, related_name='campaigns')
    target_audience = models.JSONField(
        default=dict,
        help_text="Audience targeting criteria and filters"
    )
    
    # Campaign status
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT
    )
    
    # Campaign timeline
    scheduled_start = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    # Performance targets
    target_send_count = models.IntegerField(default=0)
    target_delivery_rate = models.DecimalField(
        max_digits=5, decimal_places=2, 
        default=Decimal('95.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    target_open_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('25.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    target_response_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('5.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Campaign ownership
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'actual_start']),
            models.Index(fields=['campaign_type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['scheduled_start']),
        ]
        
    def __str__(self):
        return f"Campaign: {self.name}"
    
    @property
    def is_active(self) -> bool:
        """Check if campaign is currently active"""
        return self.status == CampaignStatus.ACTIVE
    
    @property
    def duration_days(self) -> Optional[int]:
        """Calculate campaign duration in days"""
        if self.actual_start and self.actual_end:
            return (self.actual_end - self.actual_start).days
        return None


class PerformanceMetrics(models.Model):
    """
    Aggregated performance metrics for channels, campaigns, and time periods
    Provides real-time analytics and reporting data
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Metrics scope
    date = models.DateField()
    hour = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        help_text="Hour for hourly metrics (0-23), null for daily metrics"
    )
    
    # Scope filters
    channel = models.ForeignKey(
        Channel, 
        on_delete=models.CASCADE, 
        related_name='performance_metrics',
        null=True, blank=True,
        help_text="Specific channel, null for all channels"
    )
    campaign = models.ForeignKey(
        CampaignTracking,
        on_delete=models.CASCADE,
        related_name='performance_metrics', 
        null=True, blank=True,
        help_text="Specific campaign, null for all campaigns"
    )
    
    # Volume metrics
    messages_sent = models.IntegerField(default=0)
    messages_delivered = models.IntegerField(default=0)
    messages_failed = models.IntegerField(default=0)
    messages_read = models.IntegerField(default=0)
    responses_received = models.IntegerField(default=0)
    
    # Performance rates (as percentages)
    delivery_rate = models.DecimalField(
        max_digits=5, decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    open_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    response_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    bounce_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Engagement metrics
    avg_response_time_minutes = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True,
        help_text="Average response time in minutes"
    )
    avg_read_time_seconds = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True,
        help_text="Average time spent reading messages"
    )
    
    # Quality metrics
    sentiment_positive_count = models.IntegerField(default=0)
    sentiment_neutral_count = models.IntegerField(default=0)
    sentiment_negative_count = models.IntegerField(default=0)
    
    # Additional metrics
    metadata = models.JSONField(
        default=dict,
        help_text="Additional custom metrics and breakdowns"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['date', 'hour', 'channel']),
            models.Index(fields=['date', 'campaign']),
            models.Index(fields=['channel', 'date']),
            models.Index(fields=['delivery_rate']),
            models.Index(fields=['response_rate']),
        ]
        unique_together = [
            ['date', 'hour', 'channel', 'campaign'],  # Unique metrics per scope
        ]
        
    def __str__(self):
        scope_parts = []
        if self.channel:
            scope_parts.append(f"Channel: {self.channel.name}")
        if self.campaign:
            scope_parts.append(f"Campaign: {self.campaign.name}")
        
        scope = " | ".join(scope_parts) if scope_parts else "All channels"
        time_scope = f"{self.date} {self.hour:02d}:00" if self.hour is not None else str(self.date)
        
        return f"Metrics {time_scope} - {scope}"
    
    @property
    def engagement_score(self) -> Decimal:
        """Calculate overall engagement score (0-100)"""
        if self.messages_sent == 0:
            return Decimal('0.00')
        
        # Weighted score based on delivery, open, and response rates
        score = (
            (self.delivery_rate * Decimal('0.3')) +
            (self.open_rate * Decimal('0.4')) + 
            (self.response_rate * Decimal('0.3'))
        )
        return min(score, Decimal('100.00'))
    
    @property
    def total_engagement_actions(self) -> int:
        """Total number of engagement actions"""
        return self.messages_read + self.responses_received