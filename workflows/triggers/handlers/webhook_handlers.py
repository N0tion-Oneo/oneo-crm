"""
Webhook trigger handlers
"""
import logging
from typing import Dict, Any
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class WebhookHandler(BaseTriggerHandler):
    """Handler for webhook triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.WEBHOOK
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is a webhook event"""
        return event.event_type == 'webhook'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract webhook data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'webhook_data': event.event_data,
            'webhook_url': event.event_data.get('webhook_url', ''),
            'payload': event.event_data.get('payload', {}),
            'headers': event.event_data.get('headers', {}),
            'method': event.event_data.get('method', 'POST')
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.WEBHOOK
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle webhook trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'webhook',
                'webhook_data': event.data
            }
        )


class ApiEndpointHandler(BaseTriggerHandler):
    """Handler for API endpoint triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.API_ENDPOINT
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event is an API endpoint event"""
        return event.event_type == 'api_endpoint'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract API endpoint data from the event"""
        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'api_data': event.event_data,
            'endpoint': event.event_data.get('endpoint', ''),
            'method': event.event_data.get('method', 'GET'),
            'parameters': event.event_data.get('parameters', {}),
            'response_data': event.event_data.get('response_data', {}),
            'status_code': event.event_data.get('status_code', 200)
        }
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.API_ENDPOINT
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle API endpoint trigger"""
        
        return TriggerResult(
            success=True,
            should_execute=True,
            context_data={
                'trigger_type': 'api_endpoint',
                'api_data': event.data
            }
        )