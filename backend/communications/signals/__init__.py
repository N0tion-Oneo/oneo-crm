"""
Communications signals package
Centralized signal handler registration for the communications app

This module imports all signal handlers to ensure they are registered with Django.
Signals are organized by functionality:
- contact_resolution: Triggers contact resolution when records are updated
- tracking: Automatic communication tracking and analytics
- realtime: WebSocket broadcasting and cache management
"""

# Import all signal modules to register the signal handlers
from . import contact_resolution
from . import tracking  
from . import realtime

# Expose key functions for external use
from .contact_resolution import (
    trigger_manual_contact_resolution,
    get_contact_fields_from_record,
    is_contact_related_update,
    get_supported_contact_field_names
)

from .tracking import (
    handle_unipile_delivery_webhook,
    handle_tracking_pixel_request,
    track_potential_response
)

from .realtime import (
    broadcast_custom_event,
    invalidate_conversation_cache_manual
)

__all__ = [
    # Contact resolution utilities
    'trigger_manual_contact_resolution',
    'get_contact_fields_from_record', 
    'is_contact_related_update',
    'get_supported_contact_field_names',
    
    # Tracking utilities
    'handle_unipile_delivery_webhook',
    'handle_tracking_pixel_request', 
    'track_potential_response',
    
    # Real-time utilities
    'broadcast_custom_event',
    'invalidate_conversation_cache_manual'
]