"""
Celery tasks for Communication System
Handles background processing for messaging and channel synchronization
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django_tenants.utils import schema_context
from asgiref.sync import async_to_sync

from .models import (
    Channel, Message, CommunicationAnalytics, UserChannelConnection
)
from .unipile_sdk import unipile_service
from .message_sync import message_sync_service

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=2)
def sync_channel_messages(self, channel_id: str, tenant_schema: str):
    """
    Sync messages from a specific channel via UniPile
    """
    try:
        with schema_context(tenant_schema):
            channel = Channel.objects.get(id=channel_id)
            
            logger.info(f"Syncing messages for channel {channel.name} ({channel_id})")
            
            # Use async UniPile service to sync messages
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    unipile_service.sync_account_messages(
                        account_id=channel.external_account_id,
                        channel_id=channel_id
                    )
                )
                
                logger.info(f"Synced {result.get('message_count', 0)} messages for channel {channel.name}")
                return result
                
            finally:
                loop.close()
                
    except Channel.DoesNotExist:
        logger.error(f"Channel {channel_id} not found in schema {tenant_schema}")
        return {'error': 'Channel not found'}
        
    except Exception as e:
        logger.error(f"Message sync failed for channel {channel_id}: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))


@shared_task
def generate_daily_analytics(tenant_schema: str, date: str = None):
    """
    Generate daily communication analytics for a tenant
    """
    try:
        with schema_context(tenant_schema):
            target_date = datetime.fromisoformat(date) if date else django_timezone.now().date()
            
            logger.info(f"Generating analytics for {tenant_schema} on {target_date}")
            
            # Calculate message statistics
            messages_sent = Message.objects.filter(
                created_at__date=target_date,
                direction='outbound'
            ).count()
            
            messages_received = Message.objects.filter(
                created_at__date=target_date,
                direction='inbound'
            ).count()
            
            # Calculate channel activity
            active_channels = Channel.objects.filter(
                is_active=True,
                messages__created_at__date=target_date
            ).distinct().count()
            
            # Create or update analytics record
            analytics, created = CommunicationAnalytics.objects.get_or_create(
                date=target_date,
                defaults={
                    'messages_sent': messages_sent,
                    'messages_received': messages_received,
                    'active_channels': active_channels,
                    'response_rate': 0.0,  # Calculate based on your business logic
                    'engagement_score': 0.0,  # Calculate based on your business logic
                    'metadata': {
                        'generated_at': django_timezone.now().isoformat(),
                        'tenant_schema': tenant_schema
                    }
                }
            )
            
            if not created:
                # Update existing record
                analytics.messages_sent = messages_sent
                analytics.messages_received = messages_received
                analytics.active_channels = active_channels
                analytics.save()
            
            logger.info(f"Analytics generated: {messages_sent} sent, {messages_received} received, {active_channels} active channels")
            
            return {
                'date': str(target_date),
                'messages_sent': messages_sent,
                'messages_received': messages_received,
                'active_channels': active_channels,
                'created': created
            }
            
    except Exception as e:
        logger.error(f"Analytics generation failed for {tenant_schema}: {e}")
        raise


@shared_task
def sync_all_channels(tenant_schema: str):
    """
    Sync messages for all active channels in a tenant
    """
    try:
        with schema_context(tenant_schema):
            active_channels = Channel.objects.filter(is_active=True)
            
            logger.info(f"Syncing {len(active_channels)} channels for tenant {tenant_schema}")
            
            results = []
            for channel in active_channels:
                try:
                    # Queue individual sync tasks
                    sync_channel_messages.delay(str(channel.id), tenant_schema)
                    results.append({'channel_id': str(channel.id), 'status': 'queued'})
                except Exception as e:
                    logger.error(f"Failed to queue sync for channel {channel.id}: {e}")
                    results.append({'channel_id': str(channel.id), 'status': 'failed', 'error': str(e)})
            
            return {
                'tenant_schema': tenant_schema,
                'channels_processed': len(results),
                'results': results
            }
            
    except Exception as e:
        logger.error(f"Channel sync failed for {tenant_schema}: {e}")
        raise


@shared_task
def send_scheduled_message(
    message_data: Dict[str, Any],
    tenant_schema: str,
    channel_id: str
):
    """
    Send a scheduled message through a specific channel
    """
    try:
        with schema_context(tenant_schema):
            channel = Channel.objects.get(id=channel_id)
            
            logger.info(f"Sending scheduled message via {channel.name}")
            
            # Use async UniPile service to send message
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    unipile_service.send_message(
                        account_id=channel.external_account_id,
                        message_data=message_data
                    )
                )
                
                # Create message record
                message = Message.objects.create(
                    channel=channel,
                    external_message_id=result.get('message_id'),
                    content=message_data.get('content', ''),
                    direction='outbound',
                    status='sent',
                    metadata={
                        'scheduled': True,
                        'sent_at': django_timezone.now().isoformat(),
                        'unipile_result': result
                    }
                )
                
                logger.info(f"Scheduled message sent successfully: {message.id}")
                return {'message_id': str(message.id), 'status': 'sent'}
                
            finally:
                loop.close()
                
    except Channel.DoesNotExist:
        logger.error(f"Channel {channel_id} not found in schema {tenant_schema}")
        return {'error': 'Channel not found'}
        
    except Exception as e:
        logger.error(f"Scheduled message send failed: {e}")
        raise


# New message sync tasks

@shared_task(bind=True, max_retries=3)
def sync_account_messages_task(self, connection_id: str, initial_sync: bool = False, days_back: int = 30):
    """
    Celery task to sync messages for a specific account connection
    
    Args:
        connection_id: UUID of the UserChannelConnection
        initial_sync: Whether this is an initial sync
        days_back: Days to sync back for initial sync
    """
    try:
        # Get the connection
        connection = UserChannelConnection.objects.get(id=connection_id)
        
        # Run the sync
        result = async_to_sync(message_sync_service.sync_account_messages)(
            connection,
            initial_sync=initial_sync,
            days_back=days_back
        )
        
        if result['success']:
            logger.info(f"Successfully synced messages for connection {connection_id}: "
                       f"{result['messages_synced']} messages, {result['conversations_synced']} conversations")
            return result
        else:
            logger.error(f"Failed to sync messages for connection {connection_id}: {result['error']}")
            # Retry the task
            raise self.retry(countdown=60 * (2 ** self.request.retries))
    
    except UserChannelConnection.DoesNotExist:
        logger.error(f"Connection {connection_id} not found")
        return {'success': False, 'error': f'Connection {connection_id} not found'}
    
    except Exception as e:
        logger.error(f"Error in sync_account_messages_task for {connection_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)


@shared_task(bind=True)
def sync_all_active_connections_task(self, initial_sync: bool = False, days_back: int = 30):
    """
    Celery task to sync messages for all active connections across all tenants
    
    This task handles multi-tenant execution by iterating through all tenants
    """
    try:
        # Import here to avoid circular imports
        from django_tenants.utils import get_tenant_model, get_public_schema_name
        from django.db import connection
        
        tenant_model = get_tenant_model()
        tenants = tenant_model.objects.exclude(schema_name=get_public_schema_name())
        
        total_results = {
            'tenants_processed': 0,
            'total_connections': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'tenant_results': []
        }
        
        for tenant in tenants:
            try:
                # Switch to tenant schema
                connection.set_tenant(tenant)
                
                # Sync all connections for this tenant
                result = async_to_sync(message_sync_service.sync_all_active_connections)(
                    initial_sync=initial_sync,
                    days_back=days_back
                )
                
                total_results['tenants_processed'] += 1
                total_results['total_connections'] += result['total_connections']
                total_results['successful_syncs'] += result['successful_syncs']
                total_results['failed_syncs'] += result['failed_syncs']
                
                total_results['tenant_results'].append({
                    'tenant_name': tenant.name,
                    'schema_name': tenant.schema_name,
                    'result': result
                })
                
                logger.info(f"Synced tenant {tenant.name}: {result['successful_syncs']}/{result['total_connections']} connections")
                
            except Exception as e:
                logger.error(f"Failed to sync tenant {tenant.name}: {e}")
                total_results['tenant_results'].append({
                    'tenant_name': tenant.name,
                    'schema_name': tenant.schema_name,
                    'result': {'success': False, 'error': str(e)}
                })
        
        logger.info(f"Completed sync for all tenants: {total_results['successful_syncs']}/{total_results['total_connections']} total connections")
        return total_results
    
    except Exception as e:
        logger.error(f"Error in sync_all_active_connections_task: {e}")
        raise
    
    finally:
        # Switch back to public schema
        try:
            public_tenant = tenant_model.objects.get(schema_name=get_public_schema_name())
            connection.set_tenant(public_tenant)
        except Exception as e:
            logger.error(f"Failed to switch back to public schema: {e}")


@shared_task(bind=True)
def periodic_message_sync_task(self):
    """
    Periodic task to sync messages for all active connections
    This should be run every 5-15 minutes via Celery Beat
    """
    try:
        logger.info("Starting periodic message sync")
        
        # Sync all active connections (not initial sync, just recent messages)
        task_result = sync_all_active_connections_task.delay(
            initial_sync=False,
            days_back=1  # Only sync last day for periodic sync
        )
        
        logger.info(f"Periodic sync task scheduled: {task_result.id}")
        return {
            'success': True, 
            'task_id': task_result.id,
            'message': 'Periodic sync task scheduled successfully'
        }
    
    except Exception as e:
        logger.error(f"Error in periodic_message_sync_task: {e}")
        raise


@shared_task(bind=True)
def initial_sync_new_connection_task(self, connection_id: str, days_back: int = 30):
    """
    Task to perform initial sync for a newly connected account
    
    Args:
        connection_id: UUID of the UserChannelConnection
        days_back: Days to sync back for initial sync
    """
    try:
        logger.info(f"Starting initial sync for new connection {connection_id}")
        
        # Run initial sync with more messages
        result = sync_account_messages_task.delay(
            connection_id=connection_id,
            initial_sync=True,
            days_back=days_back
        ).get()
        
        if result['success']:
            logger.info(f"Initial sync completed for connection {connection_id}: "
                       f"{result['messages_synced']} messages synced")
        else:
            logger.error(f"Initial sync failed for connection {connection_id}: {result['error']}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error in initial_sync_new_connection_task for {connection_id}: {e}")
        raise


# Real-time WhatsApp enhancement tasks

@shared_task(bind=True, max_retries=3)
def fetch_contact_profile_picture(self, account_id: str, attendee_id: str, contact_email: str):
    """
    Fetch contact profile picture from UniPile API and broadcast update
    """
    try:
        from communications.unipile_sdk import unipile_service
        from django.core.cache import cache
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        # Fetch profile picture from UniPile API  
        picture_response = client.request.get(f'chat_attendees/{attendee_id}/picture')
        
        if picture_response:
            # Cache the profile picture for quick access
            cache_key = f"profile_picture:{contact_email}"
            cache.set(cache_key, picture_response, timeout=86400)  # 24 hours
            
            # Broadcast real-time update to frontend
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"channel_{account_id}",
                    {
                        'type': 'contact_profile_updated',
                        'contact': {
                            'email': contact_email,
                            'attendee_id': attendee_id,
                            'has_profile_picture': True,
                            'profile_picture_url': f'/api/v1/contacts/{contact_email}/picture/'
                        }
                    }
                )
            
            logger.info(f"Fetched and cached profile picture for {contact_email}")
            return {'success': True, 'contact_email': contact_email}
            
    except Exception as e:
        logger.error(f"Failed to fetch profile picture for {contact_email}: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def process_message_attachment(self, account_id: str, message_id: str, attachment_id: str, attachment_type: str, attachment_name: str):
    """
    Download and process message attachment from UniPile API
    """
    try:
        from communications.unipile_sdk import unipile_service
        from django.core.cache import cache
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        # Download attachment from UniPile API
        attachment_data = client.request.get(f'messages/{message_id}/attachments/{attachment_id}')
        
        if attachment_data:
            # Store attachment metadata and broadcast update
            attachment_info = {
                'id': attachment_id,
                'name': attachment_name,
                'type': attachment_type,
                'size': len(attachment_data) if isinstance(attachment_data, bytes) else 0,
                'download_url': f'/api/v1/messages/{message_id}/attachments/{attachment_id}/',
                'processed_at': django_timezone.now().isoformat()
            }
            
            # Cache attachment for quick access
            cache_key = f"attachment:{message_id}:{attachment_id}"
            cache.set(cache_key, attachment_data, timeout=3600)  # 1 hour
            
            # Broadcast real-time attachment ready notification
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"channel_{account_id}",
                    {
                        'type': 'attachment_ready',
                        'message_id': message_id,
                        'attachment': attachment_info
                    }
                )
            
            logger.info(f"Processed attachment {attachment_name} for message {message_id}")
            return {'success': True, 'attachment_id': attachment_id}
            
    except Exception as e:
        logger.error(f"Failed to process attachment {attachment_id}: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (2 ** self.request.retries))
        
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def sync_chat_history_realtime(self, account_id: str, chat_id: str, conversation_id: str):
    """
    Sync complete chat history from UniPile and broadcast updates
    """
    try:
        from communications.unipile_sdk import unipile_service
        from communications.models import Message, Conversation
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        # Sync chat history from beginning
        sync_response = client.request.get(f'chats/{chat_id}/sync')
        
        if sync_response and sync_response.get('messages'):
            # Get conversation
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Process historical messages
            new_messages = []
            for msg_data in sync_response['messages']:
                # Check if message already exists
                if not Message.objects.filter(external_message_id=msg_data.get('message_id')).exists():
                    # Process new historical message
                    new_messages.append(msg_data)
            
            # Broadcast history sync completion
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"conversation_{conversation_id}",
                    {
                        'type': 'chat_history_synced',
                        'chat_id': chat_id,
                        'new_messages_count': len(new_messages),
                        'total_messages': len(sync_response['messages']),
                        'sync_completed_at': django_timezone.now().isoformat()
                    }
                )
            
            logger.info(f"Synced {len(new_messages)} new messages for chat {chat_id}")
            return {'success': True, 'new_messages': len(new_messages)}
            
    except Exception as e:
        logger.error(f"Failed to sync chat history for {chat_id}: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120 * (2 ** self.request.retries))
        
        return {'success': False, 'error': str(e)}


@shared_task(bind=True)
def update_message_status_realtime(self, message_id: str, status: str, account_id: str):
    """
    Update message status (delivered, read) and broadcast real-time update
    """
    try:
        from communications.models import Message, MessageStatus
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Update message status
        message = Message.objects.get(external_message_id=message_id)
        old_status = message.status
        
        if status == 'delivered':
            message.status = MessageStatus.DELIVERED
        elif status == 'read':
            message.status = MessageStatus.READ
        
        message.save()
        
        # Broadcast real-time status update
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"conversation_{message.conversation.id}",
                {
                    'type': 'message_status_updated',
                    'message_id': str(message.id),
                    'external_message_id': message_id,
                    'old_status': old_status,
                    'new_status': message.status,
                    'updated_at': django_timezone.now().isoformat()
                }
            )
        
        logger.info(f"Updated message {message_id} status from {old_status} to {message.status}")
        return {'success': True, 'message_id': message_id, 'status': message.status}
        
    except Exception as e:
        logger.error(f"Failed to update message status for {message_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def mark_chat_read_realtime(self, account_id: str, chat_id: str, conversation_id: str):
    """
    Mark chat as read via UniPile API and broadcast update
    """
    try:
        from communications.unipile_sdk import unipile_service
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        # Mark chat as read via UniPile API
        read_response = client.request.patch(f'chats/{chat_id}', data={'read': True})
        
        if read_response:
            # Broadcast real-time read status update
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"channel_{account_id}",
                    {
                        'type': 'chat_marked_read',
                        'conversation_id': conversation_id,
                        'chat_id': chat_id,
                        'marked_read_at': django_timezone.now().isoformat()
                    }
                )
            
            logger.info(f"Marked chat {chat_id} as read")
            return {'success': True, 'chat_id': chat_id}
            
    except Exception as e:
        logger.error(f"Failed to mark chat {chat_id} as read: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (2 ** self.request.retries))
        
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def forward_message_realtime(self, account_id: str, message_id: str, target_chat_id: str, conversation_id: str):
    """
    Forward WhatsApp message via UniPile API and broadcast update
    """
    try:
        from communications.unipile_sdk import unipile_service
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        # Forward message via UniPile API (WhatsApp-specific)
        forward_response = client.request.post(f'messages/{message_id}/forward', data={
            'chat_id': target_chat_id
        })
        
        if forward_response:
            # Broadcast real-time forward notification
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"conversation_{conversation_id}",
                    {
                        'type': 'message_forwarded',
                        'original_message_id': message_id,
                        'target_chat_id': target_chat_id,
                        'forwarded_message_id': forward_response.get('message_id'),
                        'forwarded_at': django_timezone.now().isoformat()
                    }
                )
            
            logger.info(f"Forwarded message {message_id} to chat {target_chat_id}")
            return {'success': True, 'forwarded_message_id': forward_response.get('message_id')}
            
    except Exception as e:
        logger.error(f"Failed to forward message {message_id}: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {'success': False, 'error': str(e)}


@shared_task(bind=True)
def periodic_account_resync(self, account_id: str):
    """
    Periodic account resync for maintaining connection health
    """
    try:
        from communications.unipile_sdk import unipile_service
        from communications.models import UserChannelConnection
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        # Resync account data
        resync_response = client.request.get(f'accounts/{account_id}/sync')
        
        if resync_response:
            # Update connection last sync time
            try:
                connection = UserChannelConnection.objects.get(unipile_account_id=account_id)
                connection.last_sync_at = django_timezone.now()
                connection.sync_error_count = 0
                connection.save()
            except UserChannelConnection.DoesNotExist:
                pass
            
            logger.info(f"Periodic resync completed for account {account_id}")
            return {'success': True, 'account_id': account_id}
            
    except Exception as e:
        logger.error(f"Failed periodic resync for account {account_id}: {e}")
        return {'success': False, 'error': str(e)}


# Automatic Contact Resolution Tasks

@shared_task(bind=True, max_retries=3)
def resolve_unconnected_conversations_task(self, tenant_schema: str, limit: int = 50):
    """
    Process unconnected conversations for automatic contact resolution
    
    Args:
        tenant_schema: Tenant schema to process
        limit: Maximum number of conversations to process in one batch
    """
    try:
        with schema_context(tenant_schema):
            from .models import Conversation, Message
            from .resolvers.contact_identifier import ContactIdentifier
            from .resolvers.relationship_context import RelationshipContextResolver
            from django.db import connection as db_connection
            
            # Get tenant ID for resolvers
            tenant_id = db_connection.tenant.id if hasattr(db_connection, 'tenant') else None
            if not tenant_id:
                logger.error(f"Could not determine tenant ID for schema {tenant_schema}")
                return {'success': False, 'error': 'Could not determine tenant ID'}
            
            # Initialize resolvers
            contact_identifier = ContactIdentifier(tenant_id=tenant_id)
            relationship_resolver = RelationshipContextResolver(tenant_id=tenant_id)
            
            # Get unconnected conversations with recent activity
            unconnected_conversations = Conversation.objects.filter(
                primary_contact_record__isnull=True,
                status='active',
                last_message_at__isnull=False
            ).select_related('channel').order_by('-last_message_at')[:limit]
            
            if not unconnected_conversations:
                logger.info(f"No unconnected conversations found in {tenant_schema}")
                return {
                    'success': True,
                    'tenant_schema': tenant_schema,
                    'processed': 0,
                    'resolved': 0,
                    'message': 'No unconnected conversations to process'
                }
            
            logger.info(f"Processing {len(unconnected_conversations)} unconnected conversations in {tenant_schema}")
            
            resolved_count = 0
            processed_count = 0
            
            for conversation in unconnected_conversations:
                try:
                    # Get the most recent inbound message for contact data
                    recent_message = conversation.messages.filter(
                        direction='inbound'
                    ).order_by('-created_at').first()
                    
                    if not recent_message:
                        continue
                    
                    processed_count += 1
                    
                    # Extract contact data from message
                    contact_data = extract_contact_data_from_message(recent_message)
                    
                    if not contact_data:
                        continue
                    
                    # Attempt contact resolution
                    contact_record = contact_identifier.identify_contact(contact_data)
                    
                    if contact_record:
                        # Validate domain relationship context
                        relationship_context = relationship_resolver.get_relationship_context(
                            contact_record=contact_record,
                            message_email=contact_data.get('email')
                        )
                        
                        # Only auto-connect if domain validation passes
                        domain_validated = relationship_context.get('domain_validated', True)
                        validation_status = relationship_context.get('validation_status')
                        
                        if domain_validated and validation_status != 'domain_mismatch_warning':
                            # Auto-connect conversation to contact
                            conversation.primary_contact_record = contact_record
                            
                            # Update metadata with resolution info
                            if not conversation.metadata:
                                conversation.metadata = {}
                            
                            conversation.metadata.update({
                                'auto_resolved': True,
                                'auto_resolved_at': django_timezone.now().isoformat(),
                                'resolution_method': 'automatic_background',
                                'contact_record_id': contact_record.id,
                                'contact_pipeline_id': contact_record.pipeline.id,
                                'domain_validated': True,
                                'relationship_context': relationship_context
                            })
                            
                            conversation.save()
                            
                            # Also update the message contact_record
                            recent_message.contact_record = contact_record
                            
                            # Update message metadata
                            if not recent_message.metadata:
                                recent_message.metadata = {}
                            recent_message.metadata.update({
                                'auto_resolved': True,
                                'auto_resolved_at': django_timezone.now().isoformat()
                            })
                            
                            recent_message.save()
                            
                            resolved_count += 1
                            
                            logger.info(f"Auto-resolved conversation {conversation.id} to contact {contact_record.id}")
                        else:
                            logger.debug(f"Domain validation failed for conversation {conversation.id}, skipping auto-resolution")
                
                except Exception as e:
                    logger.warning(f"Error processing conversation {conversation.id}: {e}")
                    continue
            
            result = {
                'success': True,
                'tenant_schema': tenant_schema,
                'processed': processed_count,
                'resolved': resolved_count,
                'resolution_rate': f"{(resolved_count/processed_count*100):.1f}%" if processed_count > 0 else "0%"
            }
            
            logger.info(f"Contact resolution completed for {tenant_schema}: {resolved_count}/{processed_count} conversations resolved")
            return result
            
    except Exception as e:
        logger.error(f"Error in resolve_unconnected_conversations_task for {tenant_schema}: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {'success': False, 'error': str(e), 'tenant_schema': tenant_schema}


@shared_task(bind=True, max_retries=2)
def resolve_conversation_contact_task(self, conversation_id: str, tenant_schema: str):
    """
    Resolve contact for a specific conversation
    
    Args:
        conversation_id: UUID of the conversation to resolve
        tenant_schema: Tenant schema
    """
    try:
        with schema_context(tenant_schema):
            from .models import Conversation
            from .resolvers.contact_identifier import ContactIdentifier
            from .resolvers.relationship_context import RelationshipContextResolver
            from django.db import connection as db_connection
            
            # Get conversation
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                logger.error(f"Conversation {conversation_id} not found in {tenant_schema}")
                return {'success': False, 'error': 'Conversation not found'}
            
            # Skip if already connected
            if conversation.primary_contact_record:
                logger.info(f"Conversation {conversation_id} already connected to contact")
                return {
                    'success': True,
                    'message': 'Already connected',
                    'contact_id': conversation.primary_contact_record.id
                }
            
            # Get tenant ID for resolvers
            tenant_id = db_connection.tenant.id if hasattr(db_connection, 'tenant') else None
            if not tenant_id:
                logger.error(f"Could not determine tenant ID for schema {tenant_schema}")
                return {'success': False, 'error': 'Could not determine tenant ID'}
            
            # Initialize resolvers
            contact_identifier = ContactIdentifier(tenant_id=tenant_id)
            relationship_resolver = RelationshipContextResolver(tenant_id=tenant_id)
            
            # Get the most recent inbound message
            recent_message = conversation.messages.filter(
                direction='inbound'
            ).order_by('-created_at').first()
            
            if not recent_message:
                logger.info(f"No inbound messages found for conversation {conversation_id}")
                return {'success': False, 'error': 'No inbound messages found'}
            
            # Extract contact data
            contact_data = extract_contact_data_from_message(recent_message)
            
            if not contact_data:
                logger.info(f"No contact data extracted from conversation {conversation_id}")
                return {'success': False, 'error': 'No contact data found'}
            
            # Attempt contact resolution
            contact_record = contact_identifier.identify_contact(contact_data)
            
            if not contact_record:
                logger.info(f"No matching contact found for conversation {conversation_id}")
                return {'success': False, 'error': 'No matching contact found'}
            
            # Validate domain relationship context
            relationship_context = relationship_resolver.get_relationship_context(
                contact_record=contact_record,
                message_email=contact_data.get('email')
            )
            
            domain_validated = relationship_context.get('domain_validated', True)
            validation_status = relationship_context.get('validation_status')
            
            # Connect conversation to contact
            conversation.primary_contact_record = contact_record
            
            # Update metadata
            if not conversation.metadata:
                conversation.metadata = {}
            
            conversation.metadata.update({
                'auto_resolved': True,
                'auto_resolved_at': django_timezone.now().isoformat(),
                'resolution_method': 'targeted_resolution',
                'contact_record_id': contact_record.id,
                'contact_pipeline_id': contact_record.pipeline.id,
                'domain_validated': domain_validated,
                'validation_status': validation_status,
                'relationship_context': relationship_context
            })
            
            conversation.save()
            
            # Also update the message
            recent_message.contact_record = contact_record
            if not recent_message.metadata:
                recent_message.metadata = {}
            recent_message.metadata.update({
                'auto_resolved': True,
                'auto_resolved_at': django_timezone.now().isoformat()
            })
            recent_message.save()
            
            logger.info(f"Successfully resolved conversation {conversation_id} to contact {contact_record.id}")
            
            return {
                'success': True,
                'conversation_id': conversation_id,
                'contact_id': contact_record.id,
                'contact_pipeline_id': contact_record.pipeline.id,
                'domain_validated': domain_validated,
                'validation_status': validation_status
            }
            
    except Exception as e:
        logger.error(f"Error in resolve_conversation_contact_task for {conversation_id}: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (2 ** self.request.retries))
        
        return {'success': False, 'error': str(e), 'conversation_id': conversation_id}


@shared_task(bind=True)
def periodic_contact_resolution_task(self):
    """
    Periodic task to resolve unconnected conversations across all tenants
    Runs every 30 minutes to check for new unconnected conversations
    """
    try:
        from django_tenants.utils import get_tenant_model, get_public_schema_name
        from django.db import connection
        
        logger.info("Starting periodic contact resolution across all tenants")
        
        tenant_model = get_tenant_model()
        tenants = tenant_model.objects.exclude(schema_name=get_public_schema_name())
        
        total_results = {
            'tenants_processed': 0,
            'total_processed': 0,
            'total_resolved': 0,
            'tenant_results': []
        }
        
        for tenant in tenants:
            try:
                # Process each tenant
                result = resolve_unconnected_conversations_task.delay(
                    tenant_schema=tenant.schema_name,
                    limit=20  # Smaller batch for periodic processing
                ).get()
                
                total_results['tenants_processed'] += 1
                total_results['total_processed'] += result.get('processed', 0)
                total_results['total_resolved'] += result.get('resolved', 0)
                
                total_results['tenant_results'].append({
                    'tenant_name': tenant.name,
                    'schema_name': tenant.schema_name,
                    'result': result
                })
                
                logger.info(f"Processed tenant {tenant.name}: {result.get('resolved', 0)}/{result.get('processed', 0)} conversations resolved")
                
            except Exception as e:
                logger.error(f"Failed to process tenant {tenant.name}: {e}")
                total_results['tenant_results'].append({
                    'tenant_name': tenant.name,
                    'schema_name': tenant.schema_name,
                    'result': {'success': False, 'error': str(e)}
                })
        
        # Calculate overall success rate
        if total_results['total_processed'] > 0:
            overall_rate = (total_results['total_resolved'] / total_results['total_processed']) * 100
            total_results['overall_resolution_rate'] = f"{overall_rate:.1f}%"
        else:
            total_results['overall_resolution_rate'] = "0%"
        
        logger.info(f"Periodic contact resolution completed: {total_results['total_resolved']}/{total_results['total_processed']} conversations resolved across {total_results['tenants_processed']} tenants")
        
        return total_results
        
    except Exception as e:
        logger.error(f"Error in periodic_contact_resolution_task: {e}")
        raise


def extract_contact_data_from_message(message) -> dict:
    """
    Helper function to extract contact data from a message
    
    Args:
        message: Message instance
        
    Returns:
        dict: Contact data for identification
    """
    contact_data = {}
    
    # Extract from contact_email field
    if message.contact_email:
        contact_data['email'] = message.contact_email
        
        # For WhatsApp, contact_email contains phone number (legacy support)
        if '@s.whatsapp.net' in message.contact_email:
            phone_number = message.contact_email.replace('@s.whatsapp.net', '')
            # Format with country code (add + prefix)
            contact_data['phone'] = f"+{phone_number}" if phone_number else ''
    
    # Extract from contact_phone field (new approach - already formatted with +)
    if message.contact_phone:
        contact_data['phone'] = message.contact_phone
    
    # Extract from message metadata
    if message.metadata:
        # Name from contact_name or sender info
        if 'contact_name' in message.metadata:
            contact_data['name'] = message.metadata['contact_name']
        elif 'sender' in message.metadata and isinstance(message.metadata['sender'], dict):
            sender_info = message.metadata['sender']
            if 'attendee_name' in sender_info:
                contact_data['name'] = sender_info['attendee_name']
        
        # Extract any additional contact data stored in metadata
        if 'unmatched_contact_data' in message.metadata:
            additional_data = message.metadata['unmatched_contact_data']
            contact_data.update(additional_data)
    
    # Filter out empty values
    contact_data = {k: v for k, v in contact_data.items() if v and v.strip()}
    
    return contact_data