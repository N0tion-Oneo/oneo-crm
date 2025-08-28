"""
Email Sync Configuration
"""
from typing import Dict, Any

# Default sync configuration for email
DEFAULT_SYNC_OPTIONS = {
    'max_threads': 100,  # Number of email threads to sync
    'max_messages_per_thread': 50,  # Messages per thread
    'max_total_messages': 250,  # Total messages per sync batch
    'days_back': 30,  # Days to look back for messages (0 = no filter)
    'folders_to_sync': ['inbox', 'sent', 'drafts'],  # Default folders
    'meta_only': False,  # Whether to fetch only metadata (faster)
    'include_headers': False,  # Whether to include email headers
    'sync_attachments': True,  # Whether to download attachment metadata
}

# Email-specific sync configuration
EMAIL_SYNC_CONFIG = {
    'batch_size': 50,  # API batch size for fetching emails
    'max_api_limit': 250,  # UniPile max limit per request
    'sync_interval_minutes': 15,  # Background sync interval
    'folder_roles': [
        'inbox', 'sent', 'archive', 'drafts', 
        'trash', 'spam', 'all', 'important', 'starred'
    ],
    'supported_providers': ['GOOGLE', 'GOOGLE_OAUTH', 'OUTLOOK', 'EXCHANGE', 'MAIL', 'ICLOUD'],
    'thread_grouping_enabled': True,  # Group emails by thread_id
    'auto_mark_read_historical': True,  # Mark historical emails as read
}

def get_sync_options(custom_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get sync options with custom overrides
    
    Args:
        custom_options: Custom options to override defaults
        
    Returns:
        Merged sync options dictionary
    """
    options = DEFAULT_SYNC_OPTIONS.copy()
    
    if custom_options:
        # Only override specific keys that are provided
        for key in custom_options:
            if key in options:
                options[key] = custom_options[key]
    
    return options