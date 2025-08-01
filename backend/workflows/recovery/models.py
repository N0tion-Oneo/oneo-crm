"""
Models for workflow replay and recovery system
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from ..models import Workflow, WorkflowExecution, WorkflowExecutionLog

User = get_user_model()


class CheckpointType(models.TextChoices):
    """Types of workflow checkpoints"""
    AUTO = 'auto', 'Automatic'
    MANUAL = 'manual', 'Manual'
    NODE_COMPLETION = 'node_completion', 'Node Completion'
    ERROR_BOUNDARY = 'error_boundary', 'Error Boundary'
    MILESTONE = 'milestone', 'Milestone'


class RecoveryStatus(models.TextChoices):
    """Status of recovery operations"""
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'


class RecoveryStrategyType(models.TextChoices):
    """Types of recovery strategies"""
    RETRY = 'retry', 'Retry from Last Checkpoint'
    ROLLBACK = 'rollback', 'Rollback to Previous State'
    SKIP = 'skip', 'Skip Failed Node'
    MANUAL = 'manual', 'Manual Intervention'
    RESTART = 'restart', 'Restart from Beginning'


class WorkflowCheckpoint(models.Model):
    """
    Workflow execution checkpoints for replay and recovery
    Stores execution state at specific points for recovery purposes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='checkpoints')
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='checkpoints')
    
    # Checkpoint details
    checkpoint_type = models.CharField(max_length=20, choices=CheckpointType.choices)
    node_id = models.CharField(max_length=100, blank=True)
    node_name = models.CharField(max_length=200, blank=True)
    sequence_number = models.IntegerField(help_text="Sequential order of checkpoints")
    
    # State data
    execution_state = models.JSONField(
        default=dict,
        help_text="Complete execution state at checkpoint"
    )
    context_data = models.JSONField(
        default=dict,
        help_text="Workflow context and variables at checkpoint"
    )
    node_outputs = models.JSONField(
        default=dict,
        help_text="Outputs from completed nodes"
    )
    
    # Checkpoint metadata
    description = models.TextField(blank=True)
    checkpoint_size_bytes = models.IntegerField(null=True, blank=True)
    
    # Status
    is_recoverable = models.BooleanField(
        default=True,
        help_text="Whether this checkpoint can be used for recovery"
    )
    is_milestone = models.BooleanField(
        default=False,
        help_text="Whether this is a milestone checkpoint"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When this checkpoint expires and can be cleaned up"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['execution', 'sequence_number']),
            models.Index(fields=['workflow', 'created_at']),
            models.Index(fields=['checkpoint_type', 'is_recoverable']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = ['execution', 'sequence_number']
        
    def __str__(self):
        return f"Checkpoint {self.sequence_number} - {self.workflow.name}"
    
    @property
    def is_expired(self) -> bool:
        """Check if checkpoint has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def get_state_size_mb(self) -> float:
        """Get checkpoint state size in MB"""
        if self.checkpoint_size_bytes:
            return self.checkpoint_size_bytes / (1024 * 1024)
        return 0.0


class RecoveryStrategy(models.Model):
    """
    Recovery strategies for different types of workflow failures
    Defines how to handle specific failure scenarios
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Strategy identification
    name = models.CharField(max_length=200)
    description = models.TextField()
    strategy_type = models.CharField(max_length=20, choices=RecoveryStrategyType.choices)
    
    # Strategy configuration
    workflow = models.ForeignKey(
        Workflow, 
        on_delete=models.CASCADE, 
        related_name='recovery_strategies',
        null=True, blank=True,
        help_text="Specific workflow (null for global strategies)"
    )
    node_type = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Node type this strategy applies to"
    )
    error_patterns = models.JSONField(
        default=list,
        help_text="Error patterns that trigger this strategy"
    )
    
    # Strategy parameters
    max_retry_attempts = models.IntegerField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    retry_delay_seconds = models.IntegerField(
        default=60,
        validators=[MinValueValidator(0), MaxValueValidator(3600)]
    )
    backoff_multiplier = models.DecimalField(
        max_digits=3, decimal_places=2,
        default=Decimal('1.5'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Conditions
    conditions = models.JSONField(
        default=dict,
        help_text="Conditions that must be met for this strategy to apply"
    )
    
    # Strategy actions
    recovery_actions = models.JSONField(
        default=list,
        help_text="Ordered list of recovery actions to perform"
    )
    
    # Status and priorities
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Strategy priority (higher numbers = higher priority)"
    )
    
    # Usage statistics
    usage_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['workflow', 'is_active']),
            models.Index(fields=['strategy_type', 'priority']),
            models.Index(fields=['node_type', 'is_active']),
            models.Index(fields=['priority', 'is_active']),
        ]
        
    def __str__(self):
        scope = f"({self.workflow.name})" if self.workflow else "(Global)"
        return f"{self.name} {scope}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.usage_count == 0:
            return 0.0
        return (self.success_count / self.usage_count) * 100
    
    def matches_error(self, error_message: str, node_type: str = None) -> bool:
        """Check if this strategy matches the given error"""
        # Check node type
        if self.node_type and node_type and self.node_type != node_type:
            return False
        
        # Check error patterns
        if self.error_patterns:
            for pattern in self.error_patterns:
                if pattern.lower() in error_message.lower():
                    return True
            return False
        
        return True  # No specific patterns means it matches all errors


class WorkflowRecoveryLog(models.Model):
    """
    Log of workflow recovery operations
    Tracks recovery attempts, strategies used, and outcomes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='recovery_logs')
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='recovery_logs')
    checkpoint = models.ForeignKey(
        WorkflowCheckpoint, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='recovery_logs'
    )
    strategy = models.ForeignKey(
        RecoveryStrategy,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='recovery_logs'
    )
    
    # Recovery details
    recovery_type = models.CharField(max_length=20, choices=RecoveryStrategyType.choices)
    trigger_reason = models.CharField(
        max_length=100,
        choices=[
            ('execution_failed', 'Execution Failed'),
            ('node_error', 'Node Error'),
            ('timeout', 'Timeout'),
            ('manual_trigger', 'Manual Trigger'),
            ('system_error', 'System Error'),
            ('resource_unavailable', 'Resource Unavailable')
        ]
    )
    
    # Error information
    original_error = models.TextField(blank=True)
    failed_node_id = models.CharField(max_length=100, blank=True)
    failed_node_name = models.CharField(max_length=200, blank=True)
    
    # Recovery process
    status = models.CharField(max_length=20, choices=RecoveryStatus.choices, default=RecoveryStatus.PENDING)
    attempt_number = models.IntegerField(default=1)
    
    # Recovery actions
    recovery_actions_taken = models.JSONField(
        default=list,
        help_text="List of recovery actions that were performed"
    )
    recovery_data = models.JSONField(
        default=dict,
        help_text="Additional recovery data and context"
    )
    
    # Timing
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    # Results
    was_successful = models.BooleanField(null=True, blank=True)
    recovery_error = models.TextField(blank=True)
    new_execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='recovered_from_logs',
        help_text="New execution created by recovery"
    )
    
    # Metadata
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['execution', 'started_at']),
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['recovery_type', 'was_successful']),
            models.Index(fields=['trigger_reason', 'started_at']),
            models.Index(fields=['status', 'started_at']),
        ]
        
    def __str__(self):
        return f"Recovery {self.recovery_type} - {self.workflow.name} (#{self.attempt_number})"
    
    def mark_completed(self, success: bool, error: str = None) -> None:
        """Mark recovery as completed"""
        self.completed_at = timezone.now()
        self.was_successful = success
        self.status = RecoveryStatus.COMPLETED if success else RecoveryStatus.FAILED
        
        if error:
            self.recovery_error = error
        
        # Calculate duration
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        self.save()
    
    @property
    def is_completed(self) -> bool:
        """Check if recovery is completed"""
        return self.status in [RecoveryStatus.COMPLETED, RecoveryStatus.FAILED, RecoveryStatus.CANCELLED]


class WorkflowReplaySession(models.Model):
    """
    Workflow replay sessions for debugging and analysis
    Allows replaying workflow executions with different parameters
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='replay_sessions')
    original_execution = models.ForeignKey(
        WorkflowExecution, 
        on_delete=models.CASCADE, 
        related_name='replay_sessions'
    )
    
    # Replay configuration
    replay_from_checkpoint = models.ForeignKey(
        WorkflowCheckpoint,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Checkpoint to replay from (null = from beginning)"
    )
    replay_type = models.CharField(
        max_length=20,
        choices=[
            ('full', 'Full Replay'),
            ('partial', 'Partial Replay'),
            ('debug', 'Debug Replay'),
            ('test', 'Test Replay')
        ]
    )
    
    # Replay parameters
    modified_inputs = models.JSONField(
        default=dict,
        help_text="Modified inputs for replay"
    )
    modified_context = models.JSONField(
        default=dict,
        help_text="Modified context variables for replay"
    )
    skip_nodes = models.JSONField(
        default=list,
        help_text="Node IDs to skip during replay"
    )
    debug_mode = models.BooleanField(default=False)
    
    # Session status
    status = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Created'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled')
        ],
        default='created'
    )
    
    # Replay results
    replay_execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='replay_session',
        help_text="New execution created by replay"
    )
    
    # Session metadata
    purpose = models.TextField(blank=True, help_text="Purpose of this replay session")
    notes = models.TextField(blank=True)
    
    # Session management
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['workflow', 'created_at']),
            models.Index(fields=['original_execution', 'status']),
            models.Index(fields=['replay_type', 'status']),
            models.Index(fields=['created_by', 'created_at']),
        ]
        
    def __str__(self):
        return f"Replay {self.replay_type} - {self.workflow.name}"
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get replay duration in seconds"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class RecoveryConfiguration(models.Model):
    """
    Configuration settings for recovery system
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Configuration identification
    config_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Checkpoint settings
    auto_checkpoint_enabled = models.BooleanField(default=True)
    checkpoint_interval_nodes = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Create checkpoint every N nodes"
    )
    max_checkpoints_per_execution = models.IntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    checkpoint_retention_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    
    # Recovery settings
    auto_recovery_enabled = models.BooleanField(default=True)
    max_recovery_attempts = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    recovery_delay_minutes = models.IntegerField(
        default=5,
        validators=[MinValueValidator(0), MaxValueValidator(60)]
    )
    
    # Replay settings
    replay_enabled = models.BooleanField(default=True)
    max_concurrent_replays = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    replay_timeout_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(72)]
    )
    
    # Cleanup settings
    auto_cleanup_enabled = models.BooleanField(default=True)
    cleanup_interval_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(30)]
    )
    
    # Advanced settings
    additional_settings = models.JSONField(
        default=dict,
        help_text="Additional configuration parameters"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return self.config_name