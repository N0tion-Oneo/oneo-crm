"""
Trigger node processors for workflow initiation
"""
from .form_submission import TriggerFormSubmittedProcessor
from .schedule import TriggerScheduleProcessor
from .webhook import TriggerWebhookProcessor
from .record_event import TriggerRecordEventProcessor
from .email_received import TriggerEmailReceivedProcessor

__all__ = [
    'TriggerFormSubmittedProcessor',
    'TriggerScheduleProcessor',
    'TriggerWebhookProcessor',
    'TriggerRecordEventProcessor',
    'TriggerEmailReceivedProcessor',
]