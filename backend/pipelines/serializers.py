"""
Serializers for pipeline system API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Pipeline, Field, Record, PipelineTemplate, FieldGroup
from .field_types import FieldType, validate_field_config
from .validation import validate_record_data

User = get_user_model()


class FieldSerializer(serializers.ModelSerializer):
    """Serializer for pipeline fields with soft delete support"""
    is_active = serializers.SerializerMethodField()
    deletion_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Field
        fields = [
            'id', 'pipeline', 'name', 'slug', 'description', 'field_type', 'field_config',
            'storage_constraints', 'business_rules', 'form_validation_rules', 
            'display_name', 'help_text', 'enforce_uniqueness', 'create_index', 
            'is_searchable', 'is_ai_field', 'display_order', 'is_visible_in_list', 
            'is_visible_in_detail', 'is_visible_in_public_forms', 'is_visible_in_shared_list_and_detail_views',
            'ai_config', 'field_group', 'is_active', 'deletion_status',
            'is_deleted', 'deleted_at', 'scheduled_for_hard_delete',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'is_active', 'deletion_status', 
            'is_deleted', 'deleted_at', 'scheduled_for_hard_delete',
            'created_at', 'updated_at'
        ]
    
    def get_is_active(self, obj):
        """Check if field is active (not deleted)"""
        return not obj.is_deleted
    
    def get_deletion_status(self, obj):
        """Get detailed deletion status"""
        if obj.scheduled_for_hard_delete:
            from django.utils import timezone
            remaining = obj.scheduled_for_hard_delete - timezone.now()
            days_remaining = remaining.days if remaining.days > 0 else 0
            return {
                'status': 'scheduled_for_hard_delete',
                'days_remaining': days_remaining,
                'hard_delete_date': obj.scheduled_for_hard_delete.isoformat(),
                'reason': obj.hard_delete_reason
            }
        elif obj.is_deleted:
            return {
                'status': 'soft_deleted',
                'deleted_at': obj.deleted_at.isoformat() if obj.deleted_at else None,
                'deleted_by': obj.deleted_by.username if obj.deleted_by else None
            }
        else:
            return {
                'status': 'active'
            }
    
    def validate_field_type(self, value):
        """Validate field type"""
        try:
            FieldType(value)
        except ValueError:
            raise serializers.ValidationError(f"Invalid field type: {value}")
        return value
    
    def validate_field_config(self, value):
        """Validate field configuration"""
        field_type = self.initial_data.get('field_type')
        if field_type:
            try:
                validate_field_config(FieldType(field_type), value)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Validate AI field configuration
        if attrs.get('is_ai_field') and attrs.get('field_type') == FieldType.AI_GENERATED:
            ai_config = attrs.get('ai_config', {})
            if not ai_config.get('prompt'):  # Fixed: use 'prompt' not 'ai_prompt'
                raise serializers.ValidationError({
                    'ai_config': 'AI fields must have a prompt in ai_config'
                })
        
        return attrs


class FieldManagementActionSerializer(serializers.Serializer):
    """Serializer for field management actions (soft delete, restore, etc.)"""
    action = serializers.ChoiceField(
        choices=['soft_delete', 'restore', 'schedule_hard_delete', 'impact_analysis'],
        help_text="Action to perform on the field"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Reason for the action (required for deletions)"
    )
    grace_days = serializers.IntegerField(
        default=7,
        min_value=1,
        max_value=30,
        required=False,
        help_text="Days before hard deletion (for schedule_hard_delete)"
    )
    
    def validate(self, attrs):
        action = attrs.get('action')
        reason = attrs.get('reason')
        
        # Require reason for destructive actions
        if action in ['soft_delete', 'schedule_hard_delete'] and not reason:
            raise serializers.ValidationError({
                'reason': 'Reason is required for deletion actions'
            })
        
        return attrs


class FieldRestoreSerializer(serializers.Serializer):
    """Serializer for direct field restore operations"""
    reason = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Reason for restoring the field"
    )
    dry_run = serializers.BooleanField(
        default=False,
        help_text="Preview restore impact without performing actual restore"
    )
    force = serializers.BooleanField(
        default=False,
        help_text="Force restore even if validation warnings exist"
    )


class BulkFieldRestoreSerializer(serializers.Serializer):
    """Serializer for bulk field restore operations"""
    field_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=20,
        help_text="List of field IDs to restore (max 20)"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Reason for bulk restore"
    )
    force = serializers.BooleanField(
        default=False,
        help_text="Force restore for all fields even with validation warnings"
    )
    
    def validate_field_ids(self, value):
        """Validate that field IDs exist and are deleted"""
        from .models import Field
        
        # Check that all field IDs exist (including soft-deleted)
        existing_fields = Field.objects.with_deleted().filter(id__in=value)
        existing_ids = set(existing_fields.values_list('id', flat=True))
        missing_ids = set(value) - existing_ids
        
        if missing_ids:
            raise serializers.ValidationError(
                f"Field IDs not found: {sorted(missing_ids)}"
            )
        
        # Check that fields are actually deleted
        non_deleted_fields = existing_fields.filter(is_deleted=False)
        if non_deleted_fields.exists():
            non_deleted_ids = list(non_deleted_fields.values_list('id', flat=True))
            raise serializers.ValidationError(
                f"Fields are not deleted and cannot be restored: {non_deleted_ids}"
            )
        
        return value


class FieldMigrationSerializer(serializers.Serializer):
    """Serializer for field schema migration requests"""
    new_config = serializers.JSONField(
        help_text="New field configuration to migrate to"
    )
    dry_run = serializers.BooleanField(
        default=False,
        help_text="Perform dry run without making actual changes"
    )
    batch_size = serializers.IntegerField(
        default=100,
        min_value=10,
        max_value=1000,
        help_text="Number of records to process per batch"
    )
    
    def validate_new_config(self, value):
        """Validate the new configuration structure"""
        required_keys = ['field_type']
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(f"Missing required key: {key}")
        
        # Validate field type
        field_type = value.get('field_type')
        try:
            from .field_types import FieldType
            FieldType(field_type)
        except ValueError:
            raise serializers.ValidationError(f"Invalid field type: {field_type}")
        
        return value


class FieldGroupSerializer(serializers.ModelSerializer):
    """Serializer for field groups"""
    field_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FieldGroup
        fields = [
            'id', 'name', 'description', 'color', 'icon', 
            'display_order', 'field_count'
        ]
    
    def get_field_count(self, obj):
        """Get count of fields in this group"""
        print(f'🔍 FieldGroupSerializer.get_field_count called for group: {obj.name}')
        count = obj.fields.count()
        print(f'   Field count: {count}')
        return count


class PipelineSerializer(serializers.ModelSerializer):
    """Serializer for pipelines"""
    fields = FieldSerializer(many=True, read_only=True)
    field_groups = FieldGroupSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'color',
            'field_schema', 'view_config', 'settings', 'pipeline_type',
            'template', 'access_level', 'permission_config', 'is_active',
            'is_system', 'record_count', 'last_record_created',
            'created_by', 'created_at', 'updated_at', 'fields', 'field_groups'
        ]
        read_only_fields = [
            'id', 'slug', 'field_schema', 'record_count', 'last_record_created',
            'created_at', 'updated_at'
        ]
    
    def validate_color(self, value):
        """Validate hex color format"""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError("Color must be in hex format (#RRGGBB)")
        return value


class PipelineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating pipelines with fields"""
    fields = FieldSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = Pipeline
        fields = [
            'name', 'description', 'icon', 'color', 'view_config',
            'settings', 'pipeline_type', 'template', 'access_level',
            'permission_config', 'fields'
        ]
    
    def create(self, validated_data):
        """Create pipeline with fields"""
        fields_data = validated_data.pop('fields', [])
        
        # Set created_by from request
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        
        pipeline = Pipeline.objects.create(**validated_data)
        
        # Create fields
        for field_data in fields_data:
            field_data['created_by'] = request.user if request and request.user else None
            Field.objects.create(pipeline=pipeline, **field_data)
        
        return pipeline


class UserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for record created_by/updated_by fields"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']


class RecordSerializer(serializers.ModelSerializer):
    """Serializer for pipeline records"""
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    
    class Meta:
        model = Record
        fields = [
            'id', 'data', 'title', 'status', 'tags', 'ai_summary', 'ai_score',
            'created_by', 'updated_by', 'created_at', 'updated_at',
            'version', 'pipeline_name', 'is_deleted'
        ]
        read_only_fields = [
            'id', 'title', 'ai_summary', 'ai_score', 'created_at', 'updated_at',
            'version', 'pipeline_name', 'is_deleted'
        ]
    
    def to_representation(self, instance):
        """Override to dynamically generate title using current pipeline template"""
        from .record_operations import RecordUtils
        from .relation_field_handler import RelationFieldHandler

        data = super().to_representation(instance)

        # Generate title dynamically using current pipeline template
        data['title'] = RecordUtils.generate_title(
            instance.data,
            instance.pipeline.name,
            instance.pipeline
        )

        # Add relation field data from Relationship table
        relation_fields = instance.pipeline.fields.filter(field_type='relation')
        for field in relation_fields:
            handler = RelationFieldHandler(field)
            related_ids = handler.get_related_ids(instance)
            # Merge relation data into the data dict
            if data.get('data') is None:
                data['data'] = {}
            data['data'][field.slug] = related_ids

        return data
    
    def validate_data(self, value):
        """Validate record data against pipeline schema"""
        if not self.instance and not hasattr(self, '_pipeline'):
            # For creation, pipeline should be set in context
            pipeline = self.context.get('pipeline')
            if not pipeline:
                raise serializers.ValidationError("Pipeline context is required")
            self._pipeline = pipeline
        else:
            self._pipeline = self.instance.pipeline if self.instance else self.context.get('pipeline')
        
        # Validate against pipeline schema
        validation_result = self._pipeline.validate_record_data(value)
        if not validation_result['is_valid']:
            raise serializers.ValidationError(validation_result['errors'])
        
        return validation_result['cleaned_data']
    
    def create(self, validated_data):
        """Create record with proper user assignment and relation field handling"""
        request = self.context.get('request')
        pipeline = self.context.get('pipeline')

        if not pipeline:
            raise serializers.ValidationError("Pipeline is required")

        # Create record instance (but don't save yet)
        record = Record(
            pipeline=pipeline,
            data=validated_data.get('data', {}),
            status=validated_data.get('status', 'active'),
            tags=validated_data.get('tags', [])
        )

        # Set user fields
        user = None
        if request and request.user:
            record.created_by = request.user
            record.updated_by = request.user
            user = request.user

        # Use RecordOperationManager to handle the save, which will:
        # 1. Extract relation fields from JSONB
        # 2. Save the record
        # 3. Sync relation fields to Relationship table
        from .record_operations import RecordOperationManager
        operation_manager = RecordOperationManager(record)
        result = operation_manager.process_record_save(user=user)

        if result.success:
            return result.record
        else:
            raise serializers.ValidationError(result.errors)
    
    def update(self, instance, validated_data):
        """Update record with proper user assignment and relation field handling"""
        import logging
        logger = logging.getLogger(__name__)

        request = self.context.get('request')

        # 🔍 DEBUG: Log user context at serializer level
        if request:
            logger.info(f"SERIALIZER_UPDATE: Request user: {request.user.email if hasattr(request.user, 'email') else request.user} (ID: {getattr(request.user, 'id', 'No ID')})")
            logger.info(f"SERIALIZER_UPDATE: Request object ID: {id(request)}")
            logger.info(f"SERIALIZER_UPDATE: User object ID: {id(request.user)}")
            logger.info(f"SERIALIZER_UPDATE: Record instance ID: {instance.id}")

            # Check for authentication state
            if hasattr(request.user, 'is_authenticated'):
                logger.info(f"SERIALIZER_UPDATE: User authenticated: {request.user.is_authenticated}")

        # Extract user for the operation
        user = None
        if request and request.user:
            validated_data['updated_by'] = request.user
            user = request.user

        # Update the record's data with validated data
        if 'data' in validated_data:
            instance.data = validated_data['data']

        # Use RecordOperationManager to handle the save, which will:
        # 1. Extract relation fields from JSONB
        # 2. Save the record
        # 3. Sync relation fields to Relationship table
        from .record_operations import RecordOperationManager
        operation_manager = RecordOperationManager(instance)
        result = operation_manager.process_record_save(user=user)

        if result.success:
            return result.record
        else:
            raise serializers.ValidationError(result.errors)


class RecordCreateSerializer(serializers.Serializer):
    """Serializer for creating records with field-by-field data"""
    data = serializers.JSONField()
    status = serializers.CharField(max_length=100, default='active')
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    
    def validate_data(self, value):
        """Validate record data against pipeline schema"""
        pipeline = self.context.get('pipeline')
        if not pipeline:
            raise serializers.ValidationError("Pipeline context is required")
        
        validation_result = pipeline.validate_record_data(value)
        if not validation_result['is_valid']:
            raise serializers.ValidationError(validation_result['errors'])
        
        return validation_result['cleaned_data']
    
    def create(self, validated_data):
        """Create record"""
        request = self.context.get('request')
        pipeline = self.context.get('pipeline')
        
        record = Record(
            pipeline=pipeline,
            data=validated_data['data'],
            status=validated_data.get('status', 'active'),
            tags=validated_data.get('tags', [])
        )
        
        if request and request.user:
            record.created_by = request.user
            record.updated_by = request.user
        
        record.save()
        return record


class PipelineTemplateSerializer(serializers.ModelSerializer):
    """Serializer for pipeline templates"""
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = PipelineTemplate
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'template_data',
            'is_system', 'is_public', 'usage_count', 'preview_config',
            'sample_data', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'usage_count', 'created_at', 'updated_at'
        ]
    
    def validate_template_data(self, value):
        """Validate template data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Template data must be a dictionary")
        
        # Check required keys
        required_keys = ['pipeline', 'fields']
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(f"Template data must contain '{key}'")
        
        # Validate pipeline data
        pipeline_data = value.get('pipeline', {})
        if not isinstance(pipeline_data, dict):
            raise serializers.ValidationError("Pipeline data must be a dictionary")
        
        # Validate fields data
        fields_data = value.get('fields', [])
        if not isinstance(fields_data, list):
            raise serializers.ValidationError("Fields data must be a list")
        
        for field_data in fields_data:
            if not isinstance(field_data, dict):
                raise serializers.ValidationError("Each field must be a dictionary")
            
            required_field_keys = ['name', 'slug', 'field_type']
            for key in required_field_keys:
                if key not in field_data:
                    raise serializers.ValidationError(f"Field must contain '{key}'")
            
            # Validate field type
            try:
                FieldType(field_data['field_type'])
            except ValueError:
                raise serializers.ValidationError(f"Invalid field type: {field_data['field_type']}")
        
        return value


class PipelineTemplateCreatePipelineSerializer(serializers.Serializer):
    """Serializer for creating pipeline from template"""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        """Create pipeline from template"""
        template = self.context['template']
        request = self.context.get('request')
        
        user = request.user if request and request.user else None
        
        return template.create_pipeline_from_template(
            name=validated_data['name'],
            created_by=user
        )


class FieldValidationSerializer(serializers.Serializer):
    """Serializer for validating individual field values"""
    value = serializers.JSONField()
    is_required = serializers.BooleanField(default=False)
    
    def validate(self, attrs):
        """Validate field value"""
        field = self.context.get('field')
        if not field:
            raise serializers.ValidationError("Field context is required")
        
        result = field.validate_value(
            attrs['value']
        )
        
        if not result.is_valid:
            raise serializers.ValidationError({'value': result.errors})
        
        attrs['cleaned_value'] = result.cleaned_value
        return attrs


class RecordSearchSerializer(serializers.Serializer):
    """Serializer for record search parameters"""
    q = serializers.CharField(required=False, help_text="Search query")
    status = serializers.CharField(required=False, help_text="Filter by status")
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Filter by tags"
    )
    created_after = serializers.DateTimeField(required=False)
    created_before = serializers.DateTimeField(required=False)
    updated_after = serializers.DateTimeField(required=False)
    updated_before = serializers.DateTimeField(required=False)
    
    # Dynamic field filters (will be added based on pipeline fields)
    def __init__(self, *args, **kwargs):
        pipeline = kwargs.pop('pipeline', None)
        super().__init__(*args, **kwargs)
        
        if pipeline:
            # Add dynamic field filters
            for field in pipeline.fields.filter(is_searchable=True):
                field_name = f"field_{field.slug}"
                
                if field.field_type in ['text', 'textarea', 'email', 'url']:
                    self.fields[field_name] = serializers.CharField(required=False)
                elif field.field_type in ['number', 'decimal']:
                    self.fields[field_name] = serializers.FloatField(required=False)
                    self.fields[f"{field_name}_min"] = serializers.FloatField(required=False)
                    self.fields[f"{field_name}_max"] = serializers.FloatField(required=False)
                elif field.field_type == 'boolean':
                    self.fields[field_name] = serializers.BooleanField(required=False)
                elif field.field_type in ['date', 'datetime']:
                    self.fields[f"{field_name}_after"] = serializers.DateTimeField(required=False)
                    self.fields[f"{field_name}_before"] = serializers.DateTimeField(required=False)
                elif field.field_type in ['select', 'multiselect']:
                    self.fields[field_name] = serializers.CharField(required=False)


class BulkRecordActionSerializer(serializers.Serializer):
    """Serializer for bulk record actions"""
    ACTION_CHOICES = [
        ('delete', 'Delete'),
        ('update_status', 'Update Status'),
        ('add_tags', 'Add Tags'),
        ('remove_tags', 'Remove Tags'),
        ('export', 'Export'),
    ]
    
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    record_ids = serializers.ListField(child=serializers.IntegerField())
    
    # Action-specific parameters
    status = serializers.CharField(required=False, help_text="For update_status action")
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="For add_tags/remove_tags actions"
    )
    export_format = serializers.ChoiceField(
        choices=[('csv', 'CSV'), ('json', 'JSON'), ('xlsx', 'Excel')],
        required=False,
        default='csv',
        help_text="For export action"
    )
    
    def validate(self, attrs):
        """Validate action-specific parameters"""
        action = attrs.get('action')
        
        if action == 'update_status' and not attrs.get('status'):
            raise serializers.ValidationError({'status': 'Status is required for update_status action'})
        
        if action in ['add_tags', 'remove_tags'] and not attrs.get('tags'):
            raise serializers.ValidationError({'tags': 'Tags are required for tag actions'})
        
        return attrs


class MigrationValidationSerializer(serializers.Serializer):
    """Serializer for pre-migration validation requests"""
    new_config = serializers.JSONField(
        help_text="Proposed new field configuration to validate"
    )
    include_impact_preview = serializers.BooleanField(
        default=False,
        help_text="Include detailed impact analysis in validation response"
    )
    
    def validate_new_config(self, value):
        """Validate the new configuration format"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("new_config must be a dictionary")
        
        # Basic validation - field_type if provided should be valid
        if 'field_type' in value:
            from .field_types import FieldType
            field_type = value['field_type']
            
            # Check if field_type is a valid FieldType
            valid_types = [ft.value for ft in FieldType]
            if field_type not in valid_types:
                raise serializers.ValidationError(
                    f"Invalid field_type '{field_type}'. Valid types: {', '.join(valid_types)}"
                )
        
        return value