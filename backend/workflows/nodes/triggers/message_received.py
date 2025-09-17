"""
Message received trigger processors for various channels
"""
from typing import Any, Dict
from ..base import BaseNodeProcessor
import logging

logger = logging.getLogger(__name__)


class TriggerLinkedInMessageProcessor(BaseNodeProcessor):
    """
    Processor for LinkedIn message received triggers
    """

    node_type = "trigger_linkedin_message"

    # Configuration schema for LinkedIn message triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "monitor_users": {
                "type": "array",
                "items": {
                    "oneOf": [
                        {"type": "string"},  # User ID
                        {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string"},
                                "account_id": {"type": "string"}  # Specific account
                            }
                        }
                    ]
                },
                "description": "Which users' LinkedIn accounts to monitor",
                "ui_hints": {
                    "widget": "user_enriched_select",
                    "channel_filter": "linkedin",
                    "multiple": True,
                    "show_all_option": True,
                    "display_format": "user_with_accounts",
                    "placeholder": "Select users to monitor",
                    "help_text": "Select specific users or 'All Users' to monitor all LinkedIn accounts"
                }
            },
            "sender_filters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by specific LinkedIn profiles or names",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "John Smith, /in/johndoe",
                    "section": "filters"
                }
            },
            "keyword_triggers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keywords that must be present in message",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "meeting, interested, demo"
                }
            },
            "conversation_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific conversation IDs to monitor",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Enter conversation IDs",
                    "section": "advanced"
                }
            },
            "connection_only": {
                "type": "boolean",
                "default": False,
                "description": "Only trigger for messages from connections",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "exclude_inmail": {
                "type": "boolean",
                "default": False,
                "description": "Exclude InMail messages",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "auto_respond": {
                "type": "boolean",
                "default": False,
                "description": "Send automatic response",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "response_template": {
                "type": "string",
                "description": "Template for automatic response",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Thanks for reaching out! I'll get back to you soon.",
                    "show_when": {"auto_respond": True}
                }
            },
            "business_hours_only": {
                "type": "boolean",
                "default": False,
                "description": "Only trigger during business hours",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            }
        }
    }

    def get_required_fields(self) -> list:
        return []

    def get_optional_fields(self) -> list:
        return [
            'sender_filter',     # Filter by specific sender
            'keyword_filter',    # Filter by keywords in message
            'conversation_id',   # Specific conversation to monitor
        ]

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process LinkedIn message trigger"""
        try:
            config = node_config.get('config', {})
            trigger_data = context.get('trigger_data', {})
            message = trigger_data.get('message', {})

            # Build output
            output = {
                'success': True,
                'trigger_type': 'linkedin_message',
                'message': message,
                'sender': message.get('sender'),
                'conversation_id': message.get('conversation_id'),
                'content': message.get('content'),
                'timestamp': message.get('timestamp'),
                'attachments': message.get('attachments', []),
            }

            logger.info(f"LinkedIn message trigger activated from {message.get('sender')}")

            # Store in context
            context['linkedin_message'] = output

            return output

        except Exception as e:
            logger.error(f"LinkedIn message trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'trigger_type': 'linkedin_message'
            }


class TriggerWhatsAppMessageProcessor(BaseNodeProcessor):
    """
    Processor for WhatsApp message received triggers
    """

    node_type = "trigger_whatsapp_message"

    # Configuration schema for WhatsApp message triggers
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "monitor_users": {
                "type": "array",
                "items": {
                    "oneOf": [
                        {"type": "string"},  # User ID
                        {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string"},
                                "account_id": {"type": "string"}  # Specific account
                            }
                        }
                    ]
                },
                "description": "Which users' WhatsApp accounts to monitor",
                "ui_hints": {
                    "widget": "user_enriched_select",
                    "channel_filter": "whatsapp",
                    "multiple": True,
                    "show_all_option": True,
                    "display_format": "user_with_accounts",
                    "placeholder": "Select users to monitor",
                    "help_text": "Select specific users or 'All Users' to monitor all WhatsApp accounts"
                }
            },
            "phone_filters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by specific phone numbers",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "+1234567890, +9876543210",
                    "section": "filters"
                }
            },
            "keyword_triggers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keywords that must be present in message",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "order, help, support"
                }
            },
            "chat_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific chat IDs to monitor",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Enter chat IDs",
                    "section": "advanced"
                }
            },
            "group_messages": {
                "type": "string",
                "enum": ["all", "exclude", "only"],
                "default": "all",
                "description": "How to handle group messages",
                "ui_hints": {
                    "widget": "select",
                    "options": [
                        {"label": "All - Include all messages", "value": "all"},
                        {"label": "Exclude - Only individual chats", "value": "exclude"},
                        {"label": "Only - Only group messages", "value": "only"}
                    ]
                }
            },
            "media_handling": {
                "type": "string",
                "enum": ["ignore", "require", "process"],
                "default": "ignore",
                "description": "How to handle media messages",
                "ui_hints": {
                    "widget": "select",
                    "options": [
                        {"label": "Ignore - Don't check for media", "value": "ignore"},
                        {"label": "Require - Only trigger if media present", "value": "require"},
                        {"label": "Process - Download and process media", "value": "process"}
                    ]
                }
            },
            "auto_respond": {
                "type": "boolean",
                "default": False,
                "description": "Send automatic response",
                "ui_hints": {
                    "widget": "checkbox"
                }
            },
            "response_template": {
                "type": "string",
                "description": "Template for automatic response",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Thank you for your message. We'll respond shortly.",
                    "show_when": {"auto_respond": True}
                }
            },
            "business_hours_only": {
                "type": "boolean",
                "default": False,
                "description": "Only trigger during business hours",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "status_messages": {
                "type": "boolean",
                "default": False,
                "description": "Include WhatsApp status messages",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            }
        }
    }

    def get_required_fields(self) -> list:
        return []

    def get_optional_fields(self) -> list:
        return [
            'phone_filter',      # Filter by specific phone number
            'keyword_filter',    # Filter by keywords in message
            'chat_id',          # Specific chat to monitor
        ]

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process WhatsApp message trigger"""
        try:
            config = node_config.get('config', {})
            trigger_data = context.get('trigger_data', {})
            message = trigger_data.get('message', {})

            # Build output
            output = {
                'success': True,
                'trigger_type': 'whatsapp_message',
                'message': message,
                'sender_phone': message.get('sender_phone'),
                'chat_id': message.get('chat_id'),
                'content': message.get('content'),
                'timestamp': message.get('timestamp'),
                'media': message.get('media', []),
                'is_group': message.get('is_group', False),
            }

            logger.info(f"WhatsApp message trigger activated from {message.get('sender_phone')}")

            # Store in context
            context['whatsapp_message'] = output

            return output

        except Exception as e:
            logger.error(f"WhatsApp message trigger error: {e}")
            return {
                'success': False,
                'error': str(e),
                'trigger_type': 'whatsapp_message'
            }