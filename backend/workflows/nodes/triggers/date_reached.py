"""
Date reached trigger processor for workflows
Triggers workflows when specific dates/times are reached
"""
from typing import Any, Dict
from datetime import datetime, timedelta
from ..base import BaseNodeProcessor
import logging

logger = logging.getLogger(__name__)


class TriggerDateReachedProcessor(BaseNodeProcessor):
    """
    Processor for date-based workflow triggers
    Used for reminders, deadlines, and scheduled events
    """

    node_type = "trigger_date_reached"

    # Configuration schema for date reached triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "date_field": {
                "type": "string",
                "description": "Field containing the target date",
                "ui_hints": {
                    "widget": "field_select",
                    "field_types": ["date", "datetime"],
                    "placeholder": "Select date field"
                }
            },
            "target_date": {
                "type": "string",
                "format": "date-time",
                "description": "Static target date (ISO format) - alternative to date_field",
                "ui_hints": {
                    "widget": "datetime",
                    "placeholder": "2024-12-25T10:00:00Z",
                    "show_when": {"date_field": ""}
                }
            },
            "offset_days": {
                "type": "integer",
                "minimum": -365,
                "maximum": 365,
                "default": 0,
                "description": "Days before (-) or after (+) the target date",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "0 (on date), -1 (day before), 1 (day after)"
                }
            },
            "offset_hours": {
                "type": "integer",
                "minimum": -24,
                "maximum": 24,
                "default": 0,
                "description": "Hours before (-) or after (+) the target date",
                "ui_hints": {
                    "widget": "number",
                    "placeholder": "0 (exact time), -2 (2 hours before)"
                }
            },
            "business_days_only": {
                "type": "boolean",
                "default": False,
                "description": "Only trigger on business days (Mon-Fri)",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "timezone": {
                "type": "string",
                "default": "UTC",
                "description": "Timezone for date calculations",
                "ui_hints": {
                    "widget": "timezone_select",
                    "placeholder": "UTC"
                }
            },
            "reminder_type": {
                "type": "string",
                "enum": ["before", "on", "after"],
                "default": "on",
                "description": "When to trigger relative to the date",
                "ui_hints": {
                    "widget": "select",
                    "options": [
                        {"value": "before", "label": "Before the date"},
                        {"value": "on", "label": "On the date"},
                        {"value": "after", "label": "After the date"}
                    ]
                }
            },
            "recurring": {
                "type": "boolean",
                "default": False,
                "description": "Make this a recurring trigger",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "recurrence_pattern": {
                "type": "string",
                "enum": ["daily", "weekly", "monthly", "yearly"],
                "description": "How often to repeat",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"recurring": True},
                    "section": "advanced",
                    "options": [
                        {"value": "daily", "label": "Daily"},
                        {"value": "weekly", "label": "Weekly"},
                        {"value": "monthly", "label": "Monthly"},
                        {"value": "yearly", "label": "Yearly"}
                    ]
                }
            },
            "recurrence_end_date": {
                "type": "string",
                "format": "date",
                "description": "When to stop recurring (optional)",
                "ui_hints": {
                    "widget": "date",
                    "show_when": {"recurring": True},
                    "section": "advanced"
                }
            },
            "max_occurrences": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "description": "Maximum number of occurrences",
                "ui_hints": {
                    "widget": "number",
                    "show_when": {"recurring": True},
                    "section": "advanced",
                    "placeholder": "Leave empty for unlimited"
                }
            }
        },
        "oneOf": [
            {"required": ["date_field"]},
            {"required": ["target_date"]}
        ]
    }

    def get_required_fields(self) -> list:
        """Required fields for date triggers"""
        return [
            'target_date',  # The date to trigger on (ISO format or field reference)
        ]

    def get_optional_fields(self) -> list:
        """Optional fields for date triggers"""
        return [
            'trigger_before_minutes',  # Trigger X minutes before target date
            'trigger_after_minutes',   # Trigger X minutes after target date
            'timezone',                # Timezone for date comparison
            'record_id',               # Associated record ID
            'date_field',              # Field containing the date (for dynamic dates)
        ]

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process date reached trigger
        """
        try:
            config = node_config.get('config', {})
            trigger_data = context.get('trigger_data', {})

            # Get target date
            target_date_str = config.get('target_date')
            if not target_date_str:
                # Try to get from a record field if specified
                date_field = config.get('date_field')
                if date_field and 'record' in trigger_data:
                    target_date_str = trigger_data['record'].get(date_field)

            if not target_date_str:
                raise ValueError("No target date specified")

            # Parse the target date
            if isinstance(target_date_str, str):
                target_date = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
            else:
                target_date = target_date_str

            # Apply before/after offsets
            before_minutes = config.get('trigger_before_minutes', 0)
            after_minutes = config.get('trigger_after_minutes', 0)

            if before_minutes:
                trigger_time = target_date - timedelta(minutes=before_minutes)
            elif after_minutes:
                trigger_time = target_date + timedelta(minutes=after_minutes)
            else:
                trigger_time = target_date

            # Build output
            output = {
                'success': True,
                'trigger_type': 'date_reached',
                'target_date': target_date.isoformat(),
                'trigger_time': trigger_time.isoformat(),
                'record_id': config.get('record_id') or trigger_data.get('record_id'),
                'date_field': config.get('date_field'),
                'offset_applied': {
                    'before_minutes': before_minutes,
                    'after_minutes': after_minutes
                }
            }

            logger.info(f"Date trigger activated for {target_date.isoformat()}")

            # Store in context for downstream nodes
            context['date_trigger'] = output

            return output

        except Exception as e:
            logger.error(f"Date trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'trigger_type': 'date_reached'
            }