"""
Serializers for workflow API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog, 
    WorkflowApproval, WorkflowSchedule
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for nested relationships"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'email', 'first_name', 'last_name']


class WorkflowSerializer(serializers.ModelSerializer):
    """Serializer for workflows"""
    
    created_by = UserSerializer(read_only=True)
    allowed_users = UserSerializer(many=True, read_only=True)
    execution_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'status', 'version',
            'trigger_type', 'trigger_config', 'workflow_definition',
            'max_executions_per_hour', 'timeout_minutes', 'retry_count',
            'is_public', 'created_by', 'allowed_users',
            'created_at', 'updated_at', 'execution_count'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'execution_count']
    
    def get_execution_count(self, obj):
        """Get total execution count"""
        return obj.executions.count()
    
    def validate_workflow_definition(self, value):
        """Validate workflow definition structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Workflow definition must be a dictionary")
        
        required_keys = ['nodes', 'edges']
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(f"Workflow definition must contain '{key}'")
        
        # Validate nodes structure
        nodes = value.get('nodes', [])
        if not isinstance(nodes, list):
            raise serializers.ValidationError("Nodes must be a list")
        
        # Validate edges structure
        edges = value.get('edges', [])
        if not isinstance(edges, list):
            raise serializers.ValidationError("Edges must be a list")
        
        # Validate node IDs are unique
        node_ids = [node.get('id') for node in nodes if isinstance(node, dict)]
        if len(node_ids) != len(set(node_ids)):
            raise serializers.ValidationError("Node IDs must be unique")
        
        # Validate edge references exist
        for edge in edges:
            if isinstance(edge, dict):
                source = edge.get('source')
                target = edge.get('target')
                if source not in node_ids or target not in node_ids:
                    raise serializers.ValidationError(f"Edge references invalid node: {source} -> {target}")
        
        return value
    
    def validate_trigger_config(self, value):
        """Validate trigger configuration"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Trigger config must be a dictionary")
        
        return value


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """Serializer for workflow executions"""
    
    workflow = WorkflowSerializer(read_only=True)
    triggered_by = UserSerializer(read_only=True)
    duration_seconds = serializers.ReadOnlyField()
    log_count = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow', 'status', 'started_at', 'completed_at',
            'duration_seconds', 'triggered_by', 'trigger_data',
            'execution_context', 'final_output', 'error_message',
            'retry_count', 'log_count'
        ]
        read_only_fields = [
            'id', 'workflow', 'started_at', 'completed_at', 'duration_seconds',
            'triggered_by', 'log_count'
        ]
    
    def get_log_count(self, obj):
        """Get execution log count"""
        return obj.logs.count()


class WorkflowExecutionLogSerializer(serializers.ModelSerializer):
    """Serializer for workflow execution logs"""
    
    execution = serializers.PrimaryKeyRelatedField(read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowExecutionLog
        fields = [
            'id', 'execution', 'node_id', 'node_type', 'node_name',
            'status', 'started_at', 'completed_at', 'duration_ms',
            'duration_seconds', 'input_data', 'output_data',
            'execution_details', 'error_details'
        ]
        read_only_fields = [
            'id', 'execution', 'started_at', 'completed_at', 'duration_ms',
            'duration_seconds'
        ]
    
    def get_duration_seconds(self, obj):
        """Convert duration from ms to seconds"""
        if obj.duration_ms:
            return round(obj.duration_ms / 1000, 2)
        return None


class WorkflowApprovalSerializer(serializers.ModelSerializer):
    """Serializer for workflow approvals"""
    
    execution = WorkflowExecutionSerializer(read_only=True)
    execution_log = WorkflowExecutionLogSerializer(read_only=True)
    requested_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    is_pending = serializers.ReadOnlyField()
    
    class Meta:
        model = WorkflowApproval
        fields = [
            'id', 'execution', 'execution_log', 'title', 'description',
            'requested_by', 'assigned_to', 'requested_at', 'approval_data',
            'approved', 'approved_at', 'approved_by', 'approval_notes',
            'is_pending'
        ]
        read_only_fields = [
            'id', 'execution', 'execution_log', 'requested_by', 'requested_at',
            'approved_at', 'approved_by', 'is_pending'
        ]


class WorkflowScheduleSerializer(serializers.ModelSerializer):
    """Serializer for workflow schedules"""
    
    workflow = WorkflowSerializer(read_only=True)
    workflow_id = serializers.PrimaryKeyRelatedField(
        queryset=Workflow.objects.all(),
        source='workflow',
        write_only=True
    )
    
    class Meta:
        model = WorkflowSchedule
        fields = [
            'id', 'workflow', 'workflow_id', 'name', 'cron_expression',
            'timezone', 'is_active', 'created_at', 'last_execution',
            'next_execution', 'execution_count'
        ]
        read_only_fields = [
            'id', 'workflow', 'created_at', 'last_execution', 'next_execution'
        ]
    
    def validate_cron_expression(self, value):
        """Validate cron expression"""
        try:
            from croniter import croniter
            croniter(value)
        except ValueError as e:
            raise serializers.ValidationError(f"Invalid cron expression: {e}")
        
        return value
    
    def validate_timezone(self, value):
        """Validate timezone"""
        try:
            import pytz
            pytz.timezone(value)
        except pytz.exceptions.UnknownTimeZoneError:
            raise serializers.ValidationError(f"Unknown timezone: {value}")
        
        return value
    
    def create(self, validated_data):
        """Create schedule with next execution calculation"""
        from croniter import croniter
        from django.utils import timezone
        from datetime import datetime
        import pytz
        
        schedule = super().create(validated_data)
        
        # Calculate next execution time
        tz = pytz.timezone(schedule.timezone) if schedule.timezone else timezone.get_current_timezone()
        now = timezone.now().astimezone(tz)
        cron = croniter(schedule.cron_expression, now)
        schedule.next_execution = cron.get_next(datetime
        )
        schedule.save()
        
        return schedule


class WorkflowExecutionLogDetailSerializer(WorkflowExecutionLogSerializer):
    """Detailed serializer for execution logs with full data"""
    
    class Meta(WorkflowExecutionLogSerializer.Meta):
        # Include all fields for detailed view
        pass


class WorkflowStatsSerializer(serializers.Serializer):
    """Serializer for workflow statistics"""
    
    total_workflows = serializers.IntegerField()
    active_workflows = serializers.IntegerField()
    total_executions = serializers.IntegerField()
    successful_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    success_rate = serializers.FloatField()
    
    # Recent activity
    recent_executions = WorkflowExecutionSerializer(many=True)
    recent_approvals = WorkflowApprovalSerializer(many=True)


class WorkflowNodeTemplateSerializer(serializers.Serializer):
    """Serializer for workflow node templates"""
    
    type = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    icon = serializers.CharField(required=False)
    color = serializers.CharField(required=False)
    inputs = serializers.ListField(child=serializers.DictField())
    outputs = serializers.ListField(child=serializers.DictField())
    config_schema = serializers.DictField()


class WorkflowTemplateSerializer(serializers.Serializer):
    """Serializer for workflow templates"""
    
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    icon = serializers.CharField(required=False)
    nodes = serializers.ListField(child=serializers.DictField())
    edges = serializers.ListField(child=serializers.DictField())
    trigger_config = serializers.DictField(required=False)


class WorkflowExportSerializer(serializers.Serializer):
    """Serializer for workflow export/import"""
    
    workflow = WorkflowSerializer()
    schedules = WorkflowScheduleSerializer(many=True, required=False)
    export_metadata = serializers.DictField()
    
    def create(self, validated_data):
        """Import workflow from export data"""
        workflow_data = validated_data['workflow']
        schedules_data = validated_data.get('schedules', [])
        
        # Create workflow
        workflow = Workflow.objects.create(**workflow_data)
        
        # Create schedules
        for schedule_data in schedules_data:
            schedule_data['workflow'] = workflow
            WorkflowSchedule.objects.create(**schedule_data)
        
        return {
            'workflow': workflow,
            'schedules': workflow.schedules.all(),
            'export_metadata': validated_data.get('export_metadata', {})
        }