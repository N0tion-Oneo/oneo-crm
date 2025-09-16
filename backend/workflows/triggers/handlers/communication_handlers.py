"""
Communication trigger handlers with enhanced thread awareness and multi-channel monitoring
"""
import logging
from typing import Dict, Any, List, Optional
from .base import BaseTriggerHandler
from ..types import TriggerEvent, TriggerResult
from ...models import WorkflowTriggerType
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class EmailReceivedHandler(BaseTriggerHandler):
    """Enhanced handler for email received triggers with thread awareness"""

    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.EMAIL_RECEIVED

    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event matches email trigger criteria"""
        if event.event_type != 'email_received':
            return False

        trigger_config = trigger.configuration or {}

        # Check if monitoring specific accounts
        monitor_accounts = trigger_config.get('monitor_accounts', [])
        if monitor_accounts:
            recipient_email = event.event_data.get('recipient', '')
            if recipient_email not in monitor_accounts:
                return False

        # Check if monitoring specific threads
        monitor_thread = trigger_config.get('monitor_thread_only', False)
        if monitor_thread:
            required_thread_id = trigger_config.get('thread_id')
            event_thread_id = event.event_data.get('thread_id') or event.event_data.get('in_reply_to')
            if required_thread_id and event_thread_id != required_thread_id:
                return False

        # Check sender filters
        allowed_senders = trigger_config.get('allowed_senders', [])
        if allowed_senders:
            sender = event.event_data.get('sender', '')
            if sender not in allowed_senders:
                return False

        return True

    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract enhanced email data including thread information"""
        event_data = event.event_data

        # Extract thread information
        thread_id = event_data.get('thread_id') or event_data.get('in_reply_to')
        is_reply = bool(event_data.get('in_reply_to'))

        # Get parent message if this is a reply
        parent_message_id = None
        if is_reply:
            parent_message_id = event_data.get('in_reply_to')

        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'email_data': event_data,
            'sender': event_data.get('sender', ''),
            'subject': event_data.get('subject', ''),
            'recipient': event_data.get('recipient', ''),
            'message_id': event_data.get('message_id', ''),
            'thread_id': thread_id,
            'is_reply': is_reply,
            'parent_message_id': parent_message_id,
            'conversation_id': event_data.get('conversation_id'),
            'channel_account': event_data.get('channel_account', ''),
            'headers': event_data.get('headers', {})
        }

    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.EMAIL_RECEIVED

    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle email received trigger with enhanced context"""
        extracted = await self.extract_data(None, event)

        # Build comprehensive context for workflow
        context_data = {
            'trigger_type': 'email_received',
            'email_data': event.data,
            'thread_id': extracted.get('thread_id'),
            'is_reply': extracted.get('is_reply'),
            'parent_message_id': extracted.get('parent_message_id'),
            'conversation_id': extracted.get('conversation_id'),
            'message_id': extracted.get('message_id'),
            'sender': extracted.get('sender'),
            'recipient': extracted.get('recipient'),
            'subject': extracted.get('subject')
        }

        # Add thread context if available
        if extracted.get('thread_id'):
            context_data['external_thread_id'] = extracted['thread_id']

        return TriggerResult(
            success=True,
            should_execute=True,
            context_data=context_data
        )


class MessageReceivedHandler(BaseTriggerHandler):
    """Enhanced handler for multi-channel message triggers (WhatsApp, LinkedIn, SMS)"""

    def __init__(self):
        super().__init__()
        self.trigger_type = WorkflowTriggerType.MESSAGE_RECEIVED

    async def matches_event(self, trigger, event: TriggerEvent) -> bool:
        """Check if event matches message trigger criteria with channel filtering"""
        if event.event_type != 'message_received':
            return False

        trigger_config = trigger.configuration or {}
        event_data = event.event_data

        # Check channel filter
        monitor_channels = trigger_config.get('monitor_channels', [])
        if monitor_channels and 'all' not in monitor_channels:
            message_channel = event_data.get('channel', '').lower()
            if message_channel not in [ch.lower() for ch in monitor_channels]:
                return False

        # Check if monitoring specific accounts/numbers
        monitor_accounts = trigger_config.get('monitor_accounts', [])
        if monitor_accounts:
            # Different channels use different identifiers
            channel = event_data.get('channel', '').lower()
            identifier = None

            if channel == 'whatsapp':
                identifier = event_data.get('recipient_phone') or event_data.get('to_number')
            elif channel == 'linkedin':
                identifier = event_data.get('recipient_profile') or event_data.get('account_id')
            elif channel == 'sms':
                identifier = event_data.get('recipient_phone') or event_data.get('to_number')

            if identifier and identifier not in monitor_accounts:
                return False

        # Check if monitoring specific conversation/chat
        monitor_conversation = trigger_config.get('monitor_conversation_only', False)
        if monitor_conversation:
            required_chat_id = trigger_config.get('chat_id') or trigger_config.get('conversation_id')
            event_chat_id = event_data.get('chat_id') or event_data.get('conversation_id')
            if required_chat_id and event_chat_id != required_chat_id:
                return False

        # Check sender filters
        allowed_senders = trigger_config.get('allowed_senders', [])
        if allowed_senders:
            sender = event_data.get('sender', '') or event_data.get('from', '')
            if sender not in allowed_senders:
                return False

        return True

    async def extract_data(self, trigger, event: TriggerEvent) -> Dict[str, Any]:
        """Extract enhanced message data including conversation context"""
        event_data = event.event_data
        channel = event_data.get('channel', '').lower()

        # Extract conversation/thread information based on channel
        chat_id = None
        thread_id = None
        is_reply = False
        parent_message_id = None

        if channel == 'whatsapp':
            chat_id = event_data.get('chat_id')
            is_reply = bool(event_data.get('reply_to'))
            parent_message_id = event_data.get('reply_to')
        elif channel == 'linkedin':
            thread_id = event_data.get('thread_id') or event_data.get('conversation_urn')
            is_reply = bool(event_data.get('in_reply_to'))
            parent_message_id = event_data.get('in_reply_to')
        elif channel == 'sms':
            # SMS typically doesn't have thread concept, but may have conversation groups
            thread_id = event_data.get('conversation_id')

        return {
            'trigger_type': self.trigger_type,
            'timestamp': event.timestamp.isoformat(),
            'message_data': event_data,
            'sender': event_data.get('sender', '') or event_data.get('from', ''),
            'channel': channel,
            'message_type': event_data.get('message_type', 'text'),
            'content': event_data.get('content', '') or event_data.get('text', ''),
            'message_id': event_data.get('message_id', ''),
            'chat_id': chat_id,
            'thread_id': thread_id,
            'is_reply': is_reply,
            'parent_message_id': parent_message_id,
            'conversation_id': event_data.get('conversation_id'),
            'media_attachments': event_data.get('media', []),
            'channel_account': event_data.get('channel_account', '')
        }

    def get_supported_trigger_type(self) -> str:
        return WorkflowTriggerType.MESSAGE_RECEIVED

    async def handle(self, event: TriggerEvent, config: Dict[str, Any]) -> TriggerResult:
        """Handle message received trigger with enhanced context"""
        extracted = await self.extract_data(None, event)

        # Build comprehensive context for workflow
        context_data = {
            'trigger_type': 'message_received',
            'message_data': event.data,
            'channel': extracted.get('channel'),
            'chat_id': extracted.get('chat_id'),
            'thread_id': extracted.get('thread_id'),
            'is_reply': extracted.get('is_reply'),
            'parent_message_id': extracted.get('parent_message_id'),
            'conversation_id': extracted.get('conversation_id'),
            'message_id': extracted.get('message_id'),
            'sender': extracted.get('sender'),
            'content': extracted.get('content'),
            'media_attachments': extracted.get('media_attachments', [])
        }

        # Set external_thread_id based on channel
        if extracted.get('chat_id'):
            context_data['external_thread_id'] = extracted['chat_id']
        elif extracted.get('thread_id'):
            context_data['external_thread_id'] = extracted['thread_id']

        # Set last_sent_message_id if this is a reply
        if extracted.get('parent_message_id'):
            context_data['last_sent_message_id'] = extracted['parent_message_id']

        return TriggerResult(
            success=True,
            should_execute=True,
            context_data=context_data
        )