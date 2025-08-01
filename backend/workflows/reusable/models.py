"""
Reusable Workflow Models for composable workflow building blocks
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from workflows.models import WorkflowExecution, ExecutionStatus

User = get_user_model()


class ReusableWorkflow(models.Model):
    """Reusable workflow definitions that can be embedded in other workflows"""
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)
    version = models.CharField(max_length=20, default="1.0")
    
    # Schema definitions
    input_schema = models.JSONField(help_text="Expected inputs with types/validation")
    output_schema = models.JSONField(help_text="Guaranteed outputs with types")
    
    # The actual workflow logic
    workflow_definition = models.JSONField()
    
    # Metadata
    is_public = models.BooleanField(default=False, help_text="Available to all tenants")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Performance metrics
    avg_execution_time_ms = models.PositiveIntegerField(null=True, blank=True)
    success_rate = models.FloatField(default=1.0)
    
    class Meta:
        unique_together = ['name', 'version']
        indexes = [
            models.Index(fields=['category', 'is_public']),
            models.Index(fields=['name', 'version']),
            models.Index(fields=['-usage_count']),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    def increment_usage(self):
        """Increment usage counter and update last used timestamp"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])
    
    def update_performance_metrics(self, execution_time_ms: int, success: bool):
        """Update performance metrics based on execution results"""
        if self.avg_execution_time_ms is None:
            self.avg_execution_time_ms = execution_time_ms
        else:
            # Rolling average with weight towards recent executions
            self.avg_execution_time_ms = int(
                (self.avg_execution_time_ms * 0.8) + (execution_time_ms * 0.2)
            )
        
        # Update success rate
        total_executions = self.usage_count
        if total_executions > 0:
            current_successes = self.success_rate * (total_executions - 1)
            new_successes = current_successes + (1 if success else 0)
            self.success_rate = new_successes / total_executions
        
        self.save(update_fields=['avg_execution_time_ms', 'success_rate'])


class ReusableWorkflowExecution(models.Model):
    """Track executions of reusable workflows within parent workflows"""
    parent_execution = models.ForeignKey(
        WorkflowExecution, 
        on_delete=models.CASCADE,
        related_name='reusable_executions'
    )
    reusable_workflow = models.ForeignKey(
        ReusableWorkflow, 
        on_delete=models.CASCADE,
        related_name='executions'
    )
    parent_node_id = models.CharField(
        max_length=100, 
        help_text="Node in parent workflow that called this reusable workflow"
    )
    
    # Execution data
    input_data = models.JSONField()
    output_data = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ExecutionStatus.choices)
    error_details = models.JSONField(null=True, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Context preservation
    execution_context = models.JSONField(default=dict)
    
    class Meta:
        indexes = [
            models.Index(fields=['parent_execution', 'started_at']),
            models.Index(fields=['reusable_workflow', '-started_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.reusable_workflow.name} in {self.parent_execution.workflow.name}"
    
    def mark_completed(self, output_data: dict):
        """Mark execution as completed with output data"""
        self.status = ExecutionStatus.COMPLETED
        self.output_data = output_data
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save()
        
        # Update reusable workflow metrics
        self.reusable_workflow.update_performance_metrics(
            self.duration_ms or 0, 
            success=True
        )
    
    def mark_failed(self, error_details: dict):
        """Mark execution as failed with error details"""
        self.status = ExecutionStatus.FAILED
        self.error_details = error_details
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save()
        
        # Update reusable workflow metrics
        self.reusable_workflow.update_performance_metrics(
            self.duration_ms or 0, 
            success=False
        )


class ReusableWorkflowTemplate(models.Model):
    """Templates for creating new reusable workflows"""
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)
    
    # Template structure
    template_definition = models.JSONField()
    default_input_schema = models.JSONField()
    default_output_schema = models.JSONField()
    
    # Configuration options
    configurable_fields = models.JSONField(
        default=list,
        help_text="Fields that can be customized when creating from template"
    )
    
    # Metadata
    is_system_template = models.BooleanField(
        default=False,
        help_text="System-provided template vs user-created"
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['-usage_count']),
        ]
    
    def __str__(self):
        return f"Template: {self.name}"
    
    def create_reusable_workflow(self, name: str, customizations: dict, created_by: User) -> ReusableWorkflow:
        """Create a new reusable workflow from this template"""
        # Apply customizations to template
        workflow_definition = self.template_definition.copy()
        input_schema = self.default_input_schema.copy()
        output_schema = self.default_output_schema.copy()
        
        # Apply customizations (this would be more sophisticated in practice)
        for field, value in customizations.items():
            if field in self.configurable_fields:
                # Apply field-specific customization logic
                pass
        
        reusable_workflow = ReusableWorkflow.objects.create(
            name=name,
            description=f"Created from template: {self.name}",
            category=self.category,
            input_schema=input_schema,
            output_schema=output_schema,
            workflow_definition=workflow_definition,
            created_by=created_by
        )
        
        # Update template usage
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
        
        return reusable_workflow