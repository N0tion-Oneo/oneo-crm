"""
Serializers for saved filters and sharing functionality
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from pipelines.models import SavedFilter, Pipeline
from sharing.models import SharedFilter
from authentication.serializers import UserSerializer

User = get_user_model()


class SavedFilterSerializer(serializers.ModelSerializer):
    """Serializer for SavedFilter model"""
    
    created_by = UserSerializer(read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    pipeline_slug = serializers.CharField(source='pipeline.slug', read_only=True)
    can_share = serializers.SerializerMethodField()
    shareable_fields = serializers.SerializerMethodField()
    share_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedFilter
        fields = [
            'id', 'name', 'description', 'pipeline', 'pipeline_name', 'pipeline_slug',
            'created_by', 'filter_config', 'view_mode', 'visible_fields', 'sort_config',
            'is_shareable', 'share_access_level', 'is_default', 'usage_count', 
            'last_used_at', 'can_share', 'shareable_fields', 'share_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'usage_count', 'last_used_at', 'created_at', 'updated_at']
    
    def get_can_share(self, obj):
        """Check if this filter can be shared"""
        can_share, reason = obj.can_be_shared()
        return {
            'allowed': can_share,
            'reason': reason
        }
    
    def get_shareable_fields(self, obj):
        """Get list of fields that can be shared"""
        return list(obj.get_shareable_fields())
    
    def get_share_count(self, obj):
        """Get number of active shares for this filter"""
        return obj.shares.filter(is_active=True).count()
    
    def create(self, validated_data):
        """Set the created_by field to the request user"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate_visible_fields(self, value):
        """Validate that visible fields belong to the pipeline"""
        if not value:
            return value
        
        pipeline = self.instance.pipeline if self.instance else None
        if not pipeline and 'pipeline' in self.initial_data:
            try:
                pipeline = Pipeline.objects.get(id=self.initial_data['pipeline'])
            except Pipeline.DoesNotExist:
                raise serializers.ValidationError("Invalid pipeline")
        
        if pipeline:
            valid_fields = set(pipeline.fields.values_list('slug', flat=True))
            invalid_fields = set(value) - valid_fields
            if invalid_fields:
                raise serializers.ValidationError(
                    f"Invalid fields for this pipeline: {', '.join(invalid_fields)}"
                )
        
        return value
    
    def validate(self, attrs):
        """Validate the saved filter data"""
        # Ensure only one default filter per user per pipeline
        if attrs.get('is_default', False):
            pipeline = attrs.get('pipeline') or (self.instance.pipeline if self.instance else None)
            user = self.context['request'].user
            
            existing_default = SavedFilter.objects.filter(
                pipeline=pipeline,
                created_by=user,
                is_default=True
            )
            
            if self.instance:
                existing_default = existing_default.exclude(id=self.instance.id)
            
            if existing_default.exists():
                raise serializers.ValidationError(
                    "You already have a default filter for this pipeline"
                )
        
        return attrs


class SavedFilterListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing saved filters"""
    
    created_by = UserSerializer(read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    share_count = serializers.SerializerMethodField()
    can_share = serializers.SerializerMethodField()
    shareable_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedFilter
        fields = [
            'id', 'name', 'description', 'pipeline', 'pipeline_name',
            'created_by', 'filter_config', 'view_mode', 'visible_fields', 'sort_config',
            'is_shareable', 'is_default', 'usage_count', 'last_used_at', 
            'can_share', 'shareable_fields', 'share_count', 'created_at'
        ]
    
    def get_can_share(self, obj):
        """Check if this filter can be shared"""
        can_share, reason = obj.can_be_shared()
        return {
            'allowed': can_share,
            'reason': reason
        }
    
    def get_shareable_fields(self, obj):
        """Get list of fields that can be shared"""
        return list(obj.get_shareable_fields())
    
    def get_share_count(self, obj):
        """Get number of active shares for this filter"""
        return obj.shares.filter(is_active=True).count()


class SharedFilterSerializer(serializers.ModelSerializer):
    """Serializer for SharedFilter model"""
    
    shared_by = UserSerializer(read_only=True)
    saved_filter_name = serializers.CharField(source='saved_filter.name', read_only=True)
    pipeline_name = serializers.CharField(source='saved_filter.pipeline.name', read_only=True)
    time_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedFilter
        fields = [
            'id', 'saved_filter', 'saved_filter_name', 'pipeline_name',
            'encrypted_token', 'shared_by', 'intended_recipient_email',
            'access_mode', 'shared_fields', 'expires_at', 'access_count', 'last_accessed_at',
            'last_accessed_ip', 'is_active', 'revoked_at', 'revoked_by',
            'time_remaining', 'status', 'created_at'
        ]
        read_only_fields = [
            'encrypted_token', 'shared_by', 'access_count', 'last_accessed_at',
            'last_accessed_ip', 'revoked_at', 'revoked_by', 'created_at'
        ]
    
    def get_time_remaining(self, obj):
        """Get time remaining in seconds"""
        return obj.time_remaining_seconds
    
    def create(self, validated_data):
        """Set the shared_by field to the request user"""
        validated_data['shared_by'] = self.context['request'].user
        return super().create(validated_data)


class SharedFilterCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating shared filters"""
    
    shared_fields = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="Specific field slugs to include in this share"
    )
    
    class Meta:
        model = SharedFilter
        fields = [
            'intended_recipient_email', 'access_mode', 'expires_at', 'shared_fields'
        ]
    
    def validate_saved_filter(self, value):
        """Validate that the filter can be shared"""
        can_share, reason = value.can_be_shared()
        if not can_share:
            raise serializers.ValidationError(f"Filter cannot be shared: {reason}")
        return value
    
    def validate_shared_fields(self, value):
        """Validate that shared fields are approved for sharing"""
        if not value:  # Empty list is allowed
            return value
        
        # Get the saved filter from the request data
        saved_filter_id = self.initial_data.get('saved_filter')
        if not saved_filter_id:
            return value
        
        try:
            from pipelines.models import SavedFilter
            saved_filter = SavedFilter.objects.get(id=saved_filter_id)
            
            # Get fields that are approved for sharing
            shareable_fields = set(saved_filter.get_shareable_fields())
            
            # Check if all requested fields are in the shareable set
            invalid_fields = set(value) - shareable_fields
            if invalid_fields:
                raise serializers.ValidationError(
                    f"Fields not approved for sharing: {', '.join(invalid_fields)}. "
                    f"Only these fields can be shared: {', '.join(shareable_fields)}"
                )
                
        except Exception as e:
            # If we can't validate, log and continue
            print(f"Warning: Could not validate shared_fields: {e}")
        
        return value
    
    def validate(self, attrs):
        """Validate sharing permissions"""
        # Get saved_filter from context (passed by the view)
        saved_filter = self.context.get('saved_filter')
        if not saved_filter:
            raise serializers.ValidationError("Saved filter not found in context")
            
        user = self.context['request'].user
        
        # Check if user owns the filter or has permission to share it
        if saved_filter.created_by != user:
            raise serializers.ValidationError(
                "You can only share filters you created"
            )
        
        # If no shared_fields specified, default to all shareable fields
        if 'shared_fields' not in attrs or not attrs['shared_fields']:
            attrs['shared_fields'] = list(saved_filter.get_shareable_fields())
        
        return attrs


class SharedFilterAccessSerializer(serializers.Serializer):
    """Serializer for accessing shared filters via token"""
    
    accessor_name = serializers.CharField(max_length=255)
    accessor_email = serializers.EmailField()
    
    def validate_accessor_email(self, value):
        """Validate that accessor email matches intended recipient"""
        shared_filter = self.context.get('shared_filter')
        if shared_filter and shared_filter.intended_recipient_email != value:
            raise serializers.ValidationError(
                "Email does not match intended recipient"
            )
        return value