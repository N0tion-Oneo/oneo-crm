"""
Django admin interface for workflow recovery system
Rich admin interfaces for managing checkpoints, recovery strategies, and replay sessions
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    WorkflowCheckpoint, WorkflowRecoveryLog, RecoveryStrategy,
    WorkflowReplaySession, RecoveryConfiguration
)


@admin.register(WorkflowCheckpoint)
class WorkflowCheckpointAdmin(admin.ModelAdmin):
    """Admin interface for workflow checkpoints"""
    
    list_display = [
        'sequence_number', 'workflow_name', 'execution_link', 'checkpoint_type',
        'node_name', 'checkpoint_size_display', 'is_recoverable', 'is_milestone',
        'created_at', 'expires_at'
    ]
    list_filter = [
        'checkpoint_type', 'is_recoverable', 'is_milestone', 'created_at',
        'workflow__name'
    ]
    search_fields = [
        'workflow__name', 'execution__id', 'node_name', 'description'
    ]
    readonly_fields = [
        'id', 'sequence_number', 'checkpoint_size_bytes', 'created_at',
        'execution_state_display', 'context_data_display', 'node_outputs_display'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'workflow', 'execution', 'sequence_number')
        }),
        ('Checkpoint Details', {
            'fields': (
                'checkpoint_type', 'node_id', 'node_name', 'description',
                'is_recoverable', 'is_milestone'
            )
        }),
        ('State Data', {
            'fields': ('execution_state_display', 'context_data_display', 'node_outputs_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('checkpoint_size_bytes', 'created_at', 'expires_at')
        })
    )
    
    def workflow_name(self, obj):
        """Display workflow name"""
        return obj.workflow.name if obj.workflow else 'Unknown'
    workflow_name.short_description = 'Workflow'
    
    def execution_link(self, obj):
        """Link to execution admin"""
        if obj.execution:
            url = reverse('admin:workflows_workflowexecution_change', args=[obj.execution.id])
            return format_html('<a href="{}">{}</a>', url, str(obj.execution.id)[:8])
        return 'No execution'
    execution_link.short_description = 'Execution'
    
    def checkpoint_size_display(self, obj):
        """Display checkpoint size in human readable format"""
        if obj.checkpoint_size_bytes:
            size_mb = obj.checkpoint_size_bytes / (1024 * 1024)
            if size_mb < 1:
                return f"{obj.checkpoint_size_bytes / 1024:.1f} KB"
            return f"{size_mb:.2f} MB"
        return 'Unknown'
    checkpoint_size_display.short_description = 'Size'
    
    def execution_state_display(self, obj):
        """Display formatted execution state"""
        if obj.execution_state:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.execution_state, indent=2))
        return 'No state data'
    execution_state_display.short_description = 'Execution State'
    
    def context_data_display(self, obj):
        """Display formatted context data"""
        if obj.context_data:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.context_data, indent=2))
        return 'No context data'
    context_data_display.short_description = 'Context Data'
    
    def node_outputs_display(self, obj):
        """Display formatted node outputs"""
        if obj.node_outputs:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.node_outputs, indent=2))
        return 'No output data'
    node_outputs_display.short_description = 'Node Outputs'


@admin.register(RecoveryStrategy)
class RecoveryStrategyAdmin(admin.ModelAdmin):
    """Admin interface for recovery strategies"""
    
    list_display = [
        'name', 'strategy_type', 'workflow_scope', 'priority', 'success_rate_display',
        'usage_count', 'is_active', 'last_used_at'
    ]
    list_filter = [
        'strategy_type', 'is_active', 'workflow', 'node_type', 'created_at'
    ]
    search_fields = ['name', 'description', 'workflow__name', 'node_type']
    readonly_fields = [
        'id', 'usage_count', 'success_count', 'success_rate_display',
        'last_used_at', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'strategy_type', 'workflow', 'node_type')
        }),
        ('Strategy Configuration', {
            'fields': (
                'error_patterns', 'conditions', 'recovery_actions',
                'max_retry_attempts', 'retry_delay_seconds', 'backoff_multiplier'
            )
        }),
        ('Status & Priority', {
            'fields': ('is_active', 'priority')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'success_count', 'success_rate_display', 'last_used_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def workflow_scope(self, obj):
        """Display workflow scope"""
        return obj.workflow.name if obj.workflow else 'Global'
    workflow_scope.short_description = 'Scope'
    
    def success_rate_display(self, obj):
        """Display success rate with color coding"""
        rate = obj.success_rate
        if rate >= 80:
            color = 'green'
        elif rate >= 50:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {}">{:.1f}%</span>', color, rate)
    success_rate_display.short_description = 'Success Rate'


@admin.register(WorkflowRecoveryLog)
class WorkflowRecoveryLogAdmin(admin.ModelAdmin):
    """Admin interface for workflow recovery logs"""
    
    list_display = [
        'workflow_name', 'recovery_type', 'attempt_number', 'status_display',
        'trigger_reason', 'was_successful', 'duration_display', 'started_at'
    ]
    list_filter = [
        'recovery_type', 'status', 'trigger_reason', 'was_successful',
        'started_at', 'workflow__name'
    ]
    search_fields = [
        'workflow__name', 'execution__id', 'original_error',
        'failed_node_name', 'recovery_error'
    ]
    readonly_fields = [
        'id', 'started_at', 'completed_at', 'duration_seconds',
        'created_at', 'updated_at', 'recovery_actions_display',
        'recovery_data_display'
    ]
    
    fieldsets = (
        ('Recovery Information', {
            'fields': (
                'workflow', 'execution', 'recovery_type', 'trigger_reason',
                'attempt_number', 'strategy', 'checkpoint'
            )
        }),
        ('Error Details', {
            'fields': (
                'original_error', 'failed_node_id', 'failed_node_name'
            )
        }),
        ('Recovery Process', {
            'fields': (
                'status', 'recovery_actions_display', 'recovery_data_display'
            )
        }),
        ('Timing & Results', {
            'fields': (
                'started_at', 'completed_at', 'duration_seconds',
                'was_successful', 'recovery_error', 'new_execution'
            )
        }),
        ('Metadata', {
            'fields': ('triggered_by', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def workflow_name(self, obj):
        """Display workflow name"""
        return obj.workflow.name if obj.workflow else 'Unknown'
    workflow_name.short_description = 'Workflow'
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': 'blue',
            'in_progress': 'orange',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {}">{}</span>', color, obj.get_status_display())
    status_display.short_description = 'Status'
    
    def duration_display(self, obj):
        """Display duration in human readable format"""
        if obj.duration_seconds:
            if obj.duration_seconds < 60:
                return f"{obj.duration_seconds}s"
            elif obj.duration_seconds < 3600:
                return f"{obj.duration_seconds // 60}m {obj.duration_seconds % 60}s"
            else:
                hours = obj.duration_seconds // 3600
                minutes = (obj.duration_seconds % 3600) // 60
                return f"{hours}h {minutes}m"
        return 'N/A'
    duration_display.short_description = 'Duration'
    
    def recovery_actions_display(self, obj):
        """Display formatted recovery actions"""
        if obj.recovery_actions_taken:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.recovery_actions_taken, indent=2))
        return 'No actions recorded'
    recovery_actions_display.short_description = 'Recovery Actions'
    
    def recovery_data_display(self, obj):
        """Display formatted recovery data"""
        if obj.recovery_data:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.recovery_data, indent=2))
        return 'No recovery data'
    recovery_data_display.short_description = 'Recovery Data'


@admin.register(WorkflowReplaySession)
class WorkflowReplaySessionAdmin(admin.ModelAdmin):
    """Admin interface for workflow replay sessions"""
    
    list_display = [
        'workflow_name', 'replay_type', 'status_display', 'debug_mode',
        'duration_display', 'created_by', 'created_at'
    ]
    list_filter = [
        'replay_type', 'status', 'debug_mode', 'created_at', 'workflow__name'
    ]
    search_fields = [
        'workflow__name', 'original_execution__id', 'purpose', 'notes'
    ]
    readonly_fields = [
        'id', 'duration_seconds', 'created_at', 'updated_at',
        'modified_inputs_display', 'modified_context_display', 'skip_nodes_display'
    ]
    
    fieldsets = (
        ('Replay Configuration', {
            'fields': (
                'workflow', 'original_execution', 'replay_from_checkpoint',
                'replay_type', 'debug_mode'
            )
        }),
        ('Replay Parameters', {
            'fields': (
                'modified_inputs_display', 'modified_context_display', 'skip_nodes_display'
            )
        }),
        ('Session Status', {
            'fields': ('status', 'started_at', 'completed_at', 'replay_execution')
        }),
        ('Session Details', {
            'fields': ('purpose', 'notes', 'created_by', 'created_at', 'updated_at')
        })
    )
    
    def workflow_name(self, obj):
        """Display workflow name"""
        return obj.workflow.name if obj.workflow else 'Unknown'
    workflow_name.short_description = 'Workflow'
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'created': 'blue',
            'running': 'orange',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {}">{}</span>', color, obj.get_status_display())
    status_display.short_description = 'Status'
    
    def duration_display(self, obj):
        """Display duration in human readable format"""
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
        return 'N/A'
    duration_display.short_description = 'Duration'
    
    def modified_inputs_display(self, obj):
        """Display formatted modified inputs"""
        if obj.modified_inputs:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.modified_inputs, indent=2))
        return 'No modified inputs'
    modified_inputs_display.short_description = 'Modified Inputs'
    
    def modified_context_display(self, obj):
        """Display formatted modified context"""
        if obj.modified_context:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.modified_context, indent=2))
        return 'No modified context'
    modified_context_display.short_description = 'Modified Context'
    
    def skip_nodes_display(self, obj):
        """Display skip nodes list"""
        if obj.skip_nodes:
            return ', '.join(obj.skip_nodes)
        return 'No nodes skipped'
    skip_nodes_display.short_description = 'Skip Nodes'


@admin.register(RecoveryConfiguration)
class RecoveryConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for recovery configuration"""
    
    list_display = [
        'config_name', 'is_active', 'auto_checkpoint_enabled', 'auto_recovery_enabled',
        'replay_enabled', 'checkpoint_retention_days', 'max_recovery_attempts'
    ]
    list_filter = [
        'is_active', 'auto_checkpoint_enabled', 'auto_recovery_enabled',
        'replay_enabled', 'auto_cleanup_enabled'
    ]
    search_fields = ['config_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'additional_settings_display']
    
    fieldsets = (
        ('Configuration Identity', {
            'fields': ('config_name', 'description', 'is_active')
        }),
        ('Checkpoint Settings', {
            'fields': (
                'auto_checkpoint_enabled', 'checkpoint_interval_nodes',
                'max_checkpoints_per_execution', 'checkpoint_retention_days'
            )
        }),
        ('Recovery Settings', {
            'fields': (
                'auto_recovery_enabled', 'max_recovery_attempts', 'recovery_delay_minutes'
            )
        }),
        ('Replay Settings', {
            'fields': (
                'replay_enabled', 'max_concurrent_replays', 'replay_timeout_hours'
            )
        }),
        ('Cleanup Settings', {
            'fields': ('auto_cleanup_enabled', 'cleanup_interval_days')
        }),
        ('Advanced Settings', {
            'fields': ('additional_settings_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def additional_settings_display(self, obj):
        """Display formatted additional settings"""
        if obj.additional_settings:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.additional_settings, indent=2))
        return 'No additional settings'
    additional_settings_display.short_description = 'Additional Settings'


# Custom admin actions
def mark_checkpoints_expired(modeladmin, request, queryset):
    """Mark selected checkpoints as expired"""
    updated = queryset.update(expires_at=timezone.now())
    modeladmin.message_user(
        request, 
        f"{updated} checkpoints marked as expired."
    )
mark_checkpoints_expired.short_description = "Mark selected checkpoints as expired"

def activate_recovery_strategies(modeladmin, request, queryset):
    """Activate selected recovery strategies"""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(
        request, 
        f"{updated} recovery strategies activated."
    )
activate_recovery_strategies.short_description = "Activate selected strategies"

def deactivate_recovery_strategies(modeladmin, request, queryset):
    """Deactivate selected recovery strategies"""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(
        request, 
        f"{updated} recovery strategies deactivated."
    )
deactivate_recovery_strategies.short_description = "Deactivate selected strategies"

# Add actions to admin classes
WorkflowCheckpointAdmin.actions = [mark_checkpoints_expired]
RecoveryStrategyAdmin.actions = [activate_recovery_strategies, deactivate_recovery_strategies]