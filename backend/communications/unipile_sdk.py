"""
UniPile SDK - Backward Compatibility Layer
This file maintains backward compatibility while redirecting to the new modular structure.

DEPRECATED: This file is deprecated. Please import from communications.unipile directly.
New imports:
    from communications.unipile import UnipileClient, unipile_service
    from communications.unipile.core.exceptions import UnipileConnectionError
"""

import warnings

# Issue deprecation warning for direct imports from this file
warnings.warn(
    "Importing from unipile_sdk.py is deprecated. Use 'from communications.unipile import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import all classes and functions from the new modular structure
from .unipile.core.client import UnipileClient
from .unipile.core.exceptions import (
    UnipileConnectionError,
    UnipileAuthenticationError,
    UnipileRateLimitError
)

# Import all client classes
from .unipile.clients.account import UnipileAccountClient
from .unipile.clients.messaging import UnipileMessagingClient
from .unipile.clients.users import UnipileUsersClient
from .unipile.clients.webhooks import UnipileWebhookClient
from .unipile.clients.linkedin import UnipileLinkedInClient
from .unipile.clients.email import UnipileEmailClient
from .unipile.clients.calendar import UnipileCalendarClient

# Import utility classes
from .unipile.utils.request import UnipileRequestClient

# Import service class and global instance
from .unipile.services.service import UnipileService

# Maintain the global service instance for backward compatibility
unipile_service = UnipileService()

# Export all symbols for backward compatibility
__all__ = [
    # Core classes
    'UnipileClient',
    'UnipileConnectionError',
    'UnipileAuthenticationError',
    'UnipileRateLimitError',
    
    # Client classes
    'UnipileAccountClient',
    'UnipileMessagingClient',
    'UnipileUsersClient',
    'UnipileWebhookClient',
    'UnipileLinkedInClient',
    'UnipileEmailClient',
    'UnipileCalendarClient',
    
    # Utility classes
    'UnipileRequestClient',
    
    # Service
    'UnipileService',
    'unipile_service',
]