"""
Webhook handlers package - Provider-specific webhook event handlers
"""
from .base import BaseWebhookHandler
from .whatsapp import WhatsAppWebhookHandler
from .email import EmailWebhookHandler
from .linkedin import LinkedInWebhookHandler
from .tracking import TrackingWebhookHandler

# Backward compatibility alias - lazy import to avoid circular import
webhook_handler = None

def get_webhook_handler():
    global webhook_handler
    if webhook_handler is None:
        from ..dispatcher import webhook_dispatcher
        webhook_handler = webhook_dispatcher
    return webhook_handler

__all__ = [
    'BaseWebhookHandler',
    'WhatsAppWebhookHandler', 
    'EmailWebhookHandler',
    'LinkedInWebhookHandler',
    'TrackingWebhookHandler',
    'webhook_handler'
]