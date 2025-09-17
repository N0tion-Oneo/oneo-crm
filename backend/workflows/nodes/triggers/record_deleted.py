"""
Record deleted trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor

logger = logging.getLogger(__name__)


class TriggerRecordDeletedProcessor(BaseNodeProcessor):
    """
    Processes record deleted trigger events
    This node starts a workflow when a record is deleted
    """

    node_type = "trigger_record_deleted"

    # Configuration schema for record deleted triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "pipeline_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Which pipelines to monitor?",
                "ui_hints": {
                    "widget": "pipeline_multiselect",
                    "placeholder": "Select pipelines (empty = all pipelines)",
                    "help_text": "Leave empty to monitor all pipelines"
                }
            },
            "field_conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "operator": {"type": "string"},
                        "value": {}
                    }
                },
                "description": "Which records should trigger when deleted?",
                "ui_hints": {
                    "widget": "condition_builder",
                    "help_text": "Only trigger when deleted records meet these conditions"
                }
            },
            "deleted_by_filter": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only trigger for deletions by these users",
                "ui_hints": {
                    "widget": "user_multiselect",
                    "placeholder": "Select users",
                    "help_text": "Leave empty for all users",
                    "section": "advanced"
                }
            },
            "capture_snapshot": {
                "type": "boolean",
                "default": True,
                "description": "Capture record data before deletion",
                "ui_hints": {
                    "widget": "checkbox",
                    "help_text": "Save the record's data for use in the workflow"
                }
            },
            "include_relationships": {
                "type": "boolean",
                "default": False,
                "description": "Include related records in snapshot",
                "ui_hints": {
                    "widget": "checkbox",
                    "help_text": "Capture data from related records before deletion",
                    "section": "advanced"
                }
            },
            "soft_delete_only": {
                "type": "boolean",
                "default": False,
                "description": "Only trigger on soft deletes",
                "ui_hints": {
                    "widget": "checkbox",
                    "help_text": "Ignore permanent deletions",
                    "section": "advanced"
                }
            },
            "hard_delete_only": {
                "type": "boolean",
                "default": False,
                "description": "Only trigger on permanent deletes",
                "ui_hints": {
                    "widget": "checkbox",
                    "help_text": "Ignore soft deletions (records can be restored)",
                    "section": "advanced"
                }
            },
            "minimum_age_days": {
                "type": "integer",
                "minimum": 0,
                "maximum": 365,
                "description": "Only trigger for records older than (days)",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "30",
                    "help_text": "Prevent accidental deletion of new records",
                    "section": "advanced"
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
            }
        }
    }

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process record deleted trigger

        The record data from the event is passed in context['trigger_data']
        """
        trigger_data = context.get('trigger_data', {})

        # Extract configuration
        pipeline_ids = config.get('pipeline_ids', [])
        capture_snapshot = config.get('capture_snapshot', True)
        field_conditions = config.get('field_conditions', [])
        logic_operator = config.get('logic_operator', 'AND')
        group_operators = config.get('group_operators', {})

        # Extract record data
        record_snapshot = trigger_data.get('record_snapshot', {}) if capture_snapshot else {}
        pipeline_id = trigger_data.get('pipeline_id')
        deleted_by = trigger_data.get('deleted_by')
        is_soft_delete = trigger_data.get('is_soft_delete', False)

        logger.info(f"Record deleted trigger activated for pipeline {pipeline_id}, soft_delete={is_soft_delete}")

        # Check if we have conditions to evaluate
        if field_conditions and record_snapshot:
            from workflows.utils.condition_evaluator import condition_evaluator

            # Evaluate conditions against the record snapshot
            matches, details = condition_evaluator.evaluate(
                conditions=field_conditions,
                data=record_snapshot,
                logic_operator=logic_operator,
                group_operators=group_operators
            )

            if not matches:
                logger.info(f"Record deleted trigger conditions not met: {details}")
                return {
                    'success': False,
                    'skip': True,
                    'reason': 'Conditions not met',
                    'evaluation_details': details
                }

        # Pass record data forward
        return {
            'success': True,
            'record_snapshot': record_snapshot,
            'pipeline_id': pipeline_id,
            'deleted_by': deleted_by,
            'deleted_at': trigger_data.get('deleted_at'),
            'is_soft_delete': is_soft_delete,
            'trigger_type': 'record_deleted'
        }

    def get_display_name(self) -> str:
        return "Record Deleted Trigger"

    def get_description(self) -> str:
        return "Starts workflow when a record is deleted"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "🗑️"