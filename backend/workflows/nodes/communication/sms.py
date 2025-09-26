"""
SMS Communication Node Processor - Send SMS messages via UniPile
"""
import logging
import re
from typing import Dict, Any
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class SMSProcessor(AsyncNodeProcessor):
    """Process SMS message sending nodes via UniPile integration"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["recipient_phone", "message_content"],
        "properties": {
            "recipient_phone": {
                "type": "string",
                "pattern": "^\\+?[1-9]\\d{1,14}$",
                "description": "Recipient phone number with country code",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{contact.phone}} or +1234567890"
                }
            },
            "message_content": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1600,
                "description": "SMS message content (max 1600 chars)",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 4,
                    "placeholder": "Your appointment is confirmed for {{appointment.date}}..."
                }
            },
            "user_id": {
                "type": "string",
                "description": "User ID for SMS account",
                "ui_hints": {
                    "widget": "user_select",
                    "placeholder": "{{assigned_user.id}}"
                }
            },
            "sender_id": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9]{0,11}$",
                "description": "Custom sender ID (max 11 chars)",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "COMPANY",
                    "help_text": "Alphanumeric sender ID if supported by provider"
                }
            },
            "conversation_id": {
                "type": "string",
                "description": "Conversation ID for threading",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{conversation.id}}",
                    "section": "advanced"
                }
            },
            "thread_id": {
                "type": "string",
                "description": "SMS thread ID",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{conversation.thread_id}}",
                    "section": "advanced"
                }
            },
            "sequence_metadata": {
                "type": "object",
                "description": "Metadata for sequence tracking",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 3,
                    "section": "advanced"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "unipile_send_sms"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process SMS message sending node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration with context formatting
        user_id = self.format_template(config.get('user_id', ''), context)
        recipient_phone = self.format_template(config.get('recipient_phone', ''), context)
        message_content = self.format_template(config.get('message_content', ''), context)

        # Optional parameters
        sequence_metadata = config.get('sequence_metadata', {})
        sender_id = config.get('sender_id', '')  # Custom sender ID if supported

        # Thread/reply parameters (SMS has limited threading support)
        conversation_id = config.get('conversation_id') or context.get('conversation_id')
        thread_id = config.get('thread_id') or context.get('external_thread_id')
        
        # Validate required fields
        if not all([user_id, recipient_phone, message_content]):
            raise ValueError("SMS node requires user_id, recipient_phone, and message_content")
        
        # Validate phone number format
        if not self._validate_phone_number(recipient_phone):
            raise ValueError("Invalid phone number format for SMS")
        
        # Validate message length (SMS has character limits)
        if len(message_content) > 1600:  # Multiple SMS segments limit
            raise ValueError("SMS message too long (max 1600 characters)")
        
        try:
            # Get user's SMS channel connection
            from communications.models import UserChannelConnection, ChannelType
            
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    user_id=user_id,
                    channel_type=ChannelType.SMS,
                    is_active=True,
                    auth_status='connected'
                ).first
            )()
            
            if not user_channel:
                raise ValueError('No active SMS channel found for user')
            
            # Check rate limits
            if not await self._check_rate_limits(user_channel):
                raise ValueError('Rate limit exceeded for SMS channel')
            
            # Send SMS via UniPile SDK
            result = await self._send_sms_via_unipile(
                user_channel=user_channel,
                recipient=recipient_phone,
                content=message_content,
                sender_id=sender_id,
                metadata=sequence_metadata,
                conversation_id=conversation_id,
                thread_id=thread_id
            )
            
            if result['success']:
                # Log successful send for tracking
                await self._log_sms_send(
                    user_channel=user_channel,
                    recipient=recipient_phone,
                    content=message_content,
                    message_id=result.get('message_id'),
                    metadata=sequence_metadata
                )

                # Calculate SMS segments
                segments = self._calculate_sms_segments(message_content)

                message_id = result.get('message_id')
                conversation_id = result.get('conversation_id')
                thread_id = result.get('thread_id')  # SMS conversation thread

                # Update context with message and conversation info for downstream nodes
                if message_id:
                    context['last_sent_message_id'] = message_id
                if conversation_id:
                    context['conversation_id'] = conversation_id
                if thread_id:
                    context['external_thread_id'] = thread_id

                return {
                    'success': True,
                    'message_id': message_id,
                    'external_message_id': result.get('external_message_id'),
                    'conversation_id': conversation_id,
                    'thread_id': thread_id,
                    'recipient': recipient_phone,
                    'content': message_content,
                    'channel': user_channel.name,
                    'sender_id': sender_id or user_channel.sender_id,
                    'segments_count': segments,
                    'character_count': len(message_content),
                    'sent_at': timezone.now().isoformat()
                }
            else:
                raise ValueError(f"SMS send failed: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipient': recipient_phone,
                'content': message_content
            }
    
    async def _send_sms_via_unipile(
        self,
        user_channel,
        recipient: str,
        content: str,
        sender_id: str = '',
        metadata: dict = None,
        conversation_id: str = None,
        thread_id: str = None
    ) -> Dict[str, Any]:
        """Send SMS via UniPile SDK"""
        
        try:
            from communications.unipile_sdk import unipile_service
            
            extra_params = {}
            if sender_id:
                extra_params['sender_id'] = sender_id
            if metadata:
                extra_params['metadata'] = metadata
            if conversation_id:
                extra_params['conversation_id'] = conversation_id
            if thread_id:
                extra_params['thread_id'] = thread_id
            
            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient,
                content=content,
                message_type='sms',
                extra_params=extra_params
            )
            
            return result
            
        except ImportError:
            # Fallback for development/testing
            logger.warning("UniPile SDK not available, simulating SMS send")
            return {
                'success': True,
                'message_id': f'dev_sms_{timezone.now().timestamp()}',
                'external_message_id': f'ext_sms_{timezone.now().timestamp()}'
            }
    
    def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format for SMS"""
        
        # Remove common formatting characters
        cleaned_phone = phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        # Basic validation - should be digits only and reasonable length
        if not cleaned_phone.isdigit():
            return False
        
        # SMS typically requires country code, so minimum 10 digits
        if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
            return False
        
        return True
    
    def _calculate_sms_segments(self, content: str) -> int:
        """Calculate number of SMS segments needed"""
        
        # GSM 7-bit encoding characters
        gsm_chars = set("@£$¥èéùìòÇ\\nØø\\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\\\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
        
        # Check if message can use GSM 7-bit encoding
        can_use_gsm = all(c in gsm_chars for c in content)
        
        if can_use_gsm:
            # GSM 7-bit: 160 chars per segment, 153 for multi-part
            if len(content) <= 160:
                return 1
            else:
                return (len(content) - 1) // 153 + 1
        else:
            # UCS-2 encoding: 70 chars per segment, 67 for multi-part
            if len(content) <= 70:
                return 1
            else:
                return (len(content) - 1) // 67 + 1
    
    async def _check_rate_limits(self, user_channel) -> bool:
        """Check if user channel is within rate limits"""
        
        # SMS has different rate limits depending on provider
        # Check daily rate limit
        if user_channel.rate_limit_per_day:
            messages_today = await sync_to_async(lambda: user_channel.messages_sent_today)()
            if messages_today >= user_channel.rate_limit_per_day:
                return False
        
        # Check hourly rate limit
        if user_channel.rate_limit_per_hour:
            messages_this_hour = await sync_to_async(lambda: user_channel.messages_sent_this_hour())()
            if messages_this_hour >= user_channel.rate_limit_per_hour:
                return False
        
        return True
    
    async def _log_sms_send(
        self,
        user_channel,
        recipient: str,
        content: str,
        message_id: str,
        metadata: dict = None
    ):
        """Log SMS send for analytics and tracking"""
        
        try:
            segments = self._calculate_sms_segments(content)
            
            # This would integrate with the monitoring system
            # For now, just log the action
            logger.info(
                f"SMS sent - Channel: {user_channel.name}, "
                f"Recipient: {recipient}, Message ID: {message_id}, "
                f"Segments: {segments}"
            )
            
            # Update channel statistics (count segments for cost tracking)
            await sync_to_async(user_channel.increment_messages_sent)(segments)
            
        except Exception as e:
            logger.warning(f"Failed to log SMS send: {e}")
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template string with context variables"""
        if not template:
            return ''
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate SMS node inputs"""
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Check required fields are present
        required_fields = ['recipient_phone', 'message_content']
        for field in required_fields:
            if not config.get(field):
                return False

        # Validate phone number format
        recipient_phone = self.format_template(config.get('recipient_phone', ''), context)
        if not self._validate_phone_number(recipient_phone):
            return False

        # Validate message length
        message_content = self.format_template(config.get('message_content', ''), context)
        if len(message_content) > 1600:  # Reasonable limit for SMS
            return False

        # Validate sender ID if provided (alphanumeric, max 11 chars)
        sender_id = config.get('sender_id', '')
        if sender_id:
            if len(sender_id) > 11 or not re.match(r'^[a-zA-Z0-9]+$', sender_id):
                return False

        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for SMS node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})
        message_content = self.format_template(config.get('message_content', ''), context)

        checkpoint.update({
            'sms_config': {
                'recipient': self.format_template(config.get('recipient_phone', ''), context),
                'message_length': len(message_content),
                'user_id': self.format_template(config.get('user_id', ''), context),
                'sender_id': config.get('sender_id', ''),
                'segments_count': self._calculate_sms_segments(message_content)
            }
        })

        return checkpoint