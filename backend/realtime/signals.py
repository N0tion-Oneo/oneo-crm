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
import hashlib

logger = logging.getLogger(__name__)

# Broadcast deduplication cache (prevents duplicate messages within 1 second)
_broadcast_cache = {}
_cache_cleared_at = time.time()


def _should_broadcast(record_id, data_hash):
    """Prevent duplicate broadcasts within 1 second window"""
    global _broadcast_cache, _cache_cleared_at

    # Clear cache every second
    now = time.time()
    if now - _cache_cleared_at > 1.0:
        _broadcast_cache.clear()
        _cache_cleared_at = now

    cache_key = f"{record_id}_{data_hash}"
    if cache_key in _broadcast_cache:
        logger.debug(f"⏭️ Skipping duplicate broadcast for record {record_id}")
        return False

    _broadcast_cache[cache_key] = now
    return True


def _get_data_hash(data):
    """Generate hash of data for deduplication"""
    try:
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()
    except:
        return str(hash(str(data)))


def safe_group_send_sync(channel_layer, group_name, message):
    """
    Safely send message to channel group from sync context.
    Handles event loop issues properly.
    """
    import asyncio
    import threading

    logger.debug(f"🔄 WEBSOCKET SEND: Attempting to send message to group '{group_name}' - type: {message.get('type', 'unknown')}")

    # Critical fix: Check if channel_layer is None before attempting to use it
    if channel_layer is None:
        logger.error(f"❌ WEBSOCKET SEND FAILED: channel_layer is None for group '{group_name}'")
        logger.error(f"❌ This indicates the Django Channels Redis layer is not properly initialized")
        return

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
                logger.debug(f"🔄 WEBSOCKET: Processing record save for {instance.id} (created: {created})")

                # Get complete data including relation fields
                # CRITICAL: Always fetch fresh relation field data, don't rely on instance.data
                complete_data = instance.data.copy() if instance.data else {}
                logger.debug(f"📦 Base record data: {list(complete_data.keys())}")

                # Add relation field data from Relationship table with display values
                # This ensures we get the LATEST relation data even if sync happened after record save
                from pipelines.relation_field_handler import RelationFieldHandler
                relation_fields = instance.pipeline.fields.filter(field_type='relation', is_deleted=False)
                logger.debug(f"🔗 Found {relation_fields.count()} relation fields to process")

                for field in relation_fields:
                    try:
                        handler = RelationFieldHandler(field)
                        related_ids = handler.get_related_ids(instance)
                        logger.debug(f"🔗 Field '{field.slug}' related IDs: {related_ids}")

                        # Convert IDs to objects with display values
                        if related_ids is not None:
                            display_field = field.field_config.get('display_field', 'title')

                            if isinstance(related_ids, list):
                                # Multiple relations
                                related_objects = []
                                for record_id in related_ids:
                                    try:
                                        related_record = Record.objects.get(id=record_id)
                                        display_value = related_record.data.get(display_field) or related_record.title or f"Record #{record_id}"
                                        related_objects.append({
                                            'id': record_id,
                                            'display_value': display_value
                                        })
                                    except Record.DoesNotExist:
                                        related_objects.append({
                                            'id': record_id,
                                            'display_value': f"Record #{record_id} (deleted)"
                                        })
                                complete_data[field.slug] = related_objects
                                logger.debug(f"✅ Set multiple relation data for '{field.slug}': {len(related_objects)} items")
                            else:
                                # Single relation
                                try:
                                    related_record = Record.objects.get(id=related_ids)
                                    display_value = related_record.data.get(display_field) or related_record.title or f"Record #{related_ids}"
                                    complete_data[field.slug] = {
                                        'id': related_ids,
                                        'display_value': display_value
                                    }
                                    logger.debug(f"✅ Set single relation data for '{field.slug}': {related_ids}")
                                except Record.DoesNotExist:
                                    complete_data[field.slug] = {
                                        'id': related_ids,
                                        'display_value': f"Record #{related_ids} (deleted)"
                                    }
                        else:
                            complete_data[field.slug] = None
                            logger.debug(f"➖ No relation data for '{field.slug}'")
                    except Exception as e:
                        logger.error(f"❌ Failed to get relation data for field {field.slug}: {e}")
                        complete_data[field.slug] = None

                # Detect if any relation fields changed (for relationship_changed flag)
                has_relation_changes = False
                if not created and hasattr(instance, '_change_context'):
                    try:
                        from pipelines.record_operations import ChangeContext
                        change_ctx = instance._change_context
                        if isinstance(change_ctx, ChangeContext):
                            # Check if any changed fields are relation fields
                            relation_field_slugs = set(
                                field.slug for field in relation_fields
                            )
                            has_relation_changes = bool(
                                change_ctx.changed_fields & relation_field_slugs
                            )
                            logger.debug(f"   🔍 Relation change detection: {has_relation_changes}")
                    except:
                        pass

                # Create event data with complete user information
                event_data = {
                    'type': 'record_created' if created else 'record_updated',
                    'record_id': str(instance.id),
                    'pipeline_id': str(instance.pipeline_id),
                    'title': getattr(instance, 'title', f'Record {instance.id}'),
                    'data': complete_data,  # Use complete data with relation fields
                    'relationship_changed': has_relation_changes,  # Add relationship change flag
                    'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
                    'created_by': {
                        'id': instance.created_by.id if instance.created_by else None,
                        'first_name': instance.created_by.first_name if instance.created_by else None,
                        'last_name': instance.created_by.last_name if instance.created_by else None,
                        'email': instance.created_by.email if instance.created_by else None,
                    } if instance.created_by else None,
                    'updated_by': {
                        'id': instance.updated_by.id if instance.updated_by else None,
                        'first_name': instance.updated_by.first_name if instance.updated_by else None,
                        'last_name': instance.updated_by.last_name if instance.updated_by else None,
                        'email': instance.updated_by.email if instance.updated_by else None,
                    } if instance.updated_by else None,
                    'created_at': instance.created_at.isoformat() if instance.created_at else None,
                    'new_count': new_record_count,  # Add the updated count
                    'timestamp': time.time()
                }


                # Check if we should broadcast (deduplication)
                data_hash = _get_data_hash(complete_data)
                if not _should_broadcast(instance.id, data_hash):
                    logger.debug(f"⏭️ Skipping duplicate broadcast for record {instance.id}")
                    return

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
        logger.info(f"🚀 PIPELINE SIGNAL FIRED: Pipeline {instance.id} ({instance.name}) {'created' if created else 'updated'}")
        logger.info(f"   📦 Icon value: {instance.icon}")
        
        try:
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.warning("No channel layer available for pipeline signal")
                return
            
            # Create event data
            event_data = {
                'type': 'pipeline_created' if created else 'pipeline_updated',
                'pipeline_id': str(instance.id),
                'name': instance.name,
                'description': instance.description,
                'icon': instance.icon,  # Include the icon field
                'pipeline_type': getattr(instance, 'pipeline_type', 'custom'),
                'is_active': getattr(instance, 'is_active', True),
                'record_count': instance.record_count,  # Include record count
                'timestamp': time.time()
            }
            
            # Broadcast to general pipeline subscribers
            logger.info(f"📡 Broadcasting pipeline update to 'pipeline_updates' channel")
            logger.info(f"   📦 Event data: {event_data}")
            safe_group_send_sync(channel_layer, "pipeline_updates", {
                'type': 'pipeline_update',
                'data': event_data
            })
            logger.info(f"✅ Pipeline update broadcast complete")
            
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
        """Handle relationship creation and updates for real-time broadcasting"""
        # LOG SIGNAL ENTRY
        logger.info(f"🚨 SIGNAL FIRED: post_save for Relationship {instance.id}")
        logger.info(f"   🆕 Created: {created}")
        logger.info(f"   📍 Source: {instance.source_record_id} → Target: {instance.target_record_id}")
        logger.info(f"   🏷️ Type: {instance.relationship_type_id}")
        logger.info(f"   🗑️ Is Deleted: {instance.is_deleted}")

        # Handle soft deletion - treat as deletion event
        if instance.is_deleted and not created:
            logger.info(f"🗑️ WEBSOCKET: Processing relationship soft deletion - ID: {instance.id}")
            _handle_relationship_deletion(instance, "soft_deleted")
            return

        # Handle resurrection - relationship was soft deleted but now is active again
        # This happens when is_deleted=False and created=False (existing relationship being reactivated)
        if not instance.is_deleted and not created:
            logger.info(f"🔄 WEBSOCKET: Processing relationship resurrection/update - ID: {instance.id}")
            logger.info(f"   🔍 DEBUG: created={created}, is_deleted={instance.is_deleted}")
            # Trigger record updates for both sides to refresh display fields
            _trigger_record_updates_for_relationship(instance, "resurrected")
            return

        # Handle new relationship creation
        if created:
            logger.info(f"🆕 WEBSOCKET: Processing new relationship creation - ID: {instance.id}")
            # Trigger record updates for both sides to refresh display fields
            _trigger_record_updates_for_relationship(instance, "created")
            return

        # If we get here, something unexpected happened
        logger.warning(f"⚠️ WEBSOCKET: Unexpected relationship signal state - ID: {instance.id}, created: {created}, is_deleted: {instance.is_deleted}")


    def _trigger_record_update_for_relationship_change(relationship_instance, is_created, channel_layer=None):
        """
        Trigger record update broadcasts for both sides of a relationship change.
        This ensures that relation field data is updated in real-time in record lists and drawers.
        """
        try:
            # CRITICAL FIX: Always get fresh channel layer instead of relying on parameter
            if channel_layer is None:
                channel_layer = get_channel_layer()
                logger.info(f"🔍 CHANNEL FIX: Retrieved fresh channel_layer = {channel_layer}")

            if channel_layer is None:
                logger.error(f"❌ WEBSOCKET: Cannot proceed - channel_layer is None even after fresh retrieval")
                return

            logger.info(f"🔄 WEBSOCKET: Starting record updates for relationship change")
            # Get both records involved in the relationship
            record_ids = [relationship_instance.source_record_id, relationship_instance.target_record_id]
            logger.info(f"   📋 Will update records: {record_ids}")

            for record_id in record_ids:
                try:
                    logger.info(f"   🔍 Processing record {record_id}...")
                    # Get the record
                    record = Record.objects.get(id=record_id, is_deleted=False)
                    logger.info(f"   ✅ Found record {record_id} in pipeline {record.pipeline.name}")

                    # Get complete data including updated relation fields
                    # CRITICAL: Always fetch fresh relation field data
                    complete_data = record.data.copy() if record.data else {}
                    logger.info(f"   📦 Base data fields: {list(complete_data.keys())}")

                    # Add relation field data from Relationship table with display values
                    from pipelines.relation_field_handler import RelationFieldHandler
                    relation_fields = record.pipeline.fields.filter(field_type='relation', is_deleted=False)
                    logger.info(f"   🔗 Found {relation_fields.count()} relation fields to update")

                    for field in relation_fields:
                        try:
                            handler = RelationFieldHandler(field)
                            related_ids = handler.get_related_ids(record)
                            logger.info(f"   🔗 Field '{field.slug}' has related IDs: {related_ids}")

                            # Convert IDs to objects with display values
                            if related_ids is not None:
                                if isinstance(related_ids, list):
                                    # Multiple relations - use handler method for proper display values
                                    logger.info(f"   🔄 Getting display values for multiple relations in '{field.slug}'")
                                    related_objects = handler.get_related_records_with_display(record)
                                    if related_objects is None:
                                        related_objects = []
                                    complete_data[field.slug] = related_objects
                                    logger.info(f"   ✅ Set {len(related_objects)} related objects for '{field.slug}'")
                                else:
                                    # Single relation - use handler method for proper display values
                                    logger.info(f"   🔄 Getting display value for single relation in '{field.slug}'")
                                    related_object = handler.get_related_records_with_display(record)
                                    complete_data[field.slug] = related_object
                                    if related_object:
                                        logger.info(f"   ✅ Set single related object for '{field.slug}': {related_object.get('display_value', 'N/A')}")
                                    else:
                                        logger.info(f"   ⚠️ No related object found for '{field.slug}'")

                                # Skip the manual display value logic - handler already does this properly
                                logger.info(f"   ✅ Updated relation field '{field.slug}' with proper display values")
                                continue

                            # Fallback for when there are no related IDs
                            if isinstance(related_ids, list):
                                complete_data[field.slug] = []
                            else:
                                complete_data[field.slug] = None

                        except Exception as field_e:
                            logger.error(f"   ❌ Error processing relation field '{field.slug}': {field_e}")
                            # Set empty value on error
                            if field.field_config.get('allow_multiple', False):
                                complete_data[field.slug] = []
                            else:
                                complete_data[field.slug] = None

                    # Now trigger the actual WebSocket broadcasts with updated relation data
                    logger.info(f"   📡 Broadcasting record update to WebSocket channels...")

                    # Create the record event data with FLAT structure and relationship_changed flag
                    record_event_data = {
                        'type': 'record_updated',
                        'record_id': str(record.id),
                        'pipeline_id': str(record.pipeline_id),
                        'title': record.title,
                        'data': complete_data,
                        'relationship_changed': True,  # Flag to indicate this was a relationship change
                        'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                        'timestamp': time.time()
                    }

                    # Check if we should broadcast (deduplication)
                    data_hash = _get_data_hash(complete_data)
                    if not _should_broadcast(record.id, data_hash):
                        logger.info(f"   ⏭️ Skipping duplicate broadcast for record {record.id}")
                        continue

                    # Broadcast to pipeline-specific record channel with FLAT structure
                    pipeline_record_group = f"pipeline_records_{record.pipeline_id}"
                    safe_group_send_sync(channel_layer, pipeline_record_group, {
                        'type': 'record_update',
                        'data': record_event_data
                    })
                    logger.info(f"   📡 → Pipeline channel: {pipeline_record_group}")

                    # Broadcast to document-specific channel (for record drawer)
                    document_group = f"document_{record.id}"
                    safe_group_send_sync(channel_layer, document_group, {
                        'type': 'document_updated',
                        'data': record_event_data
                    })
                    logger.info(f"   📡 → Document channel: {document_group}")

                    # Broadcast to pipelines overview (for pipeline list with record counts)
                    pipelines_overview_group = "pipelines_overview"
                    safe_group_send_sync(channel_layer, pipelines_overview_group, {
                        'type': 'record_update',
                        'data': record_event_data
                    })
                    logger.info(f"   📡 → Overview channel: {pipelines_overview_group}")

                    logger.info(f"   ✅ Successfully triggered record update for record {record.id}")

                except Record.DoesNotExist:
                    logger.warning(f"   ⚠️ Record {record_id} not found or deleted - skipping WebSocket update")
                except Exception as record_e:
                    logger.error(f"   ❌ Error processing record {record_id}: {record_e}")

            logger.info(f"🏁 WEBSOCKET: Completed record updates for relationship change")

        except Exception as e:
            logger.error(f"❌ WEBSOCKET: Error in _trigger_record_update_for_relationship_change: {e}")
            import traceback
            logger.error(f"❌ WEBSOCKET: Traceback: {traceback.format_exc()}")


    @receiver(post_delete, sender=Relationship)
    def handle_relationship_deleted(sender, instance, **kwargs):
        """Handle hard relationship deletion for real-time broadcasting"""
        logger.info(f"🚨 SIGNAL FIRED: post_delete for Relationship {instance.id}")
        logger.info(f"   📍 Source: {instance.source_record_id} → Target: {instance.target_record_id}")
        logger.info(f"   🏷️ Type: {instance.relationship_type_id}")

        _handle_relationship_deletion(instance, "hard_deleted")


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


def _handle_relationship_deletion(instance, deletion_type):
    """Unified handler for both soft and hard relationship deletions"""
    try:
        logger.info(f"🗑️ WEBSOCKET: Processing relationship {deletion_type} - ID: {instance.id}")
        logger.info(f"   📍 Source: {instance.source_record_id} → Target: {instance.target_record_id}")

        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning(f"❌ No channel layer available for relationship {deletion_type} signal")
            return

        # Create event data
        event_data = {
            'type': 'relationship_deleted',
            'relationship_id': str(instance.id),
            'source_record_id': str(instance.source_record_id),
            'target_record_id': str(instance.target_record_id),
            'relationship_type': str(instance.relationship_type_id),
            'deletion_type': deletion_type,
            'timestamp': time.time()
        }

        logger.info(f"📡 Broadcasting {deletion_type} to channels...")

        # Broadcast to relationship subscribers
        safe_group_send_sync(channel_layer, "relationship_updates", {
            'type': 'relationship_delete',
            'data': event_data
        })

        # Broadcast to both record documents
        for record_id in [instance.source_record_id, instance.target_record_id]:
            document_group = f"document_{record_id}"
            safe_group_send_sync(channel_layer, document_group, {
                'type': 'relationship_delete',
                'data': event_data
            })

        # CRITICAL: Trigger record updates for both sides to refresh relation field data
        logger.info(f"🔄 WEBSOCKET: Triggering record updates for both sides of {deletion_type} relationship")
        _trigger_record_update_for_relationship_change(instance, False, channel_layer)

        logger.info(f"✅ WEBSOCKET: Successfully processed relationship {deletion_type}: {instance.id}")

    except Exception as e:
        logger.error(f"❌ WEBSOCKET: Error handling relationship {deletion_type}: {e}")
        import traceback
        logger.error(f"❌ WEBSOCKET: Traceback: {traceback.format_exc()}")


def _trigger_record_updates_for_relationship(instance, action_type):
    """
    Trigger record updates for both sides of a relationship to refresh display fields
    Used for relationship creation and resurrection to ensure WebSocket updates include display values
    """
    try:
        logger.info(f"🔄 WEBSOCKET: Triggering record updates for relationship {action_type} - ID: {instance.id}")

        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning(f"❌ No channel layer available for relationship {action_type} record updates")
            return

        # Determine if this is a creation action
        is_created = action_type == "created"

        # Use the existing function to trigger record updates
        _trigger_record_update_for_relationship_change(instance, is_created, channel_layer)

        logger.info(f"✅ WEBSOCKET: Successfully triggered record updates for relationship {action_type}: {instance.id}")

    except Exception as e:
        logger.error(f"❌ WEBSOCKET: Error triggering record updates for relationship {action_type}: {e}")
        import traceback
        logger.error(f"❌ WEBSOCKET: Traceback: {traceback.format_exc()}")