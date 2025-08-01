"""
DRF serializers for workflow recovery system
Comprehensive serializers for REST API endpoints
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from ..serializers import WorkflowSerializer, WorkflowExecutionSerializer
from .models import (
    WorkflowCheckpoint, WorkflowRecoveryLog, RecoveryStrategy,
    WorkflowReplaySession, RecoveryConfiguration,
    CheckpointType, RecoveryStatus, RecoveryStrategyType
)

User = get_user_model()


class WorkflowCheckpointSerializer(serializers.ModelSerializer):
    """Serializer for workflow checkpoints"""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    execution_id = serializers.CharField(source='execution.id', read_only=True)
    checkpoint_size_mb = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    recovery_count = serializers.SerializerMethodField()
    replay_count = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowCheckpoint
        fields = [
            'id', 'workflow', 'workflow_name', 'execution', 'execution_id',
            'checkpoint_type', 'node_id', 'node_name', 'sequence_number',
            'execution_state', 'context_data', 'node_outputs',
            'description', 'checkpoint_size_bytes', 'checkpoint_size_mb',
            'is_recoverable', 'is_milestone', 'is_expired',
            'recovery_count', 'replay_count',
            'created_at', 'expires_at'
        ]
        read_only_fields = [
            'id', 'sequence_number', 'checkpoint_size_bytes', 'created_at'
        ]
    
    def get_checkpoint_size_mb(self, obj):
        """Get checkpoint size in MB"""
        return obj.get_state_size_mb()
    
    def get_recovery_count(self, obj):
        """Get number of recoveries using this checkpoint"""
        return obj.recovery_logs.count()
    
    def get_replay_count(self, obj):
        """Get number of replays using this checkpoint"""
        return obj.replay_sessions.count()


class WorkflowCheckpointSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for checkpoint lists"""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    checkpoint_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowCheckpoint
        fields = [
            'id', 'workflow_name', 'checkpoint_type', 'sequence_number',
            'node_name', 'checkpoint_size_mb', 'is_recoverable', 'is_milestone',
            'created_at', 'expires_at'
        ]
    
    def get_checkpoint_size_mb(self, obj):
        """Get checkpoint size in MB"""
        return obj.get_state_size_mb()


class RecoveryStrategySerializer(serializers.ModelSerializer):
    """Serializer for recovery strategies"""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    recent_usage = serializers.SerializerMethodField()
    
    class Meta:
        model = RecoveryStrategy
        fields = [
            'id', 'name', 'description', 'strategy_type',
            'workflow', 'workflow_name', 'node_type', 'error_patterns',
            'max_retry_attempts', 'retry_delay_seconds', 'backoff_multiplier',
            'conditions', 'recovery_actions', 'is_active', 'priority',
            'usage_count', 'success_count', 'success_rate', 'recent_usage',
            'last_used_at', 'created_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'usage_count', 'success_count', 'last_used_at',
            'created_at', 'updated_at'
        ]
    
    def get_recent_usage(self, obj):
        """Get recent usage statistics"""
        from django.utils import timezone
        from datetime import timedelta
        
        recent_logs = obj.recovery_logs.filter(
            started_at__gte=timezone.now() - timedelta(days=30)
        )
        
        return {
            'total_attempts': recent_logs.count(),
            'successful_attempts': recent_logs.filter(was_successful=True).count(),
            'last_30_days': recent_logs.count()
        }


class WorkflowRecoveryLogSerializer(serializers.ModelSerializer):
    """Serializer for workflow recovery logs"""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    execution_id = serializers.CharField(source='execution.id', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    checkpoint_sequence = serializers.IntegerField(source='checkpoint.sequence_number', read_only=True)
    triggered_by_username = serializers.CharField(source='triggered_by.username', read_only=True)
    new_execution_id = serializers.CharField(source='new_execution.id', read_only=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowRecoveryLog
        fields = [
            'id', 'workflow', 'workflow_name', 'execution', 'execution_id',
            'checkpoint', 'checkpoint_sequence', 'strategy', 'strategy_name',
            'recovery_type', 'trigger_reason', 'original_error',
            'failed_node_id', 'failed_node_name', 'status', 'attempt_number',
            'recovery_actions_taken', 'recovery_data', 'started_at',
            'completed_at', 'duration_seconds', 'duration_display',
            'was_successful', 'recovery_error', 'new_execution',
            'new_execution_id', 'triggered_by_username', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'duration_seconds', 'created_at', 'updated_at'
        ]
    
    def get_duration_display(self, obj):
        """Get human readable duration"""
        if obj.duration_seconds:
            duration = obj.duration_seconds
            if duration < 60:
                return f"{duration}s"
            elif duration < 3600:
                return f"{duration // 60}m {duration % 60}s"
            else:
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                return f"{hours}h {minutes}m"
        return None


class WorkflowRecoveryLogSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for recovery log lists"""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    strategy_name = serializers.CharField(source='strategy.name', read_only=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowRecoveryLog
        fields = [
            'id', 'workflow_name', 'recovery_type', 'status', 'attempt_number',
            'was_successful', 'strategy_name', 'duration_display', 'started_at'
        ]
    
    def get_duration_display(self, obj):
        """Get human readable duration"""
        if obj.duration_seconds:
            duration = obj.duration_seconds
            if duration < 60:
                return f"{duration}s"
            return f"{duration // 60}m"
        return None


class WorkflowReplaySessionSerializer(serializers.ModelSerializer):
    """Serializer for workflow replay sessions"""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    original_execution_id = serializers.CharField(source='original_execution.id', read_only=True)
    replay_execution_id = serializers.CharField(source='replay_execution.id', read_only=True)
    checkpoint_sequence = serializers.IntegerField(source='replay_from_checkpoint.sequence_number', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    duration_seconds = serializers.IntegerField(read_only=True)
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowReplaySession
        fields = [
            'id', 'workflow', 'workflow_name', 'original_execution',
            'original_execution_id', 'replay_from_checkpoint', 'checkpoint_sequence',
            'replay_type', 'modified_inputs', 'modified_context', 'skip_nodes',
            'debug_mode', 'status', 'replay_execution', 'replay_execution_id',
            'purpose', 'notes', 'created_by_username', 'started_at',
            'completed_at', 'duration_seconds', 'duration_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'replay_execution', 'started_at', 'completed_at',
            'created_at', 'updated_at'
        ]
    
    def get_duration_display(self, obj):
        """Get human readable duration"""
        duration = obj.duration_seconds
        if duration:
            if duration < 60:
                return f"{duration}s"
            elif duration < 3600:
                return f"{duration // 60}m {duration % 60}s"
            else:
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                return f"{hours}h {minutes}m"
        return None


class WorkflowReplaySessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating replay sessions"""
    
    class Meta:
        model = WorkflowReplaySession
        fields = [
            'workflow', 'original_execution', 'replay_from_checkpoint',
            'replay_type', 'modified_inputs', 'modified_context',
            'skip_nodes', 'debug_mode', 'purpose', 'notes'
        ]
    
    def validate(self, data):
        """Validate replay session data"""
        workflow = data.get('workflow')
        original_execution = data.get('original_execution')
        checkpoint = data.get('replay_from_checkpoint')
        
        # Validate execution belongs to workflow
        if original_execution and original_execution.workflow != workflow:
            raise serializers.ValidationError(
                "Original execution must belong to the specified workflow"
            )
        
        # Validate checkpoint belongs to execution
        if checkpoint and checkpoint.execution != original_execution:
            raise serializers.ValidationError(
                "Checkpoint must belong to the original execution"
            )
        
        # Validate checkpoint is not expired
        if checkpoint and checkpoint.is_expired:
            raise serializers.ValidationError(
                "Cannot replay from expired checkpoint"
            )
        
        return data


class RecoveryConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for recovery configuration"""
    
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = RecoveryConfiguration
        fields = [
            'id', 'config_name', 'description', 'auto_checkpoint_enabled',
            'checkpoint_interval_nodes', 'max_checkpoints_per_execution',
            'checkpoint_retention_days', 'auto_recovery_enabled',
            'max_recovery_attempts', 'recovery_delay_minutes',
            'replay_enabled', 'max_concurrent_replays', 'replay_timeout_hours',
            'auto_cleanup_enabled', 'cleanup_interval_days',
            'additional_settings', 'is_active', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReplayComparisonSerializer(serializers.Serializer):
    """Serializer for replay comparison data"""
    
    session_id = serializers.UUIDField()
    original_execution = serializers.DictField()
    replay_execution = serializers.DictField()
    differences = serializers.ListField(child=serializers.DictField())
    node_comparisons = serializers.ListField(child=serializers.DictField())


class FailureAnalysisSerializer(serializers.Serializer):
    """Serializer for failure analysis data"""
    
    period_days = serializers.IntegerField()
    workflow = serializers.CharField()
    total_failures = serializers.IntegerField()
    failure_patterns = serializers.DictField()
    recovery_success_rate = serializers.FloatField()
    common_failure_nodes = serializers.ListField(child=serializers.DictField())
    failure_trends = serializers.ListField(child=serializers.DictField())
    recommendations = serializers.ListField(child=serializers.CharField())


class CheckpointStatisticsSerializer(serializers.Serializer):
    """Serializer for checkpoint statistics"""
    
    period_days = serializers.IntegerField()
    workflow = serializers.CharField()
    total_checkpoints = serializers.IntegerField()
    checkpoint_types = serializers.DictField()
    average_checkpoint_size_mb = serializers.FloatField()
    checkpoint_usage = serializers.DictField()
    cleanup_stats = serializers.DictField()


class RecoveryActionSerializer(serializers.Serializer):
    """Serializer for recovery actions"""
    
    action_type = serializers.ChoiceField(choices=[
        ('create_checkpoint', 'Create Checkpoint'),
        ('recover_workflow', 'Recover Workflow'),
        ('start_replay', 'Start Replay'),
        ('cleanup_checkpoints', 'Cleanup Checkpoints')
    ])
    workflow_id = serializers.UUIDField(required=False)
    execution_id = serializers.UUIDField(required=False)
    checkpoint_id = serializers.UUIDField(required=False)
    strategy_id = serializers.UUIDField(required=False)
    parameters = serializers.DictField(default=dict)


class BulkRecoverySerializer(serializers.Serializer):
    """Serializer for bulk recovery operations"""
    
    execution_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    recovery_strategy_id = serializers.UUIDField(required=False)
    trigger_reason = serializers.CharField(default='manual_bulk_recovery')
    notes = serializers.CharField(required=False, allow_blank=True)


class CheckpointCleanupSerializer(serializers.Serializer):
    """Serializer for checkpoint cleanup operations"""
    
    workflow_id = serializers.UUIDField(required=False)
    days_old = serializers.IntegerField(default=30, min_value=1, max_value=365)
    cleanup_type = serializers.ChoiceField(choices=[
        ('expired', 'Expired Only'),
        ('unused', 'Unused Only'),
        ('all_old', 'All Old Checkpoints')
    ], default='expired')
    dry_run = serializers.BooleanField(default=True)