"""
Sharing models for tracking shared records and access history
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from pipelines.models import Record
import uuid

User = get_user_model()


class SharedRecord(models.Model):
    """
    Track shared records with history and analytics
    """
    ACCESS_MODES = (
        ('readonly', 'Read-only'),
        ('editable', 'Editable'),
    )
    
    # Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    encrypted_token = models.CharField(max_length=500, unique=True, db_index=True)
    
    # Relationships
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_records')
    
    # Access Configuration
    access_mode = models.CharField(max_length=10, choices=ACCESS_MODES, default='editable')
    expires_at = models.DateTimeField()
    intended_recipient_email = models.EmailField(help_text="Email address of the intended recipient who can access this share")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Analytics
    access_count = models.PositiveIntegerField(default=0)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    last_accessed_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='revoked_shares')
    
    class Meta:
        db_table = 'sharing_shared_records'
        indexes = [
            models.Index(fields=['encrypted_token']),
            models.Index(fields=['record', 'shared_by']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_active', 'expires_at']),
            models.Index(fields=['shared_by', 'created_at']),
            models.Index(fields=['intended_recipient_email']),
            models.Index(fields=['intended_recipient_email', 'is_active']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Share {self.record} by {self.shared_by} for {self.intended_recipient_email} ({self.access_mode})"
    
    @property
    def is_expired(self):
        """Check if the share link has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if the share link is still valid"""
        return self.is_active and not self.is_expired and not self.revoked_at
    
    @property
    def time_remaining_seconds(self):
        """Get time remaining in seconds"""
        if self.is_expired:
            return 0
        return int((self.expires_at - timezone.now()).total_seconds())
    
    @property
    def status(self):
        """Get human-readable status"""
        if self.revoked_at:
            return 'revoked'
        elif self.is_expired:
            return 'expired'
        elif not self.is_active:
            return 'inactive'
        else:
            return 'active'
    
    def track_access(self, ip_address=None):
        """Track an access to this shared record"""
        self.access_count += 1
        self.last_accessed_at = timezone.now()
        if ip_address:
            self.last_accessed_ip = ip_address
        self.save(update_fields=['access_count', 'last_accessed_at', 'last_accessed_ip'])
    
    def revoke(self, revoked_by=None):
        """Revoke the share link"""
        self._was_revoked = True  # Flag for signal handling
        self.is_active = False
        self.revoked_at = timezone.now()
        self.revoked_by = revoked_by
        self.save(update_fields=['is_active', 'revoked_at', 'revoked_by'])


class SharedRecordAccess(models.Model):
    """
    Track individual access events to shared records for detailed analytics
    """
    shared_record = models.ForeignKey(SharedRecord, on_delete=models.CASCADE, related_name='access_logs')
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Required accessor information
    accessor_name = models.CharField(max_length=255, help_text="Name of the person accessing the shared record")
    accessor_email = models.EmailField(help_text="Email of the person accessing the shared record")
    
    # Geographic data (can be populated via IP lookup)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Session tracking
    session_duration = models.PositiveIntegerField(null=True, blank=True, help_text="Session duration in seconds")
    
    class Meta:
        db_table = 'sharing_shared_record_access'
        indexes = [
            models.Index(fields=['shared_record', 'accessed_at']),
            models.Index(fields=['accessed_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['accessor_email']),
            models.Index(fields=['accessor_name', 'accessor_email']),
        ]
        ordering = ['-accessed_at']
    
    def __str__(self):
        return f"Access by {self.accessor_name} ({self.accessor_email}) to {self.shared_record} at {self.accessed_at}"