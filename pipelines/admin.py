"""
Django admin configuration for pipelines
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import Pipeline, Field, Record, PipelineTemplate


class FieldInline(admin.TabularInline):
    """Inline admin for pipeline fields"""
    model = Field
    extra = 0
    fields = [
        'name', 'slug', 'field_type', 'is_required', 'is_ai_field',
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
    """Admin interface for fields"""
    list_display = [
        'name', 'pipeline', 'field_type', 'is_required', 'is_ai_field',
        'display_order', 'created_at'
    ]
    list_filter = ['field_type', 'is_required', 'is_ai_field', 'is_indexed', 'is_searchable']
    search_fields = ['name', 'pipeline__name']
    readonly_fields = ['slug']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pipeline', 'name', 'slug', 'description', 'field_type')
        }),
        ('Configuration', {
            'fields': ('field_config', 'validation_rules')
        }),
        ('Display', {
            'fields': (
                'display_name', 'help_text', 'placeholder',
                'display_order', 'width',
                'is_visible_in_list', 'is_visible_in_detail'
            )
        }),
        ('Behavior', {
            'fields': ('is_required', 'is_unique', 'is_indexed', 'is_searchable')
        }),
        ('AI Configuration', {
            'fields': ('is_ai_field', 'ai_config'),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('pipeline', 'created_by')


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