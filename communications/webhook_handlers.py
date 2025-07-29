"""
Webhook Handlers for Real-time Communication Processing
Handles UniPile webhooks and automatic contact resolution
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from tenants.models import TenantUniPileConfig
from .models import (
    UserChannelConnection, Conversation, Message, 
    MessageDirection, MessageStatus, ChannelType
)
from .contact_resolver import contact_resolver
from .services import communication_service

logger = logging.getLogger(__name__)
User = get_user_model()


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_http_methods(["POST"]), name='dispatch')
class UniPileWebhookView(View):
    """Handle UniPile webhook events"""
    
    async def post(self, request):
        """Process UniPile webhook payload"""
        
        try:
            # Parse webhook payload
            payload = json.loads(request.body)
            event_type = payload.get('event_type')
            
            if not event_type:
                return HttpResponseBadRequest('Missing event_type')
            
            # Verify webhook signature
            signature_valid = await self._verify_webhook_signature(request, payload)
            if not signature_valid:
                logger.warning("Invalid webhook signature")
                return HttpResponseBadRequest('Invalid signature')
            
            # Route to appropriate handler
            if event_type == 'message.received':
                result = await self._handle_message_received(payload)
            elif event_type == 'message.sent':
                result = await self._handle_message_sent(payload)
            elif event_type == 'message.delivered':
                result = await self._handle_message_delivered(payload)
            elif event_type == 'message.read':
                result = await self._handle_message_read(payload)
            elif event_type == 'account.connected':
                result = await self._handle_account_connected(payload)
            elif event_type == 'account.disconnected':
                result = await self._handle_account_disconnected(payload)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return HttpResponse('Event type not supported', status=200)
            
            if result.get('success'):
                return HttpResponse('OK', status=200)
            else:
                logger.error(f"Webhook processing failed: {result.get('error')}")
                return HttpResponse('Processing failed', status=500)
                
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON payload')
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return HttpResponse('Internal server error', status=500)
    
    async def _verify_webhook_signature(self, request, payload: Dict[str, Any]) -> bool:
        """Verify UniPile webhook signature"""
        
        try:
            import hmac
            import hashlib
            
            # Get signature from headers
            signature = request.headers.get('X-UniPile-Signature')
            if not signature:
                return False
            
            # Find tenant config by account ID
            account_id = payload.get('account_id')
            if not account_id:
                return False
            
            # Get user channel connection to find tenant
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    unipile_account_id=account_id
                ).first
            )()
            
            if not user_channel:
                logger.warning(f"No user channel found for account_id: {account_id}")
                return False
            
            # Get tenant config
            tenant_config = user_channel.get_tenant_config()
            if not tenant_config:
                return False
            
            # Calculate expected signature
            webhook_secret = tenant_config.webhook_secret
            if not webhook_secret:
                return False
            
            payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            expected_signature = hmac.new(
                webhook_secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, f'sha256={expected_signature}')
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    async def _handle_message_received(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming message webhook"""
        
        try:
            account_id = payload.get('account_id')
            message_data = payload.get('message', {})
            
            # Find user channel connection
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    unipile_account_id=account_id,
                    is_active=True
                ).first
            )()
            
            if not user_channel:
                return {
                    'success': False,
                    'error': f'No active channel found for account_id: {account_id}'
                }
            
            # Process the message
            result = await self._process_inbound_message(user_channel, message_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle message received: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_message_sent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outbound message confirmation webhook"""
        
        try:
            message_id = payload.get('message', {}).get('id')
            if not message_id:
                return {'success': False, 'error': 'Missing message ID'}
            
            # Find and update local message record
            message = await sync_to_async(
                Message.objects.filter(
                    external_message_id=message_id
                ).first
            )()
            
            if message:
                message.status = MessageStatus.SENT
                message.sent_at = datetime.now(timezone.utc)
                await sync_to_async(message.save)()
                
                # Broadcast real-time update
                await self._broadcast_message_update(message, 'sent')
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to handle message sent: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_message_delivered(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message delivery confirmation webhook"""
        
        try:
            message_id = payload.get('message', {}).get('id')
            if not message_id:
                return {'success': False, 'error': 'Missing message ID'}
            
            # Find and update local message record
            message = await sync_to_async(
                Message.objects.filter(
                    external_message_id=message_id
                ).first
            )()
            
            if message:
                message.status = MessageStatus.DELIVERED
                message.delivered_at = datetime.now(timezone.utc)
                await sync_to_async(message.save)()
                
                # Broadcast real-time update
                await self._broadcast_message_update(message, 'delivered')
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to handle message delivered: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_message_read(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message read confirmation webhook"""
        
        try:
            message_id = payload.get('message', {}).get('id')
            if not message_id:
                return {'success': False, 'error': 'Missing message ID'}
            
            # Find and update local message record
            message = await sync_to_async(
                Message.objects.filter(
                    external_message_id=message_id
                ).first
            )()
            
            if message:
                message.status = MessageStatus.READ
                message.read_at = datetime.now(timezone.utc)
                await sync_to_async(message.save)()
                
                # Broadcast real-time update
                await self._broadcast_message_update(message, 'read')
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to handle message read: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_account_connected(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account connection webhook"""
        
        try:
            account_id = payload.get('account_id')
            provider = payload.get('provider')
            
            # Find user channel connection
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    unipile_account_id=account_id
                ).first
            )()
            
            if user_channel:
                user_channel.auth_status = 'connected'
                user_channel.provider_config = payload.get('config', {})
                await sync_to_async(user_channel.save)()
                
                logger.info(f"Account {account_id} connected for user {user_channel.user.email}")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to handle account connected: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_account_disconnected(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account disconnection webhook"""
        
        try:
            account_id = payload.get('account_id')
            
            # Find user channel connection
            user_channel = await sync_to_async(
                UserChannelConnection.objects.filter(
                    unipile_account_id=account_id
                ).first
            )()
            
            if user_channel:
                user_channel.auth_status = 'disconnected'
                await sync_to_async(user_channel.save)()
                
                logger.info(f"Account {account_id} disconnected for user {user_channel.user.email}")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to handle account disconnected: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _process_inbound_message(
        self,
        user_channel: UserChannelConnection,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process inbound message and create records"""
        
        try:
            # Resolve or create contact
            contact_result = await contact_resolver.resolve_contact_from_message(
                message_data=message_data,
                user_channel=user_channel,
                direction='inbound'
            )
            
            # Get or create conversation
            conversation = await self._get_or_create_conversation(
                user_channel=user_channel,
                message_data=message_data,
                contact_record=contact_result.get('contact_record')
            )
            
            # Create message record
            message = await self._create_message_record(
                conversation=conversation,
                message_data=message_data,
                direction=MessageDirection.INBOUND,
                contact_result=contact_result
            )
            
            # Analyze message with AI if enabled
            if user_channel.get_tenant_config():
                await self._analyze_message_with_ai(message)
            
            # Broadcast real-time update
            await self._broadcast_message_update(message, 'received')
            
            # Trigger any response workflows
            await self._trigger_response_workflows(message, conversation)
            
            return {
                'success': True,
                'message_id': str(message.id),
                'conversation_id': str(conversation.id),
                'contact_resolved': contact_result.get('success', False),
                'contact_created': contact_result.get('created', False)
            }
            
        except Exception as e:
            logger.error(f"Failed to process inbound message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_or_create_conversation(
        self,
        user_channel: UserChannelConnection,
        message_data: Dict[str, Any],
        contact_record: Optional[Any] = None
    ) -> Conversation:
        """Get or create conversation for message"""
        
        thread_id = message_data.get('thread_id')
        
        # Try to find existing conversation by thread ID
        if thread_id:
            conversation = await sync_to_async(
                Conversation.objects.filter(
                    user_channel=user_channel,
                    external_thread_id=thread_id
                ).first
            )()
            
            if conversation:
                return conversation
        
        # Extract participants from message
        participants = []
        sender = message_data.get('sender', {})
        
        if sender:
            participant = {}
            if sender.get('email'):
                participant['email'] = sender['email']
            if sender.get('name'):
                participant['name'] = sender['name']
            if sender.get('phone'):
                participant['phone'] = sender['phone']
            
            if participant:
                participants.append(participant)
        
        # Create new conversation
        conversation = await sync_to_async(Conversation.objects.create)(
            user_channel=user_channel,
            external_thread_id=thread_id,
            participants=participants,
            subject=message_data.get('subject') or f"Conversation via {user_channel.channel_type}",
            primary_contact=contact_record,
            status='active'
        )
        
        return conversation
    
    async def _create_message_record(
        self,
        conversation: Conversation,
        message_data: Dict[str, Any],
        direction: str,
        contact_result: Dict[str, Any]
    ) -> Message:
        """Create message record in database"""
        
        sender = message_data.get('sender', {})
        
        message = await sync_to_async(Message.objects.create)(
            conversation=conversation,
            external_message_id=message_data.get('id'),
            thread_id=message_data.get('thread_id'),
            content=message_data.get('content', ''),
            content_type=message_data.get('content_type', 'text'),
            direction=direction,
            message_type=message_data.get('type', 'message'),
            sender_email=sender.get('email'),
            sender_name=sender.get('name'),
            sender_phone=sender.get('phone'),
            recipient_info=message_data.get('recipients', {}),
            status=MessageStatus.DELIVERED,  # Inbound messages are delivered
            attachments=message_data.get('attachments', []),
            sent_at=self._parse_datetime(message_data.get('timestamp')),
            delivered_at=datetime.now(timezone.utc)
        )
        
        # Update conversation counters
        conversation.last_message_at = message.created_at
        conversation.last_inbound_at = message.created_at
        conversation.message_count += 1
        await sync_to_async(conversation.save)()
        
        return message
    
    async def _analyze_message_with_ai(self, message: Message):
        """Analyze message content with AI"""
        
        try:
            from workflows.ai_integration import workflow_ai_processor
            from django.db import connection
            
            tenant = connection.tenant
            if not tenant.can_use_ai_features():
                return
            
            # Analyze sentiment
            sentiment_result = await workflow_ai_processor.process_ai_field_async(
                record_data={'message_content': message.content},
                field_config={
                    'ai_prompt': f'Analyze the sentiment of this message and return only: positive, negative, or neutral. Message: {message.content}',
                    'ai_model': 'gpt-4',
                    'temperature': 0.1,
                    'max_tokens': 10
                },
                tenant=tenant,
                user=None
            )
            
            message.sentiment = sentiment_result.get('content', '').strip().lower()
            
            # Analyze intent
            intent_result = await workflow_ai_processor.process_ai_field_async(
                record_data={'message_content': message.content},
                field_config={
                    'ai_prompt': f'Determine the intent of this message. Choose from: question, complaint, request, compliment, support, purchase, other. Return only the intent. Message: {message.content}',
                    'ai_model': 'gpt-4',
                    'temperature': 0.1,
                    'max_tokens': 20
                },
                tenant=tenant,
                user=None
            )
            
            message.intent = intent_result.get('content', '').strip().lower()
            
            await sync_to_async(message.save)()
            
        except Exception as e:
            logger.error(f"AI message analysis failed: {e}")
    
    async def _broadcast_message_update(self, message: Message, event_type: str):
        """Broadcast real-time message update"""
        
        try:
            from channels.layers import get_channel_layer
            
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Broadcast to conversation group
            await channel_layer.group_send(
                f"conversation_{message.conversation_id}",
                {
                    'type': 'message_update',
                    'event': event_type,
                    'message': {
                        'id': str(message.id),
                        'content': message.content,
                        'direction': message.direction,
                        'sender_name': message.sender_name,
                        'sender_email': message.sender_email,
                        'status': message.status,
                        'created_at': message.created_at.isoformat(),
                        'sent_at': message.sent_at.isoformat() if message.sent_at else None,
                        'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
                        'read_at': message.read_at.isoformat() if message.read_at else None,
                        'sentiment': message.sentiment,
                        'intent': message.intent
                    }
                }
            )
            
            # Broadcast to user notifications
            if message.conversation.user_channel:
                await channel_layer.group_send(
                    f"user_{message.conversation.user_channel.user_id}",
                    {
                        'type': 'notification',
                        'notification': {
                            'type': 'new_message',
                            'title': f'New message from {message.sender_name or message.sender_email}',
                            'message': message.content[:100],
                            'conversation_id': str(message.conversation_id),
                            'timestamp': message.created_at.isoformat()
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to broadcast message update: {e}")
    
    async def _trigger_response_workflows(self, message: Message, conversation: Conversation):
        """Trigger any automated response workflows"""
        
        try:
            from workflows.models import Workflow, WorkflowTriggerType
            from workflows.engine import workflow_engine
            
            # Find workflows triggered by message received
            workflows = await sync_to_async(list)(
                Workflow.objects.filter(
                    status='active',
                    trigger_type=WorkflowTriggerType.RECORD_CREATED,
                    trigger_config__event_type='message_received'
                )
            )
            
            for workflow in workflows:
                try:
                    # Prepare trigger data
                    trigger_data = {
                        'message_id': str(message.id),
                        'conversation_id': str(conversation.id),
                        'contact_id': str(conversation.primary_contact.id) if conversation.primary_contact else None,
                        'message_content': message.content,
                        'sender_email': message.sender_email,
                        'sender_name': message.sender_name,
                        'channel_type': conversation.get_channel_type(),
                        'sentiment': message.sentiment,
                        'intent': message.intent
                    }
                    
                    # Execute workflow asynchronously
                    await workflow_engine.execute_workflow(
                        workflow=workflow,
                        trigger_data=trigger_data,
                        triggered_by=conversation.user_channel.user
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to execute response workflow {workflow.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to trigger response workflows: {e}")
    
    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """Parse datetime string"""
        
        if not dt_string:
            return None
        
        try:
            # Handle various datetime formats
            if dt_string.endswith('Z'):
                dt_string = dt_string[:-1] + '+00:00'
            
            return datetime.fromisoformat(dt_string)
        except ValueError:
            try:
                # Fallback to timestamp
                return datetime.fromtimestamp(float(dt_string), tz=timezone.utc)
            except (ValueError, TypeError):
                logger.warning(f"Failed to parse datetime: {dt_string}")
                return None


# URL pattern for webhook
unipile_webhook_view = UniPileWebhookView.as_view()