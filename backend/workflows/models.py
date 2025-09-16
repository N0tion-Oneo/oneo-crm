"""
Workflow automation models for Phase 7
Leverages existing Phase 3 AI infrastructure
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import json
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from tenants.models import Tenant

User = get_user_model()


class WorkflowStatus(models.TextChoices):
    """Workflow status options"""
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    ARCHIVED = 'archived', 'Archived'


class WorkflowTriggerType(models.TextChoices):
    """Available workflow trigger types"""
    MANUAL = 'manual', 'Manual'
    RECORD_CREATED = 'record_created', 'Record Created'
    RECORD_UPDATED = 'record_updated', 'Record Updated'
    RECORD_DELETED = 'record_deleted', 'Record Deleted'
    # FIELD_CHANGED = 'field_changed', 'Field Changed'  # Deprecated - use RECORD_UPDATED with specific_fields
    SCHEDULED = 'scheduled', 'Scheduled'
    WEBHOOK = 'webhook', 'Webhook'
    
    # Enhanced trigger types
    API_ENDPOINT = 'api_endpoint', 'API Endpoint'
    FORM_SUBMITTED = 'form_submitted', 'Form Submitted'
    EMAIL_RECEIVED = 'email_received', 'Email Received'
    MESSAGE_RECEIVED = 'message_received', 'Message Received'
    LINKEDIN_MESSAGE = 'linkedin_message', 'LinkedIn Message'
    WHATSAPP_MESSAGE = 'whatsapp_message', 'WhatsApp Message'
    # STATUS_CHANGED = 'status_changed', 'Status Changed'  # Deprecated - use RECORD_UPDATED with update_type
    DATE_REACHED = 'date_reached', 'Date Reached'
    CONDITION_MET = 'condition_met', 'Condition Met'
    PIPELINE_STAGE_CHANGED = 'pipeline_stage_changed', 'Pipeline Stage Changed'
    ENGAGEMENT_THRESHOLD = 'engagement_threshold', 'Engagement Threshold'
    WORKFLOW_COMPLETED = 'workflow_completed', 'Workflow Completed'


class WorkflowNodeType(models.TextChoices):
    """Available workflow node types"""
    # AI Actions (use ai.integrations.AIIntegrationManager)
    AI_PROMPT = 'ai_prompt', 'AI Prompt'
    AI_ANALYSIS = 'ai_analysis', 'AI Analysis'
    AI_CLASSIFICATION = 'ai_classification', 'AI Classification'  # Deprecated - use AI_ANALYSIS
    AI_CONVERSATION_LOOP = 'ai_conversation_loop', 'AI Conversation Loop'
    
    # Record Operations
    RECORD_CREATE = 'record_create', 'Create Record'
    RECORD_UPDATE = 'record_update', 'Update Record'
    RECORD_DELETE = 'record_delete', 'Delete Record'
    RECORD_FIND = 'record_find', 'Find Records'
    
    # Logic and Control Flow
    CONDITION = 'condition', 'Condition (If/Else)'
    FOR_EACH = 'for_each', 'For Each (Loop)'
    WAIT_DELAY = 'wait_delay', 'Wait/Delay'
    WAIT_FOR_RESPONSE = 'wait_for_response', 'Wait for Response'
    WAIT_FOR_RECORD_EVENT = 'wait_for_record_event', 'Wait for Record Event'
    WAIT_FOR_CONDITION = 'wait_for_condition', 'Wait for Condition'
    
    # External Integration
    HTTP_REQUEST = 'http_request', 'HTTP Request'
    WEBHOOK_OUT = 'webhook_out', 'Send Webhook'
    
    # Human Interaction
    APPROVAL = 'approval', 'Human Approval'
    TASK_NOTIFY = 'task_notify', 'Task/Notification'
    
    # Advanced
    SUB_WORKFLOW = 'sub_workflow', 'Sub-workflow Call'
    REUSABLE_WORKFLOW = 'reusable_workflow', 'Reusable Workflow'  # Deprecated - use SUB_WORKFLOW
    MERGE_DATA = 'merge_data', 'Merge Data'
    
    # Communication Nodes (UniPile Integration)
    UNIPILE_SEND_EMAIL = 'unipile_send_email', 'Send Email via UniPile'
    UNIPILE_SEND_LINKEDIN = 'unipile_send_linkedin', 'Send LinkedIn Message'
    UNIPILE_SEND_WHATSAPP = 'unipile_send_whatsapp', 'Send WhatsApp Message'
    UNIPILE_SEND_SMS = 'unipile_send_sms', 'Send SMS'
    UNIPILE_SYNC_MESSAGES = 'unipile_sync_messages', 'Sync UniPile Messages'
    
    # Message Tracking & Contact Management
    LOG_COMMUNICATION = 'log_communication', 'Log Communication Activity'
    RESOLVE_CONTACT = 'resolve_contact', 'Resolve/Create Contact Record'
    UPDATE_CONTACT_STATUS = 'update_contact_status', 'Update Contact Status'
    CREATE_FOLLOW_UP_TASK = 'create_follow_up_task', 'Create Follow-up Task'
    
    # Communication Analytics
    ANALYZE_COMMUNICATION = 'analyze_communication', 'Analyze Communication Patterns'
    SCORE_ENGAGEMENT = 'score_engagement', 'Score Contact Engagement'


class ExecutionStatus(models.TextChoices):
    """Workflow execution status"""
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    SUCCESS = 'success', 'Success'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    PAUSED = 'paused', 'Paused (Approval)'


class WorkflowVisibility(models.TextChoices):
    """Workflow visibility options"""
    PRIVATE = 'private', 'Private'
    INTERNAL = 'internal', 'Internal (Team)'
    PUBLIC = 'public', 'Public'


class WorkflowCategory(models.TextChoices):
    """Workflow categories for organization"""
    COMMUNICATION = 'communication', 'Communication'
    CRM = 'crm', 'CRM & Sales'
    MARKETING = 'marketing', 'Marketing'
    AUTOMATION = 'automation', 'Automation'
    ANALYTICS = 'analytics', 'Analytics'
    INTEGRATION = 'integration', 'Integration'
    CUSTOM = 'custom', 'Custom'


class Workflow(models.Model):
    """Main workflow definition with reusable workflow support"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflows')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Ownership and access
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_workflows')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Workflow configuration
    status = models.CharField(max_length=20, choices=WorkflowStatus.choices, default=WorkflowStatus.DRAFT)
    version = models.PositiveIntegerField(default=1)
    category = models.CharField(max_length=20, choices=WorkflowCategory.choices, default=WorkflowCategory.CUSTOM)
    
    # Legacy trigger fields - deprecated, use trigger nodes instead
    # trigger_type = models.CharField(max_length=30, choices=WorkflowTriggerType.choices)
    # trigger_config = models.JSONField(default=dict, help_text="Trigger-specific configuration")
    
    # Enhanced execution settings
    max_executions_per_hour = models.PositiveIntegerField(default=100)
    timeout_minutes = models.PositiveIntegerField(default=60)
    retry_count = models.PositiveIntegerField(default=3)
    enable_logging = models.BooleanField(default=True)
    enable_debugging = models.BooleanField(default=False)
    
    # Reusable workflow integration
    uses_reusable_workflows = models.BooleanField(default=False, help_text="Whether this workflow uses reusable workflow components")
    reusable_workflow_dependencies = models.JSONField(default=list, help_text="List of reusable workflow names this workflow depends on")
    
    # Access control and visibility
    visibility = models.CharField(max_length=10, choices=WorkflowVisibility.choices, default=WorkflowVisibility.PRIVATE)
    allowed_users = models.ManyToManyField(User, blank=True, related_name='accessible_workflows')
    allowed_teams = models.JSONField(default=list, help_text="Team IDs that have access to this workflow")
    
    # Workflow definition (stored as JSON for React Flow compatibility)
    workflow_definition = models.JSONField(default=dict, help_text="Complete workflow definition including nodes and edges")
    
    # Performance and analytics
    execution_count = models.PositiveIntegerField(default=0)
    success_rate = models.FloatField(default=0.0, help_text="Success rate as percentage")
    avg_execution_time_ms = models.PositiveIntegerField(default=0)
    last_executed_at = models.DateTimeField(null=True, blank=True)
    
    # Tags and metadata
    tags = models.JSONField(default=list, help_text="Tags for workflow organization and search")
    metadata = models.JSONField(default=dict, help_text="Additional workflow metadata")
    
    class Meta:
        db_table = 'workflows_workflow'
        indexes = [
            models.Index(fields=['status']),  # Removed trigger_type from index
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['category', 'visibility']),
            models.Index(fields=['uses_reusable_workflows']),
            models.Index(fields=['last_executed_at']),
        ]
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
    
    def can_execute(self) -> bool:
        """Check if workflow can be executed"""
        return self.status == WorkflowStatus.ACTIVE
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get workflow nodes from definition"""
        return self.workflow_definition.get('nodes', [])
    
    def get_edges(self) -> List[Dict[str, Any]]:
        """Get workflow edges from definition"""
        return self.workflow_definition.get('edges', [])
    
    def get_reusable_workflow_nodes(self) -> List[Dict[str, Any]]:
        """Get all reusable workflow nodes from definition"""
        nodes = self.get_nodes()
        # Check for both SUB_WORKFLOW with is_reusable flag and legacy REUSABLE_WORKFLOW
        return [node for node in nodes if
                node.get('type') == 'SUB_WORKFLOW' and node.get('data', {}).get('is_reusable', False) or
                node.get('type') == 'REUSABLE_WORKFLOW']  # Legacy support
    
    def extract_reusable_workflow_dependencies(self) -> List[str]:
        """Extract reusable workflow dependencies from workflow definition"""
        dependencies = set()
        reusable_nodes = self.get_reusable_workflow_nodes()
        
        for node in reusable_nodes:
            workflow_name = node.get('data', {}).get('workflow_name')
            if workflow_name:
                dependencies.add(workflow_name)
        
        return list(dependencies)
    
    def update_reusable_dependencies(self) -> bool:
        """Update reusable workflow dependencies and return if changed"""
        new_dependencies = self.extract_reusable_workflow_dependencies()
        old_dependencies = self.reusable_workflow_dependencies
        
        if set(new_dependencies) != set(old_dependencies):
            self.reusable_workflow_dependencies = new_dependencies
            self.uses_reusable_workflows = len(new_dependencies) > 0
            return True
        
        return False
    
    def can_user_access(self, user: User) -> bool:
        """Check if user can access this workflow"""
        if self.created_by == user:
            return True
        
        if self.visibility == WorkflowVisibility.PUBLIC:
            return True
        
        if self.visibility == WorkflowVisibility.INTERNAL:
            # Check if user is in same tenant
            from django.db import connection
            if hasattr(connection, 'tenant') and connection.tenant == self.tenant:
                return True
            return False
        
        return self.allowed_users.filter(id=user.id).exists()
    
    def update_performance_metrics(self, execution_time_ms: int, success: bool):
        """Update workflow performance metrics"""
        self.execution_count += 1
        
        # Update average execution time
        if self.avg_execution_time_ms == 0:
            self.avg_execution_time_ms = execution_time_ms
        else:
            # Rolling average
            self.avg_execution_time_ms = int(
                (self.avg_execution_time_ms * (self.execution_count - 1) + execution_time_ms) / self.execution_count
            )
        
        # Update success rate
        if success:
            success_count = int(self.success_rate * (self.execution_count - 1) / 100) if self.execution_count > 1 else 0
            success_count += 1
            self.success_rate = (success_count / self.execution_count) * 100
        else:
            success_count = int(self.success_rate * (self.execution_count - 1) / 100) if self.execution_count > 1 else 0
            self.success_rate = (success_count / self.execution_count) * 100
        
        from django.utils import timezone
        self.last_executed_at = timezone.now()


class WorkflowExecution(models.Model):
    """Individual workflow execution instance"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflow_executions')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    
    # Execution metadata
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ExecutionStatus.choices, default=ExecutionStatus.PENDING)
    
    # Trigger context
    trigger_data = models.JSONField(default=dict, help_text="Data that triggered this execution")
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Execution context and results
    execution_context = models.JSONField(default=dict, help_text="Shared context across all nodes")
    final_output = models.JSONField(null=True, blank=True, help_text="Final workflow output")
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'workflows_execution'
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['started_at']),
        ]
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.workflow.name} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get execution duration in seconds"""
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
    
    def is_running(self) -> bool:
        """Check if execution is currently running"""
        return self.status == ExecutionStatus.RUNNING


class WorkflowExecutionLog(models.Model):
    """Detailed execution logs for each node"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflow_execution_logs')
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='logs')
    
    # Node identification
    node_id = models.CharField(max_length=255, help_text="Node ID from workflow definition")
    node_type = models.CharField(max_length=30, choices=WorkflowNodeType.choices)
    node_name = models.CharField(max_length=255, blank=True)
    
    # Execution details
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ExecutionStatus.choices, default=ExecutionStatus.PENDING)
    
    # Node input/output
    input_data = models.JSONField(default=dict, help_text="Data passed to this node")
    output_data = models.JSONField(null=True, blank=True, help_text="Data produced by this node")
    
    # Execution context
    execution_details = models.JSONField(default=dict, help_text="Node-specific execution details")
    error_details = models.JSONField(null=True, blank=True, help_text="Error information if node failed")
    
    # Performance metrics
    duration_ms = models.PositiveIntegerField(null=True, blank=True, help_text="Execution duration in milliseconds")
    
    class Meta:
        db_table = 'workflows_execution_log'
        indexes = [
            models.Index(fields=['execution', 'node_id']),
            models.Index(fields=['started_at']),
        ]
        ordering = ['started_at']
    
    def __str__(self):
        return f"{self.execution.workflow.name} - {self.node_name or self.node_id}"


class ApprovalStatus(models.TextChoices):
    """Approval status options"""
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    EXPIRED = 'expired', 'Expired'


class WorkflowApproval(models.Model):
    """Human approval requests for workflow nodes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflow_approvals')
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='approvals')
    
    # Approval metadata
    created_at = models.DateTimeField(auto_now_add=True)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_approvals')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_approvals')
    
    # Approval content
    title = models.CharField(max_length=255)
    description = models.TextField()
    approval_data = models.JSONField(default=dict, help_text="Data requiring approval")
    
    # Enhanced approval settings
    status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    timeout_at = models.DateTimeField(null=True, blank=True, help_text="When approval expires")
    escalation_rules = models.JSONField(default=list, help_text="Escalation rules if not approved in time")
    
    # Response
    responded_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_approvals')
    response_comments = models.TextField(blank=True)
    
    class Meta:
        db_table = 'workflows_approval'
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['timeout_at']),
        ]
    
    def __str__(self):
        return f"Approval: {self.title}"
    
    @property
    def is_pending(self) -> bool:
        """Check if approval is still pending"""
        return self.status == ApprovalStatus.PENDING
    
    def is_expired(self) -> bool:
        """Check if approval has expired"""
        if self.timeout_at:
            from django.utils import timezone
            return timezone.now() > self.timeout_at
        return False


class WorkflowSchedule(models.Model):
    """Scheduled workflow executions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflow_schedules')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='schedules')
    
    # Schedule configuration
    name = models.CharField(max_length=255)
    cron_expression = models.CharField(max_length=255, help_text="Cron expression for scheduling")
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Execution tracking
    last_execution = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField(null=True, blank=True)
    execution_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'workflows_schedule'
        indexes = [
            models.Index(fields=['is_active', 'next_execution']),
        ]
    
    def __str__(self):
        return f"Schedule: {self.name}"


class WorkflowTemplate(models.Model):
    """Predefined workflow templates for quick setup"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflow_templates', null=True, blank=True, help_text="Null for system templates")
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Template metadata
    category = models.CharField(max_length=20, choices=WorkflowCategory.choices)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Template configuration
    is_system_template = models.BooleanField(default=False, help_text="Built-in system template")
    is_active = models.BooleanField(default=True)
    visibility = models.CharField(max_length=10, choices=WorkflowVisibility.choices, default=WorkflowVisibility.PUBLIC)
    
    # Template definition
    template_definition = models.JSONField(help_text="Workflow template structure")
    default_config = models.JSONField(default=dict, help_text="Default configuration values")
    required_fields = models.JSONField(default=list, help_text="Fields that must be configured by user")
    
    # Usage statistics
    usage_count = models.PositiveIntegerField(default=0)
    
    # Tags and metadata
    tags = models.JSONField(default=list)
    
    class Meta:
        db_table = 'workflows_template'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_system_template']),
        ]
    
    def __str__(self):
        return self.name


class WorkflowVersion(models.Model):
    """Version history for workflows"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflow_versions')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='versions')
    
    # Version metadata
    version_number = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Version data
    workflow_definition = models.JSONField(help_text="Workflow definition at this version")
    change_summary = models.TextField(blank=True, help_text="Summary of changes in this version")
    is_active = models.BooleanField(default=False, help_text="Whether this version is currently active")
    
    class Meta:
        db_table = 'workflows_version'
        unique_together = ['workflow', 'version_number']
        indexes = [
            models.Index(fields=['workflow', 'version_number']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.workflow.name} v{self.version_number}"


class WorkflowAnalytics(models.Model):
    """Analytics and performance metrics for workflows"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflow_analytics')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='analytics')
    
    # Time period
    date = models.DateField(help_text="Date for these analytics")
    
    # Execution metrics
    total_executions = models.PositiveIntegerField(default=0)
    successful_executions = models.PositiveIntegerField(default=0)
    failed_executions = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    avg_execution_time_ms = models.PositiveIntegerField(default=0)
    min_execution_time_ms = models.PositiveIntegerField(default=0)
    max_execution_time_ms = models.PositiveIntegerField(default=0)
    
    # Node-specific metrics
    node_performance = models.JSONField(default=dict, help_text="Performance metrics per node type")
    
    # Error tracking
    error_distribution = models.JSONField(default=dict, help_text="Error types and counts")
    most_common_errors = models.JSONField(default=list, help_text="Most common error messages")
    
    class Meta:
        db_table = 'workflows_analytics'
        unique_together = ['workflow', 'date']
        indexes = [
            models.Index(fields=['workflow', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} analytics for {self.date}"


class WorkflowEvent(models.Model):
    """Event log for workflow lifecycle events"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflow_events')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='events')
    execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, null=True, blank=True, related_name='events')
    
    # Event data
    event_type = models.CharField(max_length=50, help_text="Type of event (created, executed, failed, etc.)")
    event_data = models.JSONField(default=dict, help_text="Event-specific data")
    
    # Event metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'workflows_event'
        indexes = [
            models.Index(fields=['workflow', 'event_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['execution']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.workflow.name} - {self.event_type}"