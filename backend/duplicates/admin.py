from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import (
    DuplicateRule, URLExtractionRule, DuplicateRuleTest, DuplicateDetectionResult,
    DuplicateMatch, DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
)


# Inline for resolutions
class DuplicateResolutionInline(admin.TabularInline):
    model = DuplicateResolution
    extra = 0
    readonly_fields = ['resolved_at', 'resolved_by']


@admin.register(DuplicateRule)
class DuplicateRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'pipeline', 'action_on_duplicate', 'is_active', 'created_at'
    ]
    list_filter = ['action_on_duplicate', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'pipeline__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'name', 'description', 'pipeline')
        }),
        ('Rule Logic', {
            'fields': ('logic', 'action_on_duplicate', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(URLExtractionRule)
class URLExtractionRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'extraction_format', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'extraction_format']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(DuplicateRuleTest)
class DuplicateRuleTestAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule', 'expected_result', 'last_test_result', 'last_test_at']
    list_filter = ['expected_result', 'last_test_result', 'last_test_at']
    search_fields = ['name', 'rule__name']
    readonly_fields = ['last_test_at', 'last_test_result', 'test_details']
    
    fieldsets = (
        ('Test Information', {
            'fields': ('rule', 'name', 'description')
        }),
        ('Test Data', {
            'fields': ('record1_data', 'record2_data', 'expected_result')
        }),
        ('Test Results', {
            'fields': ('last_test_result', 'last_test_at', 'test_details'),
            'classes': ['collapse']
        })
    )


@admin.register(DuplicateMatch)
class DuplicateMatchAdmin(admin.ModelAdmin):
    list_display = [
        'record1_link', 'record2_link', 'rule', 'confidence_score',
        'status', 'detection_method', 'detected_at'
    ]
    list_filter = [
        'status', 'rule', 'detection_method', 'detected_at',
        'reviewed_at'
    ]
    search_fields = [
        'record1__id', 'record2__id', 'rule__name'
    ]
    readonly_fields = [
        'detected_at', 'field_scores_formatted', 'matched_fields_formatted'
    ]
    inlines = [DuplicateResolutionInline]
    
    fieldsets = (
        ('Match Information', {
            'fields': (
                'tenant', 'rule', 'record1', 'record2', 'confidence_score',
                'detection_method'
            )
        }),
        ('Match Details', {
            'fields': ('field_scores_formatted', 'matched_fields_formatted'),
            'classes': ['collapse']
        }),
        ('Review Information', {
            'fields': (
                'status', 'reviewed_by', 'reviewed_at',
                'resolution_notes', 'auto_resolution_reason'
            )
        }),
        ('Timestamps', {
            'fields': ('detected_at',),
            'classes': ['collapse']
        })
    )
    
    def record1_link(self, obj):
        url = reverse('admin:pipelines_record_change', args=[obj.record1.pk])
        return format_html('<a href="{}">{}</a>', url, obj.record1.pk)
    record1_link.short_description = 'Record 1'
    
    def record2_link(self, obj):
        url = reverse('admin:pipelines_record_change', args=[obj.record2.pk])
        return format_html('<a href="{}">{}</a>', url, obj.record2.pk)
    record2_link.short_description = 'Record 2'
    
    def field_scores_formatted(self, obj):
        if obj.field_scores:
            return mark_safe(f'<pre>{json.dumps(obj.field_scores, indent=2)}</pre>')
        return "No field scores"
    field_scores_formatted.short_description = 'Field Scores'
    
    def matched_fields_formatted(self, obj):
        if obj.matched_fields:
            return ', '.join(obj.matched_fields)
        return "No matched fields"
    matched_fields_formatted.short_description = 'Matched Fields'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(DuplicateResolution)
class DuplicateResolutionAdmin(admin.ModelAdmin):
    list_display = [
        'duplicate_match', 'action_taken', 'resolved_by', 'resolved_at'
    ]
    list_filter = ['action_taken', 'resolved_at']
    search_fields = [
        'duplicate_match__record1__id', 'duplicate_match__record2__id',
        'notes'
    ]
    readonly_fields = ['resolved_at']
    
    fieldsets = (
        ('Resolution Information', {
            'fields': (
                'tenant', 'duplicate_match', 'action_taken', 'notes'
            )
        }),
        ('Resolution Details', {
            'fields': (
                'primary_record', 'merged_record', 'data_changes'
            )
        }),
        ('Metadata', {
            'fields': ('resolved_by', 'resolved_at'),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(DuplicateAnalytics)
class DuplicateAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'rule', 'date', 'records_processed', 'duplicates_detected',
        'false_positives', 'avg_confidence_score'
    ]
    list_filter = ['rule', 'date']
    search_fields = ['rule__name']
    readonly_fields = ['field_performance_formatted', 'algorithm_performance_formatted']
    
    fieldsets = (
        ('Analytics Information', {
            'fields': (
                'tenant', 'rule', 'date', 'records_processed',
                'duplicates_detected', 'false_positives', 'true_positives'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'avg_confidence_score', 'processing_time_ms',
                'field_performance_formatted', 'algorithm_performance_formatted'
            ),
            'classes': ['collapse']
        })
    )
    
    def field_performance_formatted(self, obj):
        if obj.field_performance:
            return mark_safe(f'<pre>{json.dumps(obj.field_performance, indent=2)}</pre>')
        return "No field performance data"
    field_performance_formatted.short_description = 'Field Performance'
    
    def algorithm_performance_formatted(self, obj):
        if obj.algorithm_performance:
            return mark_safe(f'<pre>{json.dumps(obj.algorithm_performance, indent=2)}</pre>')
        return "No algorithm performance data"
    algorithm_performance_formatted.short_description = 'Algorithm Performance'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(DuplicateExclusion)
class DuplicateExclusionAdmin(admin.ModelAdmin):
    list_display = [
        'record1_link', 'record2_link', 'reason_short', 'created_by', 'created_at'
    ]
    list_filter = ['created_by', 'created_at']
    search_fields = [
        'record1__id', 'record2__id', 'reason'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Exclusion Information', {
            'fields': ('tenant', 'record1', 'record2', 'reason')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ['collapse']
        })
    )
    
    def record1_link(self, obj):
        url = reverse('admin:pipelines_record_change', args=[obj.record1.pk])
        return format_html('<a href="{}">{}</a>', url, obj.record1.pk)
    record1_link.short_description = 'Record 1'
    
    def record2_link(self, obj):
        url = reverse('admin:pipelines_record_change', args=[obj.record2.pk])
        return format_html('<a href="{}">{}</a>', url, obj.record2.pk)
    record2_link.short_description = 'Record 2'
    
    def reason_short(self, obj):
        return obj.reason[:50] + "..." if len(obj.reason) > 50 else obj.reason
    reason_short.short_description = 'Reason'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs