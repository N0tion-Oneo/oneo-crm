"""
URL patterns for communications API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountConnectionViewSet
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
    get_conversation_messages,
    mark_conversation_as_read,
    send_message
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
    get_inbox_stats
)

router = DefaultRouter()
router.register(r'accounts', AccountConnectionViewSet, basename='account-connection')
router.register(r'connections', CommunicationConnectionViewSet, basename='communication-connection')
router.register(r'drafts', MessageDraftViewSet, basename='message-draft')

urlpatterns = [
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
    
    # Unified Inbox endpoints
    path('inbox/', get_unified_inbox, name='unified-inbox'),
    path('conversations/<str:conversation_id>/messages/', get_conversation_messages, name='conversation-messages'),
    path('conversations/<str:conversation_id>/mark-read/', mark_conversation_as_read, name='mark-conversation-read'),
    path('messages/send/', send_message, name='send-message'),
    
    # Attachment endpoints
    path('attachments/upload/', AttachmentUploadView.as_view(), name='attachment-upload'),
    path('messages/send-with-attachments/', send_message_with_attachments, name='send-message-with-attachments'),
    path('attachments/<str:attachment_id>/', delete_attachment, name='delete-attachment'),
    
    # Draft endpoints
    path('drafts/auto-save/', auto_save_draft, name='auto-save-draft'),
    path('drafts/manual-save/', save_manual_draft, name='save-manual-draft'),
    path('drafts/context/', get_draft_for_context, name='get-draft-for-context'),
    path('drafts/<uuid:draft_id>/delete/', delete_draft, name='delete-draft'),
    path('drafts/cleanup/', cleanup_stale_drafts, name='cleanup-stale-drafts'),
    path('draft-settings/', DraftSettingsView.as_view(), name='draft-settings'),
    
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
    path('local-inbox/stats/', get_inbox_stats, name='inbox-stats'),
]