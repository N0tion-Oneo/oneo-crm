"""
Storage Layer for Record Communications

Handles all data persistence operations.
No business logic or API calls should happen here.
"""

from .conversation_store import ConversationStore
from .message_store import MessageStore
from .link_manager import LinkManager
from .metrics_updater import MetricsUpdater

__all__ = [
    'ConversationStore',
    'MessageStore',
    'LinkManager',
    'MetricsUpdater'
]