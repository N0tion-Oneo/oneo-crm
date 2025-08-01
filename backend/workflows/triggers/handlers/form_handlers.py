"""
Form submission trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class FormSubmissionHandler(BaseTriggerHandler):
    """Handler for form submission triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.FORM_SUBMITTED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a form submission event"""
        return event.event_type == 'form_submitted'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract form submission data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'form_data': event.event_data,
            'form_id': event.event_data.get('form_id', ''),
            'submitted_fields': event.event_data.get('fields', {}),
            'submitter_ip': event.event_data.get('ip_address', ''),
            'user_agent': event.event_data.get('user_agent', '')
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.FORM_SUBMITTED
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle form submission trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'form_submitted',
                'form_data': event.data
            }
        )