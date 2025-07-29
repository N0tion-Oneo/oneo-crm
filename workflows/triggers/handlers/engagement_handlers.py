"""
Engagement trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class EngagementThresholdHandler(BaseTriggerHandler):
    """Handler for engagement threshold triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.ENGAGEMENT_THRESHOLD
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is an engagement threshold event"""
        return event.event_type == 'engagement_threshold'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract engagement threshold data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'engagement_data': event.event_data,
            'engagement_score': event.event_data.get('score', 0),
            'threshold_value': event.event_data.get('threshold', 0),
            'threshold_type': event.event_data.get('threshold_type', 'above'),
            'contact_id': event.event_data.get('contact_id', ''),
            'engagement_activities': event.event_data.get('activities', [])
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.ENGAGEMENT_THRESHOLD
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle engagement threshold trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'engagement_threshold',
                'engagement_data': event.data
            }
        )