"""
Workflow trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class WorkflowCompletionHandler(BaseTriggerHandler):
    """Handler for workflow completion triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.WORKFLOW_COMPLETED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a workflow completion event"""
        return event.event_type == 'workflow_completed'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract workflow completion data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'workflow_data': event.event_data,
            'completed_workflow_id': event.event_data.get('workflow_id', ''),
            'execution_id': event.event_data.get('execution_id', ''),
            'completion_status': event.event_data.get('status', 'success'),
            'execution_duration': event.event_data.get('duration', 0),
            'output_data': event.event_data.get('output', {})
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.WORKFLOW_COMPLETED
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle workflow completion trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'workflow_completed',
                'workflow_data': event.data
            }
        )