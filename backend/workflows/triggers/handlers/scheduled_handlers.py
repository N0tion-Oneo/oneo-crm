"""
Scheduled trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class ScheduledTriggerHandler(BaseTriggerHandler):
    """Handler for scheduled triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.SCHEDULED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a scheduled event"""
        return event.event_type == 'scheduled'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract scheduled data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'schedule_data': event.event_data,
            'schedule_type': event.event_data.get('schedule_type', 'once'),
            'cron_expression': event.event_data.get('cron_expression', ''),
            'next_run': event.event_data.get('next_run', ''),
            'last_run': event.event_data.get('last_run', ''),
            'schedule_config': event.event_data.get('config', {})
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.SCHEDULED
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle scheduled trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'scheduled',
                'schedule_data': event.data
            }
        )