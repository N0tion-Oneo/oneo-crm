from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import (
    ValidationRule, FormTemplate, FormFieldConfiguration
)


@admin.register(ValidationRule)
class ValidationRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'rule_type', 'tenant', 'is_active', 'created_at'
    ]
    list_filter = [
        'rule_type', 'is_active', 'tenant', 'created_at'
    ]
    search_fields = ['name', 'description', 'error_message']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'name', 'description', 'rule_type')
        }),
        ('Configuration', {
            'fields': ('configuration', 'error_message', 'warning_message')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


# Removed FormFieldValidationInline - simplified validation approach


class FormFieldConfigurationInline(admin.TabularInline):
    model = FormFieldConfiguration
    extra = 0
    fields = [
        'pipeline_field', 'display_order', 'is_visible', 'is_readonly',
        'custom_label', 'field_width', 'is_active'
    ]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'form_type', 'pipeline', 'tenant', 'is_active', 'created_at'
    ]
    list_filter = [
        'form_type', 'is_active', 'tenant', 'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [FormFieldConfigurationInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'name', 'description', 'pipeline')
        }),
        ('Form Configuration', {
            'fields': ('form_type', 'dynamic_mode', 'target_stage', 'success_message')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(FormFieldConfiguration)
class FormFieldConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'form_template', 'pipeline_field', 'display_order',
        'is_visible', 'is_readonly', 'is_active'
    ]
    list_filter = [
        'is_visible', 'is_readonly', 'is_active', 'field_width',
        'form_template__form_type'
    ]
    search_fields = [
        'form_template__name', 'pipeline_field__name',
        'custom_label'
    ]
    readonly_fields = ['created_at', 'updated_at']
    # Removed validation inlines - simplified validation approach
    
    fieldsets = (
        ('Field Configuration', {
            'fields': (
                'form_template', 'pipeline_field', 'display_order',
                'field_width'
            )
        }),
        ('Visibility & Behavior', {
            'fields': ('is_visible', 'is_readonly', 'is_active')
        }),
        ('Customization', {
            'fields': (
                'custom_label', 'custom_placeholder', 'custom_help_text',
                'default_value'
            ),
            'classes': ['collapse']
        }),
        ('Conditional Logic', {
            'fields': ('conditional_logic',),
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        })
    )
    
    # Removed validation_count method - simplified validation approach
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(form_template__tenant=request.tenant)
        return qs


# Removed FormSubmission and FormAnalytics admin classes - simplified forms approach
