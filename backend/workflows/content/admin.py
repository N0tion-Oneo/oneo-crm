"""
Django Admin configuration for Content Management System
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    ContentLibrary, ContentAsset, ContentTag, ContentUsage, 
    ContentApproval, ContentType, ContentStatus
)


@admin.register(ContentLibrary)
class ContentLibraryAdmin(admin.ModelAdmin):
    """Admin interface for content libraries"""
    
    list_display = [
        'name', 'parent_library', 'visibility', 'asset_count', 
        'requires_approval', 'is_active', 'created_by', 'created_at'
    ]
    list_filter = ['visibility', 'requires_approval', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['allowed_users']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'parent_library')
        }),
        ('Access Control', {
            'fields': ('visibility', 'created_by', 'allowed_users')
        }),
        ('Settings', {
            'fields': ('is_active', 'requires_approval', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def asset_count(self, obj):
        """Display asset count"""
        count = obj.assets.filter(is_current_version=True).count()
        if count > 0:
            url = reverse('admin:workflows_contentasset_changelist')
            return format_html('<a href="{}?library__id__exact={}">{} assets</a>', url, obj.id, count)
        return '0 assets'
    
    asset_count.short_description = 'Assets'


@admin.register(ContentAsset)
class ContentAssetAdmin(admin.ModelAdmin):
    """Admin interface for content assets"""
    
    list_display = [
        'name', 'content_type', 'library', 'status', 'version', 
        'usage_count', 'performance_score', 'created_by', 'created_at'
    ]
    list_filter = [
        'content_type', 'status', 'visibility', 'is_current_version',
        'library', 'created_at'
    ]
    search_fields = ['name', 'description', 'content_text']
    readonly_fields = [
        'usage_count', 'last_used_at', 'performance_score', 
        'file_size', 'mime_type', 'created_at', 'updated_at'
    ]
    filter_horizontal = ['tags']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'content_type', 'library')
        }),
        ('Content', {
            'fields': ('content_text', 'content_file', 'content_data')
        }),
        ('Template Configuration', {
            'fields': ('template_variables', 'variable_schema'),
            'classes': ('collapse',)
        }),
        ('Organization', {
            'fields': ('tags', 'visibility')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Version Control', {
            'fields': ('version', 'is_current_version', 'parent_version'),
            'classes': ('collapse',)
        }),
        ('Usage Analytics', {
            'fields': ('usage_count', 'last_used_at', 'performance_score'),
            'classes': ('collapse',)
        }),
        ('File Information', {
            'fields': ('file_size', 'mime_type', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        return super().get_queryset(request).select_related(
            'library', 'created_by', 'approved_by'
        ).prefetch_related('tags')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize foreign key fields"""
        if db_field.name == "parent_version":
            # Only show previous versions of the same content
            if hasattr(request, '_obj_'):
                kwargs["queryset"] = ContentAsset.objects.filter(
                    name=request._obj_.name,
                    library=request._obj_.library
                ).exclude(id=request._obj_.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ContentTag)
class ContentTagAdmin(admin.ModelAdmin):
    """Admin interface for content tags"""
    
    list_display = ['name', 'category', 'usage_count', 'color_display', 'created_by', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    def color_display(self, obj):
        """Display color as a colored box"""
        if obj.color_code:
            return format_html(
                '<div style="width:20px;height:20px;background-color:{};border:1px solid #ccc;"></div>',
                obj.color_code
            )
        return '-'
    
    color_display.short_description = 'Color'


@admin.register(ContentUsage)
class ContentUsageAdmin(admin.ModelAdmin):
    """Admin interface for content usage tracking"""
    
    list_display = [
        'content_asset', 'workflow_name', 'node_type', 'usage_type',
        'execution_count', 'success_rate', 'last_execution'
    ]
    list_filter = ['usage_type', 'node_type', 'last_execution']
    search_fields = ['content_asset__name', 'workflow_name', 'node_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Usage Information', {
            'fields': ('content_asset', 'workflow_id', 'workflow_name', 'node_id', 'node_type')
        }),
        ('Usage Details', {
            'fields': ('usage_type', 'variables_used')
        }),
        ('Performance Metrics', {
            'fields': ('execution_count', 'last_execution', 'success_rate')
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('content_asset')


@admin.register(ContentApproval)
class ContentApprovalAdmin(admin.ModelAdmin):
    """Admin interface for content approvals"""
    
    list_display = [
        'content_asset', 'status', 'requested_by', 'assigned_to', 
        'created_at', 'responded_at'
    ]
    list_filter = ['status', 'created_at', 'responded_at']
    search_fields = ['content_asset__name', 'request_message', 'response_message']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Approval Request', {
            'fields': ('content_asset', 'requested_by', 'assigned_to')
        }),
        ('Request Details', {
            'fields': ('request_message', 'changes_requested')
        }),
        ('Response', {
            'fields': ('status', 'response_message', 'responded_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'content_asset', 'requested_by', 'assigned_to'
        )


# Custom admin actions
@admin.action(description='Approve selected content assets')
def approve_content_assets(modeladmin, request, queryset):
    """Bulk approve content assets"""
    updated = queryset.update(
        status=ContentStatus.APPROVED,
        approved_by=request.user,
        approved_at=timezone.now()
    )
    modeladmin.message_user(request, f'{updated} content assets were approved.')


@admin.action(description='Archive selected content assets')
def archive_content_assets(modeladmin, request, queryset):
    """Bulk archive content assets"""
    updated = queryset.update(status=ContentStatus.ARCHIVED)
    modeladmin.message_user(request, f'{updated} content assets were archived.')


# Add actions to ContentAssetAdmin
ContentAssetAdmin.actions = [approve_content_assets, archive_content_assets]