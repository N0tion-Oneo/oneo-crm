"""
Serializers for task management
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Task, TaskComment, TaskAttachment
from pipelines.models import Record

User = get_user_model()


class TaskCommentSerializer(serializers.ModelSerializer):
    """Serializer for task comments"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = TaskComment
        fields = [
            'id', 'comment', 'user', 'user_name', 'user_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for task attachments"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskAttachment
        fields = [
            'id', 'file', 'file_url', 'filename', 
            'uploaded_by', 'uploaded_by_name', 'uploaded_at'
        ]
        read_only_fields = ['uploaded_by', 'uploaded_at']
    
    def get_file_url(self, obj):
        """Get the full URL for the file"""
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class TaskSerializer(serializers.ModelSerializer):
    """Full serializer for tasks"""
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    attachments_count = serializers.IntegerField(source='attachments.count', read_only=True)
    
    # Record information
    record_id = serializers.IntegerField(source='record.id', read_only=True)
    record_name = serializers.SerializerMethodField()
    pipeline_id = serializers.IntegerField(source='record.pipeline_id', read_only=True)
    pipeline_name = serializers.CharField(source='record.pipeline.name', read_only=True)
    
    # Nested serializers for read operations
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'priority', 'status',
            'due_date', 'reminder_at', 'completed_at',
            'record', 'record_id', 'record_name', 'pipeline_id', 'pipeline_name',
            'assigned_to', 'assigned_to_name', 'assigned_to_email',
            'created_by', 'created_by_name', 'created_by_email',
            'metadata', 'is_overdue',
            'comments', 'comments_count',
            'attachments', 'attachments_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'completed_at']
    
    def validate_record(self, value):
        """Validate that the record exists and user has access"""
        if not value:
            raise serializers.ValidationError("Record is required")
        
        # Check if record exists and is not deleted
        if value.is_deleted:
            raise serializers.ValidationError("Cannot create task for deleted record")
        
        return value
    
    def get_record_name(self, obj):
        """Get display name for the record"""
        if not obj.record:
            return None
        
        # Use the RecordSerializer to get the properly generated title
        from pipelines.serializers import RecordSerializer
        record_data = RecordSerializer(obj.record).data
        return record_data.get('title', f"Record #{obj.record.id}")
    
    def validate_due_date(self, value):
        """Validate due date if provided"""
        if value:
            from django.utils import timezone
            # Allow due dates in the past for historical tasks
            # But warn if creating a new task with past due date
            if value < timezone.now() and self.instance is None:
                # This is a new task with past due date - allow but could log warning
                pass
        return value


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks with minimal fields"""
    record_id = serializers.IntegerField(write_only=True)
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'priority', 'status',
            'due_date', 'reminder_at', 'record_id', 'assigned_to_id',
            'metadata'
        ]
    
    def validate_record_id(self, value):
        """Validate record exists"""
        try:
            record = Record.objects.get(id=value, is_deleted=False)
            return record
        except Record.DoesNotExist:
            raise serializers.ValidationError("Record not found")
    
    def validate_assigned_to_id(self, value):
        """Validate assigned user exists"""
        if value:
            try:
                user = User.objects.get(id=value)
                return user
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found")
        return None
    
    def create(self, validated_data):
        """Create task with proper relationships"""
        # Extract and convert IDs to objects
        record = validated_data.pop('record_id')
        assigned_to = validated_data.pop('assigned_to_id', None)
        
        # Set the created_by from request context
        validated_data['created_by'] = self.context['request'].user
        validated_data['record'] = record
        if assigned_to:
            validated_data['assigned_to'] = assigned_to
        
        return super().create(validated_data)


class TaskStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for quick status updates"""
    class Meta:
        model = Task
        fields = ['status']
    
    def validate_status(self, value):
        """Validate status transition"""
        if self.instance:
            current_status = self.instance.status
            # Add any business rules for status transitions here
            # For example, can't go from completed back to pending without going through in_progress
            
        return value


class TaskListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for task lists"""
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    record_id = serializers.IntegerField(source='record.id', read_only=True)
    record_name = serializers.SerializerMethodField()
    pipeline_id = serializers.IntegerField(source='record.pipeline_id', read_only=True)
    pipeline_name = serializers.CharField(source='record.pipeline.name', read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'priority', 'status',
            'due_date', 'assigned_to', 'assigned_to_name',
            'created_by', 'created_by_name', 'created_by_email',
            'is_overdue', 'created_at', 'updated_at',
            'record', 'record_id', 'record_name', 'pipeline_id', 'pipeline_name'
        ]
    
    def get_record_name(self, obj):
        """Get display name for the record"""
        if not obj.record:
            return None
        
        # Use the RecordSerializer to get the properly generated title
        from pipelines.serializers import RecordSerializer
        record_data = RecordSerializer(obj.record).data
        return record_data.get('title', f"Record #{obj.record.id}")