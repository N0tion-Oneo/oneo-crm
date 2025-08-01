"""
Trigger Processors - Process trigger logic and prepare data for workflow execution
"""

from .base import BaseTriggerProcessor
from .factory import TriggerProcessorFactory

__all__ = ['BaseTriggerProcessor', 'TriggerProcessorFactory']