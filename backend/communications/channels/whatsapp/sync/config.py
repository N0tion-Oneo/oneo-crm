"""
Sync Configuration and Constants
"""
import os

# Log verbosity levels
LOG_LEVEL_QUIET = 'QUIET'      # Only errors
LOG_LEVEL_NORMAL = 'NORMAL'    # Errors and major milestones
LOG_LEVEL_VERBOSE = 'VERBOSE'  # All progress updates

# Sync configuration defaults - now includes performance settings
SYNC_CONFIG = {
    # API batch settings
    'conversations_per_batch': 50,      # Conversations per API request
    'messages_per_batch': 100,          # Messages per API request (deprecated - use messages_batch_size)
    'messages_batch_size': int(os.environ.get('SYNC_MESSAGES_BATCH_SIZE', 200)),  # Messages per API call when paginating (API max: 200)
    'enable_message_pagination': os.environ.get('SYNC_ENABLE_MESSAGE_PAGINATION', 'true').lower() == 'true',  # Enable message pagination
    'concurrent_chat_tasks': 3,         # Parallel chat processing tasks
    'max_retries': 2,                   # Maximum retry attempts
    'retry_delay_base': 60,             # Base retry delay in seconds
    
    # Progress and logging configuration
    'progress_update_interval': 10,     # Update progress every N items
    'log_level': os.environ.get('SYNC_LOG_LEVEL', LOG_LEVEL_NORMAL),
    'progress_update_frequency': int(os.environ.get('SYNC_PROGRESS_FREQUENCY', 10)),  # Update every N%
    'progress_db_interval': int(os.environ.get('SYNC_PROGRESS_DB_INTERVAL', 5)),    # Save to DB every N seconds
    
    # WebSocket broadcasting
    'websocket_enabled': os.environ.get('SYNC_WEBSOCKET_ENABLED', 'true').lower() == 'true',
    'broadcast_milestones_only': os.environ.get('SYNC_BROADCAST_MILESTONES', 'true').lower() == 'true',
    'websocket_update_interval': int(os.environ.get('SYNC_WEBSOCKET_INTERVAL', 10)),  # Seconds
}

# Default sync options - production ready values
# These are the ONLY defaults that should be used across the system
DEFAULT_SYNC_OPTIONS = {
    'max_conversations': int(os.environ.get('SYNC_MAX_CONVERSATIONS', 5)),
    'max_messages_per_chat': int(os.environ.get('SYNC_MAX_MESSAGES', 300)),  # API limit: 250 max
    'days_back': int(os.environ.get('SYNC_DAYS_BACK', 0)),  # 0 = no date filter (sync all), >0 = filter messages by age in days
}

# Get sync options without overrides
def get_sync_options(overrides: dict = None) -> dict:
    """
    Get sync options from centralized configuration.
    Frontend overrides are IGNORED to ensure config is strictly respected.
    
    Args:
        overrides: Ignored - kept for backward compatibility
        
    Returns:
        Sync options dictionary from DEFAULT_SYNC_OPTIONS only
    """
    # Log what we're receiving vs returning for debugging
    import logging
    logger = logging.getLogger(__name__)
    
    if overrides:
        logger.info(f"📊 get_sync_options called with overrides: {overrides}")
        logger.info(f"✅ Returning config defaults instead: {DEFAULT_SYNC_OPTIONS}")
    
    # Ignore any overrides - return only the configured defaults
    return DEFAULT_SYNC_OPTIONS.copy()

# Sync job status codes
SYNC_STATUS = {
    'PENDING': 'pending',
    'IN_PROGRESS': 'in_progress',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled',
}

# Sync job types
SYNC_TYPE = {
    'COMPREHENSIVE': 'comprehensive',
    'CONVERSATIONS': 'conversations',
    'MESSAGES': 'messages',
    'CHAT_SPECIFIC': 'chat_specific',
    'INCREMENTAL': 'incremental',
}

def get_log_level() -> str:
    """Get configured log level"""
    return SYNC_CONFIG.get('log_level', LOG_LEVEL_NORMAL)

def should_log_progress(percentage: float, last_percentage: float) -> bool:
    """Determine if progress should be logged based on configuration"""
    level = SYNC_CONFIG['log_level']
    
    if level == LOG_LEVEL_QUIET:
        # Only log completion
        return percentage == 100
    elif level == LOG_LEVEL_NORMAL:
        # Log major milestones (25%, 50%, 75%, 100%)
        milestones = [25, 50, 75, 100]
        for milestone in milestones:
            if last_percentage < milestone <= percentage:
                return True
        return False
    else:  # VERBOSE
        # Log based on frequency setting
        frequency = SYNC_CONFIG['progress_update_frequency']
        return abs(percentage - last_percentage) >= frequency

def should_broadcast_progress(percentage: float, last_percentage: float) -> bool:
    """Determine if progress should be broadcast via WebSocket"""
    if not SYNC_CONFIG['websocket_enabled']:
        return False
    
    if SYNC_CONFIG['broadcast_milestones_only']:
        # Only broadcast major milestones
        milestones = [0, 25, 50, 75, 100]
        for milestone in milestones:
            if last_percentage < milestone <= percentage:
                return True
        return False
    else:
        # Broadcast based on frequency
        frequency = SYNC_CONFIG['progress_update_frequency']
        return abs(percentage - last_percentage) >= frequency