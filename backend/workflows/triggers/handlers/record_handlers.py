"""
Record-specific trigger handlers
"""
import logging
from typing import Dict, Any, Optional, List
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType
from ...utils.condition_evaluator import condition_evaluator

logger = logging.getLogger(__name__)


class RecordCreatedHandler(BaseTriggerHandler):
    """Handler for record creation triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.RECORD_CREATED
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.RECORD_CREATED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if record creation trigger matches event"""
        return event.event_type == 'record_created'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract data for record creation triggers"""
        return {
            'record_data': event.event_data.get('record_data', {}),
            'pipeline_id': event.event_data.get('pipeline_id'),
            'timestamp': event.timestamp.isoformat(),
            'trigger_type': 'record_created'
        }
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle record creation trigger"""
        
        try:
            # Extract record data from event
            record_data = event.data.get('record_data', {})
            pipeline_id = event.data.get('pipeline_id')
            
            # Check if this pipeline is being monitored
            pipeline_ids = config.get('pipeline_ids', [])
            if pipeline_ids and str(pipeline_id) not in map(str, pipeline_ids):
                return TriggerResult(
                    success=False,
                    should_execute=False,
                    reason="Pipeline not in monitored list"
                )
            
            # Apply field conditions if configured (supports grouped conditions)
            field_conditions = config.get('field_conditions', [])
            if field_conditions:
                # Get condition logic operator
                condition_logic = config.get('condition_logic', 'AND')

                # Check for group operators if conditions have groups
                group_operators = config.get('group_operators', {})

                # Evaluate conditions using the enhanced evaluator
                matches, details = condition_evaluator.evaluate(
                    conditions=field_conditions,
                    data=record_data,
                    logic_operator=condition_logic,
                    group_operators=group_operators
                )

                if not matches:
                    return TriggerResult(
                        success=False,
                        should_execute=False,
                        reason=f"Field conditions not met: {details.get('message', 'Conditions failed')}"
                    )

            # Legacy support for field_filters (simple key-value)
            field_filters = config.get('field_filters', {})
            if field_filters:
                for field, expected_value in field_filters.items():
                    actual_value = record_data.get(field)
                    if actual_value != expected_value:
                        return TriggerResult(
                            success=False,
                            should_execute=False,
                            reason=f"Field filter not met: {field}={actual_value}, expected={expected_value}"
                        )
            
            return TriggerResult(
                success=True,
                should_execute=True,
                context_data={
                    'record_data': record_data,
                    'pipeline_id': pipeline_id,
                    'trigger_type': 'record_created'
                }
            )
            
        except Exception as e:
            logger.error(f"Record created handler error: {e}")
            return TriggerResult(
                success=False,
                error=str(e)
            )


class RecordUpdatedHandler(BaseTriggerHandler):
    """Handler for record update triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.RECORD_UPDATED
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.RECORD_UPDATED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if record update trigger matches event"""
        return event.event_type == 'record_updated'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract data for record update triggers"""
        return {
            'record_data': event.event_data.get('record_data', {}),
            'previous_data': event.event_data.get('previous_data', {}),
            'pipeline_id': event.event_data.get('pipeline_id'),
            'timestamp': event.timestamp.isoformat(),
            'trigger_type': 'record_updated'
        }
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle record update trigger"""
        
        try:
            record_data = event.data.get('record_data', {})
            previous_data = event.data.get('previous_data', {})
            pipeline_id = event.data.get('pipeline_id')
            
            # Check pipeline filter
            pipeline_ids = config.get('pipeline_ids', [])
            if pipeline_ids and str(pipeline_id) not in map(str, pipeline_ids):
                return TriggerResult(
                    success=False,
                    should_execute=False,
                    reason="Pipeline not in monitored list"
                )
            
            # Check if we should watch all fields or specific ones
            watch_all_fields = config.get('watch_all_fields', True)
            specific_fields = config.get('specific_fields', [])
            ignore_fields = config.get('ignore_fields', [])
            
            changed_fields = []
            
            if watch_all_fields:
                # Check all fields for changes
                for field, new_value in record_data.items():
                    if field in ignore_fields:
                        continue
                    old_value = previous_data.get(field)
                    if old_value != new_value:
                        changed_fields.append(field)
            else:
                # Check only specific fields
                for field in specific_fields:
                    if field in ignore_fields:
                        continue
                    new_value = record_data.get(field)
                    old_value = previous_data.get(field)
                    if old_value != new_value:
                        changed_fields.append(field)
            
            # Check if actual changes occurred
            require_actual_changes = config.get('require_actual_changes', True)
            if require_actual_changes and not changed_fields:
                return TriggerResult(
                    success=False,
                    should_execute=False,
                    reason="No actual field changes detected"
                )

            # Apply field conditions if configured (supports grouped conditions)
            field_conditions = config.get('field_conditions', [])
            if field_conditions:
                # Get condition logic operator
                condition_logic = config.get('condition_logic', 'AND')

                # Check for group operators if conditions have groups
                group_operators = config.get('group_operators', {})

                # For update triggers, we need to prepare data with change tracking
                eval_data = record_data.copy()
                eval_data['__changed_fields'] = changed_fields
                eval_data['__previous_data'] = previous_data

                # Evaluate conditions using the enhanced evaluator
                matches, details = condition_evaluator.evaluate(
                    conditions=field_conditions,
                    data=eval_data,
                    logic_operator=condition_logic,
                    group_operators=group_operators
                )

                if not matches:
                    return TriggerResult(
                        success=False,
                        should_execute=False,
                        reason=f"Field conditions not met: {details.get('message', 'Conditions failed')}"
                    )

            return TriggerResult(
                success=True,
                should_execute=True,
                context_data={
                    'record_data': record_data,
                    'previous_data': previous_data,
                    'changed_fields': changed_fields,
                    'pipeline_id': pipeline_id,
                    'trigger_type': 'record_updated'
                }
            )
            
        except Exception as e:
            logger.error(f"Record updated handler error: {e}")
            return TriggerResult(
                success=False,
                error=str(e)
            )


class RecordDeletedHandler(BaseTriggerHandler):
    """Handler for record deletion triggers"""
    
    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.RECORD_DELETED
    
    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.RECORD_DELETED
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if record deletion trigger matches event"""
        return event.event_type == 'record_deleted'
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract data for record deletion triggers"""
        return {
            'deleted_record_data': event.event_data.get('record_data', {}),
            'pipeline_id': event.event_data.get('pipeline_id'),
            'timestamp': event.timestamp.isoformat(),
            'trigger_type': 'record_deleted'
        }
    
    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle record deletion trigger"""
        
        try:
            record_data = event.data.get('record_data', {})
            pipeline_id = event.data.get('pipeline_id')
            
            # Check pipeline filter
            pipeline_ids = config.get('pipeline_ids', [])
            if pipeline_ids and str(pipeline_id) not in map(str, pipeline_ids):
                return TriggerResult(
                    success=False,
                    should_execute=False,
                    reason="Pipeline not in monitored list"
                )

            # Apply field conditions if configured (supports grouped conditions)
            field_conditions = config.get('field_conditions', [])
            if not field_conditions:
                # Also check legacy field_filters
                field_conditions = config.get('field_filters', [])

            if field_conditions:
                # Get condition logic operator
                condition_logic = config.get('condition_logic', 'AND')

                # Check for group operators if conditions have groups
                group_operators = config.get('group_operators', {})

                # Evaluate conditions using the enhanced evaluator
                matches, details = condition_evaluator.evaluate(
                    conditions=field_conditions,
                    data=record_data,
                    logic_operator=condition_logic,
                    group_operators=group_operators
                )

                if not matches:
                    return TriggerResult(
                        success=False,
                        should_execute=False,
                        reason=f"Field conditions not met: {details.get('message', 'Conditions failed')}"
                    )

            return TriggerResult(
                success=True,
                should_execute=True,
                context_data={
                    'deleted_record_data': record_data,
                    'pipeline_id': pipeline_id,
                    'trigger_type': 'record_deleted'
                }
            )
            
        except Exception as e:
            logger.error(f"Record deleted handler error: {e}")
            return TriggerResult(
                success=False,
                error=str(e)
            )