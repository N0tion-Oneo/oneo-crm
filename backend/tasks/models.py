"""
Task management models for Oneo CRM
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Task(models.Model):
    """
    Task model for managing tasks associated with records
    """
    
    # Priority choices
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Core fields
    title = models.CharField(
        max_length=255,
        help_text="Task title"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed task description"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="Task priority level"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current task status"
    )
    
    # Date fields
    due_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the task is due"
    )
    reminder_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When to send a reminder"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the task was completed"
    )
    
    # Relationships
    record = models.ForeignKey(
        'pipelines.Record',
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text="Associated record"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='assigned_tasks',
        help_text="User assigned to this task"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
        help_text="User who created this task"
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional task metadata"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the task was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the task was last updated"
    )
    
    class Meta:
        ordering = ['-priority', 'due_date', '-created_at']
        indexes = [
            models.Index(fields=['record', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to handle status changes"""
        # Set completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'completed':
            self.completed_at = None
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.due_date
        return False
    
    @property
    def priority_score(self):
        """Get numeric priority score for sorting"""
        priority_map = {
            'urgent': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return priority_map.get(self.priority, 0)


class TaskComment(models.Model):
    """
    Comments on tasks for collaboration
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment on {self.task.title} by {self.user}"


class TaskAttachment(models.Model):
    """
    File attachments for tasks
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='task_attachments/%Y/%m/%d/'
    )
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Attachment: {self.filename}"
