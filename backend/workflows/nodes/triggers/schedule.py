"""
Schedule trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import AsyncNodeProcessor
from datetime import datetime

logger = logging.getLogger(__name__)


class TriggerScheduleProcessor(AsyncNodeProcessor):
    """
    Processes scheduled trigger events
    This node starts a workflow on a schedule
    """

    node_type = "trigger_scheduled"

    # Configuration schema for scheduled triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "cron_expression": {
                "type": "string",
                "description": "When should this workflow run?",
                "ui_hints": {
                    "widget": "schedule_builder",
                    "placeholder": "0 9 * * *",
                    "help_text": "Set up a recurring schedule for your workflow"
                }
            },
            "timezone": {
                "type": "string",
                "default": "UTC",
                "description": "Timezone for the schedule",
                "ui_hints": {
                    "widget": "timezone_select",
                    "placeholder": "Select timezone"
                }
            },
            "max_instances": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 1,
                "description": "How many can run at the same time?",
                "ui_hints": {
                    "widget": "number",
                    "help_text": "Limit how many instances of this workflow can run simultaneously"
                }
            },
            "overlap_policy": {
                "type": "string",
                "enum": ["skip", "queue", "replace"],
                "default": "skip",
                "description": "How to handle overlapping executions",
                "ui_hints": {
                    "widget": "select",
                    "options": [
                        {"label": "Skip - Don't run if previous still running", "value": "skip"},
                        {"label": "Queue - Queue execution after current completes", "value": "queue"},
                        {"label": "Replace - Cancel previous and start new", "value": "replace"}
                    ]
                }
            },
            "jitter_seconds": {
                "type": "integer",
                "minimum": 0,
                "maximum": 300,
                "default": 0,
                "description": "Add random delay (seconds)",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced",
                    "help_text": "Adds a random delay to prevent all workflows from starting at exactly the same time"
                }
            },
            "active_days": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                },
                "description": "Days of week when schedule is active",
                "ui_hints": {
                    "widget": "multiselect",
                    "section": "advanced",
                    "placeholder": "Select active days (empty = all days)"
                }
            },
            "active_hours": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "pattern": "^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
                    },
                    "end": {
                        "type": "string",
                        "pattern": "^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
                    }
                },
                "description": "Time range when schedule is active",
                "ui_hints": {
                    "widget": "time_range",
                    "section": "advanced",
                    "help_text": "Schedule only runs within this time window"
                }
            },
            "skip_weekends": {
                "type": "boolean",
                "default": False,
                "description": "Skip execution on weekends",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "skip_holidays": {
                "type": "boolean",
                "default": False,
                "description": "Skip execution on holidays",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "retry_on_failure": {
                "type": "boolean",
                "default": True,
                "description": "Retry if workflow execution fails",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "max_retries": {
                "type": "integer",
                "minimum": 0,
                "maximum": 5,
                "default": 3,
                "description": "Maximum retry attempts on failure",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced",
                    "show_when": {"retry_on_failure": True}
                }
            }
        },
        "required": ["cron_expression"]
    }

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process scheduled trigger

        Config includes schedule settings like cron expression, timezone, etc.
        """
        schedule_config = config.get('schedule', {})

        # Get current execution time
        execution_time = datetime.now().isoformat()

        logger.info(f"Schedule trigger activated at {execution_time}")

        # Pass schedule information forward
        return {
            'success': True,
            'triggered_at': execution_time,
            'schedule': schedule_config,
            'trigger_type': 'schedule',
            'is_scheduled': True
        }

    def get_display_name(self) -> str:
        return "Schedule Trigger"

    def get_description(self) -> str:
        return "Starts workflow on a schedule"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "⏰"