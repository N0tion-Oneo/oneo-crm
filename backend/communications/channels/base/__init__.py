"""
Base classes for all communication channels
Provides abstract interfaces that all channels must implement
"""

from .client import BaseChannelClient
from .service import BaseChannelService
from .webhooks import BaseWebhookHandler
from .views import BaseChannelViews

__all__ = [
    'BaseChannelClient',
    'BaseChannelService',
    'BaseWebhookHandler',
    'BaseChannelViews'
]