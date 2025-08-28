"""
URL patterns for communications API
"""
from django.urls import path, include
from django.http import JsonResponse
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
from .participant_inbox_views import (
    get_participant_inbox,
    link_conversation_to_contact
)
from .conversation_messages import (
    get_conversation_messages
)
from .attachment_views import (
    AttachmentUploadView,
    send_message_with_attachments,
    delete_attachment,
    download_attachment
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
# Unified inbox views removed - legacy code
# Threading views removed - legacy code
# Channel availability views removed - legacy code
from ..views import CommunicationAnalyticsViewSet
# Import WhatsApp inbox views from channels directory  
from communications.channels.whatsapp.inbox_views import (
    get_whatsapp_inbox,
    link_whatsapp_conversation
)

# Import NEW live WhatsApp views (selective storage approach)
from communications.channels.whatsapp.live_inbox_views import (
    get_whatsapp_live_inbox,
    store_whatsapp_conversation
)
from communications.channels.whatsapp.live_message_views import (
    get_whatsapp_chat_messages_live
)

# Import consolidated local-first WhatsApp views from channels directory
from communications.channels.whatsapp.api_views import (
    get_whatsapp_chats_local_first,
    get_chat_messages_local_first,
    send_message_local_first,
    get_whatsapp_accounts,
    update_chat,
    test_mark_read_formats,
    get_whatsapp_attendees,
    sync_whatsapp_data,
    get_attendee_picture,
    get_message_attachment,
    sync_chat_history,
    get_chat_sync_status
)

# Import WhatsApp background sync views from channels directory
from communications.channels.whatsapp.background_sync_views import (
    start_background_sync,
    start_chat_specific_sync,
    get_sync_jobs,
    get_sync_job_status,
    cancel_sync_job,
    get_active_sync_jobs
)

# Import Email inbox views from channels directory
from communications.channels.email.inbox_views_cursor import (
    get_email_inbox_cursor
)
from communications.channels.email.inbox_views import (
    get_email_inbox,
    link_email_conversation
)
from communications.channels.email.read_status_views import (
    mark_email_as_read,
    mark_email_as_unread,
    mark_thread_as_read,
    mark_thread_as_unread
)

# Import Email views from channels directory
from communications.channels.email.api_views import (
    get_email_accounts,
    get_email_threads,
    get_thread_messages,
    send_email,
    update_email,
    get_email_folders,
    sync_email_data,
    get_active_email_sync_jobs,
    get_email_live_threads,  # New: Live data from UniPile
    get_merged_email_threads,  # New: Merged stored + live data
    link_thread_to_contact,  # New: Link thread to existing contact
    create_contact_from_thread,  # New: Create contact from email
    sync_thread_history,  # New: Sync historical messages for linked thread
    delete_email  # New: Delete email endpoint
)


# Import Email background sync views from channels directory
from communications.channels.email.background_sync_views import (
    start_email_background_sync,
    start_thread_sync,
    get_email_sync_jobs,
    cancel_email_sync_job
)

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
    path('inbox/test-endpoint/', lambda request: JsonResponse({'status': 'ok', 'method': request.method}), name='test-endpoint'),
    
    # Unified Inbox endpoints - removed (legacy code)
    path('conversations/<str:conversation_id>/messages/', get_conversation_messages, name='conversation-messages'),
    path('conversations/<str:conversation_id>/mark-read/', mark_conversation_as_read, name='mark-conversation-read'),
    
    # Attachment endpoints
    path('attachments/upload/', AttachmentUploadView.as_view(), name='attachment-upload'),
    path('attachments/<str:attachment_id>/', delete_attachment, name='delete-attachment'),
    path('messages/<str:message_id>/attachments/<str:attachment_id>/download/', download_attachment, name='download-attachment'),
    
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
    
    # Participant-based inbox endpoints (with participant resolution)
    path('inbox/participant/', get_participant_inbox, name='participant-inbox'),
    path('inbox/link-contact/', link_conversation_to_contact, name='link-conversation-contact'),
    
    # Conversation threading endpoints - removed (legacy code)
    
    # Channel availability endpoints - removed (legacy code)
    
    # Communication analytics endpoints (handled by ViewSet router above)
    # Analytics endpoints are automatically available at:
    # /api/v1/communications/analytics/portfolio_overview/
    # /api/v1/communications/analytics/{record_id}/record_analytics/
    # /api/v1/communications/analytics/{record_id}/engagement_timeline/
    # /api/v1/communications/analytics/{record_id}/health_metrics/
    # /api/v1/communications/analytics/insights_dashboard/
    
    # WhatsApp-specific endpoints for Unipile integration
    # Import new WhatsApp views from the channels structure
    path('whatsapp/inbox/', get_whatsapp_inbox, name='whatsapp-inbox'),  # OLD: Stored data inbox
    path('whatsapp/inbox/live/', get_whatsapp_live_inbox, name='whatsapp-live-inbox'),  # NEW: Live data (like email)
    path('whatsapp/chats/<str:chat_id>/messages/live/', get_whatsapp_chat_messages_live, name='whatsapp-messages-live'),  # NEW: Live messages
    path('whatsapp/conversations/<str:chat_id>/link/', link_whatsapp_conversation, name='whatsapp-link-conversation'),  # OLD: Manual linking
    path('whatsapp/conversations/<str:chat_id>/store/', store_whatsapp_conversation, name='whatsapp-store-conversation'),  # NEW: Selective storage
    path('whatsapp/accounts/', get_whatsapp_accounts, name='whatsapp-accounts'),
    path('whatsapp/chats/', get_whatsapp_chats_local_first, name='whatsapp-chats'),
    path('whatsapp/chats/<str:chat_id>/messages/', get_chat_messages_local_first, name='whatsapp-chat-messages'),
    path('whatsapp/chats/<str:chat_id>/send/', send_message_local_first, name='whatsapp-send-message'),
    path('whatsapp/chats/<str:chat_id>/', update_chat, name='whatsapp-update-chat'),
    path('whatsapp/chats/<str:chat_id>/test-mark-read/', test_mark_read_formats, name='whatsapp-test-mark-read'),
    path('whatsapp/attendees/', get_whatsapp_attendees, name='whatsapp-attendees'),
    path('whatsapp/attendees/<str:attendee_id>/picture/', get_attendee_picture, name='whatsapp-attendee-picture'),
    path('whatsapp/messages/<str:message_id>/attachments/<str:attachment_id>/', get_message_attachment, name='whatsapp-message-attachment'),
    path('whatsapp/sync/', sync_whatsapp_data, name='whatsapp-sync'),
    path('whatsapp/chats/<str:chat_id>/sync/', sync_chat_history, name='whatsapp-chat-sync'),
    path('whatsapp/chats/<str:chat_id>/sync/status/', get_chat_sync_status, name='whatsapp-chat-sync-status'),
    
    # WhatsApp background sync endpoints
    path('whatsapp/sync/background/', start_background_sync, name='whatsapp-background-sync'),
    path('whatsapp/sync/background/chat/<str:chat_id>/', start_chat_specific_sync, name='whatsapp-chat-background-sync'),
    path('whatsapp/sync/jobs/', get_sync_jobs, name='whatsapp-sync-jobs'),
    path('whatsapp/sync/jobs/active/', get_active_sync_jobs, name='whatsapp-active-sync-jobs'),
    path('whatsapp/sync/jobs/<uuid:sync_job_id>/', get_sync_job_status, name='whatsapp-sync-job-status'),
    path('whatsapp/sync/jobs/<uuid:sync_job_id>/cancel/', cancel_sync_job, name='whatsapp-cancel-sync-job'),
    
    # Email-specific endpoints for UniPile integration
    path('email/inbox/', get_email_inbox_cursor, name='email-inbox'),  # CURSOR: Fast cursor-based pagination
    path('email/inbox/offset/', get_email_inbox, name='email-inbox-offset'),  # OLD: Offset-based (slow)
    path('email/conversations/<str:thread_id>/link/', link_email_conversation, name='email-link-conversation'),  # NEW: Manual linking
    path('email/accounts/', get_email_accounts, name='email-accounts'),
    
    # Email read status management
    path('email/mark-read/', mark_email_as_read, name='email-mark-read'),
    path('email/mark-unread/', mark_email_as_unread, name='email-mark-unread'),
    path('email/thread/mark-read/', mark_thread_as_read, name='email-thread-mark-read'),
    path('email/thread/mark-unread/', mark_thread_as_unread, name='email-thread-mark-unread'),
    path('email/threads/', get_email_threads, name='email-threads'),
    path('email/threads/live/', get_email_live_threads, name='email-live-threads'),  # New: Live data
    path('email/threads/merged/', get_merged_email_threads, name='email-merged-threads'),  # New: Merged data
    path('email/threads/<str:thread_id>/messages/', get_thread_messages, name='email-thread-messages'),
    path('email/threads/<str:thread_id>/link-contact/', link_thread_to_contact, name='email-link-contact'),
    path('email/threads/<str:thread_id>/create-contact/', create_contact_from_thread, name='email-create-contact'),
    path('email/threads/<str:thread_id>/sync-history/', sync_thread_history, name='email-sync-history'),
    path('email/send/', send_email, name='email-send'),
    path('email/emails/<str:email_id>/', update_email, name='email-update'),
    path('email/emails/<str:email_id>/delete/', delete_email, name='email-delete'),
    path('email/folders/', get_email_folders, name='email-folders'),
    path('email/sync/', sync_email_data, name='email-sync'),
    path('email/sync/jobs/active/', get_active_email_sync_jobs, name='email-active-sync-jobs'),
    
    # Email background sync endpoints
    path('email/sync/background/', start_email_background_sync, name='email-background-sync'),
    path('email/sync/threads/<str:thread_id>/', start_thread_sync, name='email-thread-sync'),
    path('email/sync/jobs/', get_email_sync_jobs, name='email-sync-jobs'),
    path('email/sync/jobs/<uuid:sync_job_id>/cancel/', cancel_email_sync_job, name='email-cancel-sync-job'),
]