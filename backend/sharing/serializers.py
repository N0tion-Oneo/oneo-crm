"""
Serializers for sharing models
"""
from rest_framework import serializers
from .models import SharedRecord, SharedRecordAccess
from pipelines.serializers import RecordSerializer


class SharedRecordSerializer(serializers.ModelSerializer):
    """Serializer for SharedRecord model"""
    
    record = RecordSerializer(read_only=True)
    shared_by_name = serializers.CharField(source='shared_by.get_full_name', read_only=True)
    shared_by_email = serializers.CharField(source='shared_by.email', read_only=True)
    status = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    time_remaining_seconds = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = SharedRecord
        fields = [
            'id', 'encrypted_token', 'record', 'shared_by_name', 'shared_by_email',
            'access_mode', 'expires_at', 'created_at', 'updated_at',
            'access_count', 'last_accessed_at', 'last_accessed_ip',
            'is_active', 'revoked_at', 'status', 'is_expired', 'is_valid',
            'time_remaining_seconds'
        ]
        extra_kwargs = {
            'encrypted_token': {'write_only': True}  # Don't expose token in listings
        }


class SharedRecordListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    
    record_title = serializers.CharField(source='record.title', read_only=True)
    pipeline_name = serializers.CharField(source='record.pipeline.name', read_only=True)
    shared_by_name = serializers.CharField(source='shared_by.get_full_name', read_only=True)
    status = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    time_remaining_seconds = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = SharedRecord
        fields = [
            'id', 'encrypted_token', 'record_title', 'pipeline_name', 'shared_by_name',
            'access_mode', 'expires_at', 'created_at',
            'access_count', 'last_accessed_at',
            'is_active', 'revoked_at', 'status', 'is_expired',
            'time_remaining_seconds'
        ]


class SharedRecordAccessSerializer(serializers.ModelSerializer):
    """Serializer for SharedRecordAccess model"""
    
    class Meta:
        model = SharedRecordAccess
        fields = [
            'id', 'accessed_at', 'accessor_name', 'accessor_email',
            'ip_address', 'user_agent', 'country', 'city', 'session_duration'
        ]


class RevokeSharedRecordSerializer(serializers.Serializer):
    """Serializer for revoking shared records"""
    
    reason = serializers.CharField(max_length=500, required=False, help_text="Optional reason for revocation")