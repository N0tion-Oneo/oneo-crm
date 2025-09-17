"""
Email received trigger node processor
"""
import logging
from typing import Dict, Any
from workflows.nodes.base import BaseNodeProcessor

logger = logging.getLogger(__name__)


class TriggerEmailReceivedProcessor(BaseNodeProcessor):
    """
    Processes email received trigger events
    This node starts a workflow when an email is received
    """

    node_type = "trigger_email_received"

    # Configuration schema for email received triggers
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
                "description": "Which users' email accounts to monitor",
                "ui_hints": {
                    "widget": "user_enriched_select",
                    "channel_filter": "email",
                    "multiple": True,
                    "show_all_option": True,
                    "display_format": "user_with_accounts",
                    "placeholder": "Select users to monitor",
                    "help_text": "Select specific users or 'All Users' to monitor all email accounts"
                }
            },
            "sender_filters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only accept emails from",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Type email or domain (e.g., @gmail.com)",
                    "help_text": "Filter by sender email addresses or domains",
                    "section": "filters"
                }
            },
            "subject_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subject must contain",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "Enter keywords to look for in subject",
                    "help_text": "Trigger only when subject contains these words",
                    "section": "filters"
                }
            },
            "body_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Body content patterns (regex supported)",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "invoice, payment, refund",
                    "section": "filters"
                }
            },
            "attachment_handling": {
                "type": "string",
                "enum": ["ignore", "require", "process"],
                "default": "ignore",
                "description": "How to handle email attachments",
                "ui_hints": {
                    "widget": "select",
                    "options": [
                        {"label": "Ignore - Don't check attachments", "value": "ignore"},
                        {"label": "Require - Only trigger if attachments present", "value": "require"},
                        {"label": "Process - Extract and process attachments", "value": "process"}
                    ]
                }
            },
            "attachment_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Allowed attachment file types",
                "ui_hints": {
                    "widget": "tag_input",
                    "placeholder": "pdf, docx, xlsx",
                    "section": "filters",
                    "show_when": {"attachment_handling": ["require", "process"]}
                }
            },
            "auto_reply_template": {
                "type": "string",
                "description": "Template for automatic reply (leave empty to disable)",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Thank you for your email. We have received it and will respond within 24 hours.",
                    "section": "actions"
                }
            },
            "mark_as_read": {
                "type": "boolean",
                "default": True,
                "description": "Mark email as read after processing",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "actions"
                }
            },
            "folder_to_move": {
                "type": "string",
                "description": "Move processed emails to folder",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "Processed",
                    "section": "actions"
                }
            },
            "spam_filter": {
                "type": "boolean",
                "default": True,
                "description": "Enable spam filtering",
                "ui_hints": {
                    "widget": "checkbox",
                    "section": "advanced"
                }
            },
            "max_size_mb": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 10,
                "description": "Maximum email size in MB",
                "ui_hints": {
                    "widget": "number",
                    "section": "advanced"
                }
            },
            "cc_handling": {
                "type": "string",
                "enum": ["ignore", "include", "trigger_separate"],
                "default": "ignore",
                "description": "How to handle CC recipients",
                "ui_hints": {
                    "widget": "select",
                    "section": "advanced"
                }
            }
        },
        "required": []
    }

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email received trigger

        The email data from the event is passed in context['trigger_data']
        """
        trigger_data = context.get('trigger_data', {})

        # Extract user monitoring configuration
        monitor_users = config.get('monitor_users', [])

        # Extract filter configuration
        sender_filters = config.get('sender_filters', [])
        subject_patterns = config.get('subject_patterns', [])

        # Extract email data
        email_from = trigger_data.get('from', '')
        email_to = trigger_data.get('to', '')
        subject = trigger_data.get('subject', '')
        body = trigger_data.get('body', '')
        html = trigger_data.get('html', '')
        attachments = trigger_data.get('attachments', [])

        # Extract user and account information if available
        user_id = trigger_data.get('user_id')
        account_id = trigger_data.get('account_id')
        account_name = trigger_data.get('account_name')

        logger.info(f"Email trigger activated from {email_from} to {email_to}")

        # Pass email data forward with user context
        return {
            'success': True,
            'from': email_from,
            'to': email_to,
            'subject': subject,
            'body': body,
            'html': html,
            'attachments': attachments,
            'received_at': trigger_data.get('received_at'),
            'trigger_type': 'email_received',
            'user_id': user_id,
            'account_id': account_id,
            'account_name': account_name,
            'message_id': trigger_data.get('message_id'),
            'thread_id': trigger_data.get('thread_id'),
            'conversation_id': trigger_data.get('conversation_id')
        }

    def get_display_name(self) -> str:
        return "Email Received Trigger"

    def get_description(self) -> str:
        return "Starts workflow when an email is received"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "📧"