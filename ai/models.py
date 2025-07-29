"""
AI Integration models for tracking jobs, analytics, and embeddings
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class AIJob(models.Model):
    """Track AI processing jobs"""
    
    JOB_TYPES = [
        ('field_generation', 'Field Generation'),
        ('summarization', 'Summarization'),
        ('classification', 'Classification'),
        ('sentiment_analysis', 'Sentiment Analysis'),
        ('embedding_generation', 'Embedding Generation'),
        ('semantic_search', 'Semantic Search'),
    ]
    
    STATUSES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    AI_PROVIDERS = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('local', 'Local'),
    ]
    
    # Job identification
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    
    # Target information
    pipeline = models.ForeignKey('pipelines.Pipeline', on_delete=models.CASCADE, null=True, blank=True)
    record_id = models.IntegerField(null=True, blank=True)
    field_name = models.CharField(max_length=100, blank=True)
    
    # AI configuration
    ai_provider = models.CharField(max_length=20, choices=AI_PROVIDERS)
    model_name = models.CharField(max_length=100)
    prompt_template = models.TextField(blank=True)
    ai_config = models.JSONField(default=dict)
    
    # Processing details
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    tokens_used = models.IntegerField(default=0)
    cost_cents = models.IntegerField(default=0)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['job_type']),
            models.Index(fields=['record_id']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.job_type} - {self.status} - {self.created_at}"
    
    @property
    def cost_dollars(self):
        """Get cost in dollars"""
        return self.cost_cents / 100.0
    
    def can_retry(self):
        """Check if job can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries


class AIEmbedding(models.Model):
    """Store vector embeddings for semantic search"""
    
    CONTENT_TYPES = [
        ('record', 'Pipeline Record'),
        ('field', 'Pipeline Field'),
        ('document', 'Document'),
        ('user', 'User Profile'),
    ]
    
    # Content identification
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPES)
    content_id = models.CharField(max_length=100)
    content_hash = models.CharField(max_length=64)  # SHA-256 hash
    
    # Embedding data (stored as JSON array for now - could use pgvector in production)
    embedding = models.JSONField()
    model_name = models.CharField(max_length=100)
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['content_hash']),
            models.Index(fields=['model_name']),
        ]
        unique_together = ['content_type', 'content_id', 'model_name']
    
    def __str__(self):
        return f"{self.content_type}:{self.content_id} - {self.model_name}"


class AIUsageAnalytics(models.Model):
    """Track AI usage for analytics and billing"""
    
    # Usage details
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ai_provider = models.CharField(max_length=20)
    model_name = models.CharField(max_length=100)
    operation_type = models.CharField(max_length=50)
    
    # Metrics
    tokens_used = models.IntegerField()
    cost_cents = models.IntegerField()
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # Context
    pipeline = models.ForeignKey('pipelines.Pipeline', on_delete=models.CASCADE, null=True, blank=True)
    record_id = models.IntegerField(null=True, blank=True)
    
    # Time tracking
    created_at = models.DateTimeField(default=timezone.now)
    date = models.DateField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['user', 'date']),
            models.Index(fields=['ai_provider', 'date']),
            models.Index(fields=['operation_type', 'date']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.operation_type} - {self.date}"
    
    @property
    def cost_dollars(self):
        """Get cost in dollars"""
        return self.cost_cents / 100.0


class AIPromptTemplate(models.Model):
    """Store AI prompt templates for reuse"""
    
    AI_PROVIDERS = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('local', 'Local'),
    ]
    
    # Template identification
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    # Template content
    prompt_template = models.TextField()
    system_message = models.TextField(blank=True)
    
    # Configuration
    ai_provider = models.CharField(max_length=20, choices=AI_PROVIDERS)
    model_name = models.CharField(max_length=100)
    temperature = models.DecimalField(max_digits=3, decimal_places=2, default=0.7)
    max_tokens = models.IntegerField(default=1000)
    
    # Usage context
    field_types = models.JSONField(default=list)  # Which field types this applies to
    pipeline_types = models.JSONField(default=list)  # Which pipeline types this applies to
    
    # Template variables
    required_variables = models.JSONField(default=list)
    optional_variables = models.JSONField(default=list)
    
    # Version control
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    def render_prompt(self, variables: dict) -> str:
        """Render prompt template with variables"""
        try:
            return self.prompt_template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")
    
    def validate_variables(self, variables: dict) -> list:
        """Validate that all required variables are provided"""
        missing_vars = []
        for var in self.required_variables:
            if var not in variables:
                missing_vars.append(var)
        return missing_vars