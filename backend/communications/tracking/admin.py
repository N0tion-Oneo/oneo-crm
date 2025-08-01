"""
Django Admin interface for Communication Tracking System
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
import json

from .models import (
    CommunicationTracking, DeliveryTracking, ReadTracking,
    ResponseTracking, CampaignTracking, PerformanceMetrics
)


@admin.register(CommunicationTracking)
class CommunicationTrackingAdmin(admin.ModelAdmin):
    """Admin for communication tracking events"""
    
    list_display = [
        'tracking_type', 'message_subject', 'channel_name', 'status',
        'event_timestamp', 'response_time_display'
    ]
    list_filter = [
        'tracking_type', 'status', 'event_timestamp', 'channel__channel_type'
    ]
    search_fields = [
        'message__subject', 'message__content', 'channel__name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'tracking_data_display'
    ]
    
    fieldsets = (
        ('Tracking Information', {
            'fields': ('message', 'channel', 'conversation', 'tracking_type', 'status')
        }),
        ('Event Details', {
            'fields': ('event_timestamp', 'response_time_ms')
        }),
        ('Technical Data', {
            'fields': ('user_agent', 'ip_address', 'tracking_data_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def message_subject(self, obj):
        """Display message subject or content preview"""
        if obj.message.subject:
            return obj.message.subject
        return obj.message.content[:50] + '...' if len(obj.message.content) > 50 else obj.message.content
    message_subject.short_description = 'Message'
    
    def channel_name(self, obj):
        """Display channel name with link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:communications_channel_change', args=[obj.channel.id]),
            obj.channel.name
        )
    channel_name.short_description = 'Channel'
    
    def response_time_display(self, obj):
        """Display response time in human readable format"""
        if obj.response_time_ms:
            if obj.response_time_ms < 1000:
                return f"{obj.response_time_ms}ms"
            else:
                return f"{obj.response_time_ms/1000:.1f}s"
        return '-'
    response_time_display.short_description = 'Response Time'
    
    def tracking_data_display(self, obj):
        """Display formatted tracking data"""
        if obj.tracking_data:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.tracking_data, indent=2)
            )
        return 'No data'
    tracking_data_display.short_description = 'Tracking Data'


@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
    """Admin for delivery tracking"""
    
    list_display = [
        'message_subject', 'channel_name', 'attempt_count', 'delivery_status',
        'delivery_time_display', 'delivered_at'
    ]
    list_filter = [
        'delivered_at', 'failed_at', 'attempt_count', 'channel__channel_type'
    ]
    search_fields = [
        'message__subject', 'message__content', 'external_tracking_id'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'error_history_display', 
        'provider_response_display'
    ]
    
    fieldsets = (
        ('Delivery Information', {
            'fields': ('message', 'channel', 'external_tracking_id')
        }),
        ('Attempt Tracking', {
            'fields': ('attempt_count', 'max_attempts', 'first_attempt_at')
        }),
        ('Delivery Status', {
            'fields': ('delivered_at', 'failed_at', 'total_delivery_time_ms')
        }),
        ('Error Tracking', {
            'fields': ('last_error_code', 'last_error_message', 'error_history_display'),
            'classes': ('collapse',)
        }),
        ('Provider Data', {
            'fields': ('provider_response_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def message_subject(self, obj):
        """Display message subject"""
        return obj.message.subject or obj.message.content[:50] + '...'
    message_subject.short_description = 'Message'
    
    def channel_name(self, obj):
        """Display channel name"""
        return obj.channel.name
    channel_name.short_description = 'Channel'
    
    def delivery_status(self, obj):
        """Display delivery status with color coding"""
        if obj.is_delivered:
            return format_html('<span style="color: green;">✓ Delivered</span>')
        elif obj.is_failed:
            return format_html('<span style="color: red;">✗ Failed</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending</span>')
    delivery_status.short_description = 'Status'
    
    def delivery_time_display(self, obj):
        """Display delivery time"""
        if obj.total_delivery_time_ms:
            seconds = obj.total_delivery_time_ms / 1000
            if seconds < 60:
                return f"{seconds:.1f}s"
            else:
                return f"{seconds/60:.1f}min"
        return '-'
    delivery_time_display.short_description = 'Delivery Time'
    
    def error_history_display(self, obj):
        """Display error history"""
        if obj.error_history:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.error_history, indent=2)
            )
        return 'No errors'
    error_history_display.short_description = 'Error History'
    
    def provider_response_display(self, obj):
        """Display provider response"""
        if obj.provider_response:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.provider_response, indent=2)
            )
        return 'No response data'
    provider_response_display.short_description = 'Provider Response'


@admin.register(ReadTracking)
class ReadTrackingAdmin(admin.ModelAdmin):
    """Admin for read tracking"""
    
    list_display = [
        'message_subject', 'channel_name', 'read_status', 'read_count',
        'first_read_at', 'time_to_read_display'
    ]
    list_filter = [
        'first_read_at', 'read_receipt_enabled', 'tracking_pixel_loaded',
        'channel__channel_type'
    ]
    search_fields = [
        'message__subject', 'message__content'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'read_devices_display', 'read_locations_display'
    ]
    
    fieldsets = (
        ('Read Information', {
            'fields': ('message', 'channel', 'read_receipt_enabled', 'tracking_pixel_loaded')
        }),
        ('Read Metrics', {
            'fields': ('first_read_at', 'last_read_at', 'read_count', 'time_to_first_read_minutes')
        }),
        ('Engagement', {
            'fields': ('total_read_time_seconds',)
        }),
        ('Tracking Data', {
            'fields': ('read_devices_display', 'read_locations_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def message_subject(self, obj):
        """Display message subject"""
        return obj.message.subject or obj.message.content[:50] + '...'
    message_subject.short_description = 'Message'
    
    def channel_name(self, obj):
        """Display channel name"""
        return obj.channel.name
    channel_name.short_description = 'Channel'
    
    def read_status(self, obj):
        """Display read status"""
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        else:
            return format_html('<span style="color: gray;">○ Unread</span>')
    read_status.short_description = 'Status'
    
    def time_to_read_display(self, obj):
        """Display time to first read"""
        if obj.time_to_first_read_minutes:
            hours = obj.time_to_first_read_minutes // 60
            minutes = obj.time_to_first_read_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return '-'
    time_to_read_display.short_description = 'Time to Read'
    
    def read_devices_display(self, obj):
        """Display read devices"""
        if obj.read_devices:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 150px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.read_devices, indent=2)
            )
        return 'No device data'
    read_devices_display.short_description = 'Read Devices'
    
    def read_locations_display(self, obj):
        """Display read locations"""
        if obj.read_locations:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 150px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.read_locations, indent=2)
            )
        return 'No location data'
    read_locations_display.short_description = 'Read Locations'


@admin.register(ResponseTracking)
class ResponseTrackingAdmin(admin.ModelAdmin):
    """Admin for response tracking"""
    
    list_display = [
        'original_message_subject', 'response_time_display', 'response_sentiment',
        'response_length', 'response_received_at'
    ]
    list_filter = [
        'response_sentiment', 'response_received_at', 'contains_question',
        'contains_action_request'
    ]
    search_fields = [
        'original_message__subject', 'response_message__content'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'response_analysis_display'
    ]
    
    fieldsets = (
        ('Response Information', {
            'fields': ('original_message', 'response_message', 'conversation')
        }),
        ('Response Metrics', {
            'fields': ('response_time_minutes', 'response_received_at', 'response_length')
        }),
        ('Response Analysis', {
            'fields': ('response_sentiment', 'response_category', 'contains_question', 'contains_action_request')
        }),
        ('AI Analysis', {
            'fields': ('response_analysis_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def original_message_subject(self, obj):
        """Display original message subject"""
        return obj.original_message.subject or obj.original_message.content[:50] + '...'
    original_message_subject.short_description = 'Original Message'
    
    def response_time_display(self, obj):
        """Display response time in readable format"""
        minutes = obj.response_time_minutes
        if minutes < 60:
            return f"{minutes}min"
        elif minutes < 1440:  # Less than 24 hours
            hours = minutes // 60
            remaining_minutes = minutes % 60
            return f"{hours}h {remaining_minutes}m"
        else:  # Days
            days = minutes // 1440
            remaining_hours = (minutes % 1440) // 60
            return f"{days}d {remaining_hours}h"
    response_time_display.short_description = 'Response Time'
    
    def response_analysis_display(self, obj):
        """Display response analysis"""
        if obj.response_analysis:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.response_analysis, indent=2)
            )
        return 'No analysis data'
    response_analysis_display.short_description = 'AI Analysis'


@admin.register(CampaignTracking)
class CampaignTrackingAdmin(admin.ModelAdmin):
    """Admin for campaign tracking"""
    
    list_display = [
        'name', 'campaign_type', 'status', 'channel_count',
        'scheduled_start', 'actual_start', 'performance_summary'
    ]
    list_filter = [
        'status', 'campaign_type', 'created_at', 'scheduled_start'
    ]
    search_fields = ['name', 'description']
    readonly_fields = [
        'created_at', 'updated_at', 'duration_days', 'target_audience_display'
    ]
    filter_horizontal = ['channels']
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('name', 'description', 'campaign_type', 'status')
        }),
        ('Configuration', {
            'fields': ('channels', 'target_audience_display')
        }),
        ('Timeline', {
            'fields': ('scheduled_start', 'actual_start', 'scheduled_end', 'actual_end', 'duration_days')
        }),
        ('Performance Targets', {
            'fields': ('target_send_count', 'target_delivery_rate', 'target_open_rate', 'target_response_rate')
        }),
        ('Ownership', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def channel_count(self, obj):
        """Display number of channels"""
        count = obj.channels.count()
        return f"{count} channel{'s' if count != 1 else ''}"
    channel_count.short_description = 'Channels'
    
    def performance_summary(self, obj):
        """Display performance summary"""
        # This would typically fetch from PerformanceMetrics
        return "View Details"  # Placeholder
    performance_summary.short_description = 'Performance'
    
    def target_audience_display(self, obj):
        """Display target audience"""
        if obj.target_audience:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 150px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.target_audience, indent=2)
            )
        return 'No targeting data'
    target_audience_display.short_description = 'Target Audience'


@admin.register(PerformanceMetrics)
class PerformanceMetricsAdmin(admin.ModelAdmin):
    """Admin for performance metrics"""
    
    list_display = [
        'date_time_display', 'scope_display', 'messages_sent', 'delivery_rate',
        'open_rate', 'response_rate', 'engagement_score'
    ]
    list_filter = [
        'date', 'hour', 'channel__channel_type', 'campaign__campaign_type'
    ]
    search_fields = ['channel__name', 'campaign__name']
    readonly_fields = [
        'created_at', 'updated_at', 'engagement_score', 'total_engagement_actions',
        'metadata_display'
    ]
    
    fieldsets = (
        ('Metrics Scope', {
            'fields': ('date', 'hour', 'channel', 'campaign')
        }),
        ('Volume Metrics', {
            'fields': ('messages_sent', 'messages_delivered', 'messages_failed', 'messages_read', 'responses_received')
        }),
        ('Performance Rates', {
            'fields': ('delivery_rate', 'open_rate', 'response_rate', 'bounce_rate')
        }),
        ('Engagement Metrics', {
            'fields': ('engagement_score', 'total_engagement_actions', 'avg_response_time_minutes', 'avg_read_time_seconds')
        }),
        ('Quality Metrics', {
            'fields': ('sentiment_positive_count', 'sentiment_neutral_count', 'sentiment_negative_count')
        }),
        ('Additional Data', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def date_time_display(self, obj):
        """Display date and time"""
        if obj.hour is not None:
            return f"{obj.date} {obj.hour:02d}:00"
        return str(obj.date)
    date_time_display.short_description = 'Date/Time'
    
    def scope_display(self, obj):
        """Display metrics scope"""
        parts = []
        if obj.channel:
            parts.append(f"Channel: {obj.channel.name}")
        if obj.campaign:
            parts.append(f"Campaign: {obj.campaign.name}")
        return " | ".join(parts) if parts else "All channels"
    scope_display.short_description = 'Scope'
    
    def metadata_display(self, obj):
        """Display metadata"""
        if obj.metadata:
            return format_html(
                '<pre style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return 'No additional data'
    metadata_display.short_description = 'Additional Metrics'