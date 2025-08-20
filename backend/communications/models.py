"""
Communication models - omni-channel messaging with UniPile integration
Focused purely on communication functionality: channels, messages, conversations
Includes tenant-level UniPile configuration
"""
import uuid
import json
import base64
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone as django_timezone
from cryptography.fernet import Fernet

# Tenant isolation is handled by django-tenants at the schema level

User = get_user_model()


class TenantUniPileConfig(models.Model):
    """Tenant-level UniPile preferences and settings"""
    # Note: Global DSN/API key are in settings.py, this stores tenant-specific preferences
    
    # Webhook Configuration (optional - for tenant-specific secrets)
    webhook_secret = models.CharField(max_length=255, blank=True, help_text="Optional tenant-specific webhook secret")
    
    # Message tracking settings
    auto_create_contacts = models.BooleanField(default=True, help_text="Auto-create contact records from messages")
    default_contact_pipeline = models.ForeignKey(
        'pipelines.Pipeline', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Default pipeline for auto-created contacts"
    )
    default_contact_status = models.CharField(
        max_length=100, 
        default='new_lead', 
        help_text="Default status for auto-created contacts"
    )
    
    # Sync settings
    sync_historical_days = models.PositiveIntegerField(
        default=30, 
        help_text="Days of historical messages to sync on initial connection"
    )
    enable_real_time_sync = models.BooleanField(
        default=True, 
        help_text="Enable real-time message sync via webhooks"
    )
    
    # Rate limiting (tenant preference within global limits)
    max_api_calls_per_hour = models.PositiveIntegerField(
        default=1000,
        help_text="Maximum UniPile API calls per hour (tenant preference within global limits)"
    )
    
    # Provider-specific preferences (within global feature limits)
    provider_preferences = models.JSONField(
        default=dict,
        help_text="Provider-specific preferences and feature toggles within global limits"
    )
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    last_webhook_received = models.DateTimeField(null=True, blank=True)
    webhook_failures = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_tenantunipileconfig'  # Updated table name
    
    def __str__(self):
        from django_tenants.utils import connection
        return f"UniPile Config for tenant: {connection.tenant.name if hasattr(connection, 'tenant') else 'Unknown'}"
    
    @classmethod
    def get_or_create_for_tenant(cls):
        """Get or create UniPile config for current tenant"""
        config, created = cls.objects.get_or_create(defaults={
            'auto_create_contacts': True,
            'sync_historical_days': 30,
            'enable_real_time_sync': True,
            'max_api_calls_per_hour': 1000,
            'is_active': True
        })
        return config
    
    def get_global_config(self):
        """Get global UniPile configuration from settings"""
        from django.conf import settings
        return settings.UNIPILE_SETTINGS
    
    def is_configured(self):
        """Check if UniPile is properly configured (globally + tenant active)"""
        global_config = self.get_global_config()
        return global_config.is_configured() and self.is_active
    
    def get_api_credentials(self):
        """Get API credentials (DSN and API key from global config)"""
        global_config = self.get_global_config()
        return {
            'dsn': global_config.dsn,
            'api_key': global_config.api_key
        }
    
    def record_webhook_success(self):
        """Record successful webhook reception"""
        self.last_webhook_received = django_timezone.now()
        self.webhook_failures = 0
        self.save(update_fields=['last_webhook_received', 'webhook_failures'])
    
    def record_webhook_failure(self):
        """Record webhook failure"""
        self.webhook_failures += 1
        self.save(update_fields=['webhook_failures'])
    
    def get_provider_preferences(self, provider_type):
        """Get preferences for a specific provider"""
        return self.provider_preferences.get(provider_type, {})
    
    def set_provider_preferences(self, provider_type, preferences):
        """Set preferences for a specific provider (validates against global limits)"""
        global_config = self.get_global_config()
        global_provider_config = global_config.get_provider_config(provider_type)
        
        if not global_provider_config:
            raise ValueError(f"Provider {provider_type} not supported globally")
        
        # Validate that enabled features are within global limits
        global_features = global_provider_config.get('features', {})
        enabled_features = preferences.get('enabled_features', [])
        
        for feature in enabled_features:
            if not global_features.get(feature, False):
                raise ValueError(f"Feature {feature} not enabled globally for {provider_type}")
        
        # Store preferences
        if not self.provider_preferences:
            self.provider_preferences = {}
        
        self.provider_preferences[provider_type] = preferences
        self.save(update_fields=['provider_preferences'])
    
    def is_provider_feature_enabled(self, provider_type, feature):
        """Check if a feature is enabled for a provider (tenant preference + global limit)"""
        global_config = self.get_global_config()
        
        # Check global enablement first
        if not global_config.is_feature_enabled(provider_type, feature):
            return False
        
        # Check tenant preferences
        provider_prefs = self.get_provider_preferences(provider_type)
        enabled_features = provider_prefs.get('enabled_features', [])
        
        # If no tenant preferences, default to global settings
        if not enabled_features:
            return True
        
        return feature in enabled_features
    
    def get_provider_rate_limit(self, provider_type, limit_type):
        """Get rate limit for a provider (tenant preference within global limits)"""
        global_config = self.get_global_config()
        global_limits = global_config.get_provider_rate_limits(provider_type)
        global_limit = global_limits.get(limit_type, 0)
        
        # Get tenant preferences
        provider_prefs = self.get_provider_preferences(provider_type)
        tenant_limits = provider_prefs.get('rate_limits', {})
        tenant_limit = tenant_limits.get(limit_type, global_limit)
        
        # Return the minimum of global and tenant limits
        return min(global_limit, tenant_limit) if global_limit > 0 else tenant_limit
    
    def get_default_provider_preferences(self):
        """Get default provider preferences based on global configuration"""
        global_config = self.get_global_config()
        default_prefs = {}
        
        for provider_type in global_config.get_supported_providers():
            provider_config = global_config.get_provider_config(provider_type)
            features = provider_config.get('features', {})
            
            # Enable all globally available features by default
            enabled_features = [feature for feature, enabled in features.items() if enabled]
            
            default_prefs[provider_type] = {
                'enabled_features': enabled_features,
                'auto_sync_enabled': True,
                'sync_frequency': 'real_time',
                'auto_create_contacts': True,
                'preferred_auth_method': provider_config.get('auth_methods', ['hosted'])[0],
                'rate_limits': provider_config.get('rate_limits', {}),
                'notifications_enabled': True
            }
        
        return default_prefs


class ChannelType(models.TextChoices):
    """Available communication channel types matching UniPile providers exactly"""
    # UniPile supported: LINKEDIN | WHATSAPP | INSTAGRAM | MESSENGER | TELEGRAM | GOOGLE | OUTLOOK | MAIL | TWITTER
    LINKEDIN = 'linkedin', 'LinkedIn'
    GOOGLE = 'gmail', 'Gmail'  # Maps to GOOGLE in UniPile
    OUTLOOK = 'outlook', 'Outlook'
    MAIL = 'mail', 'Email (Generic)'  # UniPile MAIL provider
    WHATSAPP = 'whatsapp', 'WhatsApp'
    INSTAGRAM = 'instagram', 'Instagram'
    MESSENGER = 'messenger', 'Facebook Messenger'
    TELEGRAM = 'telegram', 'Telegram'
    TWITTER = 'twitter', 'Twitter/X'


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
    unipile_account_id = models.CharField(max_length=255, blank=True, default='', help_text="UniPile account ID")
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
    provider_config = models.JSONField(
        default=dict,
        help_text="Provider-specific configuration and preferences"
    )
    
    # Hosted authentication support
    hosted_auth_url = models.URLField(blank=True, help_text="Hosted authentication URL for pending connections")
    checkpoint_data = models.JSONField(
        default=dict,
        help_text="2FA/checkpoint data for authentication challenges"
    )
    
    # Enhanced status tracking
    account_status = models.CharField(
        max_length=50,
        default='pending',
        choices=[
            ('pending', 'Pending Connection'),
            ('active', 'Active'),
            ('failed', 'Failed'),
            ('expired', 'Expired'),
            ('checkpoint_required', 'Checkpoint Required'),
            ('disconnected', 'Disconnected'),
        ],
        help_text="Current account status"
    )
    
    # Status and metadata
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_error_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True)
    messages_sent_count = models.IntegerField(default=0)
    
    # Rate limiting and usage tracking
    messages_sent_today = models.IntegerField(default=0)
    rate_limit_per_hour = models.IntegerField(default=100)
    last_rate_limit_reset = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'channel_type', 'unipile_account_id']
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
    
    def needs_reconnection(self) -> bool:
        """Check if account needs reconnection"""
        return self.account_status in ['failed', 'expired', 'disconnected']
    
    def can_send_messages(self) -> bool:
        """Check if account can send messages"""
        if not self.is_active or self.account_status != 'active':
            return False
        
        # Check rate limiting
        now = django_timezone.now()
        if self.last_rate_limit_reset and self.last_rate_limit_reset.date() != now.date():
            # Reset daily counter
            self.messages_sent_today = 0
            self.last_rate_limit_reset = now
            self.save(update_fields=['messages_sent_today', 'last_rate_limit_reset'])
        
        return self.messages_sent_today < self.rate_limit_per_hour
    
    def get_status_display_info(self) -> dict:
        """Get detailed status information for display"""
        status_info = {
            'status': self.account_status,
            'display': self.get_account_status_display(),
            'can_send': self.can_send_messages(),
            'needs_action': False,
            'action_type': None,
            'message': ''
        }
        
        if self.account_status == 'checkpoint_required':
            status_info['needs_action'] = True
            status_info['action_type'] = 'checkpoint'
            status_info['message'] = 'Account requires verification code'
        elif self.needs_reconnection():
            status_info['needs_action'] = True
            status_info['action_type'] = 'reconnect'
            status_info['message'] = 'Account needs to be reconnected'
        elif self.account_status == 'pending' and self.hosted_auth_url:
            status_info['needs_action'] = True
            status_info['action_type'] = 'complete_auth'
            status_info['message'] = 'Complete authentication process'
        
        return status_info
    
    def record_message_sent(self):
        """Record that a message was sent (for rate limiting)"""
        now = django_timezone.now()
        if not self.last_rate_limit_reset or self.last_rate_limit_reset.date() != now.date():
            # Reset daily counter
            self.messages_sent_today = 1
            self.last_rate_limit_reset = now
        else:
            self.messages_sent_today += 1
        
        self.save(update_fields=['messages_sent_today', 'last_rate_limit_reset'])
    
    def record_sync_success(self):
        """Record successful sync"""
        self.last_sync_at = django_timezone.now()
        self.sync_error_count = 0
        self.last_error = ''
        if self.account_status in ['failed', 'expired']:
            self.account_status = 'active'
        self.save(update_fields=['last_sync_at', 'sync_error_count', 'last_error', 'account_status'])
    
    def record_sync_failure(self, error_message: str = ''):
        """Record sync failure"""
        self.sync_error_count += 1
        self.last_error = error_message
        if self.sync_error_count >= 3:  # Mark as failed after 3 consecutive failures
            self.account_status = 'failed'
        self.save(update_fields=['sync_error_count', 'last_error', 'account_status'])


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
    unipile_account_id = models.CharField(
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
    Enhanced with sync capabilities and performance optimizations
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
    unread_count = models.IntegerField(default=0, help_text="Cached unread message count")
    
    # Sync metadata for persistence layer
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Sync'),
            ('synced', 'Synced'),
            ('failed', 'Sync Failed'),
            ('partial', 'Partially Synced'),
        ],
        default='pending',
        help_text="Synchronization status with external provider"
    )
    last_synced_at = models.DateTimeField(null=True, blank=True, help_text="Last successful sync timestamp")
    sync_error_count = models.IntegerField(default=0, help_text="Number of consecutive sync failures")
    sync_error_message = models.TextField(blank=True, help_text="Last sync error message")
    
    # Performance optimization fields
    is_hot = models.BooleanField(default=False, help_text="Frequently accessed conversation")
    last_accessed_at = models.DateTimeField(auto_now=True, help_text="Last time conversation was accessed")
    
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
            # Core query patterns
            models.Index(fields=['channel', 'status', '-last_message_at']),  # Conversation list queries
            models.Index(fields=['channel', '-last_message_at']),  # All conversations by recency
            models.Index(fields=['external_thread_id']),  # External ID lookups
            models.Index(fields=['primary_contact_record']),  # Contact-based queries
            
            # Sync and performance optimization
            models.Index(fields=['sync_status', 'last_synced_at']),  # Sync management
            models.Index(fields=['is_hot', '-last_accessed_at']),  # Hot conversation tracking
            models.Index(fields=['-last_accessed_at']),  # Recently accessed conversations
            
            # Status and priority filtering
            models.Index(fields=['status', '-last_message_at']),  # Status-based filtering
            models.Index(fields=['priority', 'status']),  # Priority filtering
            models.Index(fields=['unread_count']),  # Unread filtering
            
            # Date-based queries
            models.Index(fields=['-created_at']),  # Recent conversations
            models.Index(fields=['-updated_at']),  # Recently updated
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
    contact_phone = models.CharField(max_length=50, blank=True, help_text="Contact phone number for WhatsApp/SMS messages")
    
    # Status and delivery
    status = models.CharField(
        max_length=20, 
        choices=MessageStatus.choices, 
        default=MessageStatus.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    
    # Sync metadata for persistence layer
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Sync'),
            ('synced', 'Synced'),
            ('failed', 'Sync Failed'),
        ],
        default='pending',
        help_text="Synchronization status with external provider"
    )
    last_synced_at = models.DateTimeField(null=True, blank=True, help_text="Last successful sync timestamp")
    is_local_only = models.BooleanField(default=False, help_text="Message exists only locally (not yet sent to external provider)")
    
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
            # Core query patterns
            models.Index(fields=['conversation', '-created_at']),  # Message list queries (most important)
            models.Index(fields=['channel', 'direction', '-created_at']),  # Channel-based message queries
            models.Index(fields=['external_message_id']),  # External ID lookups
            
            # Sync and status tracking
            models.Index(fields=['sync_status', 'last_synced_at']),  # Sync management
            models.Index(fields=['is_local_only', '-created_at']),  # Local-only messages
            models.Index(fields=['status', 'direction']),  # Status filtering
            
            # Contact and relationship queries
            models.Index(fields=['contact_record', '-created_at']),  # Contact message history
            models.Index(fields=['contact_email']),  # Email-based lookups
            models.Index(fields=['contact_phone']),  # Phone-based lookups
            
            # Date and delivery tracking
            models.Index(fields=['-sent_at']),  # Recently sent messages
            models.Index(fields=['-received_at']),  # Recently received messages
            models.Index(fields=['-created_at']),  # Recently created messages
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['external_message_id', 'channel'],
                condition=models.Q(external_message_id__isnull=False) & ~models.Q(external_message_id=''),
                name='unique_external_message_per_channel'
            )
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


class ChatAttendee(models.Model):
    """
    Store contact/attendee information from Unipile API
    Maps external contacts to internal conversation participants
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # External identification
    external_attendee_id = models.CharField(
        max_length=255,
        help_text="Unipile attendee ID"
    )
    provider_id = models.CharField(
        max_length=255,
        help_text="Provider-specific ID (e.g., phone@s.whatsapp.net, email, etc.)"
    )
    
    # Relationships
    channel = models.ForeignKey(
        Channel, 
        on_delete=models.CASCADE, 
        related_name='attendees',
        help_text="Channel this attendee belongs to"
    )
    contact_record = models.ForeignKey(
        'pipelines.Record', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Linked contact record in CRM"
    )
    
    # Attendee information
    name = models.CharField(
        max_length=255,
        help_text="Display name of the attendee"
    )
    picture_url = models.URLField(
        blank=True,
        help_text="Profile picture URL from the platform"
    )
    is_self = models.BooleanField(
        default=False,
        help_text="Whether this attendee represents the account owner"
    )
    
    # Additional data from Unipile
    metadata = models.JSONField(
        default=dict,
        help_text="Additional attendee data from Unipile API"
    )
    
    # Sync tracking
    last_synced_at = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('stale', 'Stale'),
            ('error', 'Error')
        ],
        default='active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [
            ['channel', 'external_attendee_id'],  # One record per external attendee per channel
            ['channel', 'provider_id'],           # One record per provider ID per channel
        ]
        indexes = [
            models.Index(fields=['channel', 'provider_id']),
            models.Index(fields=['channel', 'external_attendee_id']),
            models.Index(fields=['contact_record']),
            models.Index(fields=['name']),
            models.Index(fields=['last_synced_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.provider_id}) - {self.channel.name}"
    
    @property
    def phone_number(self):
        """Extract phone number from WhatsApp provider_id"""
        if '@s.whatsapp.net' in self.provider_id:
            return self.provider_id.replace('@s.whatsapp.net', '')
        return None
    
    @property
    def is_phone_number_name(self):
        """Check if the name is just a phone number (not a real contact name)"""
        return self.name.endswith('@s.whatsapp.net') or self.name.replace('+', '').replace('-', '').replace(' ', '').isdigit()


# Import draft models
from .models_drafts import MessageDraft, DraftAutoSaveSettings