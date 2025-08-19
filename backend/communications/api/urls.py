"""
URL patterns for communications API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountConnectionViewSet
from ..views import MessageViewSet, ChannelViewSet, ConversationViewSet, ContactResolutionMonitoringView
from .account_views import (
    CommunicationConnectionViewSet, 
    request_hosted_auth, 
    hosted_auth_success_callback,
    hosted_auth_failure_callback,
    solve_checkpoint,
    resend_checkpoint,
    reconnect_account
)
from .provider_views import (
    get_provider_configurations,
    update_provider_preferences,
    update_tenant_config,
    get_provider_rate_limits,
    get_provider_features
)
from .inbox_views import (
    get_unified_inbox,
    mark_conversation_as_read,
    send_message
)
from .conversation_messages import (
    get_conversation_messages
)
from .attachment_views import (
    AttachmentUploadView,
    send_message_with_attachments,
    delete_attachment
)
from .draft_views import (
    MessageDraftViewSet,
    auto_save_draft,
    save_manual_draft,
    get_draft_for_context,
    delete_draft,
    cleanup_stale_drafts,
    DraftSettingsView
)
from .message_sync_views import (
    sync_account_messages,
    get_sync_status,
    sync_all_messages,
    webhook_message_received,
    get_message_history
)
from .local_inbox_views import (
    get_local_unified_inbox,
    get_local_conversation_messages,
    get_inbox_stats,
    mark_local_conversation_as_read
)
from .unified_inbox_views import (
    get_unified_inbox,
    get_record_timeline,
    get_record_stats,
    mark_record_conversation_read,
    get_user_channels,
    send_message_to_record
)
from .threading_views import (
    create_record_conversation_thread,
    analyze_record_threading_opportunities,
    get_record_conversation_threads,
    bulk_create_conversation_threads
)
from .channel_availability_views import (
    get_record_channel_availability,
    get_record_channel_recommendations,
    bulk_analyze_channel_availability,
    get_user_channel_summary,
    invalidate_channel_cache
)
from ..views import CommunicationAnalyticsViewSet

router = DefaultRouter()
router.register(r'accounts', AccountConnectionViewSet, basename='account-connection')
router.register(r'connections', CommunicationConnectionViewSet, basename='communication-connection')
router.register(r'drafts', MessageDraftViewSet, basename='message-draft')
router.register(r'channels', ChannelViewSet, basename='channel')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'analytics', CommunicationAnalyticsViewSet, basename='communication-analytics')
router.register(r'contact-resolution', ContactResolutionMonitoringView, basename='contact-resolution')

# Register messages ViewSet AFTER function-based views to avoid conflicts
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    # Draft endpoints (MUST come before router to avoid conflicts with /drafts/{id}/ pattern)
    path('drafts/auto-save/', auto_save_draft, name='auto-save-draft'),
    path('drafts/manual-save/', save_manual_draft, name='save-manual-draft'),
    path('drafts/context/', get_draft_for_context, name='get-draft-for-context'),
    path('drafts/<uuid:draft_id>/delete/', delete_draft, name='delete-draft'),
    path('drafts/cleanup/', cleanup_stale_drafts, name='cleanup-stale-drafts'),
    path('draft-settings/', DraftSettingsView.as_view(), name='draft-settings'),
    
    # Router URLs (includes /drafts/ ViewSet, but specific paths above take precedence)
    path('', include(router.urls)),
    
    # Account management endpoints for frontend (non-conflicting paths)
    path('request-hosted-auth/', request_hosted_auth, name='request-hosted-auth'),
    
    # Hosted authentication callbacks
    path('auth/callback/success/', hosted_auth_success_callback, name='hosted-auth-success'),
    path('auth/callback/failure/', hosted_auth_failure_callback, name='hosted-auth-failure'),
    
    # Checkpoint management
    path('connections/<uuid:connection_id>/checkpoint/solve/', solve_checkpoint, name='solve-checkpoint'),
    path('connections/<uuid:connection_id>/checkpoint/resend/', resend_checkpoint, name='resend-checkpoint'),
    path('connections/<uuid:connection_id>/reconnect/', reconnect_account, name='reconnect-account'),
    
    # Provider configuration management
    path('providers/configurations/', get_provider_configurations, name='provider-configurations'),
    path('providers/preferences/', update_provider_preferences, name='update-provider-preferences'),
    path('providers/<str:provider_type>/rate-limits/', get_provider_rate_limits, name='provider-rate-limits'),
    path('providers/<str:provider_type>/features/', get_provider_features, name='provider-features'),
    path('tenant-config/', update_tenant_config, name='update-tenant-config'),
    
    # Message sending endpoints (MUST come before router to avoid conflicts with ViewSet actions)
    path('inbox/send-message/', send_message, name='send-message'),
    path('inbox/send-message-with-attachments/', send_message_with_attachments, name='send-message-with-attachments'),
    
    # Unified Inbox endpoints
    path('inbox/', get_unified_inbox, name='unified-inbox'),
    path('conversations/<str:conversation_id>/messages/', get_conversation_messages, name='conversation-messages'),
    path('conversations/<str:conversation_id>/mark-read/', mark_conversation_as_read, name='mark-conversation-read'),
    
    # Attachment endpoints
    path('attachments/upload/', AttachmentUploadView.as_view(), name='attachment-upload'),
    path('attachments/<str:attachment_id>/', delete_attachment, name='delete-attachment'),
    
    # Message sync endpoints
    path('sync/messages/', sync_account_messages, name='sync-all-messages'),
    path('sync/messages/<uuid:connection_id>/', sync_account_messages, name='sync-connection-messages'),
    path('sync/status/', get_sync_status, name='sync-status-all'),
    path('sync/status/<uuid:connection_id>/', get_sync_status, name='sync-status-connection'),
    path('sync/admin/all/', sync_all_messages, name='sync-admin-all'),
    path('messages/history/<uuid:connection_id>/', get_message_history, name='message-history'),
    
    # Webhook endpoints (will be called from global webhook router)
    path('webhooks/messages/', webhook_message_received, name='webhook-messages'),
    
    # Local inbox endpoints (using synced database messages)
    path('local-inbox/', get_local_unified_inbox, name='local-unified-inbox'),
    path('local-inbox/conversations/<str:conversation_id>/messages/', get_local_conversation_messages, name='local-conversation-messages'),
    path('local-inbox/conversations/<str:conversation_id>/mark-read/', mark_local_conversation_as_read, name='local-mark-conversation-read'),
    path('local-inbox/stats/', get_inbox_stats, name='inbox-stats'),
    
    # Unified Record-centric inbox endpoints
    path('unified-inbox/', get_unified_inbox, name='unified-inbox'),
    path('records/<int:record_id>/timeline/', get_record_timeline, name='record-timeline'),
    path('records/<int:record_id>/stats/', get_record_stats, name='record-stats'),
    path('records/<int:record_id>/mark-read/', mark_record_conversation_read, name='mark-record-read'),
    path('records/<int:record_id>/send-message/', send_message_to_record, name='send-message-to-record'),
    path('user-channels/', get_user_channels, name='user-channels'),
    
    # Conversation threading endpoints
    path('records/<int:record_id>/threading/create/', create_record_conversation_thread, name='create-record-thread'),
    path('records/<int:record_id>/threading/analyze/', analyze_record_threading_opportunities, name='analyze-record-threading'),
    path('records/<int:record_id>/threading/', get_record_conversation_threads, name='get-record-threads'),
    path('threading/bulk-create/', bulk_create_conversation_threads, name='bulk-create-threads'),
    
    # Channel availability endpoints
    path('records/<int:record_id>/channels/', get_record_channel_availability, name='record-channel-availability'),
    path('records/<int:record_id>/channels/recommendations/', get_record_channel_recommendations, name='record-channel-recommendations'),
    path('channels/bulk-analyze/', bulk_analyze_channel_availability, name='bulk-analyze-channels'),
    path('channels/user-summary/', get_user_channel_summary, name='user-channel-summary'),
    path('channels/invalidate-cache/', invalidate_channel_cache, name='invalidate-channel-cache'),
    
    # Communication analytics endpoints (handled by ViewSet router above)
    # Analytics endpoints are automatically available at:
    # /api/v1/communications/analytics/portfolio_overview/
    # /api/v1/communications/analytics/{record_id}/record_analytics/
    # /api/v1/communications/analytics/{record_id}/engagement_timeline/
    # /api/v1/communications/analytics/{record_id}/health_metrics/
    # /api/v1/communications/analytics/insights_dashboard/
]