"""
API serializers for all models
"""
from rest_framework import serializers
from rest_framework.fields import empty
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Field, Record
from relationships.models import RelationshipType, Relationship
from authentication.models import UserType
from ai.models import AIJob, AIUsageAnalytics, AIPromptTemplate, AIEmbedding

User = get_user_model()


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
    
    class Meta:
        model = Field
        fields = [
            'id', 'name', 'slug', 'description', 'field_type', 'field_config', 
            'storage_constraints', 'business_rules', 'display_name', 'help_text',
            'enforce_uniqueness', 'create_index', 'is_searchable',
            'is_ai_field', 'display_order', 'is_visible_in_list',
            'is_visible_in_detail', 'is_visible_in_public_forms', 'ai_config', 
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