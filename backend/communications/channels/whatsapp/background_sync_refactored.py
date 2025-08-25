"""
WhatsApp Background Synchronization (Refactored)
This module provides backward compatibility while using the new modular sync system
"""
import logging
from typing import Dict, Any, Optional
from django.db import connection as db_connection

# Import from new modular structure
from .sync import (
    sync_account_comprehensive_background,
    sync_chat_specific_background,
    ComprehensiveSyncService,
    ConversationSyncService,
    MessageSyncService,
    AttendeeSyncService,
    SyncProgressTracker,
    SyncJobManager,
)
from .sync.config import SYNC_CONFIG, DEFAULT_SYNC_OPTIONS

logger = logging.getLogger(__name__)

# Re-export tasks for backward compatibility
__all__ = [
    'sync_account_comprehensive_background',
    'sync_chat_specific_background',
    'SYNC_CONFIG',
]

# =========================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# These functions maintain the same interface as the old background_sync.py
# =========================================================================

def _run_comprehensive_sync_simplified(
    channel,
    options: Dict[str, Any],
    connection=None,
    sync_job=None
) -> Dict[str, Any]:
    """
    Simplified comprehensive sync - backward compatibility wrapper
    
    This function maintains the same interface as the old implementation
    but uses the new modular sync service.
    """
    logger.info(f"🔄 Starting simplified comprehensive sync for {channel.name}")
    
    # Use the new comprehensive sync service
    sync_service = ComprehensiveSyncService(
        channel=channel,
        connection=connection,
        sync_job=sync_job
    )
    
    # Run the sync with provided options
    stats = sync_service.run_comprehensive_sync(options)
    
    logger.info(f"✅ Comprehensive sync complete: {stats}")
    
    return stats


def _mark_sync_job_failed(sync_job_id: str, error_message: str) -> None:
    """
    Mark a sync job as failed - backward compatibility wrapper
    """
    SyncJobManager.mark_sync_job_failed(sync_job_id, error_message)


def _estimate_conversation_count_sync(channel, options: Dict[str, Any]) -> int:
    """
    Estimate conversation count - backward compatibility wrapper
    """
    sync_service = ComprehensiveSyncService(channel=channel)
    estimation = sync_service.estimate_sync_time(options)
    return estimation.get('conversations_to_sync', 0)


# =========================================================================
# SIMPLIFIED SYNC FUNCTION (Used by API views)
# =========================================================================

def run_sync_with_tenant_context(
    tenant_schema: str,
    channel,
    options: Dict[str, Any],
    connection=None
) -> Dict[str, Any]:
    """
    Run sync within tenant context - used by API views
    
    This function is called directly from api_views.py for immediate sync
    """
    from tenants.models import Tenant
    
    # Switch to tenant context
    tenant = Tenant.objects.get(schema_name=tenant_schema)
    db_connection.set_tenant(tenant)
    
    logger.info(f"Running sync in tenant context: {tenant_schema}")
    
    # Run the sync using the new service
    sync_service = ComprehensiveSyncService(
        channel=channel,
        connection=connection
    )
    
    stats = sync_service.run_comprehensive_sync(options)
    
    return {
        'success': True,
        'stats': stats,
        'tenant': tenant_schema
    }


# =========================================================================
# LEGACY FUNCTION SIGNATURES
# These maintain exact compatibility with existing code
# =========================================================================

def _sync_conversations_paginated_sync(
    channel,
    connection,
    max_conversations: int,
    sync_job=None,
    progress_tracker=None
) -> Dict[str, Any]:
    """Legacy wrapper for conversation sync"""
    conv_service = ConversationSyncService(
        channel=channel,
        connection=connection,
        progress_tracker=progress_tracker
    )
    return conv_service.sync_conversations_paginated(
        max_total=max_conversations,
        batch_size=50
    )


def _sync_messages_paginated_sync(
    channel,
    conversations,
    max_messages_per_chat: int,
    sync_job=None,
    progress_tracker=None
) -> Dict[str, Any]:
    """Legacy wrapper for message sync"""
    msg_service = MessageSyncService(
        channel=channel,
        progress_tracker=progress_tracker
    )
    return msg_service.sync_messages_paginated(
        conversations=conversations,
        max_messages_per_chat=max_messages_per_chat
    )