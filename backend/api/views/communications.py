"""
Communication API views - imported from communications app
"""
from communications.views import (
    ChannelViewSet,
    ConversationViewSet,
    MessageViewSet,
    CommunicationAnalyticsViewSet
)

# Re-export for API registration
__all__ = [
    'ChannelViewSet',
    'ConversationViewSet',
    'MessageViewSet', 
    'CommunicationAnalyticsViewSet'
]