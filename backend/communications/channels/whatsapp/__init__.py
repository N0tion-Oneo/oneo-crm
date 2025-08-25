"""
WhatsApp channel implementation using UniPile SDK
Provides comprehensive WhatsApp interface for the CRM
"""

from .client import WhatsAppClient
from .service import WhatsAppService

# Initialize global instances
whatsapp_client = WhatsAppClient()
whatsapp_service = WhatsAppService()

__all__ = [
    'WhatsAppClient',
    'WhatsAppService',
    'whatsapp_client',
    'whatsapp_service'
]