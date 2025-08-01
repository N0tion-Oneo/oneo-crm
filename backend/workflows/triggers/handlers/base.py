"""
Base classes for trigger handlers
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..types import TriggerEvent, TriggerResult

logger = logging.getLogger(__name__)


class BaseTriggerHandler(ABC):
    """Base class for all trigger handlers"""
    
    def __init__(self):
        self.trigger_type = ""
        self.handler_name = self.__class__.__name__
    
    @abstractmethod
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if this trigger matches the given event"""
        pass
    
    @abstractmethod
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract relevant data from the event for workflow execution"""
        pass
    
    async def validate_trigger(self, trigger) -> bool:
        """Validate trigger configuration (override if needed)"""
        return True
    
    async def should_rate_limit(self, trigger, event: TriggerEvent) -> bool:
        """Check if trigger should be rate limited (override if needed)"""
        return False
    
    def get_supported_trigger_type(self) -> str:
        """Get the trigger type this handler supports"""
        return self.trigger_type


class RecordBasedHandler(BaseTriggerHandler):
    """Base handler for record-based triggers"""
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if record-based trigger matches event"""
        
        if not event.event_data.get('record'):
            return False
        
        record = event.event_data['record']
        config = trigger.trigger_config
        
        # Check pipeline filters
        if 'pipeline_ids' in config:
            pipeline_ids = config['pipeline_ids']
            if str(record.pipeline_id) not in pipeline_ids:
                return False
        
        # Check field filters
        if 'field_filters' in config:
            field_filters = config['field_filters']
            for field, expected_value in field_filters.items():
                if field in record.data:
                    actual_value = record.data[field]
                    if actual_value != expected_value:
                        return False
                else:
                    return False
        
        return True
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract record data from event"""
        
        record = event.event_data['record']
        
        return {
            'record_id': str(record.id),
            'record_data': record.data,
            'record_title': record.title,
            'pipeline_id': str(record.pipeline_id),
            'event_type': event.event_type,
            'timestamp': event.timestamp.isoformat()
        }


class TimeBasedHandler(BaseTriggerHandler):
    """Base handler for time-based triggers"""
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Time-based triggers don't match events - they're scheduled"""
        return False
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract time-based data"""
        
        return {
            'scheduled_time': event.timestamp.isoformat(),
            'trigger_config': trigger.trigger_config
        }


class CommunicationHandler(BaseTriggerHandler):
    """Base handler for communication-based triggers"""
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if communication trigger matches event"""
        
        config = trigger.trigger_config
        
        # Check channel filters
        if 'channels' in config:
            channels = config['channels']
            event_channel = event.event_data.get('channel')
            if event_channel not in channels:
                return False
        
        # Check sender filters
        if 'sender_filters' in config:
            sender_filters = config['sender_filters']
            sender = event.event_data.get('sender', '')
            if not any(filter_pattern in sender for filter_pattern in sender_filters):
                return False
        
        return True
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract communication data from event"""
        
        return {
            'message_data': event.event_data,
            'received_at': event.timestamp.isoformat(),
            'channel': event.event_data.get('channel'),
            'sender': event.event_data.get('sender')
        }


class ConditionalHandler(BaseTriggerHandler):
    """Base handler for conditional triggers"""
    
    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if conditional trigger matches event"""
        
        conditions = trigger.trigger_config.get('conditions', [])
        condition_logic = trigger.trigger_config.get('condition_logic', 'AND')
        
        if not conditions:
            return False
        
        # Evaluate conditions based on event data
        condition_results = []
        for condition in conditions:
            result = await self._evaluate_condition(condition, event)
            condition_results.append(result)
        
        # Apply logic
        if condition_logic == 'AND':
            return all(condition_results)
        elif condition_logic == 'OR':
            return any(condition_results)
        else:
            return all(condition_results)  # Default to AND
    
    async def _evaluate_condition(self, condition: Dict[str, Any], event: TriggerEvent) -> bool:
        """Evaluate a single condition against event data"""
        
        field = condition.get('field')
        operator = condition.get('operator', '==')
        expected_value = condition.get('value')
        
        if not field:
            return False
        
        # Get actual value from event data
        actual_value = None
        if 'record' in event.event_data and hasattr(event.event_data['record'], 'data'):
            actual_value = event.event_data['record'].data.get(field)
        elif field in event.event_data:
            actual_value = event.event_data[field]
        
        if actual_value is None:
            return condition.get('allow_missing', False)
        
        # Evaluate based on operator
        try:
            if operator == '==':
                return actual_value == expected_value
            elif operator == '!=':
                return actual_value != expected_value
            elif operator == '>':
                return float(actual_value) > float(expected_value)
            elif operator == '>=':
                return float(actual_value) >= float(expected_value)
            elif operator == '<':
                return float(actual_value) < float(expected_value)
            elif operator == '<=':
                return float(actual_value) <= float(expected_value)
            elif operator == 'contains':
                return str(expected_value).lower() in str(actual_value).lower()
            elif operator == 'in':
                return actual_value in expected_value if isinstance(expected_value, list) else False
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        except (ValueError, TypeError) as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract conditional data from event"""
        
        return {
            'conditions_met': trigger.trigger_config.get('conditions', []),
            'condition_logic': trigger.trigger_config.get('condition_logic', 'AND'),
            'event_data': event.event_data,
            'evaluation_time': event.timestamp.isoformat()
        }