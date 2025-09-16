"""
Factory for creating trigger handlers
"""
import logging
from typing import Dict, Optional, Type
from .base import BaseTriggerHandler
from ..types import TriggerEvent
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class TriggerHandlerFactory:
    """Factory for creating and managing trigger handlers"""
    
    def __init__(self):
        self._handlers: Dict[str, BaseTriggerHandler] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all trigger handlers"""
        
        # Import and register specific handlers
        try:
            from .record_handlers import RecordCreatedHandler, RecordUpdatedHandler, RecordDeletedHandler
            # from .field_handlers import FieldChangedHandler  # Deprecated - use RecordUpdatedHandler
            from .communication_handlers import EmailReceivedHandler, MessageReceivedHandler
            from .form_handlers import FormSubmissionHandler
            from .webhook_handlers import WebhookHandler, ApiEndpointHandler
            from .conditional_handlers import ConditionalTriggerHandler
            from .workflow_handlers import WorkflowCompletionHandler
            from .engagement_handlers import EngagementThresholdHandler
            # from .status_handlers import StatusChangeHandler, PipelineStageHandler  # Deprecated
            from .date_handlers import DateReachedHandler
            from .scheduled_handlers import ScheduledTriggerHandler
            from .manual_handlers import ManualTriggerHandler

            # Register handlers
            handlers = [
                ManualTriggerHandler(),
                RecordCreatedHandler(),
                RecordUpdatedHandler(),
                RecordDeletedHandler(),
                # FieldChangedHandler(),  # Deprecated - use RecordUpdatedHandler with specific_fields
                EmailReceivedHandler(),
                MessageReceivedHandler(),
                FormSubmissionHandler(),
                WebhookHandler(),
                ApiEndpointHandler(),
                ConditionalTriggerHandler(),
                WorkflowCompletionHandler(),
                EngagementThresholdHandler(),
                # StatusChangeHandler(),  # Deprecated - use RecordUpdatedHandler with update_type
                # PipelineStageHandler(),  # Deprecated
                DateReachedHandler(),
                ScheduledTriggerHandler()
            ]
            
            for handler in handlers:
                self.register_handler(handler)
                
        except ImportError as e:
            logger.warning(f"Could not import all handlers: {e}")
            # Register basic handlers as fallback
            self._register_basic_handlers()
    
    def _register_basic_handlers(self):
        """Register basic fallback handlers"""
        
        from .basic_handlers import (
            BasicRecordHandler, BasicCommunicationHandler, 
            BasicConditionalHandler, BasicTimeHandler
        )
        
        # Create basic handlers for core trigger types
        basic_handlers = [
            BasicRecordHandler(WorkflowTriggerType.RECORD_CREATED),
            BasicRecordHandler(WorkflowTriggerType.RECORD_UPDATED),
            BasicRecordHandler(WorkflowTriggerType.RECORD_DELETED),
            # BasicRecordHandler(WorkflowTriggerType.FIELD_CHANGED),  # Deprecated
            BasicCommunicationHandler(WorkflowTriggerType.EMAIL_RECEIVED),
            BasicCommunicationHandler(WorkflowTriggerType.MESSAGE_RECEIVED),
            BasicConditionalHandler(WorkflowTriggerType.CONDITION_MET),
            BasicTimeHandler(WorkflowTriggerType.SCHEDULED),
            BasicTimeHandler(WorkflowTriggerType.DATE_REACHED)
        ]
        
        for handler in basic_handlers:
            self.register_handler(handler)
    
    def register_handler(self, handler: BaseTriggerHandler):
        """Register a trigger handler"""
        
        trigger_type = handler.get_supported_trigger_type()
        if trigger_type:
            self._handlers[trigger_type] = handler
            logger.debug(f"Registered handler for trigger type: {trigger_type}")
        else:
            logger.warning(f"Handler {handler.__class__.__name__} has no trigger type")
    
    def get_handler(self, trigger_type: str) -> Optional[BaseTriggerHandler]:
        """Get handler for a trigger type"""
        
        handler = self._handlers.get(trigger_type)
        if not handler:
            logger.warning(f"No handler found for trigger type: {trigger_type}")
        
        return handler
    
    def get_all_handlers(self) -> Dict[str, BaseTriggerHandler]:
        """Get all registered handlers"""
        return self._handlers.copy()
    
    def get_handler_for_event(self, event: TriggerEvent) -> Optional[BaseTriggerHandler]:
        """Get appropriate handler for an event type"""
        
        # Map event types to trigger types
        event_to_trigger_map = {
            'record_created': WorkflowTriggerType.RECORD_CREATED,
            'record_updated': WorkflowTriggerType.RECORD_UPDATED,
            'record_deleted': WorkflowTriggerType.RECORD_DELETED,
            # 'field_changed': WorkflowTriggerType.FIELD_CHANGED,  # Deprecated - use record_updated
            # 'status_changed': WorkflowTriggerType.STATUS_CHANGED,  # Deprecated - use record_updated
            'email_received': WorkflowTriggerType.EMAIL_RECEIVED,
            'message_received': WorkflowTriggerType.MESSAGE_RECEIVED,
            'form_submitted': WorkflowTriggerType.FORM_SUBMITTED,
            'webhook_received': WorkflowTriggerType.WEBHOOK,
            'api_endpoint_called': WorkflowTriggerType.API_ENDPOINT,
            'workflow_completed': WorkflowTriggerType.WORKFLOW_COMPLETED,
            'condition_met': WorkflowTriggerType.CONDITION_MET,
            'engagement_threshold': WorkflowTriggerType.ENGAGEMENT_THRESHOLD,
            'pipeline_stage_changed': WorkflowTriggerType.PIPELINE_STAGE_CHANGED,
            'date_reached': WorkflowTriggerType.DATE_REACHED,
            'scheduled': WorkflowTriggerType.SCHEDULED
        }
        
        trigger_type = event_to_trigger_map.get(event.event_type)
        if trigger_type:
            return self.get_handler(trigger_type)
        
        return None