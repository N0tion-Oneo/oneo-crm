from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import (
    DuplicateRule, DuplicateFieldRule, DuplicateMatch,
    DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
)


class DuplicateFieldRuleInline(admin.TabularInline):
    model = DuplicateFieldRule
    extra = 0
    fields = [
        'field', 'match_type', 'match_threshold', 'weight',
        'is_required', 'is_active'
    ]
    readonly_fields = ['created_at']


@admin.register(DuplicateRule)
class DuplicateRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'pipeline', 'tenant', 'action_on_duplicate',
        'confidence_threshold', 'field_rule_count', 'is_active', 'created_at'
    ]
    list_filter = [
        'action_on_duplicate', 'is_active', 'enable_fuzzy_matching',
        'enable_phonetic_matching', 'tenant', 'created_at'
    ]
    search_fields = ['name', 'description', 'pipeline__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [DuplicateFieldRuleInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'name', 'description', 'pipeline')
        }),
        ('Detection Configuration', {
            'fields': (
                'confidence_threshold', 'auto_merge_threshold',
                'action_on_duplicate'
            )
        }),
        ('Matching Options', {
            'fields': (
                'enable_fuzzy_matching', 'enable_phonetic_matching',
                'ignore_case', 'normalize_whitespace'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ['collapse']
        })
    )
    
    def field_rule_count(self, obj):
        return obj.field_rules.count()
    field_rule_count.short_description = 'Field Rules'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(DuplicateFieldRule)
class DuplicateFieldRuleAdmin(admin.ModelAdmin):
    list_display = [
        'duplicate_rule', 'field', 'match_type', 'match_threshold',
        'weight', 'is_required', 'is_active'
    ]
    list_filter = [
        'match_type', 'is_required', 'is_active', 'duplicate_rule__pipeline'
    ]
    search_fields = [
        'duplicate_rule__name', 'field__name', 'field__display_name'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Rule Configuration', {
            'fields': ('duplicate_rule', 'field', 'match_type')
        }),
        ('Matching Parameters', {
            'fields': ('match_threshold', 'weight', 'is_required')
        }),
        ('Advanced Configuration', {
            'fields': ('preprocessing_rules', 'custom_regex'),
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(duplicate_rule__tenant=request.tenant)
        return qs


class DuplicateResolutionInline(admin.TabularInline):
    model = DuplicateResolution
    extra = 0
    fields = [
        'action_taken', 'primary_record', 'merged_record',
        'resolved_by', 'resolved_at'
    ]
    readonly_fields = ['resolved_at']


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
        return format_html(
            '<pre>{}</pre>',
            json.dumps(obj.field_scores, indent=2)
        )
    field_scores_formatted.short_description = 'Field Scores'
    
    def matched_fields_formatted(self, obj):
        return format_html(
            '<pre>{}</pre>',
            json.dumps(obj.matched_fields, indent=2)
        )
    matched_fields_formatted.short_description = 'Matched Fields'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(DuplicateResolution)
class DuplicateResolutionAdmin(admin.ModelAdmin):
    list_display = [
        'duplicate_match', 'action_taken', 'primary_record_link',
        'merged_record_link', 'resolved_by', 'resolved_at'
    ]
    list_filter = [
        'action_taken', 'resolved_at', 'resolved_by'
    ]
    search_fields = [
        'duplicate_match__record1__id', 'duplicate_match__record2__id',
        'notes'
    ]
    readonly_fields = ['resolved_at', 'data_changes_formatted']
    
    fieldsets = (
        ('Resolution Information', {
            'fields': (
                'tenant', 'duplicate_match', 'action_taken',
                'primary_record', 'merged_record'
            )
        }),
        ('Data Changes', {
            'fields': ('data_changes_formatted',),
            'classes': ['collapse']
        }),
        ('Resolution Details', {
            'fields': ('resolved_by', 'resolved_at', 'notes')
        })
    )
    
    def primary_record_link(self, obj):
        url = reverse('admin:pipelines_record_change', args=[obj.primary_record.pk])
        return format_html('<a href="{}">{}</a>', url, obj.primary_record.pk)
    primary_record_link.short_description = 'Primary Record'
    
    def merged_record_link(self, obj):
        if obj.merged_record:
            url = reverse('admin:pipelines_record_change', args=[obj.merged_record.pk])
            return format_html('<a href="{}">{}</a>', url, obj.merged_record.pk)
        return "N/A"
    merged_record_link.short_description = 'Merged Record'
    
    def data_changes_formatted(self, obj):
        return format_html(
            '<pre>{}</pre>',
            json.dumps(obj.data_changes, indent=2)
        )
    data_changes_formatted.short_description = 'Data Changes'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(DuplicateAnalytics)
class DuplicateAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'rule', 'date', 'records_processed', 'duplicates_detected',
        'detection_rate', 'avg_confidence_score', 'processing_time_display'
    ]
    list_filter = ['date', 'rule']
    search_fields = ['rule__name']
    readonly_fields = [
        'detection_rate', 'field_performance_formatted',
        'algorithm_performance_formatted'
    ]
    
    fieldsets = (
        ('Analytics Summary', {
            'fields': (
                'tenant', 'rule', 'date', 'records_processed',
                'duplicates_detected', 'detection_rate'
            )
        }),
        ('Quality Metrics', {
            'fields': (
                'false_positives', 'true_positives', 'avg_confidence_score'
            )
        }),
        ('Performance', {
            'fields': ('processing_time_ms',)
        }),
        ('Detailed Performance', {
            'fields': ('field_performance_formatted', 'algorithm_performance_formatted'),
            'classes': ['collapse']
        })
    )
    
    def detection_rate(self, obj):
        if obj.records_processed > 0:
            rate = (obj.duplicates_detected / obj.records_processed) * 100
            return f"{rate:.1f}%"
        return "0%"
    detection_rate.short_description = 'Detection Rate'
    
    def processing_time_display(self, obj):
        if obj.processing_time_ms:
            return f"{obj.processing_time_ms}ms"
        return "N/A"
    processing_time_display.short_description = 'Processing Time'
    
    def field_performance_formatted(self, obj):
        return format_html(
            '<pre>{}</pre>',
            json.dumps(obj.field_performance, indent=2)
        )
    field_performance_formatted.short_description = 'Field Performance'
    
    def algorithm_performance_formatted(self, obj):
        return format_html(
            '<pre>{}</pre>',
            json.dumps(obj.algorithm_performance, indent=2)
        )
    algorithm_performance_formatted.short_description = 'Algorithm Performance'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        return qs


@admin.register(DuplicateExclusion)
class DuplicateExclusionAdmin(admin.ModelAdmin):
    list_display = [
        'record1_link', 'record2_link', 'rule', 'reason_short',
        'created_by', 'created_at'
    ]
    list_filter = ['rule', 'created_at', 'created_by']
    search_fields = [
        'record1__id', 'record2__id', 'reason'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Exclusion Information', {
            'fields': ('tenant', 'record1', 'record2', 'rule')
        }),
        ('Reason', {
            'fields': ('reason',)
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