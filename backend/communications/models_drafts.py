"""
Draft models for message composition
Stores unsent messages that can be auto-saved and recovered
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class MessageDraft(models.Model):
    """
    Stores draft messages that haven't been sent yet
    Supports auto-save functionality for message composition
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User and account information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_drafts')
    account_connection_id = models.CharField(
        max_length=255, 
        blank=True,
        help_text="UserChannelConnection ID for sending account"
    )
    
    # Draft content
    subject = models.CharField(max_length=500, blank=True)
    content = models.TextField()
    recipient = models.CharField(max_length=500, blank=True)
    
    # Message context
    conversation_id = models.CharField(max_length=255, blank=True)
    recipient_type = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New Message'),
            ('reply', 'Reply'),
        ],
        default='new'
    )
    
    # Draft metadata
    draft_name = models.CharField(
        max_length=200, 
        blank=True,
        help_text="User-friendly name for the draft"
    )
    auto_saved = models.BooleanField(
        default=True,
        help_text="True if this is an auto-save, False if manually saved"
    )
    
    # Attachment information (stored as JSON)
    attachments_data = models.JSONField(
        default=list,
        help_text="List of attachment metadata for the draft"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_auto_save = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'auto_saved']),
            models.Index(fields=['user', 'conversation_id']),
            models.Index(fields=['last_auto_save']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        draft_type = "Auto-save" if self.auto_saved else "Draft"
        name = self.draft_name or self.subject or "Untitled"
        return f"{draft_type}: {name[:50]}"
    
    def save(self, *args, **kwargs):
        """Override save to update last_auto_save timestamp"""
        if self.auto_saved:
            self.last_auto_save = timezone.now()
        
        # Auto-generate draft name if not provided
        if not self.draft_name:
            if self.subject:
                self.draft_name = self.subject[:50]
            elif self.recipient:
                self.draft_name = f"Message to {self.recipient}"
            elif self.conversation_id:
                self.draft_name = "Reply"
            else:
                self.draft_name = "Untitled Draft"
        
        super().save(*args, **kwargs)
    
    def get_attachments_count(self):
        """Get number of attachments in this draft"""
        return len(self.attachments_data) if self.attachments_data else 0
    
    def get_content_preview(self, max_length=100):
        """Get a preview of the draft content"""
        if not self.content:
            return "No content"
        
        content = self.content.strip()
        if len(content) <= max_length:
            return content
        
        return content[:max_length] + "..."
    
    def is_stale(self, hours=24):
        """Check if draft is stale (older than specified hours)"""
        if not self.last_auto_save:
            return False
        
        stale_threshold = timezone.now() - timezone.timedelta(hours=hours)
        return self.last_auto_save < stale_threshold
    
    def to_composer_data(self):
        """Convert draft to data structure for message composer"""
        return {
            'id': str(self.id),
            'subject': self.subject,
            'content': self.content,
            'recipient': self.recipient,
            'account_connection_id': self.account_connection_id,
            'conversation_id': self.conversation_id,
            'recipient_type': self.recipient_type,
            'attachments': self.attachments_data,
            'draft_name': self.draft_name,
            'auto_saved': self.auto_saved,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class DraftAutoSaveSettings(models.Model):
    """
    User-specific settings for draft auto-save functionality
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='draft_settings'
    )
    
    # Auto-save configuration
    auto_save_enabled = models.BooleanField(default=True)
    auto_save_interval = models.PositiveIntegerField(
        default=30,
        help_text="Auto-save interval in seconds"
    )
    
    # Draft management
    max_auto_saves = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of auto-saves to keep per conversation"
    )
    auto_delete_after_days = models.PositiveIntegerField(
        default=30,
        help_text="Auto-delete drafts after this many days"
    )
    
    # Notifications
    show_draft_recovery_prompt = models.BooleanField(
        default=True,
        help_text="Show prompt to recover drafts when reopening composer"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Draft Auto-Save Settings"
        verbose_name_plural = "Draft Auto-Save Settings"
    
    def __str__(self):
        return f"Draft settings for {self.user.username}"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create settings for a user with defaults"""
        settings, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'auto_save_enabled': True,
                'auto_save_interval': 30,
                'max_auto_saves': 5,
                'auto_delete_after_days': 30,
                'show_draft_recovery_prompt': True,
            }
        )
        return settings