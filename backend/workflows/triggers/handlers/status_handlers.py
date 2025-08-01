"""
Status change trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class StatusChangeHandler(BaseTriggerHandler):
    """Handler for status change triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.STATUS_CHANGED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a status change event"""
        return event.event_type == 'status_changed'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract status change data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'status_data': event.event_data,
            'previous_status': event.event_data.get('previous_status', ''),
            'new_status': event.event_data.get('new_status', ''),
            'record_id': event.event_data.get('record_id', ''),
            'changed_by': event.event_data.get('changed_by', ''),
            'status_field': event.event_data.get('field_name', 'status')
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.STATUS_CHANGED
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle status change trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'status_changed',
                'status_data': event.data
            }
        )


class PipelineStageHandler(BaseTriggerHandler):
    """Handler for pipeline stage change triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.PIPELINE_STAGE_CHANGED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a pipeline stage change event"""
        return event.event_type == 'pipeline_stage_changed'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract pipeline stage change data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'stage_data': event.event_data,
            'previous_stage': event.event_data.get('previous_stage', ''),
            'new_stage': event.event_data.get('new_stage', ''),
            'pipeline_id': event.event_data.get('pipeline_id', ''),
            'record_id': event.event_data.get('record_id', ''),
            'moved_by': event.event_data.get('moved_by', '')
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.PIPELINE_STAGE_CHANGED
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle pipeline stage change trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'pipeline_stage_changed',
                'stage_data': event.data
            }
        )