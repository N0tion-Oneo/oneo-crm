"""
Manual trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class ManualTriggerHandler(BaseTriggerHandler):
    """Handler for manual workflow triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.MANUAL
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.MANUAL
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Manual triggers always match manual events"""
        return event.event_type == 'manual'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract data for manual triggers"""
        return {
            'triggered_by': event.event_data.get('triggered_by'),
            'manual_data': event.event_data.get('manual_data', {}),
            'timestamp': event.timestamp.isoformat(),
            'trigger_type': 'manual'
        }