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

    async def process(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email received trigger

        The email data from the event is passed in context['trigger_data']
        """
        trigger_data = context.get('trigger_data', {})

        # Extract email configuration
        to_address = config.get('to_address', '')
        subject_contains = config.get('subject_contains', '')
        from_domain = config.get('from_domain', '')

        # Extract email data
        email_from = trigger_data.get('from', '')
        email_to = trigger_data.get('to', '')
        subject = trigger_data.get('subject', '')
        body = trigger_data.get('body', '')
        html = trigger_data.get('html', '')
        attachments = trigger_data.get('attachments', [])

        logger.info(f"Email trigger activated from {email_from}")

        # Pass email data forward
        return {
            'success': True,
            'from': email_from,
            'to': email_to,
            'subject': subject,
            'body': body,
            'html': html,
            'attachments': attachments,
            'received_at': trigger_data.get('received_at'),
            'trigger_type': 'email_received'
        }

    def get_display_name(self) -> str:
        return "Email Received Trigger"

    def get_description(self) -> str:
        return "Starts workflow when an email is received"

    def get_category(self) -> str:
        return "Triggers"

    def get_icon(self) -> str:
        return "📧"