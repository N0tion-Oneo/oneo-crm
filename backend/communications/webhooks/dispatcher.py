"""
Unified webhook event dispatcher with clean separation of concerns
Routes webhook events to appropriate provider-specific handlers
"""
import logging
from typing import Dict, Any, Optional
from communications.webhooks.routing import account_router
from communications.webhooks.handlers.whatsapp import WhatsAppWebhookHandler
from communications.webhooks.handlers.email import EmailWebhookHandler
from communications.webhooks.handlers.linkedin import LinkedInWebhookHandler
from communications.webhooks.handlers.tracking import TrackingWebhookHandler

logger = logging.getLogger(__name__)


class UnifiedWebhookDispatcher:
    """
    Unified webhook dispatcher with clean separation of concerns
    Routes events to provider-specific handlers based on account type
    """
    
    def __init__(self):
        # Initialize specialized handlers
        self.whatsapp_handler = WhatsAppWebhookHandler()
        self.email_handler = EmailWebhookHandler()
        self.linkedin_handler = LinkedInWebhookHandler()
        self.tracking_handler = TrackingWebhookHandler()
        
        # Event type to tracking mapping
        self.tracking_events = {
            'delivery_status', 'read_receipt', 'tracking_pixel', 'email_opened',
            'link_clicked', 'attachment_downloaded', 'bounce', 'spam_report', 'unsubscribe'
        }
    
    def process_webhook(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook event by routing to appropriate handler
        
        Args:
            event_type: Type of webhook event
            data: Event data from UniPile
            
        Returns:
            Processing result
        """
        logger.info(f"Processing webhook event: {event_type}")
        
        # Handle tracking events first (they may not have account context)
        if event_type in self.tracking_events:
            logger.info(f"Routing {event_type} to tracking handler")
            return self._process_tracking_event(event_type, data)
        
        # Extract account ID for provider routing
        account_id = self._extract_account_id(data)
        if not account_id:
            logger.error(f"No account ID found in webhook data: {data}")
            return {'success': False, 'error': 'No account ID in webhook data'}
        
        # Determine provider type from account
        provider_type = self._get_provider_type(account_id)
        if not provider_type:
            logger.error(f"Cannot determine provider type for account {account_id}")
            return {'success': False, 'error': 'Cannot determine provider type'}
        
        # Route to appropriate provider handler
        handler = self._get_provider_handler(provider_type)
        if not handler:
            logger.error(f"No handler available for provider type: {provider_type}")
            return {'success': False, 'error': f'No handler for provider: {provider_type}'}
        
        # Validate webhook data
        if not handler.validate_webhook_data(data):
            logger.error(f"Invalid webhook data for {provider_type}: {data}")
            return {'success': False, 'error': 'Invalid webhook data structure'}
        
        # Process with tenant context
        result = account_router.process_with_tenant_context(
            account_id,
            self._process_with_handler,
            handler,
            event_type,
            data
        )
        
        if result is None:
            return {'success': False, 'error': 'Failed to route to tenant'}
        
        return result
    
    def _extract_account_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract account ID from webhook data using all handlers"""
        # Try each handler's extraction method
        handlers = [
            self.whatsapp_handler,
            self.email_handler, 
            self.linkedin_handler,
            self.tracking_handler
        ]
        
        for handler in handlers:
            try:
                account_id = handler.extract_account_id(data)
                if account_id:
                    return account_id
            except Exception as e:
                logger.debug(f"Handler {handler.provider_name} failed to extract account ID: {e}")
                continue
        
        return None
    
    def _get_provider_type(self, account_id: str) -> Optional[str]:
        """Determine provider type from account ID by checking connection"""
        try:
            # This requires tenant context, so we'll check each tenant
            from django_tenants.utils import get_tenant_model, get_public_schema_name
            from django.db import connection
            from communications.models import UserChannelConnection
            
            tenant_model = get_tenant_model()
            tenants = tenant_model.objects.exclude(schema_name=get_public_schema_name())
            
            for tenant in tenants:
                try:
                    connection.set_tenant(tenant)
                    
                    user_connection = UserChannelConnection.objects.filter(
                        unipile_account_id=account_id,
                        is_active=True
                    ).first()
                    
                    if user_connection:
                        return user_connection.channel_type
                        
                except Exception as e:
                    logger.debug(f"Error checking tenant {tenant.schema_name}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to determine provider type for account {account_id}: {e}")
            return None
        
        finally:
            # Switch back to public schema
            try:
                public_tenant = tenant_model.objects.get(schema_name=get_public_schema_name())
                connection.set_tenant(public_tenant)
            except Exception as e:
                logger.error(f"Failed to switch back to public schema: {e}")
    
    def _get_provider_handler(self, provider_type: str):
        """Get appropriate handler for provider type"""
        handler_map = {
            'whatsapp': self.whatsapp_handler,
            'gmail': self.email_handler,
            'outlook': self.email_handler,
            'mail': self.email_handler,
            'email': self.email_handler,
            'linkedin': self.linkedin_handler
        }
        
        return handler_map.get(provider_type)
    
    def _process_with_handler(self, account_id: str, handler, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process event with specific handler in tenant context"""
        try:
            result = handler.process_event(event_type, account_id, data)
            logger.info(f"Successfully processed {event_type} with {handler.provider_name} handler - Result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error processing {event_type} with {handler.provider_name} handler: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': handler.provider_name,
                'event_type': event_type
            }
    
    def _process_tracking_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process tracking events that may not have tenant context"""
        try:
            # Tracking events might need special handling for tenant context
            account_id = self.tracking_handler.extract_account_id(data)
            
            if account_id:
                # Use tenant context if we can determine it
                result = account_router.process_with_tenant_context(
                    account_id,
                    self._process_with_handler,
                    self.tracking_handler,
                    event_type,
                    data
                )
                
                if result is not None:
                    return result
            
            # Fall back to processing without tenant context for tracking
            # Some tracking events (like unsubscribes) might not need tenant context
            result = self.tracking_handler.process_event(event_type, account_id or 'unknown', data)
            logger.info(f"Processed tracking event {event_type} without tenant context")
            return result
            
        except Exception as e:
            logger.error(f"Error processing tracking event {event_type}: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'tracking',
                'event_type': event_type
            }
    
    def get_supported_events(self) -> Dict[str, list[str]]:
        """Get all supported events by provider"""
        return {
            'whatsapp': self.whatsapp_handler.get_supported_events(),
            'email': self.email_handler.get_supported_events(),
            'linkedin': self.linkedin_handler.get_supported_events(),
            'tracking': self.tracking_handler.get_supported_events()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for webhook dispatcher"""
        return {
            'status': 'healthy',
            'service': 'unified_webhook_dispatcher',
            'handlers': {
                'whatsapp': 'active',
                'email': 'active', 
                'linkedin': 'active',
                'tracking': 'active'
            },
            'supported_events': self.get_supported_events()
        }


# Global dispatcher instance
webhook_dispatcher = UnifiedWebhookDispatcher()

# Import the webhook handler from the handlers module (backward compatibility)
try:
    from .handlers import webhook_handler
except ImportError:
    try:
        from . import handlers
        webhook_handler = handlers.webhook_handler
    except (ImportError, AttributeError):
        webhook_handler = None