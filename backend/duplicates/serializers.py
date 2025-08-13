from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    DuplicateRule, URLExtractionRule, DuplicateRuleTest, DuplicateDetectionResult,
    DuplicateMatch, DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
)
from pipelines.models import Pipeline, Field, Record

User = get_user_model()


class RecordForDuplicatesSerializer(serializers.ModelSerializer):
    """Lightweight serializer for records in duplicate comparisons"""
    
    class Meta:
        model = Record
        fields = ['id', 'title', 'data']
        

class DuplicateRuleForMatchesSerializer(serializers.ModelSerializer):
    """Lightweight serializer for rules in duplicate matches"""
    
    class Meta:
        model = DuplicateRule
        fields = ['id', 'name']


class DuplicateMatchSerializer(serializers.ModelSerializer):
    """Serializer for duplicate matches"""
    rule = DuplicateRuleForMatchesSerializer(read_only=True)
    record1 = RecordForDuplicatesSerializer(read_only=True)
    record2 = RecordForDuplicatesSerializer(read_only=True)
    reviewed_by = serializers.StringRelatedField(read_only=True)
    latest_resolution = serializers.SerializerMethodField()
    
    class Meta:
        model = DuplicateMatch
        fields = [
            'id', 'rule', 'record1', 'record2', 'confidence_score',
            'field_scores', 'matched_fields', 'detection_method',
            'detected_at', 'reviewed_by', 'reviewed_at', 'status',
            'resolution_notes', 'auto_resolution_reason', 'latest_resolution'
        ]
        read_only_fields = [
            'id', 'detected_at', 'field_scores', 'matched_fields',
            'detection_method', 'confidence_score'
        ]
    
    def get_latest_resolution(self, obj):
        """Get the latest resolution for this duplicate match"""
        if obj.status != 'pending':
            # Get the most recent resolution (excluding rollback actions)
            latest_resolution = obj.resolutions.exclude(action_taken='rollback').order_by('-resolved_at').first()
            if latest_resolution:
                return {
                    'id': latest_resolution.id,
                    'action_taken': latest_resolution.action_taken,
                    'resolved_by': latest_resolution.resolved_by.username if latest_resolution.resolved_by else None,
                    'resolved_at': latest_resolution.resolved_at.isoformat() if latest_resolution.resolved_at else None,
                    'notes': latest_resolution.notes
                }
        return None


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
    rule = serializers.StringRelatedField(read_only=True)
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
        read_only_fields = ['id', 'detection_rate', 'precision']
    
    def get_detection_rate(self, obj):
        if obj.records_processed > 0:
            return obj.duplicates_detected / obj.records_processed
        return 0.0
    
    def get_precision(self, obj):
        total_detected = obj.true_positives + obj.false_positives
        if total_detected > 0:
            return obj.true_positives / total_detected
        return 0.0


class DuplicateExclusionSerializer(serializers.ModelSerializer):
    """Serializer for duplicate exclusions"""
    record1 = serializers.StringRelatedField(read_only=True)
    record2 = serializers.StringRelatedField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = DuplicateExclusion
        fields = [
            'id', 'record1', 'record2', 'reason', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']


class DuplicateDetectionRequestSerializer(serializers.Serializer):
    """Serializer for duplicate detection requests"""
    record_data = serializers.DictField()
    pipeline_id = serializers.IntegerField()
    rule_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class DuplicateComparisonSerializer(serializers.Serializer):
    """Serializer for comparing two records for duplicates"""
    record1_data = serializers.DictField()
    record2_data = serializers.DictField()


class DuplicateBulkResolutionSerializer(serializers.Serializer):
    """Serializer for bulk duplicate resolution"""
    match_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of duplicate match IDs to resolve"
    )
    action = serializers.ChoiceField(
        choices=['merge', 'keep_both', 'ignore'],
        help_text="Action to take for all selected matches"
    )
    notes = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="Optional notes for the resolution"
    )
    
    def validate_match_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one match ID is required")
        return value
    
    def validate(self, data):
        # Validate that matches exist and belong to current tenant
        request = self.context.get('request')
        if request and hasattr(request, 'tenant'):
            matches = DuplicateMatch.objects.filter(
                id__in=data['match_ids'],
                tenant=request.tenant
            )
            if matches.count() != len(data['match_ids']):
                raise serializers.ValidationError(
                    "Some matches not found or don't belong to current tenant"
                )
        return data


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