"""
Django admin configuration for pipelines
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
import json

from .models import Pipeline, Field, Record, PipelineTemplate


class FieldInline(admin.TabularInline):
    """Inline admin for pipeline fields"""
    model = Field
    extra = 0
    fields = [
        'name', 'slug', 'field_type', 'enforce_uniqueness', 'is_ai_field',
        'display_order', 'is_visible_in_list'
    ]
    readonly_fields = ['slug']
    ordering = ['display_order']


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    """Admin interface for pipelines"""
    list_display = [
        'name', 'pipeline_type', 'record_count', 'is_active',
        'created_by', 'created_at', 'field_count', 'ai_field_count'
    ]
    list_filter = ['pipeline_type', 'is_active', 'access_level', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['slug', 'field_schema', 'record_count', 'last_record_created']
    inlines = [FieldInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'icon', 'color')
        }),
        ('Configuration', {
            'fields': ('pipeline_type', 'template', 'access_level', 'is_active')
        }),
        ('Settings', {
            'fields': ('view_config', 'settings', 'permission_config'),
            'classes': ['collapse']
        }),
        ('Statistics', {
            'fields': ('record_count', 'last_record_created'),
            'classes': ['collapse']
        }),
        ('Schema Cache', {
            'fields': ('field_schema',),
            'classes': ['collapse']
        })
    )
    
    def field_count(self, obj):
        """Get total field count"""
        return obj.fields.count()
    field_count.short_description = 'Fields'
    
    def ai_field_count(self, obj):
        """Get AI field count"""
        count = obj.fields.filter(is_ai_field=True).count()
        if count > 0:
            return format_html(
                '<span style="color: #10B981; font-weight: bold;">⚡ {}</span>',
                count
            )
        return count
    ai_field_count.short_description = 'AI Fields'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('created_by', 'template')


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    """Enhanced admin interface for fields with lifecycle management"""
    list_display = [
        'name', 'pipeline', 'field_type', 'field_status', 'deletion_info',
        'enforce_uniqueness', 'is_ai_field', 'display_order', 'created_at'
    ]
    list_filter = [
        'field_type', 'is_deleted', 'enforce_uniqueness', 'is_ai_field', 
        'create_index', 'is_searchable', 'scheduled_for_hard_delete'
    ]
    search_fields = ['name', 'pipeline__name']
    readonly_fields = ['slug', 'deleted_at', 'deleted_by']
    actions = ['soft_delete_fields', 'restore_fields', 'analyze_field_impact']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pipeline', 'name', 'slug', 'description', 'field_type')
        }),
        ('Configuration', {
            'fields': ('field_config', 'storage_constraints', 'business_rules')
        }),
        ('Display', {
            'fields': (
                'display_name', 'help_text',
                'display_order',
                'is_visible_in_list', 'is_visible_in_detail'
            )
        }),
        ('Storage & Behavior', {
            'fields': ('enforce_uniqueness', 'create_index', 'is_searchable')
        }),
        ('AI Configuration', {
            'fields': ('is_ai_field', 'ai_config'),
            'classes': ['collapse']
        }),
        ('Deletion Management', {
            'fields': (
                'is_deleted', 'deleted_at', 'deleted_by',
                'scheduled_for_hard_delete', 'hard_delete_reason'
            ),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        """Include soft deleted fields by default"""
        return Field.objects.with_deleted().select_related('pipeline', 'created_by', 'deleted_by')
    
    def field_status(self, obj):
        """Display field status with color coding"""
        if obj.scheduled_for_hard_delete:
            remaining = obj.scheduled_for_hard_delete - timezone.now()
            days_remaining = remaining.days if remaining.days > 0 else 0
            return format_html(
                '<span style="color: #DC2626; font-weight: bold;">🗑️ Hard Delete in {} days</span>',
                days_remaining
            )
        elif obj.is_deleted:
            return format_html(
                '<span style="color: #F59E0B; font-weight: bold;">⚠️ Soft Deleted</span>'
            )
        else:
            return format_html(
                '<span style="color: #10B981; font-weight: bold;">✅ Active</span>'
            )
    field_status.short_description = 'Status'
    
    def deletion_info(self, obj):
        """Show deletion information"""
        if obj.is_deleted and obj.deleted_by:
            return format_html(
                '<small>Deleted by: {}<br>Date: {}</small>',
                obj.deleted_by.username,
                obj.deleted_at.strftime('%Y-%m-%d %H:%M') if obj.deleted_at else 'Unknown'
            )
        return '-'
    deletion_info.short_description = 'Deletion Info'
    
    def soft_delete_fields(self, request, queryset):
        """Soft delete selected fields"""
        active_fields = queryset.filter(is_deleted=False)
        if not active_fields:
            self.message_user(request, "No active fields selected", level='warning')
            return
        
        deleted_count = 0
        for field in active_fields:
            success, message = field.soft_delete(request.user, "Admin bulk soft delete")
            if success:
                deleted_count += 1
        
        self.message_user(
            request,
            f"Successfully soft deleted {deleted_count} field(s)",
            level='success' if deleted_count > 0 else 'warning'
        )
    soft_delete_fields.short_description = "Soft delete selected fields"
    
    def restore_fields(self, request, queryset):
        """Restore soft deleted fields"""
        deleted_fields = queryset.filter(is_deleted=True)
        if not deleted_fields:
            self.message_user(request, "No deleted fields selected", level='warning')
            return
        
        restored_count = 0
        for field in deleted_fields:
            success, message = field.restore(request.user)
            if success:
                restored_count += 1
        
        self.message_user(
            request,
            f"Successfully restored {restored_count} field(s)",
            level='success' if restored_count > 0 else 'warning'
        )
    restore_fields.short_description = "Restore selected soft deleted fields"
    
    def analyze_field_impact(self, request, queryset):
        """Analyze impact of field changes"""
        from .migrator import FieldSchemaMigrator
        
        impact_results = []
        for field in queryset:
            migrator = FieldSchemaMigrator(field.pipeline)
            impact = migrator.analyze_field_change_impact(field)
            
            impact_results.append(
                f"Field: {field.name} | "
                f"Records with data: {impact['records_with_data']} | "
                f"Risk level: {impact['risk_level']}"
            )
        
        self.message_user(
            request,
            f"Impact Analysis: {'; '.join(impact_results)}",
            level='info'
        )
    analyze_field_impact.short_description = "Analyze impact of selected fields"


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    """Admin interface for records"""
    list_display = [
        'title', 'pipeline', 'status', 'created_by', 'updated_at',
        'version', 'is_deleted'
    ]
    list_filter = ['pipeline', 'status', 'is_deleted', 'created_at', 'updated_at']
    search_fields = ['title', 'data']
    readonly_fields = ['version', 'search_vector', 'ai_last_updated']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pipeline', 'title', 'status', 'tags')
        }),
        ('Data', {
            'fields': ('data',)
        }),
        ('AI Fields', {
            'fields': ('ai_summary', 'ai_score', 'ai_last_updated'),
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': (
                'created_by', 'updated_by', 'created_at', 'updated_at',
                'version'
            ),
            'classes': ['collapse']
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ['collapse']
        }),
        ('Search', {
            'fields': ('search_vector',),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'pipeline', 'created_by', 'updated_by'
        )
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly"""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing record
            readonly.extend(['pipeline', 'created_by', 'created_at'])
        return readonly


@admin.register(PipelineTemplate)
class PipelineTemplateAdmin(admin.ModelAdmin):
    """Admin interface for pipeline templates"""
    list_display = [
        'name', 'category', 'is_system', 'is_public', 'usage_count',
        'created_by', 'created_at', 'field_count', 'ai_field_count'
    ]
    list_filter = ['category', 'is_system', 'is_public', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['slug', 'usage_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Template Data', {
            'fields': ('template_data',)
        }),
        ('Configuration', {
            'fields': ('is_system', 'is_public')
        }),
        ('Preview', {
            'fields': ('preview_config', 'sample_data'),
            'classes': ['collapse']
        }),
        ('Statistics', {
            'fields': ('usage_count',),
            'classes': ['collapse']
        })
    )
    
    def field_count(self, obj):
        """Get field count from template data"""
        return len(obj.template_data.get('fields', []))
    field_count.short_description = 'Fields'
    
    def ai_field_count(self, obj):
        """Get AI field count from template data"""
        fields = obj.template_data.get('fields', [])
        count = len([f for f in fields if f.get('is_ai_field', False)])
        if count > 0:
            return format_html(
                '<span style="color: #10B981; font-weight: bold;">⚡ {}</span>',
                count
            )
        return count
    ai_field_count.short_description = 'AI Fields'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('created_by')


# Custom admin site configuration
admin.site.site_header = "Oneo CRM Pipeline Administration"
admin.site.site_title = "Pipeline Admin"
admin.site.index_title = "Pipeline System Management"