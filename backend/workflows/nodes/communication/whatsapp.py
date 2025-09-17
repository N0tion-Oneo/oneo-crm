"""
WhatsApp Communication Node Processor - Send WhatsApp messages via UniPile
"""
import logging
from typing import Dict, Any
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class WhatsAppProcessor(AsyncNodeProcessor):
    """Process WhatsApp message sending nodes via UniPile integration"""

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
                "maxLength": 4096,
                "description": "Message content to send",
                "ui_hints": {
                    "widget": "textarea",
                    "rows": 5,
                    "placeholder": "Hi {{contact.name}}, your appointment is confirmed..."
                }
            },
            "user_id": {
                "type": "string",
                "description": "User ID for WhatsApp account",
                "ui_hints": {
                    "widget": "user_select",
                    "placeholder": "{{assigned_user.id}}"
                }
            },
            "message_type": {
                "type": "string",
                "enum": ["text", "image", "document", "audio", "video", "location", "contact"],
                "default": "text",
                "description": "Type of WhatsApp message",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "attachments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "url": {"type": "string", "format": "uri"},
                        "type": {"type": "string"}
                    }
                },
                "description": "File attachments",
                "ui_hints": {
                    "widget": "file_upload",
                    "show_when": {"message_type": ["image", "document", "audio", "video"]}
                }
            },
            "is_reply": {
                "type": "boolean",
                "default": False,
                "description": "Is this a reply to existing chat"
            },
            "reply_to_message_id": {
                "type": "string",
                "description": "Message ID to reply to",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{last_message.id}}",
                    "show_when": {"is_reply": True}
                }
            },
            "chat_id": {
                "type": "string",
                "description": "WhatsApp chat ID",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{conversation.chat_id}}",
                    "show_when": {"is_reply": True}
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
        self.node_type = "unipile_send_whatsapp"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process WhatsApp message sending node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Extract configuration with context formatting
        user_id = self._format_template(config.get('user_id', ''), context)
        recipient_phone = self._format_template(config.get('recipient_phone', ''), context)
        message_content = self._format_template(config.get('message_content', ''), context)

        # Optional parameters
        sequence_metadata = config.get('sequence_metadata', {})
        attachments = config.get('attachments', [])
        message_type = config.get('message_type', 'text')  # text, image, document, etc.

        # Thread/reply parameters
        reply_to_message_id = config.get('reply_to_message_id') or context.get('parent_message_id')
        chat_id = config.get('chat_id') or context.get('external_thread_id')
        conversation_id = config.get('conversation_id') or context.get('conversation_id')
        is_reply = config.get('is_reply', False) or bool(reply_to_message_id)
        
        # Validate required fields
        if not all([user_id, recipient_phone, message_content]):
            raise ValueError("WhatsApp node requires user_id, recipient_phone, and message_content")
        
        # Validate phone number format
        if not self._validate_phone_number(recipient_phone):
            raise ValueError("Invalid phone number format for WhatsApp")
        
        try:
            # Get user's WhatsApp channel connection
            from communications.models import UserChannelConnection, ChannelType
            
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    user_id=user_id,
                    channel_type=ChannelType.WHATSAPP,
                    is_active=True,
                    auth_status='connected'
                ).first
            )()
            
            if not user_channel:
                raise ValueError('No active WhatsApp channel found for user')
            
            # Check rate limits
            if not await self._check_rate_limits(user_channel):
                raise ValueError('Rate limit exceeded for WhatsApp channel')
            
            # Send WhatsApp message via UniPile SDK
            result = await self._send_whatsapp_message_via_unipile(
                user_channel=user_channel,
                recipient=recipient_phone,
                content=message_content,
                attachments=attachments,
                message_type=message_type,
                metadata=sequence_metadata,
                reply_to_message_id=reply_to_message_id,
                chat_id=chat_id,
                conversation_id=conversation_id,
                is_reply=is_reply
            )
            
            if result['success']:
                # Log successful send for tracking
                await self._log_whatsapp_send(
                    user_channel=user_channel,
                    recipient=recipient_phone,
                    content=message_content,
                    message_id=result.get('message_id'),
                    metadata=sequence_metadata
                )

                message_id = result.get('message_id')
                conversation_id = result.get('conversation_id')
                chat_id = result.get('chat_id')  # WhatsApp uses chat_id instead of thread_id

                # Update context with message and conversation info for downstream nodes
                if message_id:
                    context['last_sent_message_id'] = message_id
                if conversation_id:
                    context['conversation_id'] = conversation_id
                if chat_id:
                    context['external_thread_id'] = chat_id  # Store chat_id as external_thread_id

                return {
                    'success': True,
                    'message_id': message_id,
                    'external_message_id': result.get('external_message_id'),
                    'conversation_id': conversation_id,
                    'chat_id': chat_id,
                    'recipient': recipient_phone,
                    'content': message_content,
                    'channel': user_channel.name,
                    'message_type': message_type,
                    'attachments_count': len(attachments),
                    'sent_at': timezone.now().isoformat()
                }
            else:
                raise ValueError(f"WhatsApp message send failed: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"WhatsApp message send failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipient': recipient_phone,
                'content': message_content
            }
    
    async def _send_whatsapp_message_via_unipile(
        self,
        user_channel,
        recipient: str,
        content: str,
        attachments: list = None,
        message_type: str = 'text',
        metadata: dict = None,
        reply_to_message_id: str = None,
        chat_id: str = None,
        conversation_id: str = None,
        is_reply: bool = False
    ) -> Dict[str, Any]:
        """Send WhatsApp message via UniPile SDK"""
        
        try:
            from communications.unipile_sdk import unipile_service
            
            # Build extra params for threading and WhatsApp-specific options
            extra_params = {
                'whatsapp_message_type': message_type,
                'metadata': metadata
            }

            if reply_to_message_id:
                extra_params['reply_to'] = reply_to_message_id
            if chat_id:
                extra_params['chat_id'] = chat_id
            if conversation_id:
                extra_params['conversation_id'] = conversation_id
            if is_reply:
                extra_params['is_reply'] = True

            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient,
                content=content,
                message_type='whatsapp',
                attachments=attachments,
                extra_params=extra_params
            )
            
            return result
            
        except ImportError:
            # Fallback for development/testing
            logger.warning("UniPile SDK not available, simulating WhatsApp message send")
            return {
                'success': True,
                'message_id': f'dev_whatsapp_{timezone.now().timestamp()}',
                'external_message_id': f'ext_whatsapp_{timezone.now().timestamp()}'
            }
    
    def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format for WhatsApp"""
        
        # Remove common formatting characters
        cleaned_phone = phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
        
        # Basic validation - should be digits only and reasonable length
        if not cleaned_phone.isdigit():
            return False
        
        # WhatsApp typically requires country code, so minimum 10 digits
        if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
            return False
        
        return True
    
    async def _check_rate_limits(self, user_channel) -> bool:
        """Check if user channel is within rate limits"""
        
        # WhatsApp has specific rate limits from Meta/WhatsApp Business API
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
    
    async def _log_whatsapp_send(
        self,
        user_channel,
        recipient: str,
        content: str,
        message_id: str,
        metadata: dict = None
    ):
        """Log WhatsApp message send for analytics and tracking"""
        
        try:
            # This would integrate with the monitoring system
            # For now, just log the action
            logger.info(
                f"WhatsApp message sent - Channel: {user_channel.name}, "
                f"Recipient: {recipient}, Message ID: {message_id}"
            )
            
            # Update channel statistics
            await sync_to_async(user_channel.increment_messages_sent)()
            
        except Exception as e:
            logger.warning(f"Failed to log WhatsApp message send: {e}")
    
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
        """Validate WhatsApp node inputs"""
        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Check required fields are present
        required_fields = ['recipient_phone', 'message_content']
        for field in required_fields:
            if not config.get(field):
                return False

        # Validate phone number format
        recipient_phone = self._format_template(config.get('recipient_phone', ''), context)
        if not self._validate_phone_number(recipient_phone):
            return False

        # Validate message type
        message_type = config.get('message_type', 'text')
        valid_types = ['text', 'image', 'document', 'audio', 'video', 'location', 'contact']
        if message_type not in valid_types:
            return False

        # Validate attachments if present
        attachments = config.get('attachments', [])
        if not isinstance(attachments, list):
            return False

        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for WhatsApp node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})
        checkpoint.update({
            'whatsapp_config': {
                'recipient': self._format_template(config.get('recipient_phone', ''), context),
                'message_length': len(self._format_template(config.get('message_content', ''), context)),
                'user_id': self._format_template(config.get('user_id', ''), context),
                'message_type': config.get('message_type', 'text'),
                'attachments_count': len(config.get('attachments', []))
            }
        })

        return checkpoint