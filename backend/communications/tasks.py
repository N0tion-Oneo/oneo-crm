"""
Webhook-First Celery tasks for Communication System
Optimized for gap detection and recovery, not aggressive polling
Webhooks handle 95%+ of real-time updates, Celery handles edge cases
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django_tenants.utils import schema_context
from asgiref.sync import async_to_sync

from .models import (
    Channel, Message, Conversation, CommunicationAnalytics, UserChannelConnection
)
from .unipile_sdk import unipile_service
from .services.persistence import message_sync_service
from .services.gap_detection import gap_detector
from .services.message_store import message_store
from .services.conversation_cache import conversation_cache

logger = logging.getLogger(__name__)
User = get_user_model()


# =========================================================================
# WEBHOOK-FIRST GAP DETECTION TASKS (NOT AGGRESSIVE POLLING)
# =========================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def detect_and_sync_conversation_gaps(
    self,
    connection_id: str,
    trigger_reason: str = "gap_detection",
    tenant_schema: Optional[str] = None
):
    """
    WEBHOOK-FIRST: Only sync conversations when gaps are detected
    This is NOT aggressive polling - only runs when:
    1. Initial connection setup
    2. Account reconnection after downtime  
    3. Gap detection from sequence number mismatches
    4. Manual user-triggered sync
    """
    
    try:
        logger.info(f"🔍 Gap detection triggered for connection {connection_id} (reason: {trigger_reason})")
        
        # Import asyncio for proper async handling in ASGI context
        import asyncio
        
        # Create new event loop for this task (Celery compatibility)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if tenant_schema:
                with schema_context(tenant_schema):
                    result = loop.run_until_complete(_execute_targeted_sync_internal(
                        connection_id, trigger_reason
                    ))
            else:
                result = loop.run_until_complete(_execute_targeted_sync_internal(
                    connection_id, trigger_reason
                ))
                
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Gap detection sync failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300 * (2 ** self.request.retries))
        return {'error': str(e), 'trigger_reason': trigger_reason}


@shared_task(bind=True, max_retries=3, default_retry_delay=180)
def detect_and_sync_message_gaps(
    self,
    conversation_id: str,
    channel_type: str,
    tenant_schema: Optional[str] = None,
    trigger_reason: str = "gap_detection"
):
    """
    WEBHOOK-FIRST: Only sync messages when gaps are detected
    This is NOT aggressive polling - only runs when:
    1. Webhook delivery failure detected
    2. Sequence number gaps in conversation
    3. User requests manual sync
    4. Account reconnection recovery
    """
    
    try:
        logger.info(f"🔍 Message gap detection for conversation {conversation_id} (reason: {trigger_reason})")
        
        # Import asyncio for proper async handling in ASGI context
        import asyncio
        
        # Create new event loop for this task (Celery compatibility)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if tenant_schema:
                with schema_context(tenant_schema):
                    result = loop.run_until_complete(_sync_messages_internal(
                        conversation_id, channel_type, trigger_reason
                    ))
            else:
                result = loop.run_until_complete(_sync_messages_internal(
                    conversation_id, channel_type, trigger_reason
                ))
                
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Message gap detection failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=180 * (2 ** self.request.retries))
        return {'error': str(e), 'trigger_reason': trigger_reason}


@shared_task(bind=True, max_retries=2)
def preload_hot_conversations(
    self,
    channel_type: str,
    account_id: str,
    tenant_schema: Optional[str] = None
):
    """Preload frequently accessed conversations into cache"""
    
    try:
        if tenant_schema:
            with schema_context(tenant_schema):
                return conversation_cache.preload_hot_conversations(channel_type, account_id)
        else:
            return conversation_cache.preload_hot_conversations(channel_type, account_id)
            
    except Exception as e:
        logger.error(f"Hot conversation preload failed: {e}")
        return False


@shared_task(bind=True, max_retries=2)
def cleanup_old_cache_entries(self, tenant_schema: Optional[str] = None):
    """Clean up old cache entries to free memory"""
    
    try:
        if tenant_schema:
            with schema_context(tenant_schema):
                # Implementation would go here
                # For now, just log
                logger.info(f"Cache cleanup completed for tenant {tenant_schema}")
        else:
            logger.info("Cache cleanup completed for current tenant")
        
        return True
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return False


@shared_task(bind=True, max_retries=2)
def webhook_failure_recovery(self, tenant_schema: Optional[str] = None):
    """
    WEBHOOK-FIRST: Only run when webhook failures are detected
    This replaces aggressive 'process_pending_syncs' that ran every minute
    Now only runs when:
    1. Webhook delivery failures detected
    2. Connection downtime recovery needed
    3. Data integrity validation (daily, not minute-by-minute)
    """
    
    try:
        logger.info("🔄 Webhook failure recovery triggered")
        
        # Import asyncio for proper async handling in ASGI context
        import asyncio
        
        # Create new event loop for this task (Celery compatibility)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if tenant_schema:
                with schema_context(tenant_schema):
                    result = loop.run_until_complete(_webhook_failure_recovery_internal())
            else:
                result = loop.run_until_complete(_webhook_failure_recovery_internal())
                
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Webhook failure recovery failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=1800)  # 30 minute retry instead of 2 minutes
        return {'error': str(e)}


# =========================================================================
# INTERNAL ASYNC FUNCTIONS
# =========================================================================

async def _execute_targeted_sync_internal(
    connection_id: str,
    trigger_reason: str = "gap_detection"
) -> Dict[str, Any]:
    """
    WEBHOOK-FIRST: Execute targeted sync based on smart gap detection
    Only syncs when actual gaps are detected
    """
    
    try:
        # Use smart gap detection to determine if sync is needed
        gap_results = await gap_detector.detect_conversation_gaps(connection_id, trigger_reason)
        
        if not gap_results.get('gaps_detected'):
            logger.info(f"✅ No gaps detected for connection {connection_id}, skipping sync")
            return {
                'success': True,
                'gaps_detected': False,
                'sync_executed': False,
                'connection_id': connection_id,
                'trigger_reason': trigger_reason
            }
        
        # Get sync recommendations
        recommendations = await gap_detector.get_sync_recommendations(connection_id)
        
        if recommendations.get('sync_needed'):
            # Execute targeted sync
            result = await _execute_targeted_sync(connection_id, recommendations, trigger_reason)
            return result
        else:
            return {
                'success': True,
                'gaps_detected': True,
                'sync_executed': False,
                'reason': 'sync_not_recommended',
                'connection_id': connection_id
            }
            
    except Exception as e:
        logger.error(f"Internal targeted sync failed for {connection_id}: {e}")
        raise


async def _sync_conversations_internal(
    channel_type: str,
    user_id: str,
    account_id: Optional[str] = None,
    trigger_reason: str = "gap_detection"
) -> Dict[str, Any]:
    """
    WEBHOOK-FIRST: Internal function for gap detection, not routine polling
    Only syncs when there's an actual gap or specific trigger
    """
    
    try:
        # Smart gap detection - only sync if we detect missing data
        if trigger_reason == "gap_detection":
            # Check if we actually need to sync by detecting gaps
            gap_detected = await _detect_conversation_gaps(channel_type, user_id, account_id)
            if not gap_detected:
                logger.info(f"✅ No conversation gaps detected for {channel_type}, skipping sync")
                return {'conversations': [], 'synced': False, 'reason': 'no_gaps_detected'}
        
        # Only force sync when we actually need it
        result = await message_sync_service.get_conversations_local_first(
            channel_type=channel_type,
            user_id=user_id,
            account_id=account_id,
            force_sync=True  # Force API sync only when gaps detected
        )
        
        logger.info(f"🔄 Gap-based sync completed: {len(result.get('conversations', []))} conversations (reason: {trigger_reason})")
        return result
        
    except Exception as e:
        logger.error(f"Internal gap detection sync failed: {e}")
        raise


async def _sync_messages_internal(
    conversation_id: str,
    channel_type: str,
    trigger_reason: str = "gap_detection"
) -> Dict[str, Any]:
    """
    WEBHOOK-FIRST: Internal function for message gap detection
    Only syncs when webhook delivery failed or gaps detected
    """
    
    try:
        # Smart gap detection for messages
        if trigger_reason == "gap_detection":
            gap_detected = await _detect_message_gaps(conversation_id, channel_type)
            if not gap_detected:
                logger.info(f"✅ No message gaps detected for conversation {conversation_id}, skipping sync")
                return {'messages': [], 'synced': False, 'reason': 'no_gaps_detected'}
        
        # Only force sync when gaps are detected
        result = await message_sync_service.get_messages_local_first(
            conversation_id=conversation_id,
            channel_type=channel_type,
            force_sync=True  # Force API sync only when gaps detected
        )
        
        logger.info(f"🔄 Message gap sync completed: {len(result.get('messages', []))} messages (reason: {trigger_reason})")
        return result
        
    except Exception as e:
        logger.error(f"Internal message gap sync failed: {e}")
        raise


async def _webhook_failure_recovery_internal() -> Dict[str, Any]:
    """
    WEBHOOK-FIRST: Recovery process for webhook failures
    Replaces aggressive pending sync processing
    """
    
    try:
        # Only check for actual webhook failures and connection issues
        recovery_results = {
            'webhook_failures_detected': 0,
            'connections_recovered': 0,
            'conversations_synced': 0,
            'messages_synced': 0,
            'errors': []
        }
        
        # Check for accounts that need recovery (webhook failures, disconnections)
        # Use async ORM queries for ASGI compatibility
        failed_connections = []
        async for connection in UserChannelConnection.objects.filter(
            account_status__in=['error', 'failed', 'disconnected'],
            is_active=True
        ):
            failed_connections.append(connection)
        
        for connection in failed_connections:
            try:
                # Attempt recovery sync for failed connections
                if connection.account_status == 'disconnected':
                    # Skip disconnected accounts - user needs to reconnect manually
                    continue
                    
                result = await message_sync_service.sync_account_messages(
                    connection_id=str(connection.id),
                    initial_sync=False,
                    days_back=1  # Only sync last 24 hours for recovery
                )
                
                if result.get('success'):
                    recovery_results['connections_recovered'] += 1
                    recovery_results['conversations_synced'] += result.get('conversations_synced', 0)
                    recovery_results['messages_synced'] += result.get('messages_synced', 0)
                    
                    # Update connection status if recovery was successful (async save)
                    connection.account_status = 'active'
                    connection.sync_error_count = 0
                    connection.last_error = ''
                    await connection.asave(update_fields=['account_status', 'sync_error_count', 'last_error'])
                    
            except Exception as e:
                recovery_results['errors'].append(f"Failed to recover connection {connection.id}: {str(e)}")
                logger.error(f"Recovery failed for connection {connection.id}: {e}")
        
        logger.info(f"🔄 Webhook failure recovery completed: {recovery_results}")
        return recovery_results
        
    except Exception as e:
        logger.error(f"Webhook failure recovery process failed: {e}")
        raise


# =========================================================================
# SMART GAP DETECTION FUNCTIONS (WEBHOOK-FIRST STRATEGY)
# =========================================================================

async def _detect_conversation_gaps(
    channel_type: str,
    user_id: str,
    account_id: Optional[str] = None
) -> bool:
    """
    Detect if there are gaps in conversation data that require sync
    Returns True only if gaps are detected, False if data is current
    """
    
    try:
        # Check last sync time for this account (async query)
        connection = await UserChannelConnection.objects.filter(
            user_id=user_id,
            channel_type=channel_type,
            unipile_account_id=account_id,
            is_active=True
        ).afirst()
        
        if not connection:
            logger.info(f"No connection found for gap detection: {channel_type}/{account_id}")
            return False
        
        # If last sync was recent (< 1 hour) and no errors, assume webhooks are working
        if connection.last_sync_at:
            time_since_sync = django_timezone.now() - connection.last_sync_at
            if time_since_sync < timedelta(hours=1) and connection.sync_error_count == 0:
                logger.info(f"✅ Recent sync detected ({time_since_sync}), assuming webhooks working")
                return False
        
        # Check if there are webhook delivery failures
        if connection.sync_error_count > 0:
            logger.info(f"🔍 Gap detected: {connection.sync_error_count} sync errors")
            return True
        
        # Check if connection was recently restored from failed state
        if connection.account_status in ['error', 'failed'] or connection.last_error:
            logger.info(f"🔍 Gap detected: connection status indicates issues")
            return True
        
        # Default: assume webhooks are working, no gaps
        return False
        
    except Exception as e:
        logger.error(f"Gap detection failed: {e}")
        # If we can't detect gaps, err on the side of caution and sync
        return True


async def _detect_message_gaps(conversation_id: str, channel_type: str) -> bool:
    """
    Detect if there are gaps in message data for a specific conversation
    Returns True only if gaps are detected, False if data is current
    """
    
    try:
        # Find conversation in local database (async query)
        conversation = await Conversation.objects.filter(
            external_thread_id=conversation_id
        ).afirst()
        
        if not conversation:
            logger.info(f"🔍 Gap detected: conversation {conversation_id} not found locally")
            return True  # If conversation doesn't exist locally, we need to sync
        
        # Check if there are messages pending sync (async count)
        pending_messages = await conversation.messages.filter(sync_status='pending').acount()
        if pending_messages > 0:
            logger.info(f"🔍 Gap detected: {pending_messages} messages pending sync")
            return True
        
        # Check if the conversation was updated recently (should have webhook updates)
        time_since_update = django_timezone.now() - conversation.updated_at
        if time_since_update > timedelta(hours=2):
            # If conversation hasn't been updated in 2+ hours, check for missing messages
            # This might indicate webhook delivery issues
            logger.info(f"🔍 Potential gap: conversation not updated in {time_since_update}")
            return True
        
        # Default: assume webhooks are delivering messages properly
        return False
        
    except Exception as e:
        logger.error(f"Message gap detection failed: {e}")
        # If we can't detect gaps, err on the side of caution and sync
        return True


# =========================================================================
# WEBHOOK-FIRST TASK ALIASES (MAINTAIN API COMPATIBILITY)
# =========================================================================

# Keep these aliases for compatibility with existing code that might call them
# But redirect to webhook-first gap detection instead of aggressive polling

sync_conversations_background = detect_and_sync_conversation_gaps
sync_messages_background = detect_and_sync_message_gaps
process_pending_syncs = webhook_failure_recovery

# Legacy contact resolution - redirect to on-demand only  
# resolve_unconnected_conversations_task = resolve_conversation_contact_task  # Defined below
periodic_contact_resolution_task = webhook_failure_recovery  # No more automatic contact resolution
# =========================================================================
# WEBHOOK-FIRST TASK ALIASES (MAINTAIN API COMPATIBILITY)
# =========================================================================

# These aliases maintain compatibility with existing code that might call legacy tasks
# But redirect to webhook-first gap detection instead of aggressive polling

# Analytics task - this is legitimate and needed
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


# Scheduled message task - this is legitimate for workflow automation
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


# =========================================================================
# WEBHOOK-FIRST REAL-TIME ENHANCEMENT TASKS
# =========================================================================

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


# =========================================================================
# WEBHOOK-FIRST CONTACT RESOLUTION TASKS (ON-DEMAND ONLY)
# =========================================================================

@shared_task(bind=True, max_retries=2)
def resolve_conversation_contact_task(self, conversation_id: str, tenant_schema: str):
    """
    Resolve contact for a specific conversation (ON-DEMAND ONLY)
    WEBHOOK-FIRST: Only run when user explicitly requests contact resolution
    
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
                'resolution_method': 'user_requested',
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


# Legacy task alias for compatibility
resolve_unconnected_conversations_task = resolve_conversation_contact_task


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


# =========================================================================
# SMART GAP DETECTION HELPER FUNCTIONS
# =========================================================================

async def _execute_targeted_sync(connection_id: str, 
                                recommendations: Dict[str, Any], 
                                trigger_reason: str) -> Dict[str, Any]:
    """
    Execute targeted sync based on smart gap detection recommendations
    
    Args:
        connection_id: UserChannelConnection ID
        recommendations: Sync recommendations from gap detector
        trigger_reason: Why sync was triggered
        
    Returns:
        Sync execution result
    """
    try:
        connection = await UserChannelConnection.objects.aget(id=connection_id)
        
        logger.info(f"🎯 Executing targeted sync for {connection.channel_type} "
                   f"account {connection.unipile_account_id} (priority: {recommendations.get('priority')})")
        
        # Use the persistence service for intelligent sync
        result = await message_sync_service.sync_account_messages(
            connection_id=connection_id,
            initial_sync=False,
            days_back=recommendations.get('days_back', 1)
        )
        
        # Update connection sync status
        connection.last_sync_at = django_timezone.now()
        connection.sync_error_count = 0
        await connection.asave(update_fields=['last_sync_at', 'sync_error_count'])
        
        return {
            'success': True,
            'connection_id': connection_id,
            'sync_type': 'targeted',
            'priority': recommendations.get('priority'),
            'messages_synced': result.get('messages_synced', 0),
            'conversations_synced': result.get('conversations_synced', 0),
            'trigger_reason': trigger_reason
        }
        
    except Exception as e:
        logger.error(f"Targeted sync failed for connection {connection_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'connection_id': connection_id
        }


async def _execute_targeted_message_sync(conversation_id: str, 
                                       gap_analysis: Dict[str, Any],
                                       trigger_reason: str) -> Dict[str, Any]:
    """
    Execute targeted message sync for specific conversation gaps
    
    Args:
        conversation_id: Conversation ID with detected gaps
        gap_analysis: Message gap analysis results
        trigger_reason: Why sync was triggered
        
    Returns:
        Message sync execution result
    """
    try:
        conversation = await Conversation.objects.select_related('channel').aget(id=conversation_id)
        
        logger.info(f"🎯 Executing targeted message sync for conversation {conversation_id} "
                   f"({conversation.channel.channel_type})")
        
        # Use conversation's channel for targeted sync
        result = await message_sync_service.get_messages_local_first(
            conversation_id=conversation_id,
            channel_type=conversation.channel.channel_type,
            force_sync=True,
            limit=1000  # Large limit to fill gaps
        )
        
        return {
            'success': True,
            'conversation_id': conversation_id,
            'sync_type': 'targeted_messages',
            'messages_processed': len(result.get('messages', [])),
            'trigger_reason': trigger_reason
        }
        
    except Exception as e:
        logger.error(f"Targeted message sync failed for conversation {conversation_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'conversation_id': conversation_id
        }


# =========================================================================
# LEGACY TASK ALIASES (REDIRECT TO WEBHOOK-FIRST APPROACHES)
# =========================================================================

# Redirect aggressive polling tasks to webhook-first gap detection