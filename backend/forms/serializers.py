from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    ValidationRule, FormTemplate, FormFieldConfiguration,
    FormFieldValidation, FormSubmission, FormAnalytics
)
from pipelines.models import Pipeline, Field

User = get_user_model()


class ValidationRuleSerializer(serializers.ModelSerializer):
    """Serializer for validation rules with tenant isolation"""
    
    class Meta:
        model = ValidationRule
        fields = [
            'id', 'name', 'description', 'rule_type', 'configuration',
            'error_message', 'warning_message', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Automatically set tenant from request context
        validated_data['tenant'] = self.context['request'].tenant
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class FormFieldValidationSerializer(serializers.ModelSerializer):
    """Serializer for field validation rules"""
    validation_rule = ValidationRuleSerializer(read_only=True)
    validation_rule_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = FormFieldValidation
        fields = [
            'id', 'validation_rule', 'validation_rule_id', 'execution_order',
            'is_active', 'conditional_logic', 'override_message', 'is_blocking',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FormFieldConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for form field configurations"""
    pipeline_field = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Field.objects.all()
    )
    validations = FormFieldValidationSerializer(many=True, read_only=True)
    
    class Meta:
        model = FormFieldConfiguration
        fields = [
            'id', 'pipeline_field', 'display_order', 'is_visible', 'is_readonly',
            'custom_label', 'custom_placeholder', 'custom_help_text',
            'conditional_logic', 'default_value', 'field_width', 'is_active',
            'validations', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FormTemplateSerializer(serializers.ModelSerializer):
    """Serializer for form templates with field configurations"""
    pipeline = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Pipeline.objects.all()
    )
    field_configs = FormFieldConfigurationSerializer(many=True, read_only=True)
    
    class Meta:
        model = FormTemplate
        fields = [
            'id', 'name', 'description', 'pipeline', 'form_type', 'dynamic_mode',
            'target_stage', 'success_message', 'is_active', 'field_configs', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['tenant'] = self.context['request'].tenant
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class FormSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for form submissions"""
    form_template = FormTemplateSerializer(read_only=True)
    form_template_id = serializers.IntegerField(write_only=True)
    submitted_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'form_template', 'form_template_id', 'record', 'submitted_by',
            'submission_data', 'validation_results', 'duplicate_matches',
            'ip_address', 'user_agent', 'referrer', 'session_id',
            'submission_time_ms', 'status', 'submitted_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'validation_results', 'duplicate_matches', 'submitted_at',
            'processed_at'
        ]


class FormAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for form analytics"""
    form_template = FormTemplateSerializer(read_only=True)
    conversion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = FormAnalytics
        fields = [
            'id', 'form_template', 'date', 'views', 'submissions',
            'valid_submissions', 'invalid_submissions', 'duplicate_submissions',
            'abandonment_rate', 'avg_completion_time_ms', 'conversion_rate',
            'field_errors'
        ]
        read_only_fields = ['id']
    
    def get_conversion_rate(self, obj):
        if obj.views > 0:
            return (obj.submissions / obj.views) * 100
        return 0.0


class FormValidationRequestSerializer(serializers.Serializer):
    """Serializer for form validation requests"""
    form_template_id = serializers.IntegerField()
    data = serializers.DictField()
    context = serializers.DictField(required=False, default=dict)


class FieldValidationRequestSerializer(serializers.Serializer):
    """Serializer for individual field validation requests"""
    field_config_id = serializers.IntegerField()
    value = serializers.CharField(allow_blank=True, allow_null=True)
    form_data = serializers.DictField(required=False, default=dict)
    context = serializers.DictField(required=False, default=dict)


class ValidationResultSerializer(serializers.Serializer):
    """Serializer for validation results"""
    is_valid = serializers.BooleanField()
    field_name = serializers.CharField()
    rule_name = serializers.CharField()
    error_message = serializers.CharField(allow_blank=True)
    warning_message = serializers.CharField(allow_blank=True)
    value_checked = serializers.CharField(allow_null=True)
    rule_type = serializers.CharField()
    execution_time_ms = serializers.FloatField()


class FormValidationResultSerializer(serializers.Serializer):
    """Serializer for complete form validation results"""
    is_valid = serializers.BooleanField()
    field_results = serializers.DictField()
    cross_field_results = ValidationResultSerializer(many=True)
    duplicate_results = serializers.ListField()
    execution_time_ms = serializers.FloatField()
    total_errors = serializers.IntegerField()
    total_warnings = serializers.IntegerField()


class DuplicateCheckRequestSerializer(serializers.Serializer):
    """Serializer for duplicate check requests"""
    pipeline_id = serializers.IntegerField()
    data = serializers.DictField()
    exclude_record_id = serializers.CharField(required=False, allow_null=True)
    rule_id = serializers.IntegerField(required=False, allow_null=True)


class DuplicateCandidateSerializer(serializers.Serializer):
    """Serializer for duplicate candidates"""
    record_id = serializers.CharField()
    record_data = serializers.DictField()
    overall_score = serializers.FloatField()
    field_matches = serializers.ListField()
    confidence_breakdown = serializers.DictField()


class PublicFormSubmissionSerializer(serializers.Serializer):
    """Serializer for public form submissions (no authentication required)"""
    form_slug = serializers.SlugField()
    data = serializers.DictField()
    captcha_token = serializers.CharField(required=False, allow_blank=True)
    
    def validate_form_slug(self, value):
        """Validate that the form exists and is public"""
        try:
            form = FormTemplate.objects.get(public_slug=value, is_public=True, is_active=True)
            self.context['form_template'] = form
            return value
        except FormTemplate.DoesNotExist:
            raise serializers.ValidationError("Form not found or not public")


class FormBuilderSerializer(serializers.Serializer):
    """Serializer for form builder operations"""
    form_template_id = serializers.IntegerField()
    field_configs = FormFieldConfigurationSerializer(many=True)
    validation_rules = FormFieldValidationSerializer(many=True, required=False)
    
    def create(self, validated_data):
        """Create form with field configurations and validation rules"""
        form_template_id = validated_data['form_template_id']
        field_configs_data = validated_data['field_configs']
        validation_rules_data = validated_data.get('validation_rules', [])
        
        try:
            form_template = FormTemplate.objects.get(
                id=form_template_id,
                tenant=self.context['request'].tenant
            )
        except FormTemplate.DoesNotExist:
            raise serializers.ValidationError("Form template not found")
        
        # Create field configurations
        field_configs = []
        for config_data in field_configs_data:
            config_data['form_template'] = form_template
            field_config = FormFieldConfiguration.objects.create(**config_data)
            field_configs.append(field_config)
        
        # Create validation rules for fields
        for validation_data in validation_rules_data:
            field_config_id = validation_data.pop('form_field_config_id', None)
            if field_config_id:
                try:
                    field_config = FormFieldConfiguration.objects.get(
                        id=field_config_id,
                        form_template=form_template
                    )
                    validation_data['form_field_config'] = field_config
                    FormFieldValidation.objects.create(**validation_data)
                except FormFieldConfiguration.DoesNotExist:
                    continue
        
        return {
            'form_template': form_template,
            'field_configs': field_configs
        }