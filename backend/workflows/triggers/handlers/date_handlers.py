"""
Date-based trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class DateReachedHandler(BaseTriggerHandler):
    """Handler for date reached triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.DATE_REACHED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a date reached event"""
        return event.event_type == 'date_reached'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract date reached data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'date_data': event.event_data,
            'target_date': event.event_data.get('target_date', ''),
            'date_field': event.event_data.get('date_field', ''),
            'record_id': event.event_data.get('record_id', ''),
            'date_type': event.event_data.get('date_type', 'absolute'),
            'offset_days': event.event_data.get('offset_days', 0)
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.DATE_REACHED
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle date reached trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'date_reached',
                'date_data': event.data
            }
        )