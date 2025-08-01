"""
Triggers package for workflow automation system
Provides clean separation of concerns for trigger management
"""

from .manager import TriggerManager
from .registry import TriggerRegistry
from .types import TriggerType, TriggerDefinition, TriggerResult

# Main trigger system instances
trigger_manager = TriggerManager()
trigger_registry = TriggerRegistry()

# Export public API
__all__ = [
    'TriggerManager',
    'TriggerRegistry', 
    'TriggerType',
    'TriggerDefinition',
    'TriggerResult',
    'trigger_manager',
    'trigger_registry'
]