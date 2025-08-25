"""
Background sync tasks for communications app
This module imports and re-exports the actual background sync tasks from channel implementations
"""

# Import the WhatsApp background sync tasks from the refactored version
from .channels.whatsapp.sync.tasks import (
    sync_account_comprehensive_background,
    sync_chat_specific_background
)

# Re-export them so Celery can find them
__all__ = [
    'sync_account_comprehensive_background',
    'sync_chat_specific_background'
]