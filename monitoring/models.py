"""
Monitoring and reporting models for system health and performance tracking
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField

User = get_user_model()


class HealthStatus(models.TextChoices):
    """System health status levels"""
    HEALTHY = 'healthy', 'Healthy'
    WARNING = 'warning', 'Warning'
    CRITICAL = 'critical', 'Critical'
    DOWN = 'down', 'Down'


class MetricType(models.TextChoices):
    """Types of system metrics"""
    PERFORMANCE = 'performance', 'Performance'
    USAGE = 'usage', 'Usage'
    ERROR = 'error', 'Error'
    SECURITY = 'security', 'Security'
    BUSINESS = 'business', 'Business'


class ReportType(models.TextChoices):
    """Types of reports"""
    SYSTEM_HEALTH = 'system_health', 'System Health'
    PERFORMANCE = 'performance', 'Performance'
    USAGE = 'usage', 'Usage Analytics'
    SECURITY = 'security', 'Security'
    BUSINESS = 'business', 'Business Intelligence'
    COMPLIANCE = 'compliance', 'Compliance'


class AlertSeverity(models.TextChoices):
    """Alert severity levels"""
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    ERROR = 'error', 'Error'
    CRITICAL = 'critical', 'Critical'


class SystemHealthCheck(models.Model):
    """
    System health check results for various components
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Component identification
    component_name = models.CharField(max_length=100)
    component_type = models.CharField(
        max_length=50,
        choices=[
            ('database', 'Database'),
            ('cache', 'Cache'),
            ('celery', 'Celery Workers'),
            ('storage', 'File Storage'),
            ('external_api', 'External API'),
            ('workflow_engine', 'Workflow Engine'),
            ('communication', 'Communication System'),
            ('auth', 'Authentication'),
            ('api', 'API Endpoints'),
            ('web_server', 'Web Server')
        ]
    )
    
    # Health status
    status = models.CharField(max_length=20, choices=HealthStatus.choices)
    response_time_ms = models.IntegerField(
        null=True, blank=True,
        help_text="Component response time in milliseconds"
    )
    
    # Health details
    message = models.TextField(blank=True)
    details = models.JSONField(
        default=dict,
        help_text="Detailed health check information"
    )
    
    # Metrics
    cpu_usage_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    memory_usage_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    disk_usage_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Timestamps
    checked_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['component_name', 'checked_at']),
            models.Index(fields=['component_type', 'status']),
            models.Index(fields=['status', 'checked_at']),
            models.Index(fields=['checked_at']),
        ]
        
    def __str__(self):
        return f"{self.component_name} - {self.get_status_display()} at {self.checked_at}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def needs_attention(self) -> bool:
        """Check if component needs attention"""
        return self.status in [HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.DOWN]


class SystemMetrics(models.Model):
    """
    System-wide metrics collection for performance monitoring
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Metric identification
    metric_name = models.CharField(max_length=100)
    metric_type = models.CharField(max_length=20, choices=MetricType.choices)
    category = models.CharField(max_length=50, blank=True)
    
    # Metric data
    value = models.DecimalField(max_digits=15, decimal_places=4)
    unit = models.CharField(max_length=20, blank=True)
    
    # Context
    tags = models.JSONField(
        default=dict,
        help_text="Additional tags and context for the metric"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metric metadata"
    )
    
    # Timestamps
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['metric_name', 'timestamp']),
            models.Index(fields=['metric_type', 'category']),
            models.Index(fields=['timestamp']),
        ]
        
    def __str__(self):
        return f"{self.metric_name}: {self.value} {self.unit} at {self.timestamp}"


class PerformanceMetrics(models.Model):
    """
    Application performance metrics aggregated over time periods
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    granularity = models.CharField(
        max_length=20,
        choices=[
            ('minute', 'Per Minute'),
            ('hour', 'Per Hour'),
            ('day', 'Per Day'),
            ('week', 'Per Week'),
            ('month', 'Per Month')
        ]
    )
    
    # Request metrics
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    avg_response_time_ms = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    
    # Resource usage
    avg_cpu_usage = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    avg_memory_usage = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    
    # Database metrics
    db_query_count = models.IntegerField(default=0)
    avg_db_query_time_ms = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    
    # Cache metrics
    cache_hit_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    
    # Business metrics
    active_users = models.IntegerField(default=0)
    workflow_executions = models.IntegerField(default=0)
    messages_processed = models.IntegerField(default=0)
    
    # Error metrics
    error_count = models.IntegerField(default=0)
    error_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['period_start', 'granularity']),
            models.Index(fields=['granularity', 'period_start']),
        ]
        unique_together = ['period_start', 'granularity']
        
    def __str__(self):
        return f"Performance {self.granularity} - {self.period_start}"
    
    @property
    def success_rate(self) -> Decimal:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return Decimal('0.00')
        return Decimal(self.successful_requests) / Decimal(self.total_requests) * 100


class SystemAlert(models.Model):
    """
    System alerts for monitoring and notification
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Alert identification
    alert_name = models.CharField(max_length=200)
    alert_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20, choices=AlertSeverity.choices)
    
    # Alert details
    message = models.TextField()
    description = models.TextField(blank=True)
    
    # Context
    component = models.CharField(max_length=100, blank=True)
    metric_name = models.CharField(max_length=100, blank=True)
    threshold_value = models.DecimalField(
        max_digits=15, decimal_places=4,
        null=True, blank=True
    )
    actual_value = models.DecimalField(
        max_digits=15, decimal_places=4,
        null=True, blank=True
    )
    
    # Alert data
    alert_data = models.JSONField(
        default=dict,
        help_text="Additional alert context and data"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Resolution
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Timestamps
    triggered_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['severity', 'is_active']),
            models.Index(fields=['component', 'triggered_at']),
            models.Index(fields=['is_active', 'acknowledged']),
            models.Index(fields=['triggered_at']),
        ]
        
    def __str__(self):
        return f"{self.get_severity_display()}: {self.alert_name}"
    
    def acknowledge(self, user: User, notes: str = '') -> None:
        """Acknowledge the alert"""
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        if notes:
            self.alert_data['acknowledgment_notes'] = notes
        self.save()
    
    def resolve(self, user: User, notes: str = '') -> None:
        """Resolve the alert"""
        self.resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.is_active = False
        self.save()


class Report(models.Model):
    """
    Generated reports for system monitoring and business intelligence
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Report identification
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    description = models.TextField(blank=True)
    
    # Report configuration
    filters = models.JSONField(
        default=dict,
        help_text="Report filters and parameters"
    )
    date_range_start = models.DateTimeField(null=True, blank=True)
    date_range_end = models.DateTimeField(null=True, blank=True)
    
    # Report data
    data = models.JSONField(
        default=dict,
        help_text="Generated report data and results"
    )
    summary = models.JSONField(
        default=dict,
        help_text="Report summary and key metrics"
    )
    
    # Generation details
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    generation_time_seconds = models.DecimalField(
        max_digits=8, decimal_places=3,
        null=True, blank=True
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('generating', 'Generating'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('expired', 'Expired')
        ],
        default='generating'
    )
    error_message = models.TextField(blank=True)
    
    # File storage
    file_path = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.IntegerField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['report_type', 'created_at']),
            models.Index(fields=['generated_by', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"
    
    @property
    def is_expired(self) -> bool:
        """Check if report has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def mark_expired(self) -> None:
        """Mark report as expired"""
        self.status = 'expired'
        self.save()


class MonitoringConfiguration(models.Model):
    """
    Configuration settings for monitoring system
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Configuration identification
    config_name = models.CharField(max_length=100, unique=True)
    config_type = models.CharField(
        max_length=50,
        choices=[
            ('health_check', 'Health Check'),
            ('metric_collection', 'Metric Collection'),
            ('alert_rule', 'Alert Rule'),
            ('report_schedule', 'Report Schedule'),
            ('notification', 'Notification')
        ]
    )
    
    # Configuration data
    config_data = models.JSONField(
        default=dict,
        help_text="Configuration parameters and settings"
    )
    
    # Status
    is_enabled = models.BooleanField(default=True)
    
    # Timestamps
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['config_type', 'is_enabled']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.config_name} ({self.get_config_type_display()})"