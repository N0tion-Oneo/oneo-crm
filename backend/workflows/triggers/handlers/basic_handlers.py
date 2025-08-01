"""
Basic trigger handlers that serve as fallbacks
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler, RecordBasedHandler, TimeBasedHandler, CommunicationHandler, ConditionalHandler
from ..types import TriggerEvent

logger = logging.getLogger(__name__)


class BasicRecordHandler(RecordBasedHandler):
    """Basic handler for record-based triggers"""
    
    def __init__(self, trigger_type: str):
        super().__init__()
        self.trigger_type = trigger_type
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Use parent implementation with basic record matching"""
        return await super().matches_event(trigger, event)
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Use parent implementation for data extraction"""
        data = await super().extract_data(trigger, event)
        data['handler_type'] = 'basic_record'
        return data


class BasicCommunicationHandler(CommunicationHandler):
    """Basic handler for communication-based triggers"""
    
    def __init__(self, trigger_type: str):
        super().__init__()
        self.trigger_type = trigger_type
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Use parent implementation with basic communication matching"""
        return await super().matches_event(trigger, event)
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Use parent implementation for data extraction"""
        data = await super().extract_data(trigger, event)
        data['handler_type'] = 'basic_communication'
        return data


class BasicConditionalHandler(ConditionalHandler):
    """Basic handler for conditional triggers"""
    
    def __init__(self, trigger_type: str):
        super().__init__()
        self.trigger_type = trigger_type
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Use parent implementation with basic conditional matching"""
        return await super().matches_event(trigger, event)
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Use parent implementation for data extraction"""
        data = await super().extract_data(trigger, event)
        data['handler_type'] = 'basic_conditional'
        return data


class BasicTimeHandler(TimeBasedHandler):
    """Basic handler for time-based triggers"""
    
    def __init__(self, trigger_type: str):
        super().__init__()
        self.trigger_type = trigger_type
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Time-based triggers don't match events directly"""
        return False
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Use parent implementation for data extraction"""
        data = await super().extract_data(trigger, event)
        data['handler_type'] = 'basic_time'
        return data


class BasicWebhookHandler(BaseTriggerHandler):
    """Basic handler for webhook triggers"""
    
    def __init__(self, trigger_type: str = 'webhook'):
        super().__init__()
        self.trigger_type = trigger_type
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if webhook event matches trigger"""
        
        if event.event_type != 'webhook_received':
            return False
        
        config = trigger.trigger_config
        
        # Check if this webhook is for this specific workflow
        workflow_id = event.event_data.get('workflow_id')
        if workflow_id and str(trigger.workflow.id) != workflow_id:
            return False
        
        return True
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract webhook data"""
        
        return {
            'webhook_payload': event.event_data.get('payload', {}),
            'webhook_headers': event.event_data.get('headers', {}),
            'received_at': event.timestamp.isoformat(),
            'handler_type': 'basic_webhook'
        }


class BasicManualHandler(BaseTriggerHandler):
    """Basic handler for manual triggers"""
    
    def __init__(self, trigger_type: str = 'manual'):
        super().__init__()
        self.trigger_type = trigger_type
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Manual triggers always match when called"""
        return event.event_type == 'manual_trigger'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract manual trigger data"""
        
        return {
            'manual_data': event.event_data,
            'triggered_at': event.timestamp.isoformat(),
            'handler_type': 'basic_manual'
        }