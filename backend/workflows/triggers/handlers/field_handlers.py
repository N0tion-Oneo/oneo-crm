"""
Field-specific trigger handlers
"""
import logging
from typing import Dict, Any, List
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType

logger = logging.getLogger(__name__)


class FieldChangedHandler(BaseTriggerHandler):
    """Handler for field change triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.FIELD_CHANGED
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.FIELD_CHANGED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if field change trigger matches event"""
        return event.event_type == 'field_changed'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract data for field change triggers"""
        return {
            'record_data': event.event_data.get('record_data', {}),
            'previous_data': event.event_data.get('previous_data', {}),
            'changed_fields': event.event_data.get('changed_fields', []),
            'timestamp': event.timestamp.isoformat(),
            'trigger_type': 'field_changed'
        }
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle field change trigger"""
        
        try:
            record_data = event.data.get('record_data', {})
            previous_data = event.data.get('previous_data', {})
            
            # Get watched fields from config
            watched_fields = config.get('watched_fields', [])
            if not watched_fields:
                return TriggerResult(
                    success=False,
                    should_execute=False,
                    reason="No watched fields configured"
                )
            
            # Check for changes in watched fields
            changed_fields = []
            for field in watched_fields:
                new_value = record_data.get(field)
                old_value = previous_data.get(field)
                
                # Check ignore null changes setting
                ignore_null_changes = config.get('ignore_null_changes', True)
                if ignore_null_changes and (new_value is None or old_value is None):
                    continue
                
                if old_value != new_value:
                    changed_fields.append({
                        'field': field,
                        'old_value': old_value,
                        'new_value': new_value
                    })
            
            if not changed_fields:
                return TriggerResult(
                    success=False,
                    should_execute=False,
                    reason="No changes detected in watched fields"
                )
            
            # Apply value filters if configured
            value_filters = config.get('value_filters', {})
            if value_filters:
                for change in changed_fields:
                    field = change['field']
                    new_value = change['new_value']
                    
                    if field in value_filters:
                        expected_value = value_filters[field]
                        if new_value != expected_value:
                            return TriggerResult(
                                success=False,
                                should_execute=False,
                                reason=f"Value filter not met for {field}: {new_value} != {expected_value}"
                            )
            
            return TriggerResult(
                success=True,
                should_execute=True,
                context_data={
                    'record_data': record_data,
                    'previous_data': previous_data,
                    'changed_fields': changed_fields,
                    'trigger_type': 'field_changed'
                }
            )
            
        except Exception as e:
            logger.error(f"Field changed handler error: {e}")
            return TriggerResult(
                success=False,
                error=str(e)
            )