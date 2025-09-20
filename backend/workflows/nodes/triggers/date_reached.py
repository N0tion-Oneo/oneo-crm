"""
Date reached trigger processor for workflows
Triggers workflows when specific dates/times are reached
"""
from typing import Any, Dict
from datetime import datetime, timedelta
from ..base import AsyncNodeProcessor
import logging

logger = logging.getLogger(__name__)


class TriggerDateReachedProcessor(AsyncNodeProcessor):
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
            "schedule_type": {
                "type": "string",
                "enum": ["once", "recurring"],
                "default": "once",
                "description": "Schedule type for static dates",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"date_field": ""},
                    "options": [
                        {"value": "once", "label": "One-time"},
                        {"value": "recurring", "label": "Recurring"}
                    ]
                }
            },
            "time_of_day": {
                "type": "string",
                "format": "time",
                "description": "Time of day for recurring triggers (HH:MM format)",
                "ui_hints": {
                    "widget": "time",
                    "show_when": {"schedule_type": "recurring"},
                    "placeholder": "09:00"
                }
            },
            "recurring": {
                "type": "boolean",
                "default": False,
                "description": "Make this a recurring trigger (static dates only)",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced",
                    "show_when": {"date_field": ""}
                }
            },
            "recurrence_pattern": {
                "type": "string",
                "enum": ["daily", "weekly", "monthly", "yearly"],
                "description": "How often to repeat (static dates only)",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"recurring": True, "date_field": ""},
                    "section": "advanced",
                    "options": [
                        {"value": "daily", "label": "Daily"},
                        {"value": "weekly", "label": "Weekly"},
                        {"value": "monthly", "label": "Monthly"},
                        {"value": "yearly", "label": "Yearly"}
                    ]
                }
            },
            "daily_interval": {
                "type": "integer",
                "minimum": 1,
                "maximum": 365,
                "default": 1,
                "description": "Run every N days",
                "ui_hints": {
                    "widget": "number",
                    "show_when": {"recurrence_pattern": "daily"},
                    "section": "advanced",
                    "placeholder": "1 for every day, 2 for every other day"
                }
            },
            "weekly_days": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                },
                "description": "Days of the week to trigger",
                "ui_hints": {
                    "widget": "multiselect",
                    "show_when": {"recurrence_pattern": "weekly"},
                    "section": "advanced",
                    "options": [
                        {"value": "monday", "label": "Monday"},
                        {"value": "tuesday", "label": "Tuesday"},
                        {"value": "wednesday", "label": "Wednesday"},
                        {"value": "thursday", "label": "Thursday"},
                        {"value": "friday", "label": "Friday"},
                        {"value": "saturday", "label": "Saturday"},
                        {"value": "sunday", "label": "Sunday"}
                    ]
                }
            },
            "monthly_type": {
                "type": "string",
                "enum": ["date", "weekday"],
                "default": "date",
                "description": "Monthly trigger type",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"recurrence_pattern": "monthly"},
                    "section": "advanced",
                    "options": [
                        {"value": "date", "label": "Specific date (e.g., 15th)"},
                        {"value": "weekday", "label": "Specific weekday (e.g., 2nd Tuesday)"}
                    ]
                }
            },
            "monthly_date": {
                "type": "integer",
                "minimum": 1,
                "maximum": 31,
                "description": "Day of the month (1-31)",
                "ui_hints": {
                    "widget": "number",
                    "show_when": {"monthly_type": "date", "recurrence_pattern": "monthly"},
                    "section": "advanced",
                    "placeholder": "15 for the 15th of each month"
                }
            },
            "monthly_week": {
                "type": "string",
                "enum": ["first", "second", "third", "fourth", "last"],
                "description": "Week of the month",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"monthly_type": "weekday", "recurrence_pattern": "monthly"},
                    "section": "advanced",
                    "options": [
                        {"value": "first", "label": "First"},
                        {"value": "second", "label": "Second"},
                        {"value": "third", "label": "Third"},
                        {"value": "fourth", "label": "Fourth"},
                        {"value": "last", "label": "Last"}
                    ]
                }
            },
            "monthly_weekday": {
                "type": "string",
                "enum": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                "description": "Day of the week",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"monthly_type": "weekday", "recurrence_pattern": "monthly"},
                    "section": "advanced",
                    "options": [
                        {"value": "monday", "label": "Monday"},
                        {"value": "tuesday", "label": "Tuesday"},
                        {"value": "wednesday", "label": "Wednesday"},
                        {"value": "thursday", "label": "Thursday"},
                        {"value": "friday", "label": "Friday"},
                        {"value": "saturday", "label": "Saturday"},
                        {"value": "sunday", "label": "Sunday"}
                    ]
                }
            },
            "yearly_month": {
                "type": "integer",
                "minimum": 1,
                "maximum": 12,
                "description": "Month of the year (1-12)",
                "ui_hints": {
                    "widget": "select",
                    "show_when": {"recurrence_pattern": "yearly"},
                    "section": "advanced",
                    "options": [
                        {"value": 1, "label": "January"},
                        {"value": 2, "label": "February"},
                        {"value": 3, "label": "March"},
                        {"value": 4, "label": "April"},
                        {"value": 5, "label": "May"},
                        {"value": 6, "label": "June"},
                        {"value": 7, "label": "July"},
                        {"value": 8, "label": "August"},
                        {"value": 9, "label": "September"},
                        {"value": 10, "label": "October"},
                        {"value": 11, "label": "November"},
                        {"value": 12, "label": "December"}
                    ]
                }
            },
            "yearly_date": {
                "type": "integer",
                "minimum": 1,
                "maximum": 31,
                "description": "Day of the month",
                "ui_hints": {
                    "widget": "number",
                    "show_when": {"recurrence_pattern": "yearly"},
                    "section": "advanced",
                    "placeholder": "Day of the month (1-31)"
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

    def get_default_config(self, mode: str = "static") -> Dict[str, Any]:
        """
        Get default configuration for date_reached trigger

        Args:
            mode: Either "static" or "dynamic" to get mode-specific defaults
        """
        from datetime import datetime, timedelta
        from django.utils import timezone

        # Common defaults for both modes
        base_defaults = {
            "offset_days": 0,
            "offset_hours": 0,
            "timezone": "UTC",
            "business_days_only": False,
            "recurring": False,
            "schedule_type": "once"
        }

        if mode == "dynamic":
            # Dynamic mode defaults - no target_date
            return {
                **base_defaults,
                "date_field": "",  # User must select
                "pipeline_id": ""  # User must select
            }
        else:
            # Static mode defaults - with target_date
            tomorrow = timezone.now() + timedelta(days=1)
            tomorrow = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            return {
                **base_defaults,
                "target_date": tomorrow.isoformat(),
                "schedule_type": "once"
            }

    def get_required_fields(self) -> list:
        """Required fields for date triggers - handled by oneOf constraint"""
        # No strictly required fields - oneOf handles validation
        return []

    def get_optional_fields(self) -> list:
        """Optional fields for date triggers"""
        return [
            'trigger_before_minutes',  # Trigger X minutes before target date
            'trigger_after_minutes',   # Trigger X minutes after target date
            'timezone',                # Timezone for date comparison
            'record_id',               # Associated record ID
            'date_field',              # Field containing the date (for dynamic dates)
        ]

    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Custom validation for date_reached trigger to handle oneOf constraint
        """
        try:
            # Get the node's configuration data
            config_data = node_config.get('data', {}).get('config', {})

            # Check oneOf constraint: either date_field OR target_date must be present
            has_date_field = 'date_field' in config_data and config_data['date_field']
            has_target_date = 'target_date' in config_data and config_data['target_date']

            if not (has_date_field or has_target_date):
                logger.warning(f"Date reached trigger requires either 'date_field' or 'target_date'")
                return False

            # Continue with base validation for other fields
            return await super().validate_inputs(node_config, context)

        except Exception as e:
            logger.error(f"Validation error in date_reached trigger: {e}")
            return False

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