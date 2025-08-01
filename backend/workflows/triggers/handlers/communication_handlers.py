"""
Communication trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class EmailReceivedHandler(BaseTriggerHandler):
    """Handler for email received triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.EMAIL_RECEIVED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is an email received event"""
        return event.event_type == 'email_received'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract email data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'email_data': event.event_data,
            'sender': event.event_data.get('sender', ''),
            'subject': event.event_data.get('subject', ''),
            'recipient': event.event_data.get('recipient', ''),
            'message_id': event.event_data.get('message_id', '')
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.EMAIL_RECEIVED
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle email received trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'email_received',
                'email_data': event.data
            }
        )


class MessageReceivedHandler(BaseTriggerHandler):
    """Handler for message received triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.MESSAGE_RECEIVED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a message received event"""
        return event.event_type == 'message_received'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract message data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'message_data': event.event_data,
            'sender': event.event_data.get('sender', ''),
            'channel': event.event_data.get('channel', ''),
            'message_type': event.event_data.get('message_type', ''),
            'content': event.event_data.get('content', '')
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.MESSAGE_RECEIVED
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle message received trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'message_received',
                'message_data': event.data
            }
        )