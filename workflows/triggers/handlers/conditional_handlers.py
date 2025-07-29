"""
Conditional trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class ConditionalTriggerHandler(BaseTriggerHandler):
    """Handler for conditional triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.CONDITION_MET
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a condition met event"""
        return event.event_type == 'condition_met'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract condition data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'condition_data': event.event_data,
            'conditions_evaluated': event.event_data.get('conditions', []),
            'condition_results': event.event_data.get('results', {}),
            'logic_operator': event.event_data.get('logic_operator', 'AND'),
            'overall_result': event.event_data.get('overall_result', False)
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.CONDITION_MET
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle conditional trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'condition_met',
                'condition_data': event.data
            }
        )