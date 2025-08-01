"""
API serializers for all models
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Field, Record
from relationships.models import RelationshipType, Relationship
from authentication.models import UserType

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    user_type = serializers.StringRelatedField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'created_at']


class UserTypeSerializer(serializers.ModelSerializer):
    """User type serializer"""
    
    class Meta:
        model = UserType
        fields = ['id', 'name', 'slug', 'description', 'permissions', 'created_at']


class FieldSerializer(serializers.ModelSerializer):
    """Pipeline field serializer"""
    
    class Meta:
        model = Field
        fields = [
            'id', 'name', 'slug', 'description', 'field_type', 'field_config', 
            'storage_constraints', 'business_rules', 'display_name', 'help_text',
            'enforce_uniqueness', 'create_index', 'is_searchable',
            'is_ai_field', 'display_order', 'is_visible_in_list',
            'is_visible_in_detail', 'ai_config', 'created_at', 'updated_at'
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
            'pipeline_type', 'is_active', 'settings', 'record_count',
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
            'pipeline_type', 'is_active', 'record_count', 'field_count',
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
        validated_data['created_by'] = self.context['request'].user
        validated_data['updated_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['updated_by'] = self.context['request'].user
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
        pipeline = kwargs.pop('pipeline', None)
        super().__init__(*args, **kwargs)
        
        if pipeline:
            self._add_dynamic_fields(pipeline)
    
    def _add_dynamic_fields(self, pipeline):
        """Add dynamic fields based on pipeline schema"""
        for field in pipeline.fields.all():
            field_name = field.slug
            
            # Check if field is required based on business rules
            is_required = self._is_field_required(field)
            
            # Add field to serializer based on type
            if field.field_type in ['text', 'textarea', 'email', 'url']:
                self.fields[field_name] = serializers.CharField(
                    source=f'data.{field_name}',
                    required=is_required,
                    allow_blank=not is_required
                )
            elif field.field_type == 'number':
                self.fields[field_name] = serializers.IntegerField(
                    source=f'data.{field_name}',
                    required=is_required,
                    allow_null=not is_required
                )
            elif field.field_type == 'decimal':
                self.fields[field_name] = serializers.DecimalField(
                    source=f'data.{field_name}',
                    max_digits=10,
                    decimal_places=2,
                    required=is_required,
                    allow_null=not is_required
                )
            elif field.field_type == 'boolean':
                self.fields[field_name] = serializers.BooleanField(
                    source=f'data.{field_name}',
                    required=is_required
                )
            elif field.field_type in ['date', 'datetime']:
                self.fields[field_name] = serializers.DateTimeField(
                    source=f'data.{field_name}',
                    required=is_required,
                    allow_null=not is_required
                )
            elif field.field_type in ['select', 'multiselect']:
                # Handle choice fields
                choices = field.field_config.get('choices', [])
                if field.field_type == 'select':
                    self.fields[field_name] = serializers.ChoiceField(
                        source=f'data.{field_name}',
                        choices=choices,
                        required=is_required,
                        allow_blank=not is_required
                    )
                else:
                    self.fields[field_name] = serializers.ListField(
                        source=f'data.{field_name}',
                        child=serializers.ChoiceField(choices=choices),
                        required=is_required,
                        allow_empty=not is_required
                    )
            else:
                # Fallback to JSON field
                self.fields[field_name] = serializers.JSONField(
                    source=f'data.{field_name}',
                    required=is_required,
                    allow_null=not is_required
                )
    
    def _is_field_required(self, field):
        """Check if field is required based on business rules"""
        business_rules = field.business_rules or {}
        stage_requirements = business_rules.get('stage_requirements', {})
        
        # For now, consider field required if it has any stage requirements
        # In the future, this could be more sophisticated based on current stage
        return bool(stage_requirements)
    
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