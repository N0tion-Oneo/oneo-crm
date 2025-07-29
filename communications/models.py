"""
Communication models - omni-channel messaging with UniPile integration
Focused purely on communication functionality: channels, messages, conversations
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone as django_timezone

# Tenant isolation is handled by django-tenants at the schema level

User = get_user_model()


class ChannelType(models.TextChoices):
    """Available communication channel types"""
    EMAIL = 'email', 'Email'
    WHATSAPP = 'whatsapp', 'WhatsApp'
    LINKEDIN = 'linkedin', 'LinkedIn'
    SMS = 'sms', 'SMS'
    SLACK = 'slack', 'Slack'
    TELEGRAM = 'telegram', 'Telegram'
    DISCORD = 'discord', 'Discord'


class AuthStatus(models.TextChoices):
    """Authentication status for channels"""
    PENDING = 'pending', 'Pending'
    AUTHENTICATED = 'authenticated', 'Authenticated'
    FAILED = 'failed', 'Failed'
    EXPIRED = 'expired', 'Expired'


class ConversationStatus(models.TextChoices):
    """Status of conversations"""
    ACTIVE = 'active', 'Active'
    ARCHIVED = 'archived', 'Archived'
    SPAM = 'spam', 'Spam'
    DELETED = 'deleted', 'Deleted'


class Priority(models.TextChoices):
    """Priority levels for conversations"""
    LOW = 'low', 'Low'
    NORMAL = 'normal', 'Normal'
    HIGH = 'high', 'High'
    URGENT = 'urgent', 'Urgent'


class MessageDirection(models.TextChoices):
    """Direction of messages"""
    INBOUND = 'inbound', 'Inbound'
    OUTBOUND = 'outbound', 'Outbound'


class MessageStatus(models.TextChoices):
    """Status of messages"""
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    DELIVERED = 'delivered', 'Delivered'
    READ = 'read', 'Read'
    FAILED = 'failed', 'Failed'


class UserChannelConnection(models.Model):
    """
    Manages individual user connections to external communication channels
    Each user can have their own authenticated accounts across different channels
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='channel_connections')
    
    # Channel identification
    channel_type = models.CharField(max_length=20, choices=ChannelType.choices)
    external_account_id = models.CharField(max_length=255, help_text="UniPile account ID")
    account_name = models.CharField(max_length=255, help_text="Display name for the account")
    
    # Authentication details
    auth_status = models.CharField(
        max_length=20, 
        choices=AuthStatus.choices, 
        default=AuthStatus.PENDING
    )
    access_token = models.TextField(blank=True, help_text="Encrypted access token")
    refresh_token = models.TextField(blank=True, help_text="Encrypted refresh token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Connection configuration
    connection_config = models.JSONField(
        default=dict,
        help_text="Channel-specific configuration (API keys, webhooks, etc.)"
    )
    
    # Status and metadata
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_error_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'channel_type', 'external_account_id']
        indexes = [
            models.Index(fields=['user', 'channel_type']),
            models.Index(fields=['auth_status', 'is_active']),
            models.Index(fields=['last_sync_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_channel_type_display()} ({self.account_name})"
    
    def is_token_expired(self) -> bool:
        """Check if the access token is expired"""
        if not self.token_expires_at:
            return False
        return django_timezone.now() >= self.token_expires_at
    
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (expires within 1 hour)"""
        if not self.token_expires_at:
            return False
        return django_timezone.now() >= (self.token_expires_at - timezone.timedelta(hours=1))


class Channel(models.Model):
    """
    Communication channels for tenant-wide messaging
    Represents organizational-level communication channels
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    channel_type = models.CharField(max_length=20, choices=ChannelType.choices)
    
    # External integration
    external_account_id = models.CharField(
        max_length=255, 
        help_text="UniPile account ID for this channel"
    )
    auth_status = models.CharField(
        max_length=20, 
        choices=AuthStatus.choices, 
        default=AuthStatus.PENDING
    )
    
    # Configuration
    connection_config = models.JSONField(
        default=dict,
        help_text="Channel-specific configuration and settings"
    )
    sync_settings = models.JSONField(
        default=dict,
        help_text="Message sync preferences and filters"
    )
    
    # Status and permissions
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Statistics (updated by background tasks)
    message_count = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['channel_type', 'is_active']),
            models.Index(fields=['auth_status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['last_message_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class Conversation(models.Model):
    """
    Conversation threads that can span multiple messages
    Groups related messages together with metadata
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Thread identification
    external_thread_id = models.CharField(
        max_length=255, 
        blank=True,
        help_text="External platform's conversation/thread ID"
    )
    subject = models.CharField(max_length=500, blank=True)
    
    # Relationships
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='conversations')
    primary_contact_record = models.ForeignKey(
        'pipelines.Record', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Primary contact for this conversation"
    )
    
    # Conversation management
    status = models.CharField(
        max_length=20, 
        choices=ConversationStatus.choices, 
        default=ConversationStatus.ACTIVE
    )
    priority = models.CharField(
        max_length=20, 
        choices=Priority.choices, 
        default=Priority.NORMAL
    )
    
    # Statistics (updated by signals)
    message_count = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Additional conversation metadata and tags"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['primary_contact_record']),
            models.Index(fields=['last_message_at']),
            models.Index(fields=['external_thread_id']),
            models.Index(fields=['priority', 'status']),
        ]
        unique_together = ['channel', 'external_thread_id']  # Prevent duplicate threads per channel
    
    def __str__(self):
        return f"{self.subject or 'Conversation'} - {self.channel.name}"


class Message(models.Model):
    """
    Individual messages sent or received through communication channels
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Message identification
    external_message_id = models.CharField(
        max_length=255, 
        blank=True,
        help_text="External platform's message ID"
    )
    
    # Relationships
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='messages')
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages',
        null=True, 
        blank=True
    )
    contact_record = models.ForeignKey(
        'pipelines.Record', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Contact record associated with this message"
    )
    
    # Message details
    direction = models.CharField(max_length=20, choices=MessageDirection.choices)
    content = models.TextField()
    subject = models.CharField(max_length=500, blank=True)
    contact_email = models.EmailField(blank=True)
    
    # Status and delivery
    status = models.CharField(
        max_length=20, 
        choices=MessageStatus.choices, 
        default=MessageStatus.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata and attachments
    metadata = models.JSONField(
        default=dict,
        help_text="Message metadata (attachments, formatting, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['channel', 'direction']),
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['contact_record']),
            models.Index(fields=['status', 'direction']),
            models.Index(fields=['external_message_id']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['contact_email']),
        ]
    
    def __str__(self):
        direction_symbol = "←" if self.direction == MessageDirection.INBOUND else "→"
        return f"{direction_symbol} {self.subject or self.content[:50]}..."


class CommunicationAnalytics(models.Model):
    """
    Daily analytics for communication channels and overall performance
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Analytics scope
    date = models.DateField()
    channel = models.ForeignKey(
        Channel, 
        on_delete=models.CASCADE, 
        related_name='analytics',
        null=True, 
        blank=True,
        help_text="Leave blank for tenant-wide analytics"
    )
    
    # Message statistics
    messages_sent = models.IntegerField(default=0)
    messages_received = models.IntegerField(default=0)
    active_channels = models.IntegerField(default=0)
    
    # Performance metrics
    response_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Percentage of messages that received responses"
    )
    engagement_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Overall engagement score (0-100)"
    )
    
    # Additional metrics
    metadata = models.JSONField(
        default=dict,
        help_text="Additional analytics data and breakdowns"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['date', 'channel']  # One record per channel per day
        indexes = [
            models.Index(fields=['date', 'channel']),
            models.Index(fields=['date']),
            models.Index(fields=['channel']),
        ]
    
    def __str__(self):
        scope = f"Channel: {self.channel.name}" if self.channel else "Tenant-wide"
        return f"Analytics {self.date} - {scope}"


# Signal handlers to maintain data consistency
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=Message)
def update_conversation_stats(sender, instance, created, **kwargs):
    """Update conversation statistics when messages are created"""
    if created and instance.conversation:
        conversation = instance.conversation
        conversation.message_count = conversation.messages.count()
        conversation.last_message_at = instance.created_at
        conversation.save(update_fields=['message_count', 'last_message_at'])


@receiver(post_delete, sender=Message)
def update_conversation_stats_on_delete(sender, instance, **kwargs):
    """Update conversation statistics when messages are deleted"""
    if instance.conversation:
        conversation = instance.conversation
        conversation.message_count = conversation.messages.count()
        last_message = conversation.messages.order_by('-created_at').first()
        conversation.last_message_at = last_message.created_at if last_message else None
        conversation.save(update_fields=['message_count', 'last_message_at'])


@receiver(post_save, sender=Message)
def update_channel_stats(sender, instance, created, **kwargs):
    """Update channel statistics when messages are created"""
    if created:
        channel = instance.channel
        channel.message_count = channel.messages.count()
        channel.last_message_at = instance.created_at
        channel.save(update_fields=['message_count', 'last_message_at'])