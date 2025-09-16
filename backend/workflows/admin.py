"""
Django admin interface for workflow management
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json
from .models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog,
    WorkflowApproval, WorkflowSchedule, WorkflowTrigger
)


class WorkflowTriggerInline(admin.TabularInline):
    """Inline admin for workflow triggers"""
    model = WorkflowTrigger
    extra = 0
    fields = ['name', 'trigger_type', 'is_active', 'execution_count', 'last_triggered_at']
    readonly_fields = ['execution_count', 'last_triggered_at']
    can_delete = True


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'trigger_type', 'created_by', 'created_at', 'execution_count', 'action_buttons']
    list_filter = ['status', 'trigger_type', 'created_at']
    search_fields = ['name', 'description', 'created_by__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'workflow_definition_display']
    inlines = [WorkflowTriggerInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'status', 'version')
        }),
        ('Trigger Configuration', {
            'fields': ('trigger_type', 'trigger_config_display')
        }),
        ('Execution Settings', {
            'fields': ('max_executions_per_hour', 'timeout_minutes', 'retry_count')
        }),
        ('Access Control', {
            'fields': ('created_by', 'allowed_users', 'visibility')
        }),
        ('Workflow Definition', {
            'fields': ('workflow_definition_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['allowed_users']
    
    def execution_count(self, obj):
        """Show execution count"""
        count = obj.executions.count()
        if count > 0:
            url = reverse('admin:workflows_workflowexecution_changelist')
            return format_html(
                '<a href="{}?workflow__id__exact={}">{} executions</a>',
                url, obj.id, count
            )
        return '0 executions'
    execution_count.short_description = 'Executions'
    
    def action_buttons(self, obj):
        """Show action buttons"""
        buttons = []
        
        if obj.status == 'active':
            buttons.append(
                '<a class="button" href="#" onclick="triggerWorkflow(\'{}\')">Trigger</a>'.format(obj.id)
            )
        
        buttons.append(
            '<a class="button" href="{}">View Executions</a>'.format(
                reverse('admin:workflows_workflowexecution_changelist') + f'?workflow__id__exact={obj.id}'
            )
        )
        
        return format_html(' '.join(buttons))
    action_buttons.short_description = 'Actions'
    action_buttons.allow_tags = True
    
    def workflow_definition_display(self, obj):
        """Display formatted workflow definition"""
        if obj.workflow_definition:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 400px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.workflow_definition, indent=2)
            )
        return 'No definition'
    workflow_definition_display.short_description = 'Workflow Definition'
    
    def trigger_config_display(self, obj):
        """Display formatted trigger configuration"""
        if obj.trigger_config:
            return format_html(
                '<pre style="white-space: pre-wrap;">{}</pre>',
                json.dumps(obj.trigger_config, indent=2)
            )
        return 'No configuration'
    trigger_config_display.short_description = 'Trigger Configuration'
    
    class Media:
        js = ('admin/js/workflow_admin.js',)


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ['workflow_name', 'status', 'started_at', 'duration', 'triggered_by', 'node_count', 'action_buttons']
    list_filter = ['status', 'started_at', 'workflow__name']
    search_fields = ['workflow__name', 'triggered_by__email']
    readonly_fields = ['id', 'started_at', 'completed_at', 'duration_display', 'trigger_data_display', 'final_output_display']
    
    fieldsets = (
        ('Execution Info', {
            'fields': ('id', 'workflow', 'status', 'started_at', 'completed_at', 'duration_display')
        }),
        ('Trigger Information', {
            'fields': ('triggered_by', 'trigger_data_display')
        }),
        ('Results', {
            'fields': ('final_output_display', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Context', {
            'fields': ('execution_context_display',),
            'classes': ('collapse',)
        })
    )
    
    def workflow_name(self, obj):
        """Show workflow name with link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:workflows_workflow_change', args=[obj.workflow.id]),
            obj.workflow.name
        )
    workflow_name.short_description = 'Workflow'
    workflow_name.admin_order_field = 'workflow__name'
    
    def duration(self, obj):
        """Show execution duration"""
        if obj.duration_seconds:
            return f"{obj.duration_seconds}s"
        return '-'
    duration.short_description = 'Duration'
    
    def duration_display(self, obj):
        """Display detailed duration info"""
        if obj.duration_seconds:
            minutes, seconds = divmod(obj.duration_seconds, 60)
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        return 'Not completed'
    duration_display.short_description = 'Duration'
    
    def node_count(self, obj):
        """Show node execution count"""
        count = obj.logs.count()
        if count > 0:
            url = reverse('admin:workflows_workflowexecutionlog_changelist')
            return format_html(
                '<a href="{}?execution__id__exact={}">{} nodes</a>',
                url, obj.id, count
            )
        return '0 nodes'
    node_count.short_description = 'Nodes'
    
    def action_buttons(self, obj):
        """Show action buttons"""
        buttons = []
        
        buttons.append(
            '<a class="button" href="{}">View Logs</a>'.format(
                reverse('admin:workflows_workflowexecutionlog_changelist') + f'?execution__id__exact={obj.id}'
            )
        )
        
        if obj.status == 'failed' and obj.workflow.status == 'active':
            buttons.append(
                '<a class="button" href="#" onclick="retryExecution(\'{}\')">Retry</a>'.format(obj.id)
            )
        
        return format_html(' '.join(buttons))
    action_buttons.short_description = 'Actions'
    action_buttons.allow_tags = True
    
    def trigger_data_display(self, obj):
        """Display formatted trigger data"""
        if obj.trigger_data:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.trigger_data, indent=2)
            )
        return 'No trigger data'
    trigger_data_display.short_description = 'Trigger Data'
    
    def final_output_display(self, obj):
        """Display formatted final output"""
        if obj.final_output:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.final_output, indent=2)
            )
        return 'No output'
    final_output_display.short_description = 'Final Output'
    
    def execution_context_display(self, obj):
        """Display formatted execution context"""
        if obj.execution_context:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.execution_context, indent=2)
            )
        return 'No context'
    execution_context_display.short_description = 'Execution Context'


@admin.register(WorkflowTrigger)
class WorkflowTriggerAdmin(admin.ModelAdmin):
    """Admin interface for workflow triggers"""
    list_display = ['name', 'workflow', 'trigger_type', 'is_active', 'execution_count', 'last_triggered_at']
    list_filter = ['trigger_type', 'is_active', 'created_at']
    search_fields = ['name', 'workflow__name', 'description']
    readonly_fields = ['id', 'created_at', 'last_triggered_at', 'execution_count', 'trigger_config_display']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'workflow', 'name', 'description', 'trigger_type')
        }),
        ('Configuration', {
            'fields': ('is_active', 'trigger_config_display', 'conditions')
        }),
        ('Rate Limiting', {
            'fields': ('max_executions_per_minute', 'max_executions_per_hour', 'max_executions_per_day')
        }),
        ('Statistics', {
            'fields': ('execution_count', 'last_triggered_at', 'created_at'),
            'classes': ('collapse',)
        })
    )

    def trigger_config_display(self, obj):
        """Display formatted trigger configuration"""
        if obj.trigger_config:
            return format_html(
                '<pre style="white-space: pre-wrap;">{}</pre>',
                json.dumps(obj.trigger_config, indent=2)
            )
        return 'No configuration'
    trigger_config_display.short_description = 'Trigger Configuration'


@admin.register(WorkflowExecutionLog)
class WorkflowExecutionLogAdmin(admin.ModelAdmin):
    list_display = ['node_name', 'node_type', 'status', 'execution_workflow', 'started_at', 'duration_ms', 'action_buttons']
    list_filter = ['status', 'node_type', 'started_at']
    search_fields = ['node_name', 'node_id', 'execution__workflow__name']
    readonly_fields = ['id', 'started_at', 'completed_at', 'input_data_display', 'output_data_display', 'error_details_display']
    
    fieldsets = (
        ('Node Information', {
            'fields': ('id', 'execution', 'node_id', 'node_type', 'node_name')
        }),
        ('Execution Details', {
            'fields': ('status', 'started_at', 'completed_at', 'duration_ms')
        }),
        ('Data', {
            'fields': ('input_data_display', 'output_data_display'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_details_display',),
            'classes': ('collapse',)
        })
    )
    
    def execution_workflow(self, obj):
        """Show workflow name"""
        return obj.execution.workflow.name
    execution_workflow.short_description = 'Workflow'
    execution_workflow.admin_order_field = 'execution__workflow__name'
    
    def action_buttons(self, obj):
        """Show action buttons"""
        return format_html(
            '<a class="button" href="{}">View Execution</a>',
            reverse('admin:workflows_workflowexecution_change', args=[obj.execution.id])
        )
    action_buttons.short_description = 'Actions'
    action_buttons.allow_tags = True
    
    def input_data_display(self, obj):
        """Display formatted input data"""
        if obj.input_data:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.input_data, indent=2)
            )
        return 'No input data'
    input_data_display.short_description = 'Input Data'
    
    def output_data_display(self, obj):
        """Display formatted output data"""
        if obj.output_data:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.output_data, indent=2)
            )
        return 'No output data'
    output_data_display.short_description = 'Output Data'
    
    def error_details_display(self, obj):
        """Display formatted error details"""
        if obj.error_details:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto; color: red;">{}</pre>',
                json.dumps(obj.error_details, indent=2)
            )
        return 'No errors'
    error_details_display.short_description = 'Error Details'


@admin.register(WorkflowApproval)
class WorkflowApprovalAdmin(admin.ModelAdmin):
    list_display = ['title', 'execution_workflow', 'assigned_to', 'created_at', 'approval_status', 'action_buttons']
    list_filter = ['status', 'created_at', 'assigned_to']
    search_fields = ['title', 'description', 'assigned_to__email', 'execution__workflow__name']
    readonly_fields = ['id', 'execution', 'created_at', 'responded_at', 'approval_data_display']
    
    fieldsets = (
        ('Approval Request', {
            'fields': ('id', 'execution', 'title', 'description')
        }),
        ('Assignment', {
            'fields': ('requested_by', 'assigned_to', 'created_at')
        }),
        ('Response', {
            'fields': ('status', 'responded_at', 'responded_by', 'response_comments')
        }),
        ('Data', {
            'fields': ('approval_data_display',),
            'classes': ('collapse',)
        })
    )
    
    def execution_workflow(self, obj):
        """Show workflow name"""
        return obj.execution.workflow.name
    execution_workflow.short_description = 'Workflow'
    execution_workflow.admin_order_field = 'execution__workflow__name'
    
    def approval_status(self, obj):
        """Show approval status with color"""
        status = obj.status
        if status == 'pending':
            return format_html('<span style="color: orange;">Pending</span>')
        elif status == 'approved':
            return format_html('<span style="color: green;">Approved</span>')
        elif status == 'rejected':
            return format_html('<span style="color: red;">Rejected</span>')
        elif status == 'expired':
            return format_html('<span style="color: gray;">Expired</span>')
        else:
            return status
    approval_status.short_description = 'Status'
    
    def action_buttons(self, obj):
        """Show action buttons"""
        buttons = []
        
        if obj.status == 'pending':
            buttons.extend([
                '<a class="button" href="#" onclick="approveRequest(\'{}\', true)">Approve</a>'.format(obj.id),
                '<a class="button" href="#" onclick="approveRequest(\'{}\', false)">Reject</a>'.format(obj.id)
            ])
        
        buttons.append(
            '<a class="button" href="{}">View Execution</a>'.format(
                reverse('admin:workflows_workflowexecution_change', args=[obj.execution.id])
            )
        )
        
        return format_html(' '.join(buttons))
    action_buttons.short_description = 'Actions'
    action_buttons.allow_tags = True
    
    def approval_data_display(self, obj):
        """Display formatted approval data"""
        if obj.approval_data:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.approval_data, indent=2)
            )
        return 'No data'
    approval_data_display.short_description = 'Approval Data'


@admin.register(WorkflowSchedule)
class WorkflowScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'workflow', 'cron_expression', 'is_active', 'next_execution', 'execution_count', 'action_buttons']
    list_filter = ['is_active', 'timezone', 'created_at']
    search_fields = ['name', 'workflow__name', 'cron_expression']
    readonly_fields = ['id', 'created_at', 'last_execution', 'next_execution_display']
    
    fieldsets = (
        ('Schedule Information', {
            'fields': ('id', 'workflow', 'name', 'is_active')
        }),
        ('Schedule Configuration', {
            'fields': ('cron_expression', 'timezone')
        }),
        ('Execution Tracking', {
            'fields': ('created_at', 'last_execution', 'next_execution_display', 'execution_count')
        })
    )
    
    def next_execution_display(self, obj):
        """Display next execution time with timezone"""
        if obj.next_execution:
            return f"{obj.next_execution} ({obj.timezone})"
        return 'Not scheduled'
    next_execution_display.short_description = 'Next Execution'
    
    def action_buttons(self, obj):
        """Show action buttons"""
        buttons = []
        
        if obj.is_active:
            buttons.append(
                '<a class="button" href="#" onclick="pauseSchedule(\'{}\')">Pause</a>'.format(obj.id)
            )
        else:
            buttons.append(
                '<a class="button" href="#" onclick="resumeSchedule(\'{}\')">Resume</a>'.format(obj.id)
            )
        
        buttons.append(
            '<a class="button" href="#" onclick="triggerSchedule(\'{}\')">Run Now</a>'.format(obj.id)
        )
        
        return format_html(' '.join(buttons))
    action_buttons.short_description = 'Actions'
    action_buttons.allow_tags = True