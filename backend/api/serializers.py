"""
API serializers for all models
"""
from rest_framework import serializers
from rest_framework.fields import empty
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Field, Record, FieldGroup
from relationships.models import RelationshipType, Relationship
from authentication.models import UserType
from authentication.permissions import SyncPermissionManager
from ai.models import AIJob, AIUsageAnalytics, AIPromptTemplate, AIEmbedding
from duplicates.models import URLExtractionRule, DuplicateRule, DuplicateRuleTest
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class UserAssignmentField(serializers.JSONField):
    """
    Custom serializer field for USER field assignments with pipeline permission validation
    Validates that assigned users have access to the pipeline
    """
    
    def __init__(self, pipeline_id=None, **kwargs):
        self.pipeline_id = pipeline_id
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Validate user assignments with pipeline permission checking"""
        print(f"🔍 USER ASSIGNMENT FIELD: Received data: {data}")
        print(f"🔍 USER ASSIGNMENT FIELD: Data type: {type(data)}")
        # First, let JSONField handle basic JSON validation
        validated_data = super().to_internal_value(data)
        print(f"🔍 USER ASSIGNMENT FIELD: After JSONField validation: {validated_data}")
        
        # Skip validation if no pipeline context or no data
        if not self.pipeline_id or not validated_data:
            return validated_data
        
        # Extract user IDs from assignments for permission validation
        user_ids = []
        
        if isinstance(validated_data, list):
            # Multiple user assignments
            for assignment in validated_data:
                if isinstance(assignment, dict) and 'user_id' in assignment:
                    user_ids.append(assignment['user_id'])
                elif isinstance(assignment, int):
                    user_ids.append(assignment)
        elif isinstance(validated_data, dict) and 'user_id' in validated_data:
            # Single user assignment
            user_ids.append(validated_data['user_id'])
        elif isinstance(validated_data, int):
            # Simple user ID
            user_ids.append(validated_data)
        
        # Validate each user has pipeline access
        for user_id in user_ids:
            if not self._validate_user_pipeline_access(user_id):
                raise serializers.ValidationError(
                    f'User {user_id} does not have access to this pipeline'
                )
        
        return validated_data
    
    def _validate_user_pipeline_access(self, user_id: int) -> bool:
        """Check if user has access to the pipeline"""
        try:
            user = User.objects.get(id=user_id, is_active=True)
            permission_manager = SyncPermissionManager(user)
            
            # Check if user has any record-level access to the pipeline
            has_read = permission_manager.has_permission('action', 'records', 'read', str(self.pipeline_id))
            has_create = permission_manager.has_permission('action', 'records', 'create', str(self.pipeline_id))
            has_update = permission_manager.has_permission('action', 'records', 'update', str(self.pipeline_id))
            
            return has_read or has_create or has_update
            
        except User.DoesNotExist:
            return False
        except Exception as e:
            logger.warning(f"USER FIELD: Failed to validate user {user_id} pipeline access: {e}")
            return False


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    user_type = serializers.StringRelatedField()
    name = serializers.ReadOnlyField(source='get_full_name')    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'name', 'user_type', 'is_active', 'created_at']


class UserTypeSerializer(serializers.ModelSerializer):
    """User type serializer"""
    
    class Meta:
        model = UserType
        fields = ['id', 'name', 'slug', 'description', 'permissions', 'created_at']


class FieldSerializer(serializers.ModelSerializer):
    """Pipeline field serializer"""
    field_group = serializers.PrimaryKeyRelatedField(
        queryset=FieldGroup.objects.all(),
        allow_null=True,
        required=False,
        help_text="Field group this field belongs to"
    )
    field_group_name = serializers.CharField(source='field_group.name', read_only=True)
    
    class Meta:
        model = Field
        fields = [
            'id', 'name', 'slug', 'description', 'field_type', 'field_config', 
            'storage_constraints', 'business_rules', 'display_name', 'help_text',
            'enforce_uniqueness', 'create_index', 'is_searchable',
            'is_ai_field', 'display_order', 'is_visible_in_list',
            'is_visible_in_detail', 'is_visible_in_public_forms', 'ai_config', 
            'field_group', 'field_group_name',
            'created_at', 'updated_at'
        ]


class PipelineSerializer(serializers.ModelSerializer):
    """Pipeline serializer with related data"""
    fields = FieldSerializer(many=True, read_only=True)
    record_count = serializers.IntegerField(read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'color',
            'pipeline_type', 'access_level', 'is_active', 'settings', 'record_count',
            'fields', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'record_count']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class PipelineListSerializer(serializers.ModelSerializer):
    """Lightweight pipeline serializer for list views"""
    record_count = serializers.IntegerField(read_only=True)
    field_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'color',
            'pipeline_type', 'access_level', 'is_active', 'record_count', 'field_count',
            'created_at', 'updated_at'
        ]
    
    def get_field_count(self, obj):
        return obj.fields.count()


class RecordSerializer(serializers.ModelSerializer):
    """Base record serializer"""
    pipeline = PipelineListSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Record
        fields = [
            'id', 'pipeline', 'title', 'status', 'data',
            'created_by', 'updated_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['title']
    
    def create(self, validated_data):
        request = self.context.get('request')
        
        # ✅ Validate user context integrity
        if not request:
            raise serializers.ValidationError("No request context available")
        if not hasattr(request, 'user') or not request.user:
            raise serializers.ValidationError("No user in request context")
        if not request.user.is_authenticated:
            raise serializers.ValidationError("User is not authenticated")
        
        logger.info(f"SERIALIZER_CREATE: Record being created by user {request.user.id} ({request.user.email})")
        
        validated_data['created_by'] = request.user
        validated_data['updated_by'] = request.user
        
        # Create the record first
        record = super().create(validated_data)
        
        # Handle auto-assign creator for USER fields
        self._auto_assign_creator(record)
        
        return record
    
    def _auto_assign_creator(self, record):
        """Auto-assign creator to USER fields that have auto_assign_creator enabled"""
        try:
            from pipelines.field_types import FieldType
            from django.utils import timezone
            
            # Get pipeline fields
            pipeline = record.pipeline
            user_fields = pipeline.fields.filter(field_type=FieldType.USER.value)
            
            for field in user_fields:
                field_config = field.config or {}
                
                # Check if auto_assign_creator is enabled for this field
                if field_config.get('auto_assign_creator', False):
                    # Get current field data
                    current_data = record.data.get(field.name, {})
                    current_assignments = current_data.get('user_assignments', [])
                    
                    # Check if creator is already assigned
                    creator_id = record.created_by.id
                    is_already_assigned = any(
                        assignment.get('user_id') == creator_id 
                        for assignment in current_assignments
                    )
                    
                    if not is_already_assigned:
                        # Create creator assignment
                        creator_role = field_config.get('creator_default_role', 'owner')
                        creator_assignment = {
                            'user_id': creator_id,
                            'role': creator_role,
                            'name': record.created_by.get_full_name(),
                            'email': record.created_by.email,
                            'display_name': record.created_by.get_full_name(),
                            'display_email': record.created_by.email,
                            'assigned_at': timezone.now().isoformat(),
                            'auto_assigned': True
                        }
                        
                        # Add creator assignment
                        new_assignments = current_assignments + [creator_assignment]
                        
                        # Apply max_users limit if configured
                        max_users = field_config.get('max_users')
                        if max_users and len(new_assignments) > max_users:
                            # Keep the most recent assignments including the creator
                            new_assignments = new_assignments[-max_users:]
                        
                        # Update record data
                        if field.name not in record.data:
                            record.data[field.name] = {}
                        record.data[field.name]['user_assignments'] = new_assignments
                        
                        logger.info(f"AUTO_ASSIGN: Added creator {creator_id} to field '{field.name}' with role '{creator_role}'")
            
            # Save the updated record if any changes were made
            if user_fields.exists():
                record.save(update_fields=['data', 'updated_at'])
                
        except Exception as e:
            logger.error(f"AUTO_ASSIGN_ERROR: Failed to auto-assign creator: {e}")
            # Don't fail record creation if auto-assignment fails
            pass
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        
        # ✅ Extensive validation of user context
        if not request:
            raise serializers.ValidationError("No request context available")
        if not hasattr(request, 'user') or not request.user:
            raise serializers.ValidationError("No user in request context")
        if not request.user.is_authenticated:
            raise serializers.ValidationError("User is not authenticated")
        
        # ✅ Log for debugging user context issues
        logger.info(f"SERIALIZER_UPDATE: Record {instance.id if instance else 'NEW'} being updated by user {request.user.id} ({request.user.email})")
        
        # ✅ CRITICAL FIX: Set _current_user for AI trigger processing
        instance._current_user = request.user
        
        validated_data['updated_by'] = request.user
        return super().update(instance, validated_data)


class DynamicRecordSerializer(serializers.ModelSerializer):
    """Dynamic record serializer that adapts to pipeline schema"""
    pipeline = PipelineListSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Record
        fields = [
            'id', 'pipeline', 'title', 'status', 'data',
            'created_by', 'updated_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['title', 'pipeline']
    
    def __init__(self, *args, **kwargs):
        self.pipeline = kwargs.pop('pipeline', None)
        super().__init__(*args, **kwargs)
    
    def _add_dynamic_fields_to_dict(self, fields_dict, pipeline):
        """Add dynamic fields to a provided fields dictionary"""
        for field in pipeline.fields.all():
            field_name = field.slug
            
            # Check if field is required based on business rules
            is_required = self._is_field_required(field)
            
            # For partial updates, fields should not be required
            if hasattr(self, 'partial') and self.partial:
                is_required = False
            
            # Add field to serializer based on type
            if field.field_type in ['text', 'textarea', 'email', 'url']:
                fields_dict[field_name] = serializers.CharField(
                    source=f'data.{field_name}',
                    required=is_required,
                    allow_blank=not is_required
                )
            elif field.field_type == 'number':
                # Check if this is a currency field
                field_config = field.field_config or {}
                if field_config.get('format') == 'currency':
                    # Currency fields store objects like {"amount": 123.45, "currency": "USD"}
                    fields_dict[field_name] = serializers.JSONField(
                        source=f'data.{field_name}',
                        required=is_required,
                        allow_null=not is_required
                    )
                else:
                    # Regular number fields
                    fields_dict[field_name] = serializers.IntegerField(
                        source=f'data.{field_name}',
                        required=is_required,
                        allow_null=not is_required
                    )
            elif field.field_type == 'decimal':
                # Check if this is a currency field
                field_config = field.field_config or {}
                if field_config.get('format') == 'currency':
                    # Currency fields store objects like {"amount": 123.45, "currency": "USD"}
                    fields_dict[field_name] = serializers.JSONField(
                        source=f'data.{field_name}',
                        required=is_required,
                        allow_null=not is_required
                    )
                else:
                    # Regular decimal fields
                    fields_dict[field_name] = serializers.DecimalField(
                        source=f'data.{field_name}',
                        max_digits=10,
                        decimal_places=2,
                        required=is_required,
                        allow_null=not is_required
                    )
            elif field.field_type == 'boolean':
                fields_dict[field_name] = serializers.BooleanField(
                    source=f'data.{field_name}',
                    required=is_required
                )
            elif field.field_type in ['date', 'datetime']:
                fields_dict[field_name] = serializers.DateTimeField(
                    source=f'data.{field_name}',
                    required=is_required,
                    allow_null=not is_required
                )
            elif field.field_type == 'phone':
                # Check if this phone field requires country code
                field_config = field.field_config or {}
                if field_config.get('require_country_code', True):
                    # Phone fields with country code store objects like {"country_code": "+1", "number": "5551234567"}
                    fields_dict[field_name] = serializers.JSONField(
                        source=f'data.{field_name}',
                        required=is_required,
                        allow_null=not is_required
                    )
                else:
                    # Simple phone fields store strings
                    fields_dict[field_name] = serializers.CharField(
                        source=f'data.{field_name}',
                        required=is_required,
                        allow_blank=not is_required
                    )
            elif field.field_type in ['select', 'multiselect']:
                # Handle choice fields
                choices = field.field_config.get('choices', [])
                if field.field_type == 'select':
                    fields_dict[field_name] = serializers.ChoiceField(
                        source=f'data.{field_name}',
                        choices=choices,
                        required=is_required,
                        allow_blank=not is_required
                    )
                else:
                    fields_dict[field_name] = serializers.ListField(
                        source=f'data.{field_name}',
                        child=serializers.ChoiceField(choices=choices),
                        required=is_required,
                        allow_empty=not is_required
                    )
            elif field.field_type == 'user':
                # Handle user assignment fields with pipeline permission validation
                pipeline_id = getattr(self.pipeline, 'id', None) if hasattr(self, 'pipeline') else None
                fields_dict[field_name] = UserAssignmentField(
                    source=f'data.{field_name}',
                    pipeline_id=pipeline_id,
                    required=is_required,
                    allow_null=not is_required
                )
            else:
                # Fallback to JSON field
                fields_dict[field_name] = serializers.JSONField(
                    source=f'data.{field_name}',
                    required=is_required,
                    allow_null=not is_required
                )
        
        # Fields added silently for performance
    
    def _is_field_required(self, field):
        """Check if field is required based on business rules"""
        # For dynamic field creation, we can't determine stage context yet
        # So we'll make all fields optional at the serializer level
        # and let the pipeline validation handle stage-specific requirements
        return False
    
    @classmethod
    def for_pipeline(cls, pipeline):
        """Create a dynamic serializer class for a specific pipeline"""
        
        class _DynamicRecordSerializer(cls):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, pipeline=pipeline, **kwargs)
        
        _DynamicRecordSerializer.__name__ = f"{pipeline.name.replace(' ', '')}RecordSerializer"
        return _DynamicRecordSerializer
    
    def validate(self, attrs):
        """Validate record data against pipeline schema"""
        data = attrs.get('data', {})
        
        # Get pipeline from context
        pipeline = self.context.get('pipeline')
        if not pipeline and self.instance:
            pipeline = self.instance.pipeline
        
        if pipeline:
            # Validate against pipeline schema
            validation_result = pipeline.validate_record_data(data)
            if not validation_result['is_valid']:
                raise serializers.ValidationError({
                    'data': validation_result['errors']
                })
            
            # Use cleaned data
            attrs['data'] = validation_result['cleaned_data']
        
        return attrs
    
    def get_fields(self):
        """
        Create dynamic fields from pipeline schema.
        Note: PATCH filtering now handled in run_validation() - this just creates all fields
        """
        fields = super().get_fields()
        
        # Add dynamic fields if we have a pipeline
        if self.pipeline:
            self._add_dynamic_fields_to_dict(fields, self.pipeline)
            print(f"🟡 DJANGO STEP 1.5: Dynamic Fields Created")
            print(f"   🔧 Created {len(fields)} total fields for pipeline {self.pipeline.id}")
        
        return fields
    
    def run_validation(self, data=empty):
        """
        Override run_validation to prevent DRF from adding missing fields as None
        """
        print(f"🟡 DJANGO STEP 2: Serializer run_validation Starting")
        print(f"   📥 Raw Input: {data}")
        if isinstance(data, dict) and 'data' in data and isinstance(data['data'], dict):
            print(f"   🔑 Input contains {len(data['data'])} field(s): [{', '.join(data['data'].keys())}]")
            
        # Store the original provided fields for PATCH requests
        request = self.context.get('request')
        is_patch = request and request.method == 'PATCH'
        original_provided_fields = None
        
        if is_patch and isinstance(data, dict) and 'data' in data and isinstance(data['data'], dict):
            original_provided_fields = set(data['data'].keys())
            print(f"   🔒 PATCH mode: preserving only provided fields: [{', '.join(original_provided_fields)}]")
        
        # Call parent run_validation
        result = super().run_validation(data)
        
        # For PATCH requests, filter out any fields that weren't originally provided
        if is_patch and original_provided_fields is not None and 'data' in result:
            if isinstance(result['data'], dict):
                filtered_data = {}
                for field_name, field_value in result['data'].items():
                    if field_name in original_provided_fields:
                        filtered_data[field_name] = field_value
                        print(f"   ✅ Keeping provided field: {field_name} = {field_value}")
                    else:
                        print(f"   🗑️  Filtering out auto-added field: {field_name} = {field_value}")
                
                result['data'] = filtered_data
                print(f"   🧹 After filtering: {len(filtered_data)} field(s) remain")
        
        print(f"🟡 DJANGO STEP 3: Serializer run_validation Complete")
        print(f"   📊 Final Validated Data: {result}")
        if 'data' in result and isinstance(result['data'], dict):
            print(f"   🔑 Final contains {len(result['data'])} field(s): [{', '.join(result['data'].keys())}]")
            null_fields = [k for k, v in result['data'].items() if v is None]
            if null_fields:
                print(f"   ⚠️  Final contains {len(null_fields)} NULL fields: [{', '.join(null_fields)}]")
        
        return result
    
    def update(self, instance, validated_data):
        """
        Standard update method - data should already be clean from run_validation()
        Merges provided fields with existing data to preserve other field values.
        """
        print(f"🟡 DJANGO STEP 4: Serializer Update Starting")
        print(f"   📦 Validated Data: {validated_data}")
        print(f"   🔍 Record ID: {instance.id}")
        
        # 🔥 CRITICAL FIX: Add user context handling that was missing!
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['updated_by'] = request.user
            # ✅ CRITICAL FIX: Set _current_user for AI trigger processing
            instance._current_user = request.user
        
        # Extract data updates from validated_data
        data_updates = validated_data.pop('data', {})
        
        print(f"   📊 Data Updates: {data_updates}")
        
        if data_updates:
            print(f"   🔑 Updates contain {len(data_updates)} field(s): [{', '.join(data_updates.keys())}]")
            null_fields = [k for k, v in data_updates.items() if v is None]
            if null_fields:
                print(f"   ⚠️  Updates contain {len(null_fields)} NULL fields: [{', '.join(null_fields)}]")
            else:
                print(f"   ✅ No NULL fields in updates - run_validation() filtering worked!")
        
        # Merge with existing data (this is still needed to preserve other fields)
        if data_updates:
            current_data = instance.data or {}
            merged_data = current_data.copy()
            merged_data.update(data_updates)
            validated_data['data'] = merged_data
            
            print(f"   💾 Merged {len(data_updates)} new field(s) with {len(current_data)} existing field(s)")
            print(f"   📊 Final merged data has {len(merged_data)} total field(s)")
        
        # Call standard DRF update
        result = super().update(instance, validated_data)
        
        print(f"   ✅ Serializer update complete for record {instance.id}")
        
        return result


class RelationshipTypeSerializer(serializers.ModelSerializer):
    """Relationship type serializer"""
    
    class Meta:
        model = RelationshipType
        fields = [
            'id', 'name', 'slug', 'description', 'cardinality',
            'is_bidirectional', 'forward_label', 'reverse_label',
            'source_pipeline', 'target_pipeline', 'allow_user_relationships',
            'is_system', 'created_at', 'updated_at'
        ]


class RelationshipSerializer(serializers.ModelSerializer):
    """Relationship serializer"""
    relationship_type = RelationshipTypeSerializer(read_only=True)
    relationship_type_id = serializers.IntegerField(write_only=True)
    source_record = serializers.SerializerMethodField()
    target_record = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Relationship
        fields = [
            'id', 'relationship_type', 'relationship_type_id',
            'user', 'source_pipeline', 'source_record_id', 'source_record',
            'target_pipeline', 'target_record_id', 'target_record',
            'metadata', 'strength', 'status', 'role', 'is_verified',
            'can_edit', 'can_delete', 'created_by', 'created_at'
        ]
        read_only_fields = ['source_record', 'target_record']
    
    def get_source_record(self, obj):
        """Get source record title"""
        if obj.source_record:
            return {
                'id': obj.source_record.id,
                'title': obj.source_record.title,
                'pipeline': obj.source_record.pipeline.name
            }
        return None
    
    def get_target_record(self, obj):
        """Get target record title"""
        if obj.target_record:
            return {
                'id': obj.target_record.id,
                'title': obj.target_record.title,
                'pipeline': obj.target_record.pipeline.name
            }
        return None
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class RecordRelationshipSerializer(serializers.ModelSerializer):
    """Simplified relationship serializer for record views"""
    relationship_type = serializers.StringRelatedField()
    related_record = serializers.SerializerMethodField()
    
    class Meta:
        model = Relationship
        fields = [
            'id', 'relationship_type', 'related_record', 'strength',
            'status', 'metadata', 'created_at'
        ]
    
    def get_related_record(self, obj):
        """Get the related record (either source or target)"""
        # Determine which record is the "other" one based on context
        current_record_id = self.context.get('record_id')
        
        if obj.source_record_id == current_record_id:
            # Return target record
            if obj.target_record:
                return {
                    'id': obj.target_record.id,
                    'title': obj.target_record.title,
                    'pipeline': obj.target_record.pipeline.name,
                    'direction': 'outgoing'
                }
        else:
            # Return source record
            if obj.source_record:
                return {
                    'id': obj.source_record.id,
                    'title': obj.source_record.title,
                    'pipeline': obj.source_record.pipeline.name,
                    'direction': 'incoming'
                }
        
        return None


class BulkRecordSerializer(serializers.Serializer):
    """Serializer for bulk record operations"""
    records = serializers.ListField(
        child=serializers.JSONField(),
        min_length=1,
        max_length=1000
    )
    
    def validate_records(self, value):
        """Validate each record in the bulk operation"""
        pipeline = self.context.get('pipeline')
        if not pipeline:
            raise serializers.ValidationError("Pipeline context required")
        
        validated_records = []
        errors = []
        
        for i, record_data in enumerate(value):
            try:
                validation_result = pipeline.validate_record_data(record_data)
                if validation_result['is_valid']:
                    validated_records.append(validation_result['cleaned_data'])
                else:
                    errors.append({
                        'index': i,
                        'errors': validation_result['errors']
                    })
            except Exception as e:
                errors.append({
                    'index': i,
                    'errors': {'general': [str(e)]}
                })
        
        if errors:
            raise serializers.ValidationError({
                'validation_errors': errors
            })
        
        return validated_records


# AI Serializers for comprehensive AI integration

class AIJobSerializer(serializers.ModelSerializer):
    """AI job tracking serializer with tenant isolation"""
    cost_dollars = serializers.ReadOnlyField()
    can_retry = serializers.ReadOnlyField()
    created_by = UserSerializer(read_only=True)
    pipeline = PipelineListSerializer(read_only=True)
    
    class Meta:
        model = AIJob
        fields = [
            'id', 'job_type', 'status', 'pipeline', 'record_id', 'field_name',
            'ai_provider', 'model_name', 'prompt_template', 'ai_config',
            'input_data', 'output_data', 'tokens_used', 'cost_cents', 'cost_dollars',
            'processing_time_ms', 'error_message', 'retry_count', 'max_retries',
            'can_retry', 'created_by', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['cost_dollars', 'can_retry', 'created_by', 'tokens_used', 'cost_cents', 'processing_time_ms']


class AIUsageAnalyticsSerializer(serializers.ModelSerializer):
    """AI usage analytics serializer for billing and monitoring"""
    cost_dollars = serializers.ReadOnlyField()
    user = UserSerializer(read_only=True)
    pipeline = PipelineListSerializer(read_only=True)
    
    class Meta:
        model = AIUsageAnalytics
        fields = [
            'id', 'user', 'ai_provider', 'model_name', 'operation_type',
            'tokens_used', 'cost_cents', 'cost_dollars', 'response_time_ms',
            'pipeline', 'record_id', 'created_at', 'date'
        ]
        read_only_fields = ['cost_dollars', 'user', 'pipeline']


class AIPromptTemplateSerializer(serializers.ModelSerializer):
    """AI prompt template serializer with variable validation"""
    created_by = UserSerializer(read_only=True)
    variable_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AIPromptTemplate
        fields = [
            'id', 'name', 'slug', 'description', 'prompt_template', 'system_message',
            'ai_provider', 'model_name', 'temperature', 'max_tokens',
            'field_types', 'pipeline_types', 'required_variables', 'optional_variables',
            'version', 'is_active', 'is_system', 'variable_count',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_by', 'variable_count']
    
    def get_variable_count(self, obj):
        """Get total number of variables in template"""
        return len(obj.required_variables) + len(obj.optional_variables)
    
    def validate_prompt_template(self, value):
        """Validate prompt template format"""
        if not value:
            raise serializers.ValidationError("Prompt template cannot be empty")
        
        # Extract variables from template
        import re
        variables = re.findall(r'\{(\w+)\}', value)
        
        if len(variables) == 0:
            raise serializers.ValidationError("Prompt template should contain at least one variable")
        
        return value


class AIEmbeddingSerializer(serializers.ModelSerializer):
    """AI embedding serializer for semantic search"""
    embedding_dimension = serializers.SerializerMethodField()
    
    class Meta:
        model = AIEmbedding
        fields = [
            'id', 'content_type', 'content_id', 'content_hash',
            'embedding', 'embedding_dimension', 'model_name', 'created_at'
        ]
        read_only_fields = ['content_hash', 'embedding_dimension']
    
    def get_embedding_dimension(self, obj):
        """Get embedding vector dimension"""
        return len(obj.embedding) if obj.embedding else 0


class AIAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for AI analysis requests (legacy analysis types)"""
    analysis_type = serializers.ChoiceField(choices=[
        ('sentiment', 'Sentiment Analysis'),
        ('summary', 'Content Summarization'),
        ('classification', 'Content Classification'),
        ('extraction', 'Entity Extraction'),
        ('lead_qualification', 'Lead Qualification'),
        ('contact_profiling', 'Contact Profiling'),
        ('channel_optimization', 'Channel Optimization')
    ])
    content = serializers.CharField(required=False)
    data = serializers.JSONField(required=False)
    options = serializers.JSONField(required=False, default=dict)
    
    def validate(self, attrs):
        """Validate that either content or data is provided"""
        if not attrs.get('content') and not attrs.get('data'):
            raise serializers.ValidationError("Either 'content' or 'data' must be provided")
        return attrs


class AIFieldRequestSerializer(serializers.Serializer):
    """Serializer for AI field generation requests (prompt-based)"""
    job_type = serializers.ChoiceField(choices=[
        ('field_generation', 'Field Generation'),
        ('summarization', 'Summarization'),
        ('classification', 'Classification'),
        ('sentiment_analysis', 'Sentiment Analysis'),
        ('embedding_generation', 'Embedding Generation'),
        ('semantic_search', 'Semantic Search'),
    ])
    content = serializers.CharField(required=True)
    field_name = serializers.CharField(required=False)
    field_type = serializers.CharField(required=False)
    prompt = serializers.CharField(required=True)
    model = serializers.CharField(required=True)
    temperature = serializers.FloatField(default=0.3, min_value=0.0, max_value=2.0)
    max_tokens = serializers.IntegerField(default=1000, min_value=1, max_value=8000)
    output_type = serializers.ChoiceField(
        choices=[('text', 'Text'), ('number', 'Number'), ('tags', 'Tags'), ('url', 'URL'), ('json', 'JSON')],
        default='text'
    )


class AIAnalysisResultSerializer(serializers.Serializer):
    """Serializer for AI analysis results"""
    analysis_type = serializers.CharField()
    result = serializers.JSONField()
    confidence = serializers.FloatField(required=False)
    processing_time_ms = serializers.IntegerField(required=False)
    tokens_used = serializers.IntegerField(required=False)
    cost_cents = serializers.IntegerField(required=False)
    created_at = serializers.DateTimeField()


class AITenantConfigSerializer(serializers.Serializer):
    """Serializer for tenant AI configuration"""
    tenant_id = serializers.CharField(read_only=True)
    tenant_name = serializers.CharField(read_only=True)
    ai_enabled = serializers.BooleanField(default=False)
    openai_api_key = serializers.CharField(write_only=True, required=False)
    anthropic_api_key = serializers.CharField(write_only=True, required=False)
    default_provider = serializers.ChoiceField(
        choices=[('openai', 'OpenAI'), ('anthropic', 'Anthropic')],
        default='openai'
    )
    default_model = serializers.CharField(default='gpt-4o-mini')
    usage_limits = serializers.JSONField(default=dict)
    current_usage = serializers.JSONField(read_only=True)
    available_models = serializers.ListField(
        child=serializers.CharField(),
        default=lambda: ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo']
    )
    concurrent_jobs = serializers.IntegerField(default=5, min_value=1, max_value=20)


class AIUsageSummarySerializer(serializers.Serializer):
    """Serializer for AI usage summaries"""
    tenant_id = serializers.CharField()
    tenant_name = serializers.CharField()
    time_period = serializers.CharField()
    total_tokens = serializers.IntegerField()
    total_cost_dollars = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_requests = serializers.IntegerField()
    avg_response_time_ms = serializers.FloatField()
    job_type_breakdown = serializers.JSONField()
    model_usage_breakdown = serializers.JSONField()
    daily_usage = serializers.JSONField()


# =============================================================================
# DUPLICATE DETECTION SERIALIZERS (Simplified AND/OR Logic System)
# =============================================================================

class URLExtractionRuleSerializer(serializers.ModelSerializer):
    """Serializer for URL extraction rules"""
    
    class Meta:
        model = URLExtractionRule
        fields = [
            'id', 'name', 'description', 'domain_patterns', 'extraction_pattern',
            'extraction_format', 'case_sensitive', 'remove_protocol', 'remove_www',
            'remove_query_params', 'remove_fragments', 'strip_subdomains', 'normalization_steps', 
            'template_type', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        from django.db import IntegrityError
        validated_data['tenant'] = self.context['request'].tenant
        validated_data['created_by'] = self.context['request'].user
        try:
            return super().create(validated_data)
        except IntegrityError as e:
            if 'unique_together' in str(e) or 'duplicate key' in str(e):
                raise serializers.ValidationError({
                    'name': 'A URL extraction rule with this name already exists for this tenant.'
                })
            raise
    
    def validate_name(self, value):
        """Validate rule name uniqueness within tenant"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'tenant'):
            return value
        
        # Check for existing rule with same name in tenant
        existing = URLExtractionRule.objects.filter(
            tenant=request.tenant,
            name=value
        ).exclude(pk=self.instance.pk if self.instance else None)
        
        if existing.exists():
            raise serializers.ValidationError(
                "A URL extraction rule with this name already exists for this tenant."
            )
        
        return value


class DuplicateRuleSerializer(serializers.ModelSerializer):
    """Serializer for duplicate rules"""
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = DuplicateRule
        fields = [
            'id', 'name', 'description', 'pipeline', 'pipeline_name', 'logic',
            'action_on_duplicate', 'is_active', 'created_at', 'updated_at',
            'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'pipeline_name', 'created_by_name']
    
    def create(self, validated_data):
        from django.db import IntegrityError
        validated_data['tenant'] = self.context['request'].tenant
        validated_data['created_by'] = self.context['request'].user
        try:
            return super().create(validated_data)
        except IntegrityError as e:
            if 'unique_together' in str(e) or 'duplicate key' in str(e):
                raise serializers.ValidationError({
                    'name': 'A duplicate rule with this name already exists for this tenant.'
                })
            raise
    
    def validate_logic(self, value):
        """Validate the logic structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Logic must be a JSON object")
        
        if not value.get('operator'):
            raise serializers.ValidationError("Logic must have an 'operator' field")
        
        if value['operator'] not in ['AND', 'OR']:
            raise serializers.ValidationError("Operator must be 'AND' or 'OR'")
        
        # Validate structure based on operator
        if value['operator'] == 'AND':
            if 'fields' not in value:
                raise serializers.ValidationError("AND operator requires 'fields' array")
            if not isinstance(value['fields'], list) or not value['fields']:
                raise serializers.ValidationError("AND fields must be a non-empty array")
            
            # Validate each field in AND condition
            for field_config in value['fields']:
                self._validate_field_config(field_config)
        
        elif value['operator'] == 'OR':
            if 'conditions' not in value:
                raise serializers.ValidationError("OR operator requires 'conditions' array")
            if not isinstance(value['conditions'], list) or not value['conditions']:
                raise serializers.ValidationError("OR conditions must be a non-empty array")
            
            # Recursively validate each condition
            for condition in value['conditions']:
                self.validate_logic(condition)
        
        return value
    
    def _validate_field_config(self, field_config):
        """Validate individual field configuration"""
        if not isinstance(field_config, dict):
            raise serializers.ValidationError("Field config must be an object")
        
        if 'field' not in field_config:
            raise serializers.ValidationError("Field config must have 'field' name")
        
        if 'match_type' not in field_config:
            raise serializers.ValidationError("Field config must have 'match_type'")
        
        valid_match_types = [
            'exact', 'case_insensitive', 'email_normalized', 'phone_normalized',
            'url_normalized', 'fuzzy', 'numeric'
        ]
        
        if field_config['match_type'] not in valid_match_types:
            raise serializers.ValidationError(
                f"Invalid match_type. Must be one of: {valid_match_types}"
            )
    
    def validate_pipeline(self, value):
        """Validate pipeline exists and is accessible to the current tenant"""
        # In multi-tenant architecture with schema isolation,
        # if the pipeline was retrieved successfully, it belongs to the current tenant
        # No additional tenant validation needed since django-tenants handles schema isolation
        return value
    
    def validate_name(self, value):
        """Validate rule name uniqueness within tenant"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'tenant'):
            return value
        
        # Check for existing rule with same name in tenant
        existing = DuplicateRule.objects.filter(
            tenant=request.tenant,
            name=value
        ).exclude(pk=self.instance.pk if self.instance else None)
        
        if existing.exists():
            raise serializers.ValidationError(
                "A duplicate rule with this name already exists for this tenant."
            )
        
        return value


class DuplicateRuleTestSerializer(serializers.ModelSerializer):
    """Serializer for duplicate rule test cases"""
    
    class Meta:
        model = DuplicateRuleTest
        fields = [
            'id', 'name', 'record1_data', 'record2_data', 'expected_result',
            'last_test_result', 'last_test_at', 'test_details', 'created_at'
        ]
        read_only_fields = [
            'id', 'last_test_result', 'last_test_at', 'test_details', 'created_at'
        ]


class RuleBuilderConfigSerializer(serializers.Serializer):
    """Serializer for rule builder configuration data"""
    pipeline_id = serializers.IntegerField()
    
    def validate_pipeline_id(self, value):
        """Validate pipeline exists and is accessible"""
        try:
            pipeline = Pipeline.objects.get(id=value)
            self.context['pipeline'] = pipeline
            return value
        except Pipeline.DoesNotExist:
            raise serializers.ValidationError("Pipeline not found")
    
    def to_representation(self, instance):
        """Return rule builder configuration data"""
        pipeline = self.context['pipeline']
        
        # Get fields suitable for duplicate detection
        suitable_fields = pipeline.fields.filter(
            is_deleted=False,
            field_type__in=[
                'text', 'email', 'phone', 'url', 'number', 'select', 'textarea'
            ]
        ).values(
            'id', 'name', 'display_name', 'field_type', 'field_config'
        )
        
        # Get available match types per field type
        match_types_by_field_type = {
            'text': ['exact', 'case_insensitive', 'fuzzy'],
            'textarea': ['exact', 'case_insensitive', 'fuzzy'],
            'email': ['exact', 'case_insensitive', 'email_normalized'],
            'phone': ['exact', 'phone_normalized'],
            'url': ['exact', 'case_insensitive', 'url_normalized'],
            'number': ['exact', 'numeric'],
            'select': ['exact'],
        }
        
        # Get available URL extraction rules
        request = self.context.get('request')
        url_extraction_rules = []
        if hasattr(request, 'tenant'):
            url_extraction_rules = list(URLExtractionRule.objects.filter(
                tenant=request.tenant,
                is_active=True
            ).values('id', 'name', 'description', 'extraction_format'))
        
        return {
            'pipeline_id': pipeline.id,
            'pipeline_name': pipeline.name,
            'available_fields': list(suitable_fields),
            'match_types_by_field_type': match_types_by_field_type,
            'url_extraction_rules': url_extraction_rules,
            'supported_operators': ['AND', 'OR'],
            'example_logic_structures': {
                'simple_and': {
                    'operator': 'AND',
                    'fields': [
                        {'field': 'email', 'match_type': 'email_normalized'},
                        {'field': 'phone', 'match_type': 'phone_normalized'}
                    ]
                },
                'complex_or': {
                    'operator': 'OR',
                    'conditions': [
                        {
                            'operator': 'AND',
                            'fields': [
                                {'field': 'email', 'match_type': 'email_normalized'},
                                {'field': 'phone', 'match_type': 'phone_normalized'}
                            ]
                        },
                        {
                            'operator': 'AND',
                            'fields': [
                                {'field': 'linkedin_url', 'match_type': 'url_normalized'},
                                {'field': 'full_name', 'match_type': 'fuzzy'}
                            ]
                        }
                    ]
                }
            }
        }


class RuleTestRequestSerializer(serializers.Serializer):
    """Serializer for testing duplicate rules"""
    record1_data = serializers.DictField(help_text="First record data")
    record2_data = serializers.DictField(help_text="Second record data")
    
    def validate(self, attrs):
        """Validate test data has required fields"""
        record1 = attrs['record1_data']
        record2 = attrs['record2_data']
        
        if not record1:
            raise serializers.ValidationError("record1_data cannot be empty")
        
        if not record2:
            raise serializers.ValidationError("record2_data cannot be empty")
        
        return attrs


class URLExtractionTestSerializer(serializers.Serializer):
    """Serializer for testing URL extraction rules"""
    test_urls = serializers.ListField(
        child=serializers.URLField(),
        help_text="List of URLs to test extraction against"
    )
    
    def validate_test_urls(self, value):
        if not value:
            raise serializers.ValidationError("At least one test URL is required")
        return value


class FieldGroupSerializer(serializers.ModelSerializer):
    """Serializer for field groups"""
    field_count = serializers.ReadOnlyField()
    
    class Meta:
        model = FieldGroup
        fields = [
            'id', 'name', 'description', 'color', 'icon',
            'display_order', 'field_count',
            'created_at', 'created_by', 'updated_at', 'updated_by'
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'updated_at', 'updated_by']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['updated_by'] = self.context['request'].user
        return super().update(instance, validated_data)