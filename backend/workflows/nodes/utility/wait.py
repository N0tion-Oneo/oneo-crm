"""
Wait/Delay Node Processor - Add delays and scheduling to workflows
"""
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class WaitDelayProcessor(AsyncNodeProcessor):
    """Process wait/delay nodes for workflow timing control"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["schedule_type"],
        "properties": {
            "schedule_type": {
                "type": "string",
                "enum": ["immediate", "scheduled", "business_hours"],
                "default": "immediate",
                "description": "Type of delay scheduling",
                "ui_hints": {
                    "widget": "radio"
                }
            },
            "delay_type": {
                "type": "string",
                "enum": ["seconds", "minutes", "hours", "days"],
                "default": "seconds",
                "description": "Unit of delay time",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"schedule_type": ["immediate", "business_hours"]}
                }
            },
            "delay_value": {
                "type": "number",
                "minimum": 0,
                "maximum": 365,
                "default": 0,
                "description": "Amount of delay",
                "ui_hints": {
                    "show_when": {"schedule_type": ["immediate", "business_hours"]}
                }
            },
            "schedule_datetime": {
                "type": "string",
                "format": "date-time",
                "description": "Specific datetime to wait until",
                "ui_hints": {
                    "widget": "datetime",
                    "show_when": {"schedule_type": "scheduled"}
                }
            },
            "business_hours_config": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                    },
                    "start_time": {
                        "type": "string",
                        "pattern": "^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
                        "default": "09:00"
                    },
                    "end_time": {
                        "type": "string",
                        "pattern": "^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
                        "default": "17:00"
                    },
                    "timezone": {
                        "type": "string",
                        "default": "UTC"
                    }
                },
                "description": "Business hours configuration",
                "ui_hints": {
                    "widget": "business_hours",
                    "show_when": {"schedule_type": "business_hours"}
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "wait_delay"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process wait/delay node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration
        delay_type = config.get('delay_type', 'seconds')
        delay_value = config.get('delay_value', 0)
        schedule_type = config.get('schedule_type', 'immediate')
        schedule_datetime = config.get('schedule_datetime', '')
        business_hours_config = config.get('business_hours_config', {})
        
        start_time = timezone.now()
        
        try:
            if schedule_type == 'immediate':
                # Simple delay
                actual_delay = await self._process_immediate_delay(delay_type, delay_value)
                
            elif schedule_type == 'scheduled':
                # Wait until specific datetime
                actual_delay = await self._process_scheduled_delay(schedule_datetime, context)
                
            elif schedule_type == 'business_hours':
                # Wait until next business hours
                actual_delay = await self._process_business_hours_delay(
                    delay_type, delay_value, business_hours_config
                )
                
            else:
                raise ValueError(f"Unsupported schedule type: {schedule_type}")
            
            end_time = timezone.now()
            
            return {
                'success': True,
                'delay_type': delay_type,
                'delay_value': delay_value,
                'schedule_type': schedule_type,
                'actual_delay_seconds': actual_delay,
                'started_at': start_time.isoformat(),
                'resumed_at': end_time.isoformat(),
                'total_wait_time': (end_time - start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Wait/delay processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'delay_type': delay_type,
                'delay_value': delay_value,
                'schedule_type': schedule_type
            }
    
    async def _process_immediate_delay(self, delay_type: str, delay_value: float) -> float:
        """Process immediate delay"""
        
        if delay_value <= 0:
            return 0
        
        if delay_type == 'seconds':
            delay_seconds = delay_value
        elif delay_type == 'minutes':
            delay_seconds = delay_value * 60
        elif delay_type == 'hours':
            delay_seconds = delay_value * 3600
        elif delay_type == 'days':
            delay_seconds = delay_value * 86400
        else:
            raise ValueError(f"Unsupported delay type: {delay_type}")
        
        # Cap maximum delay to prevent extremely long waits
        max_delay = 24 * 3600  # 24 hours
        if delay_seconds > max_delay:
            logger.warning(f"Delay capped from {delay_seconds}s to {max_delay}s")
            delay_seconds = max_delay
        
        await asyncio.sleep(delay_seconds)
        return delay_seconds
    
    async def _process_scheduled_delay(self, schedule_datetime: str, context: Dict[str, Any]) -> float:
        """Process scheduled delay until specific datetime"""
        
        if not schedule_datetime:
            raise ValueError("schedule_datetime required for scheduled delay")
        
        # Format datetime string with context if needed
        try:
            formatted_datetime = schedule_datetime.format(**context)
        except:
            formatted_datetime = schedule_datetime
        
        # Parse target datetime
        try:
            if 'T' in formatted_datetime:
                # ISO format
                target_dt = datetime.fromisoformat(formatted_datetime.replace('Z', '+00:00'))
            else:
                # Simple format
                target_dt = datetime.strptime(formatted_datetime, '%Y-%m-%d %H:%M:%S')
            
            # Make timezone aware if needed
            if target_dt.tzinfo is None:
                target_dt = timezone.make_aware(target_dt)
                
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {formatted_datetime}")
        
        # Calculate delay
        now = timezone.now()
        if target_dt <= now:
            logger.warning(f"Target datetime {target_dt} is in the past, no delay applied")
            return 0
        
        delay_seconds = (target_dt - now).total_seconds()
        
        # Cap maximum scheduled delay
        max_delay = 30 * 24 * 3600  # 30 days
        if delay_seconds > max_delay:
            raise ValueError(f"Scheduled delay too long: {delay_seconds}s (max: {max_delay}s)")
        
        await asyncio.sleep(delay_seconds)
        return delay_seconds
    
    async def _process_business_hours_delay(
        self, 
        delay_type: str, 
        delay_value: float, 
        business_hours_config: Dict[str, Any]
    ) -> float:
        """Process delay respecting business hours"""
        
        # Default business hours configuration
        default_config = {
            'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
            'start_time': '09:00',
            'end_time': '17:00',
            'timezone': 'UTC'
        }
        
        config = {**default_config, **business_hours_config}
        
        # Get current time
        now = timezone.now()
        
        # Check if we're currently in business hours
        if self._is_business_hours(now, config):
            # We're in business hours, apply normal delay
            return await self._process_immediate_delay(delay_type, delay_value)
        else:
            # We're outside business hours, wait until next business hours
            next_business_time = self._get_next_business_time(now, config)
            
            # Calculate delay to next business hours
            delay_to_business = (next_business_time - now).total_seconds()
            
            # Add the original delay after reaching business hours
            if delay_value > 0:
                original_delay = self._convert_delay_to_seconds(delay_type, delay_value)
                total_delay = delay_to_business + original_delay
            else:
                total_delay = delay_to_business
            
            await asyncio.sleep(total_delay)
            return total_delay
    
    def _is_business_hours(self, dt: datetime, config: Dict[str, Any]) -> bool:
        """Check if given datetime is within business hours"""
        
        # Check day of week
        day_name = dt.strftime('%A').lower()
        if day_name not in config['days']:
            return False
        
        # Check time range
        start_time = datetime.strptime(config['start_time'], '%H:%M').time()
        end_time = datetime.strptime(config['end_time'], '%H:%M').time()
        current_time = dt.time()
        
        return start_time <= current_time <= end_time
    
    def _get_next_business_time(self, current_dt: datetime, config: Dict[str, Any]) -> datetime:
        """Get the next business hours datetime"""
        
        start_time = datetime.strptime(config['start_time'], '%H:%M').time()
        
        # Start checking from current day
        check_dt = current_dt.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        
        # If it's the same day but past business hours, start from tomorrow
        if check_dt <= current_dt:
            check_dt += timedelta(days=1)
        
        # Find next business day
        max_days_check = 14  # Prevent infinite loop
        for i in range(max_days_check):
            day_name = check_dt.strftime('%A').lower()
            if day_name in config['days']:
                return check_dt
            check_dt += timedelta(days=1)
        
        # Fallback - return next Monday if no business day found
        days_until_monday = (7 - check_dt.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        return check_dt + timedelta(days=days_until_monday)
    
    def _convert_delay_to_seconds(self, delay_type: str, delay_value: float) -> float:
        """Convert delay to seconds"""
        
        if delay_type == 'seconds':
            return delay_value
        elif delay_type == 'minutes':
            return delay_value * 60
        elif delay_type == 'hours':
            return delay_value * 3600
        elif delay_type == 'days':
            return delay_value * 86400
        else:
            raise ValueError(f"Unsupported delay type: {delay_type}")
    
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for wait/delay node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        checkpoint.update({
            'wait_config': {
                'delay_type': config.get('delay_type', 'seconds'),
                'delay_value': config.get('delay_value', 0),
                'schedule_type': config.get('schedule_type', 'immediate'),
                'schedule_datetime': config.get('schedule_datetime', ''),
                'has_business_hours_config': bool(config.get('business_hours_config')),
                'expected_delay_seconds': self._convert_delay_to_seconds(
                    config.get('delay_type', 'seconds'),
                    config.get('delay_value', 0)
                )
            }
        })
        
        return checkpoint