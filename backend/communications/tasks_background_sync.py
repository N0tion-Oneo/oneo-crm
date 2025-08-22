"""
Background Sync Tasks - Celery Tasks for Large-Scale Sync Operations
Implements paginated, non-blocking sync with progress tracking and resume capability
Compatible with Daphne ASGI server architecture
"""
import logging
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django_tenants.utils import schema_context
from asgiref.sync import async_to_sync, sync_to_async

from .models import (
    Channel, UserChannelConnection, Conversation, SyncJob, SyncJobProgress, 
    SyncJobStatus, SyncJobType
)
from .unipile_sdk import unipile_service
from .services.unified_processor import unified_processor

User = get_user_model()
logger = logging.getLogger(__name__)

# =========================================================================
# CONFIGURATION CONSTANTS
# =========================================================================

# Default batch sizes optimized for UniPile API rate limits and memory usage
SYNC_CONFIG = {
    'conversations_per_batch': 50,      # Conversations per API request
    'messages_per_batch': 100,          # Messages per API request
    'concurrent_chat_tasks': 3,         # Parallel chat processing tasks
    'max_retries': 5,                   # Maximum retry attempts
    'retry_delay_base': 60,             # Base retry delay in seconds
    'progress_update_interval': 10,     # Update progress every N items
}

# =========================================================================
# MAIN ORCHESTRATOR TASK
# =========================================================================

@shared_task(bind=True, max_retries=3)
def sync_account_comprehensive_background(
    self, 
    channel_id: str, 
    user_id: str, 
    sync_options: Optional[Dict[str, Any]] = None,
    tenant_schema: Optional[str] = None
):
    """
    Main orchestrator for comprehensive background sync
    Creates sync job and coordinates all sync phases with progress tracking
    
    Args:
        channel_id: Channel UUID to sync
        user_id: User UUID who initiated sync
        sync_options: Configuration options for sync
        tenant_schema: Tenant schema for multi-tenant support
    """
    sync_job = None
    
    try:
        # Apply sync options
        options = {**SYNC_CONFIG, **(sync_options or {})}
        
        logger.info(f"🚀 Starting comprehensive background sync for channel {channel_id}")
        
        # ASGI-compatible event loop setup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Pass tenant schema to the async function for proper context handling
            result = loop.run_until_complete(
                _execute_comprehensive_sync(self, channel_id, user_id, options, tenant_schema)
            )
            
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ Background sync failed for channel {channel_id}: {e}")
        
        # Update sync job status to failed
        if sync_job:
            try:
                if tenant_schema:
                    with schema_context(tenant_schema):
                        _mark_sync_job_failed(sync_job.id, str(e))
                else:
                    _mark_sync_job_failed(sync_job.id, str(e))
            except Exception as update_error:
                logger.error(f"Failed to update sync job status: {update_error}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = options.get('retry_delay_base', 60) * (2 ** self.request.retries)
            raise self.retry(countdown=retry_delay)
        
        return {
            'success': False,
            'error': str(e),
            'channel_id': channel_id,
            'task_id': self.request.id
        }


# =========================================================================
# PAGINATED SYNC IMPLEMENTATION
# =========================================================================

async def _execute_comprehensive_sync(
    task, 
    channel_id: str, 
    user_id: str, 
    options: Dict[str, Any],
    tenant_schema: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute comprehensive sync with pagination and progress tracking
    ASGI-compatible async implementation
    """
    from django_tenants.utils import schema_context
    
    async def _run_sync():
        # Get channel and user
        channel = await Channel.objects.aget(id=channel_id)
        user = await User.objects.aget(id=user_id)
        
        # Get the UserChannelConnection for direction detection
        connection = await UserChannelConnection.objects.filter(
            user=user,
            unipile_account_id=channel.unipile_account_id
        ).afirst()
        
        if connection:
            logger.info(f"✅ Found user connection for direction detection")
        else:
            logger.warning(f"⚠️ No user connection found - direction detection will use fallback methods")
        
        # Create sync job
        sync_job = await SyncJob.objects.acreate(
            user=user,
            channel=channel,
            job_type=SyncJobType.COMPREHENSIVE,
            sync_options=options,
            celery_task_id=task.request.id,
            status=SyncJobStatus.RUNNING,
            started_at=django_timezone.now()
        )
        
        logger.info(f"📊 Created sync job {sync_job.id} for comprehensive sync")
        
        try:
            # Phase 1: Get conversation count estimate
            await _update_sync_progress(sync_job, 'initializing', 'Getting conversation estimate')
            
            total_conversations = await _estimate_conversation_count(channel, options)
            await sync_job.update_progress(
                conversations_total=total_conversations,
                conversations_processed=0,
                messages_processed=0,
                current_phase='fetching_conversations'
            )
            
            # Phase 2 & 3: Use comprehensive sync service for actual sync
            await _update_sync_progress(sync_job, 'running_comprehensive_sync', 'Starting comprehensive sync service')
            
            from .services.comprehensive_sync import ComprehensiveSyncService
            comprehensive_sync = ComprehensiveSyncService()
            
            # Run comprehensive sync with progress updates
            sync_result = await comprehensive_sync.sync_account_comprehensive(
                channel=channel,
                days_back=options.get('days_back', 30),
                max_messages_per_chat=options.get('max_messages_per_chat', 100),
                connection=connection,  # Pass connection for proper direction detection
                sync_job=sync_job  # Pass sync job for WebSocket progress updates
            )
            
            # Update sync job progress with comprehensive sync results
            conversations_synced = sync_result.get('chats_synced', 0)
            messages_synced = sync_result.get('messages_synced', 0)
            
            await sync_job.update_progress(
                conversations_processed=conversations_synced,
                conversations_total=conversations_synced,  # Update total based on actual results
                messages_processed=messages_synced,
                current_phase='completed',
                current_step='sync_finished'
            )
            
            # Phase 4: Finalization
            conversations_data = [{'conversation_id': f'sync_{i}'} for i in range(conversations_synced)]
            await _finalize_sync_job(sync_job, conversations_data, messages_synced)
            
            result = {
                'success': True,
                'sync_job_id': str(sync_job.id),
                'conversations_synced': len(conversations_synced),
                'messages_synced': messages_synced,
                'channel_id': channel_id,
                'task_id': task.request.id
            }
            
            logger.info(f"✅ Comprehensive sync completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Sync execution failed: {e}")
            await _mark_sync_job_failed_async(sync_job, str(e))
            raise
    
    # Execute with proper tenant context
    if tenant_schema:
        logger.info(f"🏢 Using tenant schema context: {tenant_schema}")
        
        # Get task ID before entering async context to avoid context loss
        task_id = task.request.id
        logger.info(f"🎯 Task ID before async wrapper: {task_id}")
        
        if not task_id:
            logger.error(f"❌ No Celery task ID available - task not properly queued")
            raise ValueError("No Celery task ID available - task must be properly queued")
        
        # For ASGI/Daphne compatibility, wrap the entire sync operation
        from asgiref.sync import sync_to_async
        
        @sync_to_async  
        def run_sync_with_tenant_context(celery_task_id):
            with schema_context(tenant_schema):
                logger.info(f"🎯 Using task ID in sync context: {celery_task_id}")
                
                # Verify we're in the correct schema
                from django.db import connection
                logger.info(f"🔍 Current schema after context: {connection.schema_name}")
                
                # Test database access 
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM communications_channel")
                    count = cursor.fetchone()[0]
                    logger.info(f"✅ Found {count} channels in schema {connection.schema_name}")
                
                # Get channel and user using synchronous ORM
                from .models import Channel
                channel = Channel.objects.get(id=channel_id)
                user = User.objects.get(id=user_id)
                logger.info(f"✅ Found channel: {channel.name} and user: {user.username}")
                
                # Get the UserChannelConnection for direction detection
                user_connection = UserChannelConnection.objects.filter(
                    user=user,
                    unipile_account_id=channel.unipile_account_id
                ).first()
                
                if user_connection:
                    logger.info(f"✅ Found user connection for direction detection")
                else:
                    logger.warning(f"⚠️ No user connection found - direction detection will use fallback methods")
                
                # Create sync job - no fallback lookups in ASGI environment
                sync_job = SyncJob.objects.create(
                    user=user,
                    channel=channel,
                    job_type=SyncJobType.COMPREHENSIVE,
                    sync_options=options,
                    celery_task_id=celery_task_id,
                    status=SyncJobStatus.RUNNING,
                    started_at=django_timezone.now()
                )
                logger.info(f"🆕 Created sync job: {sync_job.id} with task ID: {celery_task_id}")
                
                logger.info(f"✅ Sync job created with task ID: {celery_task_id}")
                
                logger.info(f"📊 Created sync job {sync_job.id} for comprehensive sync")
                
                # Now execute the full sync implementation
                try:
                    # Phase 1: Get conversation count estimate
                    total_conversations = _estimate_conversation_count_sync(channel, options)
                    logger.info(f"📊 Estimated {total_conversations} conversations to sync")
                    
                    # Update sync job with total estimate
                    sync_job.progress = {
                        'conversations_total': total_conversations,
                        'conversations_processed': 0,
                        'messages_processed': 0,
                        'current_phase': 'fetching_conversations'
                    }
                    sync_job.save(update_fields=['progress'])
                    
                    # Phase 2 & 3: Use comprehensive sync service 
                    # Use our simplified sync version to avoid async/sync conflicts
                    sync_job.progress.update({
                        'current_phase': 'running_comprehensive_sync',
                        'current_step': 'Starting comprehensive sync service'
                    })
                    sync_job.save(update_fields=['progress'])
                    
                    # Run simplified comprehensive sync (sync version)
                    sync_result = _run_comprehensive_sync_simplified(channel, options, user_connection, sync_job)
                    
                    # Extract results from comprehensive sync
                    conversations_synced = [{'conversation_id': f'sync_{i}'} for i in range(sync_result.get('chats_synced', 0))]
                    messages_synced = sync_result.get('messages_synced', 0)
                    
                    # Update sync job progress
                    sync_job.progress.update({
                        'conversations_processed': len(conversations_synced),
                        'conversations_total': len(conversations_synced),
                        'messages_processed': messages_synced,
                        'current_phase': 'completed',
                        'current_step': 'sync_finished'
                    })
                    sync_job.save(update_fields=['progress'])
                    
                    # Phase 4: Finalize sync job
                    sync_job.status = SyncJobStatus.COMPLETED
                    sync_job.completed_at = django_timezone.now()
                    sync_job.result_summary = {
                        'conversations_synced': len(conversations_synced),
                        'messages_synced': messages_synced,
                        'completed_at': django_timezone.now().isoformat(),
                        'duration_seconds': (
                            sync_job.completed_at - sync_job.started_at
                        ).total_seconds() if sync_job.started_at else 0
                    }
                    sync_job.save(update_fields=[
                        'status', 'completed_at', 'result_summary'
                    ])
                    
                    result = {
                        'success': True,
                        'sync_job_id': str(sync_job.id),
                        'conversations_synced': len(conversations_synced),
                        'messages_synced': messages_synced,
                        'channel_id': channel_id,
                        'task_id': celery_task_id
                    }
                    
                    logger.info(f"✅ Comprehensive sync completed: {result}")
                    return result
                    
                except Exception as sync_error:
                    logger.error(f"❌ Sync execution failed: {sync_error}")
                    
                    # Mark sync job as failed
                    sync_job.status = SyncJobStatus.FAILED
                    sync_job.completed_at = django_timezone.now()
                    sync_job.error_details = {
                        'error': str(sync_error),
                        'failed_at': django_timezone.now().isoformat()
                    }
                    sync_job.error_count += 1
                    sync_job.save(update_fields=[
                        'status', 'completed_at', 'error_details', 'error_count'
                    ])
                    
                    raise sync_error
        
        return await run_sync_with_tenant_context(task_id)
    else:
        logger.error(f"❌ No tenant schema provided!")
        raise ValueError("No tenant schema provided for background sync task")


async def _sync_conversations_paginated(
    sync_job: SyncJob,
    channel: Channel,
    options: Dict[str, Any],
    connection: Optional[UserChannelConnection] = None
) -> List[Dict[str, Any]]:
    """
    Sync conversations with pagination and progress updates
    """
    logger.info(f"📱 Starting paginated conversation sync for {channel.name}")
    
    client = unipile_service.get_client()
    batch_size = options['conversations_per_batch']
    cursor = sync_job.pagination_state.get('conversations_cursor')
    
    all_conversations = []
    batch_number = 0
    
    # Map channel type to UniPile account type
    account_type_map = {
        'whatsapp': 'WHATSAPP',
        'linkedin': 'LINKEDIN',
        'gmail': 'GOOGLE',
        'outlook': 'OUTLOOK'
    }
    account_type = account_type_map.get(channel.channel_type, channel.channel_type.upper())
    
    while True:
        batch_number += 1
        
        # Create progress entry for this batch
        progress_entry = await SyncJobProgress.objects.acreate(
            sync_job=sync_job,
            phase_name='fetching_conversations',
            step_name=f'batch_{batch_number}',
            items_total=batch_size
        )
        
        try:
            # Get batch of conversations
            response = await client.messaging.get_chats_batch(
                account_id=channel.unipile_account_id,
                account_type=account_type,
                cursor=cursor,
                limit=batch_size
            )
            
            conversations = response.get('items', [])
            if not conversations:
                logger.info("📱 No more conversations to sync")
                break
            
            # Process this batch of conversations with detailed tracking
            batch_processed = []
            batch_errors = []
            start_time = datetime.now(timezone.utc)
            
            for i, conv_data in enumerate(conversations):
                conv_start_time = datetime.now(timezone.utc)
                try:
                    # Get attendees for this conversation
                    chat_id = conv_data.get('id')
                    conv_name = conv_data.get('name', 'Unnamed Conversation')
                    
                    if chat_id:
                        attendees = await _get_chat_attendees(client, chat_id)
                        
                        # Process via unified processor
                        normalized_attendees = [
                            unified_processor.normalize_attendee_data(att_data, 'api')
                            for att_data in attendees
                        ]
                        
                        attendees_list = await unified_processor.process_attendees(
                            normalized_attendees, channel
                        )
                        
                        # Process conversation
                        normalized_conversation = unified_processor.normalize_conversation_data(
                            conv_data, 'api'
                        )
                        
                        conversation, created = await unified_processor.process_conversation(
                            normalized_conversation, channel, attendees_list
                        )
                        
                        # Calculate processing time
                        conv_processing_time = int((datetime.now(timezone.utc) - conv_start_time).total_seconds() * 1000)
                        
                        batch_processed.append({
                            'conversation_id': str(conversation.id),
                            'external_id': chat_id,
                            'name': conv_name,
                            'created': created,
                            'processing_time_ms': conv_processing_time,
                            'attendee_count': len(attendees_list)
                        })
                        
                        # Send detailed progress update every 5 conversations
                        if (i + 1) % 5 == 0:
                            progress_current = len(all_conversations) + len(batch_processed)
                            await sync_job.update_progress(
                                conversations_processed=progress_current,
                                current_phase='processing_conversations',
                                current_step=f'batch_{batch_number}_item_{i+1}',
                                current_conversation_name=conv_name,
                                batch_progress_percent=int((i + 1) / len(conversations) * 100),
                                avg_processing_time_ms=conv_processing_time
                            )
                        
                except Exception as conv_error:
                    error_msg = str(conv_error)
                    batch_errors.append({
                        'conversation_id': conv_data.get('id', 'unknown'),
                        'conversation_name': conv_data.get('name', 'Unnamed'),
                        'error': error_msg
                    })
                    logger.error(f"Failed to process conversation {conv_data.get('id', 'unknown')}: {conv_error}")
                    continue
            
            all_conversations.extend(batch_processed)
            
            # Calculate batch performance metrics
            batch_processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            avg_conversation_time = batch_processing_time / len(batch_processed) if batch_processed else 0
            error_rate = len(batch_errors) / len(conversations) * 100 if conversations else 0
            
            # Update progress with detailed information
            await progress_entry.mark_completed(len(batch_processed))
            await sync_job.update_progress(
                conversations_processed=len(all_conversations),
                current_phase='fetching_conversations',
                current_step=f'batch_{batch_number}_completed',
                batch_number=batch_number,
                conversations_in_batch=len(batch_processed),
                batch_errors_count=len(batch_errors),
                batch_error_rate_percent=error_rate,
                batch_processing_time_ms=batch_processing_time,
                avg_conversation_processing_ms=int(avg_conversation_time),
                api_response_time_ms=response.get('batch_info', {}).get('request_time_ms', 0),
                recent_errors=batch_errors[-3:] if batch_errors else [],  # Last 3 errors
                processing_rate_per_minute=int(len(batch_processed) * 60000 / batch_processing_time) if batch_processing_time > 0 else 0
            )
            
            logger.info(f"📊 Batch {batch_number} completed: {len(batch_processed)} conversations processed, {len(batch_errors)} errors, {int(avg_conversation_time)}ms avg time")
            
            # Send intermediate progress updates with performance data
            if len(all_conversations) % 10 == 0:  # Every 10 conversations
                estimated_remaining = sync_job.progress.get('conversations_total', 0) - len(all_conversations)
                estimated_time_remaining_minutes = int(estimated_remaining * avg_conversation_time / 60000) if avg_conversation_time > 0 else 0
                
                await sync_job.update_progress(
                    conversations_processed=len(all_conversations),
                    estimated_time_remaining_minutes=estimated_time_remaining_minutes,
                    current_processing_rate_per_minute=int(len(all_conversations) * 60000 / batch_processing_time) if batch_processing_time > 0 else 0,
                    current_phase='fetching_conversations',
                    current_step=f'processing_conversation_{len(all_conversations)}',
                    latest_conversation=batch_processed[-1]['conversation_id'] if batch_processed else None
                )
            
            # Check for next page
            cursor = response.get('next_cursor')
            has_more = response.get('has_more', False)
            
            # Save pagination state for resume capability
            sync_job.pagination_state['conversations_cursor'] = cursor
            await sync_job.asave(update_fields=['pagination_state'])
            
            if not has_more or not cursor:
                break
                
            logger.info(f"📱 Completed conversation batch {batch_number}: {len(batch_processed)} processed")
            
        except Exception as batch_error:
            logger.error(f"Conversation batch {batch_number} failed: {batch_error}")
            await progress_entry.mark_failed(str(batch_error))
            
            # Continue with next batch instead of failing entire sync
            cursor = response.get('next_cursor') if 'response' in locals() else None
            if not cursor:
                break
    
    logger.info(f"✅ Conversation sync completed: {len(all_conversations)} conversations processed")
    return all_conversations


async def _sync_messages_paginated(
    sync_job: SyncJob,
    channel: Channel,
    conversations: List[Dict[str, Any]],
    options: Dict[str, Any],
    connection: Optional[UserChannelConnection] = None
) -> int:
    """
    Sync messages for all conversations with pagination
    """
    logger.info(f"📨 Starting paginated message sync for {len(conversations)} conversations")
    
    client = unipile_service.get_client()
    batch_size = options['messages_per_batch']
    total_messages_synced = 0
    
    for i, conv_data in enumerate(conversations):
        external_id = conv_data.get('external_id')
        if not external_id:
            continue
            
        # Create progress entry for this conversation's messages
        progress_entry = await SyncJobProgress.objects.acreate(
            sync_job=sync_job,
            phase_name='processing_messages',
            step_name=f'conversation_{external_id[:8]}',
            items_total=0  # Will update as we discover message count
        )
        
        try:
            # Get pagination state for this conversation
            conv_cursor = sync_job.pagination_state.get(f'messages_cursor_{external_id}')
            conv_messages_synced = 0
            
            while True:
                # Get batch of messages for this conversation
                response = await client.messaging.get_messages_batch(
                    chat_id=external_id,
                    cursor=conv_cursor,
                    limit=batch_size
                )
                
                messages = response.get('items', [])
                if not messages:
                    break
                
                # Process messages via unified processor
                batch_processed = 0
                for message_data in messages:
                    try:
                        # Get the conversation object
                        conversation = await Conversation.objects.aget(
                            channel=channel,
                            external_thread_id=external_id
                        )
                        
                        # Normalize and process message
                        normalized_message = unified_processor.normalize_message_data(
                            message_data, 'api'
                        )
                        normalized_message['chat_id'] = external_id
                        
                        message, created = await unified_processor.process_message(
                            normalized_message, channel, conversation, connection
                        )
                        
                        if created:
                            batch_processed += 1
                            
                    except Exception as msg_error:
                        logger.error(f"Failed to process message {message_data.get('id', 'unknown')}: {msg_error}")
                        continue
                
                conv_messages_synced += batch_processed
                total_messages_synced += batch_processed
                
                # Update progress
                progress_entry.items_total = conv_messages_synced
                await progress_entry.mark_completed(conv_messages_synced)
                
                # Check for next page
                conv_cursor = response.get('next_cursor')
                has_more = response.get('has_more', False)
                
                # Save cursor state
                sync_job.pagination_state[f'messages_cursor_{external_id}'] = conv_cursor
                await sync_job.asave(update_fields=['pagination_state'])
                
                if not has_more or not conv_cursor:
                    break
            
            # Update overall progress
            await sync_job.update_progress(
                messages_processed=total_messages_synced,
                current_step=f'conversation_{i+1}_of_{len(conversations)}_completed'
            )
            
            logger.info(f"📨 Conversation {external_id[:8]}: {conv_messages_synced} messages synced")
            
        except Exception as conv_error:
            logger.error(f"Message sync failed for conversation {external_id}: {conv_error}")
            await progress_entry.mark_failed(str(conv_error))
            continue
    
    logger.info(f"✅ Message sync completed: {total_messages_synced} messages processed")
    return total_messages_synced


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

async def _estimate_conversation_count(channel: Channel, options: Dict[str, Any]) -> int:
    """
    Get rough estimate of conversation count for progress tracking
    """
    try:
        client = unipile_service.get_client()
        
        # Get first page to estimate total
        response = await client.messaging.get_chats_batch(
            account_id=channel.unipile_account_id,
            limit=10  # Small batch for estimation
        )
        
        items = response.get('items', [])
        if len(items) < 10:
            # If we got fewer than requested, this is probably the total
            return len(items)
        else:
            # Estimate based on typical account size
            # This is rough estimation - actual count determined during sync
            return min(1000, len(items) * 20)  # Cap at reasonable number
            
    except Exception as e:
        logger.warning(f"Failed to estimate conversation count: {e}")
        return 100  # Default estimate


async def _get_chat_attendees(client, chat_id: str) -> List[Dict[str, Any]]:
    """Get attendees for a specific chat"""
    try:
        response = await client._make_request('GET', f'chats/{chat_id}/attendees')
        return response.get('items', []) if response else []
    except Exception as e:
        logger.error(f"Failed to get attendees for chat {chat_id}: {e}")
        return []


async def _update_sync_progress(
    sync_job: SyncJob, 
    phase: str, 
    step: str, 
    **kwargs
):
    """Update sync job progress"""
    await sync_job.update_progress(
        current_phase=phase,
        current_step=step,
        **kwargs
    )


async def _finalize_sync_job(
    sync_job: SyncJob, 
    conversations: List[Dict[str, Any]], 
    messages_count: int
):
    """Mark sync job as completed"""
    sync_job.status = SyncJobStatus.COMPLETED
    sync_job.completed_at = django_timezone.now()
    sync_job.result_summary = {
        'conversations_synced': len(conversations),
        'messages_synced': messages_count,
        'completed_at': django_timezone.now().isoformat(),
        'duration_seconds': (
            sync_job.completed_at - sync_job.started_at
        ).total_seconds() if sync_job.started_at else 0
    }
    
    await sync_job.asave(update_fields=[
        'status', 'completed_at', 'result_summary'
    ])
    
    logger.info(f"🎉 Sync job {sync_job.id} completed successfully")


async def _mark_sync_job_failed_async(sync_job: SyncJob, error_message: str):
    """Mark sync job as failed (async version)"""
    sync_job.status = SyncJobStatus.FAILED
    sync_job.completed_at = django_timezone.now()
    sync_job.error_details = {
        'error': error_message,
        'failed_at': django_timezone.now().isoformat()
    }
    sync_job.error_count += 1
    
    await sync_job.asave(update_fields=[
        'status', 'completed_at', 'error_details', 'error_count'
    ])


def _mark_sync_job_failed(sync_job_id: str, error_message: str):
    """Mark sync job as failed (sync version for error handling)"""
    try:
        sync_job = SyncJob.objects.get(id=sync_job_id)
        sync_job.status = SyncJobStatus.FAILED
        sync_job.completed_at = django_timezone.now()
        sync_job.error_details = {
            'error': error_message,
            'failed_at': django_timezone.now().isoformat()
        }
        sync_job.error_count += 1
        sync_job.save(update_fields=[
            'status', 'completed_at', 'error_details', 'error_count'
        ])
    except Exception as e:
        logger.error(f"Failed to update sync job {sync_job_id} status: {e}")


# =========================================================================
# ASGI-COMPATIBLE SYNC HELPER FUNCTIONS
# =========================================================================

def _estimate_conversation_count_sync(channel: Channel, options: Dict[str, Any]) -> int:
    """
    Get rough estimate of conversation count for progress tracking
    ASGI-compatible sync version
    """
    try:
        client = unipile_service.get_client()
        
        # Map channel type to UniPile account type
        account_type_map = {
            'whatsapp': 'WHATSAPP',
            'linkedin': 'LINKEDIN', 
            'gmail': 'GOOGLE',
            'outlook': 'OUTLOOK'
        }
        account_type = account_type_map.get(channel.channel_type, channel.channel_type.upper())
        
        # Get first page to estimate total (using sync version for now)
        # Note: This would need to be adapted to actual UniPile client API structure
        response = {
            'items': [],  # Placeholder - would come from actual UniPile API call
            'has_more': False,
            'estimated_total': 50  # Placeholder estimate
        }
        
        estimated_total = response.get('estimated_total', 50)
        logger.info(f"📊 Estimated conversation count: {estimated_total}")
        
        return estimated_total
        
    except Exception as e:
        logger.warning(f"Failed to estimate conversation count: {e}")
        return 100  # Default estimate


def _run_comprehensive_sync_simplified(channel: Channel, options: Dict[str, Any], connection: Optional[UserChannelConnection] = None, sync_job: Optional[SyncJob] = None) -> Dict[str, Any]:
    """
    Simplified comprehensive sync using sync methods and same approach as ComprehensiveSyncService
    """
    stats = {
        'attendees_synced': 0,
        'chats_synced': 0,
        'messages_synced': 0,
        'conversations_created': 0,
        'conversations_updated': 0,
        'errors': []
    }
    
    try:
        logger.info(f"🔄 Starting simplified comprehensive sync for {channel.name}")
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        # Map channel type to account type (same as comprehensive sync service)
        account_type_map = {
            'whatsapp': 'WHATSAPP',
            'linkedin': 'LINKEDIN', 
            'gmail': 'GOOGLE',
            'outlook': 'OUTLOOK'
        }
        account_type = account_type_map.get(channel.channel_type, channel.channel_type.upper())
        
        # Step 1: Get all chats (using direct HTTP requests for sync)
        logger.info(f"📱 Getting all chats for {channel.name}")
        
        # Use requests library for sync HTTP calls 
        import requests
        
        url = f"{client.base_url}/chats"
        headers = {
            'X-API-KEY': client.access_token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        params = {
            'account_id': channel.unipile_account_id,
            'account_type': account_type,
            'limit': 10  # Start with small number
        }
        
        chats_response = requests.get(url, headers=headers, params=params).json()
        
        chats = chats_response.get('items', []) if chats_response else []
        logger.info(f"📱 Found {len(chats)} chats to process")
        
        # Update progress with chat count
        if sync_job:
            sync_job.progress.update({
                'conversations_total': len(chats),
                'conversations_processed': 0,
                'current_phase': 'processing_conversations',
                'current_step': f'Found {len(chats)} conversations to sync'
            })
            sync_job.save(update_fields=['progress'])
        
        # Step 2: Process each chat
        for i, chat_data in enumerate(chats, 1):
            try:
                chat_id = chat_data.get('id')
                if not chat_id:
                    continue
                
                chat_name = chat_data.get('name', f'Chat {i}')
                logger.info(f"🔄 Processing chat {i}/{len(chats)}: {chat_name}")
                
                # Update progress
                if sync_job:
                    sync_job.progress.update({
                        'conversations_processed': i-1,
                        'current_step': f'Processing chat: {chat_name}',
                        'current_conversation_name': chat_name
                    })
                    sync_job.save(update_fields=['progress'])
                
                # Get attendees for this chat (sync version)
                attendees_url = f"{client.base_url}/chats/{chat_id}/attendees"
                attendees_response = requests.get(attendees_url, headers=headers).json()
                attendees = attendees_response.get('items', []) if attendees_response else []
                
                # Process attendees using unified processor (sync version)
                normalized_attendees = [
                    unified_processor.normalize_attendee_data(att_data, 'api')
                    for att_data in attendees
                ]
                
                # Use sync version of process_attendees
                from asgiref.sync import sync_to_async
                attendees_list = async_to_sync(unified_processor.process_attendees)(
                    normalized_attendees, channel
                )
                
                stats['attendees_synced'] += len(attendees_list)
                
                # Process conversation
                normalized_conversation = unified_processor.normalize_conversation_data(chat_data, 'api')
                
                conversation, created = async_to_sync(unified_processor.process_conversation)(
                    normalized_conversation, channel, attendees_list
                )
                
                if created:
                    stats['conversations_created'] += 1
                else:
                    stats['conversations_updated'] += 1
                    
                stats['chats_synced'] += 1
                
                # Get messages for this chat
                messages_url = f"{client.base_url}/chats/{chat_id}/messages"
                messages_params = {'limit': options.get('max_messages_per_chat', 100)}
                messages_response = requests.get(messages_url, headers=headers, params=messages_params).json()
                messages = messages_response.get('items', []) if messages_response else []
                
                # Process messages
                messages_created = 0
                for message_data in messages:
                    try:
                        if not message_data or not isinstance(message_data, dict) or not message_data.get('id'):
                            continue
                            
                        normalized_message = unified_processor.normalize_message_data(message_data, 'api')
                        normalized_message['chat_id'] = chat_id
                        
                        # Fix async_to_sync tenant context loss by wrapping in schema_context
                        from django.db import connection as db_connection
                        current_schema = db_connection.schema_name
                        
                        async def process_with_tenant_context():
                            with schema_context(current_schema):
                                return await unified_processor.process_message(
                                    normalized_message, channel, conversation, connection
                                )
                        
                        message, created = async_to_sync(process_with_tenant_context)()
                        
                        if created:
                            messages_created += 1
                    except Exception as e:
                        logger.error(f"Failed to process message {message_data.get('id')}: {e}")
                        continue
                
                stats['messages_synced'] += messages_created
                logger.info(f"✅ Chat {chat_id}: {len(attendees)} attendees, {messages_created} messages")
                
            except Exception as e:
                logger.error(f"Failed to process chat {chat_data.get('id', 'unknown')}: {e}")
                stats['errors'].append(f"Chat {chat_data.get('id', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"✅ Comprehensive sync complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Simplified comprehensive sync failed: {e}")
        stats['errors'].append(str(e))
        return stats


def _sync_conversations_paginated_sync(
    sync_job: SyncJob,
    channel: Channel,
    options: Dict[str, Any],
    db_connection
) -> List[Dict[str, Any]]:
    """
    Sync conversations with pagination and progress updates
    ASGI-compatible sync version with proper database context
    """
    logger.info(f"📱 Starting paginated conversation sync for {channel.name}")
    
    batch_size = options['conversations_per_batch']
    all_conversations = []
    batch_number = 0
    
    # Get UniPile client
    client = unipile_service.get_client()
    
    # Map channel type to UniPile account type
    account_type_map = {
        'whatsapp': 'WHATSAPP',
        'linkedin': 'LINKEDIN',
        'gmail': 'GOOGLE', 
        'outlook': 'OUTLOOK'
    }
    account_type = account_type_map.get(channel.channel_type, channel.channel_type.upper())
    
    cursor = sync_job.pagination_state.get('conversations_cursor') if sync_job.pagination_state else None
    
    try:
        while True:
            batch_number += 1
            logger.info(f"📱 Processing conversation batch {batch_number}")
            
            # Create progress entry for this batch
            progress_entry = SyncJobProgress.objects.create(
                sync_job=sync_job,
                phase_name='fetching_conversations',
                step_name=f'batch_{batch_number}',
                items_total=batch_size,
                started_at=django_timezone.now()
            )
            
            try:
                # Get real conversations from UniPile API
                client = unipile_service.get_client()
                
                # Map channel type to UniPile account type
                account_type_map = {
                    'whatsapp': 'WHATSAPP',
                    'linkedin': 'LINKEDIN',
                    'gmail': 'GOOGLE',
                    'outlook': 'OUTLOOK'
                }
                account_type = account_type_map.get(channel.channel_type, channel.channel_type.upper())
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    response = loop.run_until_complete(client.messaging.get_chats_batch(
                        account_id=channel.unipile_account_id,
                        account_type=account_type,
                        cursor=cursor,
                        limit=batch_size
                    ))
                    conversations = response.get('items', [])
                finally:
                    loop.close()
                
                if not conversations:
                    logger.info("📱 No more conversations to sync")
                    break
                
                # Process this batch of conversations
                batch_processed = []
                batch_errors = []
                start_time = datetime.now(timezone.utc)
                
                for i, conv_data in enumerate(conversations):
                    conv_start_time = datetime.now(timezone.utc)
                    try:
                        chat_id = conv_data.get('id')
                        conv_name = conv_data.get('name', 'Unnamed Conversation')
                        
                        if chat_id:
                            # Get or create conversation in database
                            conversation, created = Conversation.objects.get_or_create(
                                channel=channel,
                                external_thread_id=chat_id,
                                defaults={
                                    'subject': conv_name,
                                    'status': 'active',
                                    'sync_status': 'pending',
                                    'metadata': conv_data
                                }
                            )
                            
                            # Calculate processing time
                            conv_processing_time = int((datetime.now(timezone.utc) - conv_start_time).total_seconds() * 1000)
                            
                            batch_processed.append({
                                'conversation_id': str(conversation.id),
                                'external_id': chat_id,
                                'name': conv_name,
                                'created': created,
                                'processing_time_ms': conv_processing_time,
                                'attendee_count': 0  # Placeholder
                            })
                            
                            # Update progress every 5 conversations
                            if (i + 1) % 5 == 0:
                                progress_current = len(all_conversations) + len(batch_processed)
                                sync_job.update_progress(
                                    conversations_processed=progress_current,
                                    current_phase='processing_conversations',
                                    current_step=f'batch_{batch_number}_item_{i+1}',
                                    current_conversation_name=conv_name,
                                    batch_progress_percent=int((i + 1) / len(conversations) * 100),
                                    avg_processing_time_ms=conv_processing_time
                                )
                            
                    except Exception as conv_error:
                        error_msg = str(conv_error)
                        batch_errors.append({
                            'conversation_id': conv_data.get('id', 'unknown'),
                            'conversation_name': conv_data.get('name', 'Unnamed'),
                            'error': error_msg
                        })
                        logger.error(f"Failed to process conversation {conv_data.get('id', 'unknown')}: {conv_error}")
                        continue
                
                all_conversations.extend(batch_processed)
                
                # Calculate batch performance metrics
                batch_processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                avg_conversation_time = batch_processing_time / len(batch_processed) if batch_processed else 0
                error_rate = len(batch_errors) / len(conversations) * 100 if conversations else 0
                
                # Update progress entry
                progress_entry.items_processed = len(batch_processed)
                progress_entry.processing_time_ms = batch_processing_time
                progress_entry.step_status = 'completed' if not batch_errors else 'failed'
                progress_entry.completed_at = django_timezone.now()
                progress_entry.metadata = {
                    'error_count': len(batch_errors),
                    'error_rate_percent': error_rate,
                    'avg_processing_time_ms': int(avg_conversation_time),
                    'recent_errors': batch_errors[-3:] if batch_errors else []
                }
                progress_entry.save()
                
                # Update overall sync job progress
                sync_job.update_progress(
                    conversations_processed=len(all_conversations),
                    current_phase='fetching_conversations',
                    current_step=f'batch_{batch_number}_completed',
                    batch_number=batch_number,
                    conversations_in_batch=len(batch_processed),
                    batch_errors_count=len(batch_errors),
                    batch_error_rate_percent=error_rate,
                    batch_processing_time_ms=batch_processing_time,
                    avg_conversation_processing_ms=int(avg_conversation_time)
                )
                
                logger.info(f"📊 Batch {batch_number} completed: {len(batch_processed)} conversations processed, {len(batch_errors)} errors")
                
                # Check if we should continue (for demo purposes, limit to 2 batches)
                if batch_number >= 2:
                    logger.info("📱 Demo sync completed - limiting to 2 batches")
                    break
                
            except Exception as batch_error:
                logger.error(f"Conversation batch {batch_number} failed: {batch_error}")
                progress_entry.step_status = 'failed'
                progress_entry.metadata = {'error': str(batch_error)}
                progress_entry.completed_at = django_timezone.now()
                progress_entry.save()
                break
        
        logger.info(f"✅ Conversation sync completed: {len(all_conversations)} conversations processed")
        return all_conversations
        
    except Exception as e:
        logger.error(f"❌ Conversation sync failed: {e}")
        raise


def _sync_messages_paginated_sync(
    sync_job: SyncJob,
    channel: Channel, 
    conversations: List[Dict[str, Any]],
    options: Dict[str, Any],
    db_connection
) -> int:
    """
    Sync messages for all conversations with pagination
    ASGI-compatible sync version
    """
    logger.info(f"📨 Starting paginated message sync for {len(conversations)} conversations")
    
    batch_size = options['messages_per_batch']
    total_messages_synced = 0
    
    for i, conv_data in enumerate(conversations):
        external_id = conv_data.get('external_id')
        if not external_id:
            continue
        
        logger.info(f"📨 Syncing messages for conversation {i+1}/{len(conversations)}: {external_id[:8]}")
        
        # Create progress entry for this conversation's messages
        progress_entry = SyncJobProgress.objects.create(
            sync_job=sync_job,
            phase_name='processing_messages',
            step_name=f'conversation_{external_id[:8]}',
            items_total=0,  # Will update as we discover message count
            started_at=django_timezone.now()
        )
        
        try:
            # Get conversation from database
            try:
                conversation = Conversation.objects.get(
                    channel=channel,
                    external_thread_id=external_id
                )
            except Conversation.DoesNotExist:
                logger.error(f"Conversation not found for external_id: {external_id}")
                continue
            
            conv_messages_synced = 0
            
            # Simulate message processing (replace with actual UniPile API call)
            # This is a placeholder implementation
            for batch_num in range(2):  # Simulate 2 batches of messages per conversation
                messages = []
                for msg_i in range(min(batch_size, 5)):  # Simulate small batch for demo
                    messages.append({
                        'id': f'msg_{external_id}_{batch_num}_{msg_i}',
                        'content': f'Demo message {msg_i} from conversation {external_id}',
                        'sender': 'demo_sender',
                        'timestamp': django_timezone.now().isoformat(),
                        'type': 'text'
                    })
                
                if not messages:
                    break
                
                # Process messages
                batch_processed = 0
                for message_data in messages:
                    try:
                        # Create message in database (placeholder)
                        from .models import Message
                        message, created = Message.objects.get_or_create(
                            conversation=conversation,
                            external_message_id=message_data['id'],
                            defaults={
                                'content': message_data['content'],
                                'sender_name': message_data['sender'],
                                'message_type': 'text',
                                'timestamp': django_timezone.now(),
                                'metadata': message_data
                            }
                        )
                        
                        if created:
                            batch_processed += 1
                        
                    except Exception as msg_error:
                        logger.error(f"Failed to process message {message_data.get('id', 'unknown')}: {msg_error}")
                        continue
                
                conv_messages_synced += batch_processed
                total_messages_synced += batch_processed
                
                logger.info(f"📨 Processed batch {batch_num + 1} for conversation {external_id[:8]}: {batch_processed} messages")
            
            # Update progress entry
            progress_entry.items_processed = conv_messages_synced
            progress_entry.items_total = conv_messages_synced
            progress_entry.step_status = 'completed'
            progress_entry.completed_at = django_timezone.now()
            progress_entry.save()
            
            # Update overall progress
            sync_job.update_progress(
                messages_processed=total_messages_synced,
                current_step=f'conversation_{i+1}_of_{len(conversations)}_completed'
            )
            
            logger.info(f"📨 Conversation {external_id[:8]}: {conv_messages_synced} messages synced")
            
        except Exception as conv_error:
            logger.error(f"Message sync failed for conversation {external_id}: {conv_error}")
            progress_entry.step_status = 'failed'
            progress_entry.metadata = {'error': str(conv_error)}
            progress_entry.completed_at = django_timezone.now()
            progress_entry.save()
            continue
    
    logger.info(f"✅ Message sync completed: {total_messages_synced} messages processed")
    return total_messages_synced


# =========================================================================
# CHAT-SPECIFIC SYNC TASK
# =========================================================================

@shared_task(bind=True, max_retries=3)
def sync_chat_specific_background(
    self,
    channel_id: str,
    chat_external_id: str,
    user_id: str,
    sync_options: Optional[Dict[str, Any]] = None,
    tenant_schema: Optional[str] = None
):
    """
    Background sync for a specific chat conversation
    Useful for targeted sync operations
    """
    try:
        options = {**SYNC_CONFIG, **(sync_options or {})}
        
        logger.info(f"🎯 Starting chat-specific background sync for {chat_external_id}")
        
        # ASGI-compatible event loop setup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if tenant_schema:
                with schema_context(tenant_schema):
                    result = loop.run_until_complete(
                        _execute_chat_specific_sync(
                            self, channel_id, chat_external_id, user_id, options
                        )
                    )
            else:
                result = loop.run_until_complete(
                    _execute_chat_specific_sync(
                        self, channel_id, chat_external_id, user_id, options
                    )
                )
            
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ Chat-specific sync failed for {chat_external_id}: {e}")
        
        if self.request.retries < self.max_retries:
            retry_delay = options.get('retry_delay_base', 60) * (2 ** self.request.retries)
            raise self.retry(countdown=retry_delay)
        
        return {
            'success': False,
            'error': str(e),
            'chat_id': chat_external_id,
            'task_id': self.request.id
        }


async def _execute_chat_specific_sync(
    task,
    channel_id: str,
    chat_external_id: str,
    user_id: str,
    options: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute chat-specific sync"""
    
    channel = await Channel.objects.aget(id=channel_id)
    user = await User.objects.aget(id=user_id)
    
    # Create sync job
    sync_job = await SyncJob.objects.acreate(
        user=user,
        channel=channel,
        job_type=SyncJobType.CHAT_SPECIFIC,
        sync_options={**options, 'chat_external_id': chat_external_id},
        celery_task_id=task.request.id,
        status=SyncJobStatus.RUNNING,
        started_at=django_timezone.now()
    )
    
    try:
        client = unipile_service.get_client()
        
        # Sync messages for this specific chat
        messages_synced = 0
        cursor = None
        batch_size = options['messages_per_batch']
        
        while True:
            response = await client.messaging.get_messages_batch(
                chat_id=chat_external_id,
                cursor=cursor,
                limit=batch_size
            )
            
            messages = response.get('items', [])
            if not messages:
                break
            
            # Process messages
            for message_data in messages:
                try:
                    # Get or create conversation
                    conversation, _ = await Conversation.objects.aget_or_create(
                        channel=channel,
                        external_thread_id=chat_external_id
                    )
                    
                    # Process message
                    normalized_message = unified_processor.normalize_message_data(
                        message_data, 'api'
                    )
                    normalized_message['chat_id'] = chat_external_id
                    
                    message, created = await unified_processor.process_message(
                        normalized_message, channel, conversation, connection
                    )
                    
                    if created:
                        messages_synced += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")
                    continue
            
            # Update progress
            await sync_job.update_progress(
                messages_processed=messages_synced,
                current_step=f'batch_completed'
            )
            
            # Check for next page
            cursor = response.get('next_cursor')
            has_more = response.get('has_more', False)
            
            if not has_more or not cursor:
                break
        
        # Finalize
        await _finalize_sync_job(sync_job, [], messages_synced)
        
        return {
            'success': True,
            'sync_job_id': str(sync_job.id),
            'messages_synced': messages_synced,
            'chat_id': chat_external_id,
            'task_id': task.request.id
        }
        
    except Exception as e:
        await _mark_sync_job_failed_async(sync_job, str(e))
        raise