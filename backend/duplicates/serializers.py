from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    DuplicateRule, DuplicateFieldRule, DuplicateMatch,
    DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
)
from pipelines.models import Pipeline, Field, Record

User = get_user_model()


class DuplicateFieldRuleSerializer(serializers.ModelSerializer):
    """Serializer for duplicate field rules"""
    field = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Field.objects.all()
    )
    
    class Meta:
        model = DuplicateFieldRule
        fields = [
            'id', 'field', 'match_type', 'match_threshold', 'weight',
            'is_required', 'preprocessing_rules', 'custom_regex',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DuplicateRuleSerializer(serializers.ModelSerializer):
    """Serializer for duplicate rules with field rules"""
    pipeline = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Pipeline.objects.all()
    )
    field_rules = DuplicateFieldRuleSerializer(many=True, read_only=True)
    
    class Meta:
        model = DuplicateRule
        fields = [
            'id', 'name', 'description', 'pipeline', 'is_active',
            'action_on_duplicate', 'confidence_threshold', 'auto_merge_threshold',
            'enable_fuzzy_matching', 'enable_phonetic_matching',
            'ignore_case', 'normalize_whitespace', 'field_rules',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['tenant'] = self.context['request'].tenant
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class DuplicateMatchSerializer(serializers.ModelSerializer):
    """Serializer for duplicate matches"""
    rule = DuplicateRuleSerializer(read_only=True)
    record1 = serializers.StringRelatedField(read_only=True)
    record2 = serializers.StringRelatedField(read_only=True)
    reviewed_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = DuplicateMatch
        fields = [
            'id', 'rule', 'record1', 'record2', 'confidence_score',
            'field_scores', 'matched_fields', 'detection_method',
            'detected_at', 'reviewed_by', 'reviewed_at', 'status',
            'resolution_notes', 'auto_resolution_reason'
        ]
        read_only_fields = [
            'id', 'detected_at', 'field_scores', 'matched_fields',
            'detection_method', 'confidence_score'
        ]


class DuplicateResolutionSerializer(serializers.ModelSerializer):
    """Serializer for duplicate resolutions"""
    duplicate_match = DuplicateMatchSerializer(read_only=True)
    primary_record = serializers.StringRelatedField(read_only=True)
    merged_record = serializers.StringRelatedField(read_only=True)
    resolved_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = DuplicateResolution
        fields = [
            'id', 'duplicate_match', 'action_taken', 'primary_record',
            'merged_record', 'data_changes', 'resolved_by', 'resolved_at',
            'notes'
        ]
        read_only_fields = ['id', 'resolved_at', 'resolved_by']


class DuplicateAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for duplicate analytics"""
    rule = DuplicateRuleSerializer(read_only=True)
    detection_rate = serializers.SerializerMethodField()
    precision = serializers.SerializerMethodField()
    
    class Meta:
        model = DuplicateAnalytics
        fields = [
            'id', 'rule', 'date', 'records_processed', 'duplicates_detected',
            'false_positives', 'true_positives', 'avg_confidence_score',
            'processing_time_ms', 'detection_rate', 'precision',
            'field_performance', 'algorithm_performance'
        ]
        read_only_fields = ['id']
    
    def get_detection_rate(self, obj):
        if obj.records_processed > 0:
            return (obj.duplicates_detected / obj.records_processed) * 100
        return 0.0
    
    def get_precision(self, obj):
        total_positives = obj.true_positives + obj.false_positives
        if total_positives > 0:
            return (obj.true_positives / total_positives) * 100
        return 0.0


class DuplicateExclusionSerializer(serializers.ModelSerializer):
    """Serializer for duplicate exclusions"""
    record1 = serializers.StringRelatedField(read_only=True)
    record2 = serializers.StringRelatedField(read_only=True)
    rule = DuplicateRuleSerializer(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = DuplicateExclusion
        fields = [
            'id', 'record1', 'record2', 'rule', 'reason',
            'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']


class DuplicateDetectionRequestSerializer(serializers.Serializer):
    """Serializer for duplicate detection requests"""
    record_data = serializers.DictField()
    pipeline_id = serializers.IntegerField()
    exclude_record_id = serializers.CharField(required=False, allow_null=True)
    rule_id = serializers.IntegerField(required=False, allow_null=True)
    confidence_threshold = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)


class DuplicateComparisonSerializer(serializers.Serializer):
    """Serializer for comparing two records"""
    record1_id = serializers.CharField()
    record2_id = serializers.CharField()
    rule_id = serializers.IntegerField(required=False, allow_null=True)


class DuplicateBulkResolutionSerializer(serializers.Serializer):
    """Serializer for bulk duplicate resolution"""
    match_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    action = serializers.ChoiceField(
        choices=DuplicateResolution.ACTION_CHOICES
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_match_ids(self, value):
        """Validate that all match IDs exist and belong to tenant"""
        tenant = self.context['request'].tenant
        existing_matches = DuplicateMatch.objects.filter(
            id__in=value,
            tenant=tenant
        ).count()
        
        if existing_matches != len(value):
            raise serializers.ValidationError(
                "One or more duplicate matches not found or not accessible"
            )
        
        return value


class DuplicateRuleBuilderSerializer(serializers.Serializer):
    """Serializer for building duplicate rules with field rules"""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    pipeline_id = serializers.IntegerField()
    confidence_threshold = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.8)
    action_on_duplicate = serializers.ChoiceField(
        choices=DuplicateRule.ACTION_CHOICES,
        default='warn'
    )
    enable_fuzzy_matching = serializers.BooleanField(default=True)
    enable_phonetic_matching = serializers.BooleanField(default=True)
    field_rules = DuplicateFieldRuleSerializer(many=True)
    
    def validate_pipeline_id(self, value):
        """Validate pipeline exists and is accessible"""
        try:
            pipeline = Pipeline.objects.get(
                id=value,
                tenant=self.context['request'].tenant
            )
            self.context['pipeline'] = pipeline
            return value
        except Pipeline.DoesNotExist:
            raise serializers.ValidationError("Pipeline not found")
    
    def create(self, validated_data):
        """Create duplicate rule with field rules"""
        field_rules_data = validated_data.pop('field_rules')
        pipeline = self.context['pipeline']
        
        # Create duplicate rule
        duplicate_rule = DuplicateRule.objects.create(
            tenant=self.context['request'].tenant,
            created_by=self.context['request'].user,
            pipeline=pipeline,
            **validated_data
        )
        
        # Create field rules
        for field_rule_data in field_rules_data:
            DuplicateFieldRule.objects.create(
                duplicate_rule=duplicate_rule,
                **field_rule_data
            )
        
        return duplicate_rule


class DuplicateMatchResultSerializer(serializers.Serializer):
    """Serializer for duplicate match results"""
    record_id = serializers.CharField()
    record_data = serializers.DictField()
    overall_score = serializers.FloatField()
    field_matches = serializers.ListField()
    confidence_breakdown = serializers.DictField()


class DuplicateStatisticsSerializer(serializers.Serializer):
    """Serializer for duplicate statistics"""
    total_rules = serializers.IntegerField()
    active_rules = serializers.IntegerField()
    total_matches = serializers.IntegerField()
    pending_matches = serializers.IntegerField()
    resolved_matches = serializers.IntegerField()
    false_positives = serializers.IntegerField()
    avg_confidence_score = serializers.FloatField()
    processing_time_stats = serializers.DictField()
    top_performing_rules = serializers.ListField()
    field_performance = serializers.DictField()