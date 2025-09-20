"""
Record event trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class TriggerRecordEventProcessor(AsyncNodeProcessor):
    """
    Processes record event triggers (created, updated, deleted)
    This node starts a workflow when a record event occurs
    """

    node_type = "trigger_record_created"  # Will handle all record events

    # Configuration schema for record event triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "event_type": {
                "type": "string",
                "enum": ["created", "updated", "deleted"],
                "default": "created",
                "description": "Type of record event to trigger on",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "pipeline_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific pipelines to monitor (leave empty for all)",
                "ui_hints": {
                    "widget": "pipeline_multiselect",
                    "placeholder": "Select pipelines (empty = all pipelines)"
                }
            },
            "field_filters": {
                "type": "object",
                "description": "Filter records by field values",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 6,
                    "placeholder": '{\n  "status": "new",\n  "source": "website",\n  "score": {"$gte": 50}\n}'
                }
            },
            "watch_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "For updates, only trigger if these fields change",
                "ui_hints": {
                    "widget": "field_multiselect",
                    "placeholder": "Select fields to watch",
                    "show_when": {"event_type": "updated"}
                }
            },
            "ignore_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "For updates, ignore changes to these fields",
                "ui_hints": {
                    "widget": "field_multiselect",
                    "placeholder": "Select fields to ignore",
                    "show_when": {"event_type": "updated"}
                }
            },
            "require_actual_changes": {
                "type": "boolean",
                "default": True,
                "description": "Only trigger if field values actually changed",
                "ui_hints": {
                    "widget": "checkbox",
                    "show_when": {"event_type": "updated"}
                }
            },
            "delay_seconds": {
                "type": "integer",
                "minimum": 0,
                "maximum": 3600,
                "default": 0,
                "description": "Delay before triggering (seconds)",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced"
                }
            },
            "batch_processing": {
                "type": "boolean",
                "default": False,
                "description": "Process multiple records as batch",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "batch_size": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 10,
                "description": "Maximum batch size",
                "ui_hints": {
                    "widget": "number",
                    "show_when": {"batch_processing": True},
                    "section": "advanced"
                }
            }
        }
    }

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