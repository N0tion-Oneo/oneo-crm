"""
Email Communication Node Processor - Send emails via UniPile
"""
import logging
from typing import Dict, Any
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class EmailProcessor(AsyncNodeProcessor):
    """Process email sending nodes via UniPile integration"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "UNIPILE_SEND_EMAIL"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process email sending node"""
        
        node_data = node_config.get('data', {})
        
        # Extract configuration with context formatting
        user_id = self._format_template(node_data.get('user_id', ''), context)
        recipient_email = self._format_template(node_data.get('recipient_email', ''), context)
        subject = self._format_template(node_data.get('subject', ''), context)
        content = self._format_template(node_data.get('content', ''), context)
        
        # Optional parameters
        tracking_enabled = node_data.get('tracking_enabled', True)
        sequence_metadata = node_data.get('sequence_metadata', {})
        attachments = node_data.get('attachments', [])

        # Thread/reply parameters
        reply_to_message_id = node_data.get('reply_to_message_id') or context.get('parent_message_id')
        thread_id = node_data.get('thread_id') or context.get('external_thread_id')
        conversation_id = node_data.get('conversation_id') or context.get('conversation_id')
        is_reply = node_data.get('is_reply', False) or bool(reply_to_message_id)
        
        # Validate required fields
        if not all([user_id, recipient_email, subject, content]):
            raise ValueError("Email node requires user_id, recipient_email, subject, and content")
        
        try:
            # Get user's email channel connection
            from communications.models import UserChannelConnection, ChannelType
            
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    user_id=user_id,
                    channel_type=ChannelType.EMAIL,
                    is_active=True,
                    auth_status='connected'
                ).first
            )()
            
            if not user_channel:
                raise ValueError('No active email channel found for user')
            
            # Check rate limits
            if not await self._check_rate_limits(user_channel):
                raise ValueError('Rate limit exceeded for email channel')
            
            # Send email via UniPile SDK
            result = await self._send_email_via_unipile(
                user_channel=user_channel,
                recipient=recipient_email,
                subject=subject,
                content=content,
                attachments=attachments,
                tracking_enabled=tracking_enabled,
                metadata=sequence_metadata,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
                conversation_id=conversation_id,
                is_reply=is_reply
            )
            
            if result['success']:
                # Log successful send for tracking
                await self._log_email_send(
                    user_channel=user_channel,
                    recipient=recipient_email,
                    subject=subject,
                    message_id=result.get('message_id'),
                    metadata=sequence_metadata
                )

                message_id = result.get('message_id')
                conversation_id = result.get('conversation_id')
                thread_id = result.get('thread_id')

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
                    'recipient': recipient_email,
                    'subject': subject,
                    'channel': user_channel.name,
                    'tracking_enabled': tracking_enabled,
                    'sent_at': timezone.now().isoformat()
                }
            else:
                raise ValueError(f"Email send failed: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipient': recipient_email,
                'subject': subject
            }
    
    async def _send_email_via_unipile(
        self,
        user_channel,
        recipient: str,
        subject: str,
        content: str,
        attachments: list = None,
        tracking_enabled: bool = True,
        metadata: dict = None,
        reply_to_message_id: str = None,
        thread_id: str = None,
        conversation_id: str = None,
        is_reply: bool = False
    ) -> Dict[str, Any]:
        """Send email via UniPile SDK"""
        
        try:
            from communications.unipile_sdk import unipile_service
            
            # Format content with subject for UniPile
            formatted_content = f"Subject: {subject}\n\n{content}"
            
            # Add tracking pixels if enabled
            if tracking_enabled:
                formatted_content = await self._add_tracking_pixels(formatted_content, metadata)

            # Build extra params for threading
            extra_params = {}
            if reply_to_message_id:
                extra_params['in_reply_to'] = reply_to_message_id
            if thread_id:
                extra_params['thread_id'] = thread_id
            if conversation_id:
                extra_params['conversation_id'] = conversation_id
            if is_reply:
                extra_params['is_reply'] = True
                # For email replies, we might want to prefix the subject
                if not subject.startswith('Re:'):
                    subject = f'Re: {subject}'
                    formatted_content = f"Subject: {subject}\n\n{content}"

            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient,
                content=formatted_content,
                message_type='email',
                attachments=attachments,
                extra_params=extra_params
            )
            
            return result
            
        except ImportError:
            # Fallback for development/testing
            logger.warning("UniPile SDK not available, simulating email send")
            return {
                'success': True,
                'message_id': f'dev_email_{timezone.now().timestamp()}',
                'external_message_id': f'ext_{timezone.now().timestamp()}'
            }
    
    async def _check_rate_limits(self, user_channel) -> bool:
        """Check if user channel is within rate limits"""
        
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
    
    async def _add_tracking_pixels(self, content: str, metadata: dict = None) -> str:
        """Add tracking pixels to email content"""
        
        if not metadata:
            return content
        
        # Generate tracking pixel URL
        tracking_params = {
            'workflow_id': metadata.get('workflow_id'),
            'sequence_name': metadata.get('sequence_name'),
            'step_number': metadata.get('step_number'),
            'timestamp': timezone.now().timestamp()
        }
        
        # Create tracking pixel (1x1 transparent image)
        tracking_pixel = f"""
        <img src="/api/v1/tracking/email/open?{self._build_query_string(tracking_params)}" 
             width="1" height="1" style="display:none;" />
        """
        
        # Add tracking pixel to HTML content
        if '<html>' in content.lower():
            # HTML email - add before closing body tag
            content = content.replace('</body>', f'{tracking_pixel}</body>')
        else:
            # Plain text email - add HTML section
            content += f'\n\n<div style="display:none;">{tracking_pixel}</div>'
        
        return content
    
    def _build_query_string(self, params: dict) -> str:
        """Build query string from parameters"""
        from urllib.parse import urlencode
        return urlencode(params)
    
    async def _log_email_send(
        self,
        user_channel,
        recipient: str,
        subject: str,
        message_id: str,
        metadata: dict = None
    ):
        """Log email send for analytics and tracking"""
        
        try:
            # This would integrate with the monitoring system
            # For now, just log the action
            logger.info(
                f"Email sent - Channel: {user_channel.name}, "
                f"Recipient: {recipient}, Subject: {subject}, "
                f"Message ID: {message_id}"
            )
            
            # Update channel statistics
            await sync_to_async(user_channel.increment_messages_sent)()
            
        except Exception as e:
            logger.warning(f"Failed to log email send: {e}")
    
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
        """Validate email node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields are present
        required_fields = ['user_id', 'recipient_email', 'subject', 'content']
        for field in required_fields:
            if not node_data.get(field):
                return False
        
        # Validate email format (basic check)
        recipient_email = self._format_template(node_data.get('recipient_email', ''), context)
        if '@' not in recipient_email:
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for email node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        checkpoint.update({
            'email_config': {
                'recipient': self._format_template(node_data.get('recipient_email', ''), context),
                'subject': self._format_template(node_data.get('subject', ''), context),
                'user_id': self._format_template(node_data.get('user_id', ''), context)
            },
            'tracking_enabled': node_data.get('tracking_enabled', True)
        })
        
        return checkpoint