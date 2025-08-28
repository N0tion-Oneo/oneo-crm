from django.contrib import admin
from .models import (
    TenantUniPileConfig, UserChannelConnection, Channel, 
    Conversation, Message, CommunicationAnalytics, ChatAttendee,
    Participant, ConversationParticipant
)


@admin.register(ChatAttendee)
class ChatAttendeeAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_id', 'channel', 'is_self', 'contact_record', 'sync_status', 'last_synced_at']
    list_filter = ['channel__channel_type', 'is_self', 'sync_status', 'last_synced_at']
    search_fields = ['name', 'provider_id', 'external_attendee_id']
    readonly_fields = ['external_attendee_id', 'last_synced_at', 'created_at', 'updated_at']
    raw_id_fields = ['contact_record']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'provider_id', 'picture_url', 'is_self')
        }),
        ('Relationships', {
            'fields': ('channel', 'contact_record')
        }),
        ('External Data', {
            'fields': ('external_attendee_id', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Sync Status', {
            'fields': ('sync_status', 'last_synced_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel', 'contact_record')


@admin.register(TenantUniPileConfig)
class TenantUniPileConfigAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_active', 'enable_real_time_sync', 'last_webhook_received', 'webhook_failures']
    list_filter = ['is_active', 'enable_real_time_sync', 'auto_create_contacts']
    readonly_fields = ['last_webhook_received', 'webhook_failures', 'created_at', 'updated_at']


@admin.register(UserChannelConnection)
class UserChannelConnectionAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'user', 'channel_type', 'auth_status', 'is_active', 'last_sync_at']
    list_filter = ['channel_type', 'auth_status', 'is_active']
    search_fields = ['account_name', 'user__username', 'unipile_account_id']
    readonly_fields = ['unipile_account_id', 'created_at', 'updated_at']


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'auth_status', 'is_active', 'created_by', 'created_at']
    list_filter = ['channel_type', 'auth_status', 'is_active']
    search_fields = ['name', 'unipile_account_id']
    readonly_fields = ['unipile_account_id', 'created_at', 'updated_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['subject', 'channel', 'status', 'message_count', 'participant_count', 'last_message_at']
    list_filter = ['status', 'channel__channel_type', 'priority', 'is_hot']
    search_fields = ['subject', 'external_thread_id']
    readonly_fields = ['external_thread_id', 'message_count', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['content_preview', 'conversation', 'direction', 'status', 'sender_participant', 'created_at']
    list_filter = ['direction', 'status', 'channel__channel_type']
    search_fields = ['content', 'subject', 'contact_email', 'contact_phone']
    readonly_fields = ['external_message_id', 'created_at', 'updated_at']
    raw_id_fields = ['sender_participant', 'contact_record', 'conversation']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if obj.content and len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel', 'conversation', 'sender_participant')


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['get_display_name', 'email', 'phone', 'contact_record', 'resolution_confidence', 'total_conversations', 'last_seen']
    list_filter = ['resolution_confidence', 'last_seen']
    search_fields = ['name', 'email', 'phone', 'linkedin_member_urn']
    readonly_fields = ['first_seen', 'last_seen', 'resolved_at', 'total_conversations', 'total_messages']
    raw_id_fields = ['contact_record']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('contact_record')


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'participant', 'role', 'is_active', 'message_count', 'last_message_at']
    list_filter = ['role', 'is_active']
    search_fields = ['conversation__subject', 'participant__name', 'participant__email']
    readonly_fields = ['joined_at', 'created_at', 'updated_at']
    raw_id_fields = ['conversation', 'participant']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('conversation', 'participant')


@admin.register(CommunicationAnalytics)
class CommunicationAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'channel', 'messages_sent', 'messages_received', 'response_rate', 'engagement_score']
    list_filter = ['date', 'channel__channel_type']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel')
