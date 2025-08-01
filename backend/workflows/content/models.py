"""
Centralized Content Management System for Workflows
Provides a content library that workflows can reference or choose to create inline content
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone

User = get_user_model()


class ContentType(models.TextChoices):
    """Types of content that can be managed"""
    EMAIL_TEMPLATE = 'email_template', 'Email Template'
    MESSAGE_TEMPLATE = 'message_template', 'Message Template'
    DOCUMENT_TEMPLATE = 'document_template', 'Document Template'
    IMAGE_ASSET = 'image_asset', 'Image Asset'
    DOCUMENT_ASSET = 'document_asset', 'Document Asset'
    VIDEO_ASSET = 'video_asset', 'Video Asset'
    HTML_SNIPPET = 'html_snippet', 'HTML Snippet'
    TEXT_SNIPPET = 'text_snippet', 'Text Snippet'
    JSON_DATA = 'json_data', 'JSON Data'


class ContentStatus(models.TextChoices):
    """Content approval status"""
    DRAFT = 'draft', 'Draft'
    PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    ARCHIVED = 'archived', 'Archived'


class ContentVisibility(models.TextChoices):
    """Content visibility levels"""
    PRIVATE = 'private', 'Private'
    TEAM = 'team', 'Team'
    ORGANIZATION = 'organization', 'Organization'
    PUBLIC = 'public', 'Public'


class ContentLibrary(models.Model):
    """Organized collections of content assets and templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Organization
    parent_library = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='child_libraries'
    )
    
    # Access control
    visibility = models.CharField(
        max_length=20, 
        choices=ContentVisibility.choices, 
        default=ContentVisibility.ORGANIZATION
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_libraries')
    allowed_users = models.ManyToManyField(User, blank=True, related_name='accessible_libraries')
    
    # Settings
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Additional library metadata and settings"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflows_content_library'
        verbose_name_plural = 'Content Libraries'
        indexes = [
            models.Index(fields=['visibility', 'is_active']),
            models.Index(fields=['parent_library']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_full_path(self) -> str:
        """Get full hierarchical path of the library"""
        if self.parent_library:
            return f"{self.parent_library.get_full_path()} / {self.name}"
        return self.name


class ContentAsset(models.Model):
    """Individual content assets and templates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    
    # Content storage
    content_text = models.TextField(
        blank=True,
        help_text="Text-based content (templates, snippets, etc.)"
    )
    content_file = models.FileField(
        upload_to='content_assets/%Y/%m/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=[
            'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp',  # Images
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',  # Documents
            'mp4', 'mov', 'avi', 'webm',  # Videos
            'json', 'xml', 'csv', 'txt'  # Data files
        ])],
        help_text="File-based content (images, documents, etc.)"
    )
    content_data = models.JSONField(
        default=dict,
        help_text="Structured data content (JSON, configuration, etc.)"
    )
    
    # Template variables (for template types)
    template_variables = models.JSONField(
        default=list,
        help_text="List of variables available in this template"
    )
    variable_schema = models.JSONField(
        default=dict,
        help_text="Schema defining variable types and validation"
    )
    
    # Organization
    library = models.ForeignKey(
        ContentLibrary, 
        on_delete=models.CASCADE, 
        related_name='assets'
    )
    tags = models.ManyToManyField('ContentTag', blank=True, related_name='assets')
    
    # Status and approval
    status = models.CharField(
        max_length=20, 
        choices=ContentStatus.choices, 
        default=ContentStatus.DRAFT
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_content'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Version control
    version = models.CharField(max_length=20, default="1.0")
    is_current_version = models.BooleanField(default=True)
    parent_version = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='version_children'
    )
    
    # Usage and performance
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    performance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Performance score based on usage analytics"
    )
    
    # Access control
    visibility = models.CharField(
        max_length=20, 
        choices=ContentVisibility.choices, 
        default=ContentVisibility.ORGANIZATION
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_content')
    
    # Metadata
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    mime_type = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(
        default=dict,
        help_text="Additional content metadata (dimensions, duration, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflows_content_asset'
        indexes = [
            models.Index(fields=['content_type', 'status']),
            models.Index(fields=['library', 'is_current_version']),
            models.Index(fields=['visibility', 'status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['usage_count']),
            models.Index(fields=['last_used_at']),
        ]
        unique_together = ['library', 'name', 'version']
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    def get_content(self) -> str:
        """Get the actual content based on content type"""
        if self.content_text:
            return self.content_text
        elif self.content_file:
            return self.content_file.url
        elif self.content_data:
            return str(self.content_data)
        return ""
    
    def render_template(self, variables: Dict[str, Any]) -> str:
        """Render template with provided variables"""
        if self.content_type not in [ContentType.EMAIL_TEMPLATE, ContentType.MESSAGE_TEMPLATE, ContentType.HTML_SNIPPET]:
            return self.get_content()
        
        content = self.content_text or ""
        
        # Simple variable substitution (can be enhanced with Jinja2)
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            content = content.replace(placeholder, str(var_value))
        
        return content
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp"""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])


class ContentTag(models.Model):
    """Tags for organizing and categorizing content"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color_code = models.CharField(
        max_length=7, 
        blank=True,
        help_text="Hex color code for UI display"
    )
    
    # Organization
    category = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Usage statistics
    usage_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflows_content_tag'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return self.name


class ContentUsage(models.Model):
    """Track where and how content is used across workflows"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content reference
    content_asset = models.ForeignKey(
        ContentAsset, 
        on_delete=models.CASCADE, 
        related_name='usage_records'
    )
    
    # Usage context
    workflow_id = models.UUIDField(help_text="ID of the workflow using this content")
    workflow_name = models.CharField(max_length=255)
    node_id = models.CharField(max_length=100, help_text="ID of the node using this content")
    node_type = models.CharField(max_length=100)
    
    # Usage details
    usage_type = models.CharField(
        max_length=50,
        help_text="How the content is used (template, asset, reference, etc.)"
    )
    variables_used = models.JSONField(
        default=dict,
        help_text="Variables passed to the content when used"
    )
    
    # Performance tracking
    execution_count = models.PositiveIntegerField(default=0)
    last_execution = models.DateTimeField(null=True, blank=True)
    success_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Context metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Additional usage context and performance data"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflows_content_usage'
        indexes = [
            models.Index(fields=['content_asset', 'workflow_id']),
            models.Index(fields=['workflow_id']),
            models.Index(fields=['execution_count']),
            models.Index(fields=['last_execution']),
        ]
        unique_together = ['content_asset', 'workflow_id', 'node_id']
    
    def __str__(self):
        return f"{self.content_asset.name} used in {self.workflow_name}"


class ContentApproval(models.Model):
    """Content approval workflow"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    content_asset = models.ForeignKey(
        ContentAsset, 
        on_delete=models.CASCADE, 
        related_name='approval_requests'
    )
    
    # Approval details
    requested_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='content_approval_requests'
    )
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='assigned_content_approvals'
    )
    
    # Request details
    request_message = models.TextField(blank=True)
    changes_requested = models.JSONField(
        default=list,
        help_text="List of requested changes or modifications"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('changes_requested', 'Changes Requested'),
        ],
        default='pending'
    )
    
    # Response
    response_message = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflows_content_approval'
        indexes = [
            models.Index(fields=['content_asset', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['requested_by']),
        ]
    
    def __str__(self):
        return f"Approval for {self.content_asset.name} - {self.status}"