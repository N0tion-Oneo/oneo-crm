"""
Signal handlers for real-time feature integration
"""
import json
import time
import asyncio
from threading import Thread
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


def safe_group_send_sync(channel_layer, group_name, message):
    """
    Safely send message to channel group from sync context.
    Handles event loop issues properly.
    """
    import asyncio
    import threading
    
    logger.debug(f"🔄 WEBSOCKET SEND: Attempting to send message to group '{group_name}' - type: {message.get('type', 'unknown')}")
    
    try:
        # First approach: use async_to_sync directly (works when no active event loop)
        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.debug(f"✅ WEBSOCKET SEND SUCCESS (async_to_sync): {group_name} - {message.get('type', 'unknown')}")
        return
    except RuntimeError as e:
        if "async event loop" in str(e).lower():
            # There's an active event loop - try alternative approaches
            logger.debug(f"🔄 Active event loop detected, trying alternative approaches for {group_name}")
        else:
            logger.error(f"❌ WEBSOCKET SEND FAILED (async_to_sync): {group_name} - {e}")
            return
    except Exception as e:
        logger.error(f"❌ WEBSOCKET SEND FAILED (async_to_sync): {group_name} - {e}")
        return
    
    # Second approach: try asyncio.run (works when no event loop at all)
    try:
        asyncio.run(channel_layer.group_send(group_name, message))
        logger.debug(f"✅ WEBSOCKET SEND SUCCESS (asyncio.run): {group_name} - {message.get('type', 'unknown')}")
        return
    except RuntimeError as e:
        if "running event loop" in str(e).lower():
            logger.debug(f"🔄 Event loop already running, trying thread-based approach for {group_name}")
        else:
            logger.error(f"❌ WEBSOCKET SEND FAILED (asyncio.run): {group_name} - {e}")
            return
    except Exception as e:
        logger.error(f"❌ WEBSOCKET SEND FAILED (asyncio.run): {group_name} - {e}")
        return
    
    # Third approach: run in a separate thread (works when there's an active event loop)
    try:
        def run_in_thread():
            asyncio.run(channel_layer.group_send(group_name, message))
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=5)  # 5 second timeout
        
        if thread.is_alive():
            logger.error(f"❌ WEBSOCKET SEND TIMEOUT: {group_name} - thread timed out after 5 seconds")
        else:
            logger.debug(f"✅ WEBSOCKET SEND SUCCESS (thread): {group_name} - {message.get('type', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ WEBSOCKET SEND FAILED (thread): {group_name} - {e}")


async def safe_group_send(channel_layer, group_name, message):
    """Safely send message to channel group"""
    try:
        await channel_layer.group_send(group_name, message)
        logger.debug(f"Sent message to group {group_name}: {message.get('type', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to send message to group {group_name}: {e}")


# Import models when they're available
try:
    from pipelines.models import Pipeline, Record, Field
    from relationships.models import Relationship
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("Pipeline/Relationship models not available for real-time signals")

# Import communication models for sync job progress tracking
try:
    from communications.models import SyncJob, SyncJobProgress
    COMMUNICATION_MODELS_AVAILABLE = True
except ImportError:
    COMMUNICATION_MODELS_AVAILABLE = False
    logger.warning("Communication models not available for real-time signals")

if MODELS_AVAILABLE:
    
    @receiver(post_save, sender=Record)
    def handle_record_saved(sender, instance, created, **kwargs):
        """Handle record creation/update/soft deletion for real-time broadcasting"""
        logger.debug(f"📡 REALTIME SIGNAL: post_save triggered for record {instance.id}")
        logger.debug(f"   🆕 Created: {created}")
        logger.debug(f"   🗑️  Is Deleted: {instance.is_deleted}")
        
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.debug(f"   ⏸️  No channel layer available, exiting")
                return
            
            # Get updated record count for the pipeline (exclude soft deleted)
            new_record_count = Record.objects.filter(pipeline_id=instance.pipeline_id, is_deleted=False).count()
            
            # Check if this is a soft deletion
            if not created and instance.is_deleted:
                # This is a soft deletion - broadcast as record_deleted
                event_data = {
                    'type': 'record_deleted',
                    'record_id': str(instance.id),
                    'pipeline_id': str(instance.pipeline_id),
                    'title': getattr(instance, 'title', f'Record {instance.id}'),
                    'new_count': new_record_count,  # Updated count after deletion
                    'timestamp': time.time()
                }
                
                # Broadcast to pipeline subscribers
                pipeline_group = f"pipeline_records_{instance.pipeline_id}"
                safe_group_send_sync(channel_layer, pipeline_group, {
                    'type': 'record_deleted',
                    'data': event_data
                })
                
                # Broadcast to document subscribers
                document_group = f"document_{instance.id}"
                safe_group_send_sync(channel_layer, document_group, {
                    'type': 'document_deleted',
                    'data': event_data
                })
                
                # Store for SSE subscribers
                store_sse_message(
                    f"pipeline_records_{instance.pipeline_id}",
                    event_data
                )
                
                logger.debug(f"Broadcasted record soft deleted: {instance.id}")
                return
            
            # Handle normal creation/update (not soft deletion)
            if not instance.is_deleted:  # Only broadcast if record is not deleted
                # Debug logging removed for production
                
                # Create event data
                event_data = {
                    'type': 'record_created' if created else 'record_updated',
                    'record_id': str(instance.id),
                    'pipeline_id': str(instance.pipeline_id),
                    'title': getattr(instance, 'title', f'Record {instance.id}'),
                    'data': instance.data,  # Use the actual saved data, not cleaned data
                    'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
                    'updated_by': {
                        'id': instance.updated_by.id if instance.updated_by else None,
                        'username': instance.updated_by.username if instance.updated_by else None,
                    },
                    'new_count': new_record_count,  # Add the updated count
                    'timestamp': time.time()
                }
                
                
                # Broadcast to pipeline subscribers
                pipeline_group = f"pipeline_records_{instance.pipeline_id}"
                safe_group_send_sync(channel_layer, pipeline_group, {
                    'type': 'record_update',
                    'data': event_data
                })
                
                # Broadcast to document subscribers (for collaborative editing)
                document_group = f"document_{instance.id}"
                safe_group_send_sync(channel_layer, document_group, {
                    'type': 'document_updated',
                    'data': event_data
                })
                
                # Store for SSE subscribers
                store_sse_message(
                    f"pipeline_records_{instance.pipeline_id}",
                    event_data
                )
                
                # Activity logging now handled by AuditLog system in pipelines/signals.py
                
                logger.debug(f"Broadcasted record {'created' if created else 'updated'}: {instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling record save signal: {e}")
    
    
    @receiver(post_delete, sender=Record)
    def handle_record_deleted(sender, instance, **kwargs):
        """Handle record deletion for real-time broadcasting"""
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Get updated record count for the pipeline (after deletion)
            new_record_count = Record.objects.filter(pipeline_id=instance.pipeline_id).count()
            
            # Create event data
            event_data = {
                'type': 'record_deleted',
                'record_id': str(instance.id),
                'pipeline_id': str(instance.pipeline_id),
                'title': getattr(instance, 'title', f'Record {instance.id}'),
                'new_count': new_record_count,  # Add the updated count
                'timestamp': time.time()
            }
            
            # Broadcast to pipeline subscribers
            pipeline_group = f"pipeline_records_{instance.pipeline_id}"
            safe_group_send_sync(channel_layer, pipeline_group, {
                'type': 'record_deleted',
                'data': event_data
            })
            
            # Broadcast to document subscribers
            document_group = f"document_{instance.id}"
            safe_group_send_sync(channel_layer, document_group, {
                'type': 'document_deleted',
                'data': event_data
            })
            
            # Store for SSE subscribers
            store_sse_message(
                f"pipeline_records_{instance.pipeline_id}",
                event_data
            )
            
            logger.debug(f"Broadcasted record deleted: {instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling record delete signal: {e}")
    
    
    @receiver(post_save, sender=Pipeline)
    def handle_pipeline_saved(sender, instance, created, **kwargs):
        """Handle pipeline creation/update for real-time broadcasting"""
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Create event data
            event_data = {
                'type': 'pipeline_created' if created else 'pipeline_updated',
                'pipeline_id': str(instance.id),
                'name': instance.name,
                'description': instance.description,
                'pipeline_type': getattr(instance, 'pipeline_type', 'custom'),
                'is_active': getattr(instance, 'is_active', True),
                'timestamp': time.time()
            }
            
            # Broadcast to general pipeline subscribers
            safe_group_send_sync(channel_layer, "pipeline_updates", {
                'type': 'pipeline_update',
                'data': event_data
            })
            
            # Broadcast to specific pipeline subscribers
            pipeline_group = f"pipeline_updates_{instance.id}"
            safe_group_send_sync(channel_layer, pipeline_group, {
                'type': 'pipeline_update',
                'data': event_data
            })
            
            # Store for SSE subscribers
            store_sse_message("global_activity", event_data)
            
            logger.debug(f"Broadcasted pipeline {'created' if created else 'updated'}: {instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling pipeline save signal: {e}")
    
    
    @receiver(post_save, sender=Relationship)
    def handle_relationship_saved(sender, instance, created, **kwargs):
        """Handle relationship creation for real-time broadcasting"""
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Create event data
            event_data = {
                'type': 'relationship_created' if created else 'relationship_updated',
                'relationship_id': str(instance.id),
                'source_record_id': str(instance.source_record_id),
                'target_record_id': str(instance.target_record_id),
                'relationship_type': str(instance.relationship_type_id),
                'strength': float(instance.strength) if hasattr(instance, 'strength') else 1.0,
                'timestamp': time.time()
            }
            
            # Broadcast to relationship subscribers
            safe_group_send_sync(channel_layer, "relationship_updates", {
                'type': 'relationship_update',
                'data': event_data
            })
            
            # Broadcast to both record documents
            for record_id in [instance.source_record_id, instance.target_record_id]:
                document_group = f"document_{record_id}"
                safe_group_send_sync(channel_layer, document_group, {
                    'type': 'relationship_update',
                    'data': event_data
                })
            
            logger.debug(f"Broadcasted relationship {'created' if created else 'updated'}: {instance.id}")
            
        except Exception as e:
            logger.error(f"Error handling relationship save signal: {e}")


    @receiver(post_save, sender=Field)
    def handle_field_saved(sender, instance, created, **kwargs):
        """Handle field creation/update for real-time broadcasting"""
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            
            # Create event data
            event_data = {
                'type': 'field_created' if created else 'field_updated',
                'field_id': str(instance.id),
                'pipeline_id': str(instance.pipeline_id),
                'name': instance.name,
                'display_name': getattr(instance, 'display_name', instance.name),
                'field_type': instance.field_type,
                'display_order': instance.display_order,
                'field_group_id': str(instance.field_group_id) if instance.field_group_id else None,
                'is_visible_in_list': getattr(instance, 'is_visible_in_list', True),
                'timestamp': time.time()
            }
            
            # Broadcast to pipeline field subscribers
            pipeline_group = f"pipeline_fields_{instance.pipeline_id}"
            safe_group_send_sync(channel_layer, pipeline_group, {
                'type': 'field_update',
                'data': event_data
            })
            
            # Broadcast to general pipeline subscribers (for field count updates)
            safe_group_send_sync(channel_layer, "pipeline_updates", {
                'type': 'field_update',
                'data': event_data
            })
            
            # Store for SSE subscribers
            store_sse_message("global_activity", event_data)
            
            logger.debug(f"Broadcasted field {'created' if created else 'updated'}: {instance.name} (Pipeline: {instance.pipeline_id})")
            
        except Exception as e:
            logger.error(f"Error handling field save signal: {e}")


    @receiver(post_delete, sender=Field)  
    def handle_field_deleted(sender, instance, **kwargs):
        """Handle field deletion for real-time broadcasting"""
        logger.debug(f"🔥 FIELD DELETE SIGNAL FIRED: Field {instance.id} ({instance.name}) deleted from pipeline {instance.pipeline_id}")
        
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.debug(f"📡 No channel layer available for field delete signal")
                return
            
            # Create event data
            event_data = {
                'type': 'field_deleted',
                'field_id': str(instance.id),
                'pipeline_id': str(instance.pipeline_id),
                'name': instance.name,
                'timestamp': time.time()
            }
            
            logger.debug(f"📡 Broadcasting field delete to WebSocket groups:")
            logger.debug(f"   🎯 Target group: pipeline_fields_{instance.pipeline_id}")
            logger.debug(f"   📦 Event data: {event_data}")
            
            # Broadcast to pipeline field subscribers
            pipeline_group = f"pipeline_fields_{instance.pipeline_id}"
            safe_group_send_sync(channel_layer, pipeline_group, {
                'type': 'field_delete',
                'data': event_data
            })
            
            # Broadcast to general pipeline subscribers
            safe_group_send_sync(channel_layer, "pipeline_updates", {
                'type': 'field_delete', 
                'data': event_data
            })
            
            # Store for SSE subscribers
            store_sse_message("global_activity", event_data)
            
            logger.debug(f"✅ Successfully broadcasted field deleted: {instance.name} (Pipeline: {instance.pipeline_id})")
            
        except Exception as e:
            logger.error(f"❌ Error handling field delete signal: {e}")
            logger.error(f"❌ Field: {instance.id} ({instance.name})")
            logger.error(f"❌ Pipeline: {instance.pipeline_id}")


def store_sse_message(channel: str, event_data: dict):
    """Store message for SSE subscribers"""
    try:
        # This is a simplified approach - in production, you'd want to 
        # maintain subscriber lists and send to specific users
        message_key = f"sse_channel_messages:{channel}"
        messages = cache.get(message_key, [])
        
        messages.append({
            'type': event_data.get('type', 'update'),
            'data': event_data,
            'timestamp': time.time()
        })
        
        # Keep only recent messages
        if len(messages) > 100:
            messages = messages[-100:]
        
        cache.set(message_key, messages, 600)  # 10 minute TTL
        
    except Exception as e:
        logger.error(f"Error storing SSE message: {e}")


def store_activity_event(activity_data: dict):
    """
    Deprecated function - now a no-op since activity data comes from AuditLog.
    
    This function previously stored activity data in Redis cache, but now that we're using
    AuditLog as the single source of truth, this function is kept only for backward 
    compatibility with existing tests and any remaining references.
    
    The actual activity data is now:
    1. Stored in AuditLog database by pipelines/signals.py
    2. Retrieved by get_recent_activity() from AuditLog  
    3. Broadcast via WebSocket by broadcast_audit_log_update()
    """
    logger.debug("store_activity_event() called - activity data now comes from AuditLog system")


# Additional utility functions for real-time features
def broadcast_user_notification(user_id: int, notification_data: dict):
    """Broadcast notification to specific user"""
    try:
        # Store for SSE
        message_key = f"sse_messages:{user_id}:user_notifications:{user_id}"
        messages = cache.get(message_key, [])
        
        messages.append({
            'type': 'notification',
            'data': notification_data,
            'timestamp': time.time()
        })
        
        if len(messages) > 20:
            messages = messages[-20:]
        
        cache.set(message_key, messages, 600)
        
        # Update unread count
        unread_key = f"unread_notifications:{user_id}"
        current_count = cache.get(unread_key, 0)
        cache.set(unread_key, current_count + 1, 3600)
        
        logger.debug(f"Broadcasted notification to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting user notification: {e}")


def broadcast_system_announcement(announcement_data: dict):
    """Broadcast system-wide announcement"""
    try:
        # Store for all SSE subscribers
        message_key = "sse_channel_messages:system_notifications"
        messages = cache.get(message_key, [])
        
        messages.append({
            'type': 'system_announcement',
            'data': announcement_data,
            'timestamp': time.time()
        })
        
        if len(messages) > 10:
            messages = messages[-10:]
        
        cache.set(message_key, messages, 1800)
        
        logger.debug("Broadcasted system announcement")
        
    except Exception as e:
        logger.error(f"Error broadcasting system announcement: {e}")


def broadcast_audit_log_update(audit_log, record_instance):
    """
    Broadcast audit log updates for real-time Activity tab updates
    Replaces the redundant activity logger functionality
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        # Format audit log data for real-time consumption (matching Activity tab expectations)
        activity_data = {
            'id': audit_log.id,
            'type': 'field_change' if audit_log.action == 'updated' else 'system',
            'message': _format_audit_changes_for_realtime(audit_log.changes, audit_log.action),
            'user': {
                'first_name': audit_log.user.first_name if audit_log.user else '',
                'last_name': audit_log.user.last_name if audit_log.user else '',
                'email': audit_log.user.email if audit_log.user else ''
            } if audit_log.user else None,
            'created_at': audit_log.timestamp.isoformat(),
            'record_id': str(record_instance.id),
            'pipeline_id': str(record_instance.pipeline_id)
        }

        # Broadcast to document subscribers (Activity tab listens to this)
        document_group = f"document_{record_instance.id}"
        
        safe_group_send_sync(channel_layer, document_group, {
            'type': 'activity_update',
            'data': activity_data
        })

        # Also store for SSE subscribers
        store_sse_message(
            f"record_activity_{record_instance.id}",
            activity_data
        )

        logger.debug(f"Broadcasted audit log update for record {record_instance.id}")

    except Exception as e:
        logger.error(f"Error broadcasting audit log update: {e}")


def _format_audit_changes_for_realtime(changes, action):
    """Format audit log changes for real-time Activity tab consumption"""
    if action == 'created':
        return f"Record created in {changes.get('pipeline_name', 'Unknown')} pipeline"
    
    elif action == 'updated':
        # Use pre-formatted change summaries from AuditLog
        if 'changes_summary' in changes and changes['changes_summary']:
            return '\n'.join(changes['changes_summary'])
        
        # Fallback to basic message
        total_changes = changes.get('total_changes', 0)
        return f"Record updated ({total_changes} field{'s' if total_changes != 1 else ''} changed)"
    
    elif action == 'deleted':
        return f"Record deleted from {changes.get('pipeline_name', 'Unknown')} pipeline"
    
    # Sharing-related actions with rich descriptions
    elif action == 'shared_record':
        primary = changes.get('primary_message', 'Shared record with external users')
        secondary = changes.get('secondary_message', '')
        if secondary:
            return f"🔗 {primary}\n{secondary}"
        return f"🔗 {primary}"
    
    elif action == 'external_access':
        # Always show it's an external user
        primary = changes.get('primary_message', 'External user accessed record')
        secondary = changes.get('secondary_message', '')
        if secondary:
            return f"🌐 {primary}\n{secondary}"
        return f"🌐 {primary}"
    
    elif action == 'external_edit':
        # Always show it's an external user
        primary = changes.get('primary_message', 'External user edited record')
        secondary = changes.get('secondary_message', '')
        # Show field changes if available
        if 'changes_detailed' in changes and changes['changes_detailed']:
            changes_text = '\n'.join(changes['changes_detailed'][:3])  # Show first 3 changes
            if len(changes['changes_detailed']) > 3:
                changes_text += f"\n... and {len(changes['changes_detailed']) - 3} more"
            return f"🌐 {primary}\n{secondary}\n\nChanges:\n{changes_text}"
        elif secondary:
            return f"🌐 {primary}\n{secondary}"
        return f"🌐 {primary}"
    
    elif action == 'share_revoked':
        revoked_by = changes.get('revoked_by', 'Unknown')
        access_count = changes.get('access_count', 0)
        return f"Share link revoked by {revoked_by}\nHad {access_count} access{'es' if access_count != 1 else ''}"
    
    elif action == 'share_deleted':
        access_count = changes.get('access_count', 0)
        return f"Share link deleted\nHad {access_count} access{'es' if access_count != 1 else ''}"
    
    return f"Record {action}"


# =========================================================================
# SYNC JOB PROGRESS SIGNAL HANDLERS
# =========================================================================

if COMMUNICATION_MODELS_AVAILABLE:
    
    @receiver(post_save, sender=SyncJob)
    def handle_sync_job_saved(sender, instance, created, **kwargs):
        """Handle sync job creation/update for real-time progress tracking"""
        logger.debug(f"📡 SYNC JOB SIGNAL: Sync job {instance.id} {'created' if created else 'updated'}")
        logger.debug(f"   🔄 Status: {instance.status}")
        logger.debug(f"   📊 Progress: {instance.progress}")
        
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.debug(f"   ⏸️  No channel layer available for sync job signal")
                return
            
            # Create event data for sync job update
            event_data = {
                'type': 'sync_job_created' if created else 'sync_job_updated',
                'sync_job_id': str(instance.id),
                'celery_task_id': instance.celery_task_id,  # Frontend needs this to match stored jobs
                'channel_id': str(instance.channel_id),
                'user_id': str(instance.user_id),
                'job_type': instance.job_type,
                'status': instance.status,
                'progress': instance.progress or {},
                'result_summary': instance.result_summary or {},
                'error_details': instance.error_details or {},
                'error_count': instance.error_count,
                'started_at': instance.started_at.isoformat() if instance.started_at else None,
                'completed_at': instance.completed_at.isoformat() if instance.completed_at else None,
                'last_progress_update': instance.last_progress_update.isoformat() if instance.last_progress_update else None,
                'completion_percentage': instance.completion_percentage,
                'is_active': instance.is_active,
                'timestamp': time.time()
            }
            
            logger.debug(f"📡 Broadcasting sync job update:")
            logger.debug(f"   🎯 Target groups: sync_jobs_{instance.user_id}, sync_job_{instance.id}")
            logger.debug(f"   📊 Progress: {instance.completion_percentage}%")
            logger.debug(f"   🔄 Status: {instance.status}")
            logger.debug(f"   🔑 Celery Task ID: {instance.celery_task_id}")
            logger.debug(f"   📋 Event Data Debug: {event_data}")
            
            # Primary broadcast: Celery task ID channel (used by frontend)
            if instance.celery_task_id:
                celery_task_group = f"sync_progress_{instance.celery_task_id}"
                progress_data = {
                    'type': 'sync_progress_update',
                    'celery_task_id': instance.celery_task_id,
                    'sync_job_id': str(instance.id),
                    'status': instance.status,
                    'progress': instance.progress or {},
                    'completion_percentage': instance.completion_percentage,
                    'updated_at': instance.last_progress_update.isoformat() if instance.last_progress_update else None,
                    'timestamp': time.time()
                }
                safe_group_send_sync(channel_layer, celery_task_group, progress_data)
                logger.debug(f"   📡 Broadcasting sync progress to: {celery_task_group}")
            
            # Optional: Keep user sync jobs channel for potential dashboard use
            user_sync_group = f"sync_jobs_{instance.user_id}"
            safe_group_send_sync(channel_layer, user_sync_group, {
                'type': 'sync_job_update',
                'data': event_data
            })
            
            # Store for SSE subscribers
            store_sse_message(
                f"sync_jobs_{instance.user_id}",
                event_data
            )
            
            logger.debug(f"✅ Successfully broadcasted sync job {'created' if created else 'updated'}: {instance.id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling sync job signal: {e}")
            logger.error(f"❌ Sync job: {instance.id}")
    
    
    @receiver(post_save, sender=SyncJobProgress)
    def handle_sync_job_progress_saved(sender, instance, created, **kwargs):
        """Handle sync job progress updates for real-time progress tracking"""
        logger.debug(f"📡 SYNC PROGRESS SIGNAL: Progress entry {instance.id} {'created' if created else 'updated'}")
        logger.debug(f"   🏷️  Phase: {instance.phase_name} - Step: {instance.step_name}")
        logger.debug(f"   📈 Progress: {instance.items_processed}/{instance.items_total} ({instance.completion_percentage}%)")
        
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.debug(f"   ⏸️  No channel layer available for sync progress signal")
                return
            
            # Create event data for progress update
            event_data = {
                'type': 'sync_progress_updated',
                'progress_id': str(instance.id),
                'sync_job_id': str(instance.sync_job_id),
                'phase_name': instance.phase_name,
                'step_name': instance.step_name,
                'items_processed': instance.items_processed,
                'items_total': instance.items_total,
                'completion_percentage': instance.completion_percentage,
                'step_status': instance.step_status,
                'processing_time_ms': instance.processing_time_ms,
                'memory_usage_mb': instance.memory_usage_mb,
                'metadata': instance.metadata or {},
                'started_at': instance.started_at.isoformat() if instance.started_at else None,
                'completed_at': instance.completed_at.isoformat() if instance.completed_at else None,
                'timestamp': time.time()
            }
            
            logger.debug(f"📡 Broadcasting sync progress update:")
            logger.debug(f"   🎯 Target groups: sync_job_{instance.sync_job_id}")
            logger.debug(f"   📈 Progress: {instance.completion_percentage}% ({instance.items_processed}/{instance.items_total})")
            logger.debug(f"   🏷️  Step: {instance.phase_name}.{instance.step_name}")
            
            # Get sync job to determine user
            try:
                sync_job = instance.sync_job
                
                # Broadcast to user's sync jobs channel
                user_sync_group = f"sync_jobs_{sync_job.user_id}"
                safe_group_send_sync(channel_layer, user_sync_group, {
                    'type': 'sync_progress_update',
                    'data': event_data
                })
                
                # Broadcast to specific sync job channel
                sync_job_group = f"sync_job_{instance.sync_job_id}"
                safe_group_send_sync(channel_layer, sync_job_group, {
                    'type': 'sync_progress_update',
                    'data': event_data
                })
                
                # Store for SSE subscribers
                store_sse_message(
                    f"sync_jobs_{sync_job.user_id}",
                    event_data
                )
                
                logger.debug(f"✅ Successfully broadcasted sync progress update: {instance.id}")
                
            except Exception as job_error:
                logger.error(f"❌ Failed to get sync job for progress broadcast: {job_error}")
            
        except Exception as e:
            logger.error(f"❌ Error handling sync progress signal: {e}")
            logger.error(f"❌ Progress entry: {instance.id}")