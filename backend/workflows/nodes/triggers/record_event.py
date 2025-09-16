"""
Record event trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor

logger = logging.getLogger(__name__)


class TriggerRecordEventProcessor(BaseNodeProcessor):
    """
    Processes record event triggers (created, updated, deleted)
    This node starts a workflow when a record event occurs
    """

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process record event trigger

        Config specifies the event type and pipeline to monitor
        """
        trigger_data = context.get('trigger_data', {})

        # Extract configuration
        event_type = config.get('event_type', 'created')  # created, updated, deleted
        pipeline_id = config.get('pipeline_id')
        field_conditions = config.get('field_conditions', {})

        # Extract record data from trigger
        record_data = trigger_data.get('record_data', {})
        record_id = trigger_data.get('record_id')
        actual_event = trigger_data.get('event_type', event_type)

        logger.info(f"Record {actual_event} trigger activated for pipeline {pipeline_id}")

        # Pass record data forward
        return {
            'success': True,
            'record_id': record_id,
            'record_data': record_data,
            'pipeline_id': pipeline_id,
            'event_type': actual_event,
            'triggered_by': trigger_data.get('triggered_by'),
            'triggered_at': trigger_data.get('triggered_at'),
            'trigger_type': f'record_{actual_event}'
        }

    def get_display_name(self) -> str:
        return "Record Event Trigger"

    def get_description(self) -> str:
        return "Starts workflow when a record is created, updated, or deleted"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "📊"