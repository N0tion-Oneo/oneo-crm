"""
UniPile SDK Package - Modular Unipile Integration
Provides clean, organized access to all UniPile functionality
"""

# Core exports
from .core.client import UnipileClient
from .core.exceptions import (
    UnipileConnectionError,
    UnipileAuthenticationError, 
    UnipileRateLimitError
)

# Client exports
from .clients.account import UnipileAccountClient
from .clients.messaging import UnipileMessagingClient
from .clients.users import UnipileUsersClient
from .clients.webhooks import UnipileWebhookClient
from .clients.linkedin import UnipileLinkedInClient
from .clients.email import UnipileEmailClient
from .clients.calendar import UnipileCalendarClient

# Service exports
from .services.service import UnipileService

# Utility exports
from .utils.request import UnipileRequestClient

# Global service instance for backward compatibility
unipile_service = UnipileService()

__all__ = [
    # Core
    'UnipileClient',
    'UnipileConnectionError',
    'UnipileAuthenticationError', 
    'UnipileRateLimitError',
    
    # Clients
    'UnipileAccountClient',
    'UnipileMessagingClient',
    'UnipileUsersClient',
    'UnipileWebhookClient',
    'UnipileLinkedInClient',
    'UnipileEmailClient',
    'UnipileCalendarClient',
    
    # Service
    'UnipileService',
    'unipile_service',
    
    # Utils
    'UnipileRequestClient',
]