"""
DRF Serializers for Content Management System
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    ContentLibrary, ContentAsset, ContentTag, ContentUsage, 
    ContentApproval, ContentType, ContentStatus, ContentVisibility
)

User = get_user_model()


class ContentTagSerializer(serializers.ModelSerializer):
    """Serializer for content tags"""
    
    class Meta:
        model = ContentTag
        fields = [
            'id', 'name', 'description', 'color_code', 'category',
            'usage_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']


class ContentLibrarySerializer(serializers.ModelSerializer):
    """Serializer for content libraries"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    full_path = serializers.CharField(read_only=True)
    asset_count = serializers.SerializerMethodField()
    child_libraries = serializers.SerializerMethodField()
    
    class Meta:
        model = ContentLibrary
        fields = [
            'id', 'name', 'description', 'parent_library', 'visibility',
            'created_by', 'created_by_name', 'is_active', 'requires_approval',
            'full_path', 'asset_count', 'child_libraries', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_asset_count(self, obj):
        """Get count of assets in this library"""
        return obj.assets.filter(is_current_version=True).count()
    
    def get_child_libraries(self, obj):
        """Get child libraries"""
        children = obj.child_libraries.filter(is_active=True)
        return ContentLibraryListSerializer(children, many=True).data


class ContentLibraryListSerializer(serializers.ModelSerializer):
    """Simplified serializer for library lists"""
    
    asset_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ContentLibrary
        fields = ['id', 'name', 'description', 'visibility', 'asset_count']
    
    def get_asset_count(self, obj):
        return obj.assets.filter(is_current_version=True).count()


class ContentAssetSerializer(serializers.ModelSerializer):
    """Serializer for content assets"""
    
    library_name = serializers.CharField(source='library.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    tags = ContentTagSerializer(many=True, read_only=True)
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False
    )
    content_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = ContentAsset
        fields = [
            'id', 'name', 'description', 'content_type', 'content_text',
            'content_file', 'content_data', 'content_url', 'template_variables',
            'variable_schema', 'library', 'library_name', 'tags', 'tag_names',
            'status', 'approved_by', 'approved_by_name', 'approved_at',
            'version', 'is_current_version', 'parent_version', 'usage_count',
            'last_used_at', 'performance_score', 'visibility', 'created_by',
            'created_by_name', 'file_size', 'file_size_mb', 'mime_type',
            'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'approved_by', 'approved_at', 'usage_count', 'last_used_at',
            'performance_score', 'created_by', 'file_size', 'mime_type',
            'created_at', 'updated_at'
        ]
    
    def get_content_url(self, obj):
        """Get content URL for file-based assets"""
        if obj.content_file:
            return obj.content_file.url
        return None
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None
    
    def create(self, validated_data):
        """Create content asset with tags"""
        tag_names = validated_data.pop('tag_names', [])
        asset = super().create(validated_data)
        
        # Add tags
        if tag_names:
            from .manager import content_manager
            content_manager._add_tags_to_asset(asset, tag_names, asset.created_by)
        
        return asset
    
    def update(self, instance, validated_data):
        """Update content asset with tags"""
        tag_names = validated_data.pop('tag_names', None)
        asset = super().update(instance, validated_data)
        
        # Update tags if provided
        if tag_names is not None:
            asset.tags.clear()
            from .manager import content_manager
            content_manager._add_tags_to_asset(asset, tag_names, asset.created_by)
        
        return asset


class ContentAssetListSerializer(serializers.ModelSerializer):
    """Simplified serializer for asset lists"""
    
    library_name = serializers.CharField(source='library.name', read_only=True)
    tags = ContentTagSerializer(many=True, read_only=True)
    content_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = ContentAsset
        fields = [
            'id', 'name', 'description', 'content_type', 'library_name',
            'tags', 'status', 'version', 'usage_count', 'last_used_at',
            'content_preview', 'created_at'
        ]
    
    def get_content_preview(self, obj):
        """Get a preview of the content"""
        if obj.content_text:
            return obj.content_text[:200] + ('...' if len(obj.content_text) > 200 else '')
        elif obj.content_file:
            return obj.content_file.url
        elif obj.content_data:
            return str(obj.content_data)[:100]
        return None


class ContentAssetCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating content assets"""
    
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = ContentAsset
        fields = [
            'name', 'description', 'content_type', 'content_text',
            'content_file', 'content_data', 'template_variables',
            'variable_schema', 'library', 'visibility', 'tag_names'
        ]
    
    def validate(self, data):
        """Validate content asset data"""
        content_type = data.get('content_type')
        
        # Ensure at least one content field is provided
        has_text = bool(data.get('content_text'))
        has_file = bool(data.get('content_file'))
        has_data = bool(data.get('content_data'))
        
        if not (has_text or has_file or has_data):
            raise serializers.ValidationError(
                "At least one content field (content_text, content_file, or content_data) must be provided"
            )
        
        # Validate content type consistency
        if content_type in [ContentType.EMAIL_TEMPLATE, ContentType.MESSAGE_TEMPLATE, 
                           ContentType.HTML_SNIPPET, ContentType.TEXT_SNIPPET]:
            if not has_text:
                raise serializers.ValidationError(
                    f"content_text is required for content_type: {content_type}"
                )
        
        elif content_type in [ContentType.IMAGE_ASSET, ContentType.DOCUMENT_ASSET, ContentType.VIDEO_ASSET]:
            if not has_file:
                raise serializers.ValidationError(
                    f"content_file is required for content_type: {content_type}"
                )
        
        elif content_type == ContentType.JSON_DATA:
            if not has_data:
                raise serializers.ValidationError(
                    f"content_data is required for content_type: {content_type}"
                )
        
        return data


class ContentUsageSerializer(serializers.ModelSerializer):
    """Serializer for content usage tracking"""
    
    content_name = serializers.CharField(source='content_asset.name', read_only=True)
    content_type = serializers.CharField(source='content_asset.content_type', read_only=True)
    
    class Meta:
        model = ContentUsage
        fields = [
            'id', 'content_asset', 'content_name', 'content_type',
            'workflow_id', 'workflow_name', 'node_id', 'node_type',
            'usage_type', 'variables_used', 'execution_count',
            'last_execution', 'success_rate', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContentApprovalSerializer(serializers.ModelSerializer):
    """Serializer for content approval requests"""
    
    content_name = serializers.CharField(source='content_asset.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = ContentApproval
        fields = [
            'id', 'content_asset', 'content_name', 'requested_by',
            'requested_by_name', 'assigned_to', 'assigned_to_name',
            'request_message', 'changes_requested', 'status',
            'response_message', 'responded_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'requested_by', 'created_at', 'updated_at']


class ContentRenderSerializer(serializers.Serializer):
    """Serializer for content rendering requests"""
    
    content_asset_id = serializers.UUIDField()
    variables = serializers.DictField(required=False, allow_empty=True)
    workflow_context = serializers.DictField(required=False, allow_empty=True)


class ContentAnalyticsSerializer(serializers.Serializer):
    """Serializer for content analytics data"""
    
    total_usage_count = serializers.IntegerField()
    total_executions = serializers.IntegerField()
    workflows_using_count = serializers.IntegerField()
    average_success_rate = serializers.FloatField()
    last_used_at = serializers.DateTimeField(allow_null=True)
    performance_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    usage_by_workflow = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )


class LibraryAnalyticsSerializer(serializers.Serializer):
    """Serializer for library analytics data"""
    
    total_assets = serializers.IntegerField()
    total_usage_count = serializers.IntegerField()
    assets_by_type = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    assets_by_status = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    most_used_assets = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )