"""
Models for record-centric communication tracking
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone
from pipelines.models import Pipeline, Record
from django.contrib.auth import get_user_model

User = get_user_model()


class RecordCommunicationProfile(models.Model):
    """Track communication identifiers and sync status per record"""
    
    record = models.OneToOneField(
        Record, 
        on_delete=models.CASCADE,
        related_name='communication_profile'
    )
    pipeline = models.ForeignKey(
        Pipeline, 
        on_delete=models.CASCADE,
        help_text="Pipeline this record belongs to"
    )
    
    # Identifiers extracted based on duplicate rules
    communication_identifiers = models.JSONField(
        default=dict,
        help_text="{'email': ['john@example.com'], 'phone': ['+27782270354'], 'linkedin': [], 'domain': []}"
    )
    
    # Track which fields are used for identification (from duplicate rules)
    identifier_fields = models.JSONField(
        default=list,
        help_text="List of field slugs used as identifiers ['email_address', 'phone_number', 'linkedin_url']"
    )
    
    # Sync tracking per connected account
    sync_status = models.JSONField(
        default=dict,
        help_text="{'account_uuid': {'last_sync': '2025-01-28T10:00:00Z', 'status': 'completed', 'message_count': 45}}"
    )
    
    # Overall sync metrics
    last_full_sync = models.DateTimeField(null=True, blank=True)
    sync_in_progress = models.BooleanField(default=False)
    sync_error_count = models.IntegerField(default=0)
    last_sync_error = models.TextField(blank=True)
    
    # Communication metrics
    total_conversations = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    total_unread = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # Configuration
    auto_sync_enabled = models.BooleanField(
        default=True,
        help_text="Automatically sync when record identifiers change"
    )
    sync_frequency_hours = models.IntegerField(
        default=24,
        help_text="How often to sync in hours (0 = manual only)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['record', '-last_message_at']),
            models.Index(fields=['pipeline', 'sync_in_progress']),
            models.Index(fields=['-last_full_sync']),
            GinIndex(fields=['communication_identifiers']),
        ]
        
    def __str__(self):
        return f"Communication Profile for Record {self.record_id}"
    
    def get_all_identifiers(self):
        """Get all identifiers as a flat list for searching"""
        identifiers = []
        for key, values in self.communication_identifiers.items():
            if isinstance(values, list):
                identifiers.extend(values)
            elif values:
                identifiers.append(values)
        return identifiers
    
    def mark_sync_started(self):
        """Mark sync as in progress"""
        self.sync_in_progress = True
        self.save(update_fields=['sync_in_progress', 'updated_at'])
    
    def mark_sync_completed(self, message_count=0):
        """Mark sync as completed"""
        self.sync_in_progress = False
        self.last_full_sync = timezone.now()
        self.sync_error_count = 0
        self.last_sync_error = ''
        if message_count:
            self.total_messages = message_count
        self.save(update_fields=[
            'sync_in_progress', 'last_full_sync', 'sync_error_count', 
            'last_sync_error', 'total_messages', 'updated_at'
        ])
    
    def mark_sync_failed(self, error_message):
        """Mark sync as failed"""
        self.sync_in_progress = False
        self.sync_error_count += 1
        self.last_sync_error = str(error_message)[:1000]  # Truncate long errors
        self.save(update_fields=[
            'sync_in_progress', 'sync_error_count', 'last_sync_error', 'updated_at'
        ])
    
    def update_metrics(self, conversations=None, messages=None, unread=None):
        """Update communication metrics"""
        update_fields = ['updated_at']
        
        if conversations is not None:
            self.total_conversations = conversations
            update_fields.append('total_conversations')
        
        if messages is not None:
            self.total_messages = messages
            update_fields.append('total_messages')
        
        if unread is not None:
            self.total_unread = unread
            update_fields.append('total_unread')
        
        self.save(update_fields=update_fields)


class RecordCommunicationLink(models.Model):
    """Links conversations to records via identifier matching"""
    
    MATCH_TYPES = [
        ('email', 'Email Address'),
        ('phone', 'Phone Number'),
        ('domain', 'Email Domain'),
        ('linkedin', 'LinkedIn Profile'),
        ('social', 'Social Media Handle'),
        ('provider_id', 'Provider ID'),
        ('manual', 'Manual Link'),
        ('webhook', 'Webhook Auto-Link'),
        ('other', 'Other'),
    ]
    
    record = models.ForeignKey(
        Record, 
        on_delete=models.CASCADE,
        related_name='communication_links'
    )
    conversation = models.ForeignKey(
        'communications.Conversation', 
        on_delete=models.CASCADE,
        related_name='record_links'
    )
    participant = models.ForeignKey(
        'communications.Participant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='record_links',
        help_text="The participant that links this conversation to the record"
    )
    
    # How this link was established
    match_type = models.CharField(
        max_length=20, 
        choices=MATCH_TYPES,
        help_text="How this conversation was linked to the record"
    )
    match_identifier = models.CharField(
        max_length=255,
        help_text="The actual identifier that matched (e.g., 'john@example.com')"
    )
    confidence_score = models.FloatField(
        default=1.0,
        help_text="Confidence in this match (0.0 to 1.0)"
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    linked_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User who created this link (null for automatic)"
    )
    is_primary = models.BooleanField(
        default=True,
        help_text="Is this the primary record for this conversation"
    )
    
    # Sync metadata
    created_by_sync = models.BooleanField(
        default=False,
        help_text="Was this link created by automatic sync"
    )
    last_verified = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last time this link was verified as valid"
    )
    
    class Meta:
        unique_together = ['record', 'conversation', 'participant']
        indexes = [
            models.Index(fields=['record', '-created_at']),
            models.Index(fields=['conversation', 'is_primary']),
            models.Index(fields=['match_type', 'match_identifier']),
            models.Index(fields=['confidence_score']),
        ]
    
    def __str__(self):
        return f"{self.record_id} <-> {self.conversation_id} ({self.match_type}: {self.match_identifier})"


class RecordAttendeeMapping(models.Model):
    """Maps discovered attendees to records for future reference"""
    
    record = models.ForeignKey(
        Record,
        on_delete=models.CASCADE,
        related_name='attendee_mappings'
    )
    profile = models.ForeignKey(
        RecordCommunicationProfile,
        on_delete=models.CASCADE,
        related_name='attendee_mappings'
    )
    
    # UniPile attendee information
    attendee_id = models.CharField(
        max_length=255, 
        db_index=True,
        help_text="UniPile attendee ID from the API"
    )
    provider_id = models.CharField(
        max_length=255, 
        db_index=True,
        help_text="Provider-specific ID (e.g., 277203124113@s.whatsapp.net)"
    )
    channel_type = models.CharField(
        max_length=20,
        help_text="Channel type: whatsapp, linkedin, instagram, etc."
    )
    
    # Extracted identifier that matched
    matched_identifier = models.CharField(
        max_length=255,
        help_text="Original identifier from record (e.g., +277203124113)"
    )
    identifier_type = models.CharField(
        max_length=20,
        help_text="Type of identifier: phone, email, linkedin, etc."
    )
    
    # Attendee details (cached from UniPile)
    attendee_name = models.CharField(max_length=255, blank=True)
    attendee_data = models.JSONField(
        default=dict,
        help_text="Full attendee object from UniPile API"
    )
    
    # Tracking
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['record', 'attendee_id', 'channel_type']]
        indexes = [
            models.Index(fields=['provider_id', 'channel_type']),
            models.Index(fields=['record', 'channel_type']),
            models.Index(fields=['matched_identifier', 'identifier_type']),
        ]
    
    def __str__(self):
        return f"Attendee {self.attendee_id} -> Record {self.record_id} ({self.channel_type})"


class RecordSyncJob(models.Model):
    """Track sync jobs for records"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    record = models.ForeignKey(
        Record, 
        on_delete=models.CASCADE,
        related_name='sync_jobs'
    )
    profile = models.ForeignKey(
        RecordCommunicationProfile,
        on_delete=models.CASCADE,
        related_name='sync_jobs'
    )
    
    # Job details
    job_type = models.CharField(
        max_length=50,
        help_text="Type of sync: full_history, incremental, webhook_trigger"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(default=0)
    current_step = models.CharField(max_length=255, blank=True)
    total_accounts_to_sync = models.IntegerField(default=0)
    accounts_synced = models.IntegerField(default=0)
    
    # Results
    messages_found = models.IntegerField(default=0)
    conversations_found = models.IntegerField(default=0)
    new_links_created = models.IntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Trigger info
    triggered_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    trigger_reason = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Why this sync was triggered"
    )
    
    # Celery task tracking
    celery_task_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['record', '-created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['celery_task_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Sync Job {self.id} for Record {self.record_id} ({self.status})"
    
    def mark_started(self):
        """Mark job as started"""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self):
        """Mark job as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.progress_percentage = 100
        self.save(update_fields=['status', 'completed_at', 'progress_percentage'])
    
    def mark_failed(self, error_message, error_details=None):
        """Mark job as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = str(error_message)[:1000]
        if error_details:
            self.error_details = error_details
        self.save(update_fields=['status', 'completed_at', 'error_message', 'error_details'])
    
    def update_progress(self, percentage, current_step=''):
        """Update job progress"""
        self.progress_percentage = min(percentage, 100)
        if current_step:
            self.current_step = current_step
        self.save(update_fields=['progress_percentage', 'current_step'])