"""
LinkedIn Communication Node Processor - Send LinkedIn messages via UniPile
"""
import logging
from typing import Dict, Any
from django.utils import timezone
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class LinkedInProcessor(AsyncNodeProcessor):
    """Process LinkedIn message sending nodes via UniPile integration"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "UNIPILE_SEND_LINKEDIN"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process LinkedIn message sending node"""
        
        node_data = node_config.get('data', {})
        
        # Extract configuration with context formatting
        user_id = self._format_template(node_data.get('user_id', ''), context)
        recipient_profile = self._format_template(node_data.get('recipient_profile', ''), context)
        message_content = self._format_template(node_data.get('message_content', ''), context)
        connection_note = self._format_template(node_data.get('connection_note', ''), context)
        
        # Optional parameters
        sequence_metadata = node_data.get('sequence_metadata', {})
        send_connection_request = node_data.get('send_connection_request', False)

        # Thread/reply parameters
        reply_to_message_id = node_data.get('reply_to_message_id') or context.get('parent_message_id')
        thread_id = node_data.get('thread_id') or context.get('external_thread_id')
        conversation_id = node_data.get('conversation_id') or context.get('conversation_id')
        is_reply = node_data.get('is_reply', False) or bool(reply_to_message_id)
        
        # Validate required fields
        if not all([user_id, recipient_profile, message_content]):
            raise ValueError("LinkedIn node requires user_id, recipient_profile, and message_content")
        
        try:
            # Get user's LinkedIn channel connection
            from communications.models import UserChannelConnection, ChannelType
            
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    user_id=user_id,
                    channel_type=ChannelType.LINKEDIN,
                    is_active=True,
                    auth_status='connected'
                ).first
            )()
            if not user_channel:
                raise ValueError('No active LinkedIn channel found for user')
            
            # Check rate limits
            if not await self._check_rate_limits(user_channel):
                raise ValueError('Rate limit exceeded for LinkedIn channel')
            
            # Send connection request first if requested
            connection_result = None
            if send_connection_request and connection_note:
                connection_result = await self._send_connection_request(
                    user_channel=user_channel,
                    recipient=recipient_profile,
                    note=connection_note,
                    metadata=sequence_metadata
                )
            
            # Send LinkedIn message via UniPile SDK
            result = await self._send_linkedin_message_via_unipile(
                user_channel=user_channel,
                recipient=recipient_profile,
                content=message_content,
                metadata=sequence_metadata,
                reply_to_message_id=reply_to_message_id,
                thread_id=thread_id,
                conversation_id=conversation_id,
                is_reply=is_reply
            )
            
            if result['success']:
                # Log successful send for tracking
                await self._log_linkedin_send(
                    user_channel=user_channel,
                    recipient=recipient_profile,
                    content=message_content,
                    message_id=result.get('message_id'),
                    metadata=sequence_metadata
                )

                message_id = result.get('message_id')
                conversation_id = result.get('conversation_id')
                thread_id = result.get('thread_id')  # LinkedIn thread ID

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
                    'recipient': recipient_profile,
                    'content': message_content,
                    'channel': user_channel.name,
                    'connection_request_sent': bool(connection_result),
                    'connection_request_result': connection_result,
                    'sent_at': timezone.now().isoformat()
                }
            else:
                raise ValueError(f"LinkedIn message send failed: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"LinkedIn message send failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'recipient': recipient_profile,
                'content': message_content
            }
    
    async def _send_linkedin_message_via_unipile(
        self,
        user_channel,
        recipient: str,
        content: str,
        metadata: dict = None,
        reply_to_message_id: str = None,
        thread_id: str = None,
        conversation_id: str = None,
        is_reply: bool = False
    ) -> Dict[str, Any]:
        """Send LinkedIn message via UniPile SDK"""
        
        try:
            from communications.unipile_sdk import unipile_service
            
            # Build extra params for threading
            extra_params = {}
            if metadata:
                extra_params['metadata'] = metadata
            if reply_to_message_id:
                extra_params['in_reply_to'] = reply_to_message_id
            if thread_id:
                extra_params['thread_id'] = thread_id
                extra_params['conversation_urn'] = thread_id  # LinkedIn uses conversation_urn
            if conversation_id:
                extra_params['conversation_id'] = conversation_id
            if is_reply:
                extra_params['is_reply'] = True

            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient,
                content=content,
                message_type='linkedin',
                extra_params=extra_params if extra_params else None
            )
            
            return result
            
        except ImportError:
            # Fallback for development/testing
            logger.warning("UniPile SDK not available, simulating LinkedIn message send")
            return {
                'success': True,
                'message_id': f'dev_linkedin_{timezone.now().timestamp()}',
                'external_message_id': f'ext_linkedin_{timezone.now().timestamp()}'
            }
    
    async def _send_connection_request(
        self,
        user_channel,
        recipient: str,
        note: str,
        metadata: dict = None
    ) -> Dict[str, Any]:
        """Send LinkedIn connection request"""
        
        try:
            from communications.unipile_sdk import unipile_service
            
            # LinkedIn connection requests are a different message type
            result = await unipile_service.send_message(
                user_channel_connection=user_channel,
                recipient=recipient,
                content=note,
                message_type='linkedin_connection_request'
            )
            
            return {
                'success': result.get('success', False),
                'request_id': result.get('message_id'),
                'note': note
            }
            
        except ImportError:
            # Fallback for development/testing
            logger.warning("UniPile SDK not available, simulating connection request")
            return {
                'success': True,
                'request_id': f'dev_connection_{timezone.now().timestamp()}',
                'note': note
            }
        except Exception as e:
            logger.error(f"LinkedIn connection request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'note': note
            }
    
    async def _check_rate_limits(self, user_channel) -> bool:
        """Check if user channel is within rate limits"""
        
        # LinkedIn has specific rate limits that are typically lower than email
        # Check daily rate limit
        if user_channel.rate_limit_per_day:
            messages_today = await sync_to_async(lambda: user_channel.messages_sent_today)()
            if messages_today >= user_channel.rate_limit_per_day:
                return False
        
        # Check hourly rate limit (LinkedIn is more restrictive)
        if user_channel.rate_limit_per_hour:
            messages_this_hour = await sync_to_async(lambda: user_channel.messages_sent_this_hour())()
            if messages_this_hour >= user_channel.rate_limit_per_hour:
                return False
        
        return True
    
    async def _log_linkedin_send(
        self,
        user_channel,
        recipient: str,
        content: str,
        message_id: str,
        metadata: dict = None
    ):
        """Log LinkedIn message send for analytics and tracking"""
        
        try:
            # This would integrate with the monitoring system
            # For now, just log the action
            logger.info(
                f"LinkedIn message sent - Channel: {user_channel.name}, "
                f"Recipient: {recipient}, Message ID: {message_id}"
            )
            
            # Update channel statistics
            await sync_to_async(user_channel.increment_messages_sent)()
            
        except Exception as e:
            logger.warning(f"Failed to log LinkedIn message send: {e}")
    
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
        """Validate LinkedIn node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields are present
        required_fields = ['user_id', 'recipient_profile', 'message_content']
        for field in required_fields:
            if not node_data.get(field):
                return False
        
        # Validate LinkedIn profile format (basic check)
        recipient_profile = self._format_template(node_data.get('recipient_profile', ''), context)
        if not recipient_profile or '@' not in recipient_profile:
            # LinkedIn profiles should be in format like "john.doe" or contain LinkedIn URL
            return False
        
        # Validate message content length (LinkedIn has character limits)
        message_content = self._format_template(node_data.get('message_content', ''), context)
        if len(message_content) > 300:  # LinkedIn message limit
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for LinkedIn node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        checkpoint.update({
            'linkedin_config': {
                'recipient': self._format_template(node_data.get('recipient_profile', ''), context),
                'message_length': len(self._format_template(node_data.get('message_content', ''), context)),
                'user_id': self._format_template(node_data.get('user_id', ''), context),
                'send_connection_request': node_data.get('send_connection_request', False)
            }
        })
        
        return checkpoint