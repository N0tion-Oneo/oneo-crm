"""
Django signals for automatic account data synchronization
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone as django_timezone
from asgiref.sync import async_to_sync

from communications.models import UserChannelConnection

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserChannelConnection)
def auto_sync_account_details(sender, instance, created, **kwargs):
    """
    Automatically sync account details when a connection is first established
    
    Triggers ONLY when:
    - A new connection is created with active status
    - An existing connection transitions from inactive to active for the first time
    - A connection gets a UniPile account ID for the first time
    
    Does NOT trigger on:
    - Subsequent saves after initial sync
    - Updates to already active connections
    """
    
    # Only process active, authenticated connections with UniPile account IDs
    if not (instance.is_active and 
            instance.account_status == 'active' and 
            instance.auth_status == 'authenticated' and 
            instance.unipile_account_id):
        return
    
    # Check if initial sync has already been performed
    # We use last_sync_at as an indicator that initial sync has been done
    if instance.last_sync_at:
        logger.debug(f"⏭️ Skipping auto-sync for {instance.unipile_account_id} - already synced at {instance.last_sync_at}")
        return
    
    # Check if this connection needs initial sync
    needs_sync = False
    
    if created:
        # New connection - always sync
        needs_sync = True
        logger.info(f"🆕 New active connection detected: {instance.unipile_account_id}")
    else:
        # For existing connections, only sync if specific fields changed
        # We check update_fields to see what actually changed
        update_fields = kwargs.get('update_fields', [])
        
        # If update_fields is provided, check if relevant fields changed
        if update_fields:
            # If only last_sync_at was updated, skip (this is the sync marking itself complete)
            if update_fields == ['last_sync_at']:
                logger.debug(f"⏭️ Skipping - only last_sync_at updated for {instance.unipile_account_id}")
                return
            
            # Only trigger sync if these specific fields were updated
            sync_trigger_fields = {'account_status', 'auth_status', 'unipile_account_id'}
            if sync_trigger_fields.intersection(update_fields):
                # One of the trigger fields changed - check if it's a meaningful change
                # This means the connection just became active or got its account ID
                needs_sync = True
                logger.info(f"🔄 Connection status changed for: {instance.unipile_account_id}")
            else:
                # Other fields changed - don't trigger sync
                logger.debug(f"📝 Non-sync fields updated for {instance.unipile_account_id}: {update_fields}")
                return
        else:
            # No update_fields means a full save() was called
            # Only sync if this looks like an initial activation
            # (no last_sync_at and has required fields)
            if not instance.last_sync_at:
                needs_sync = True
                logger.info(f"🔗 Initial activation detected for: {instance.unipile_account_id}")
    
    if needs_sync:
        # Trigger comprehensive sync for the newly connected account
        try:
            # Import based on channel type
            if instance.channel_type == 'whatsapp':
                from communications.channels.whatsapp.sync.tasks import sync_account_comprehensive_background
                from communications.channels.whatsapp.sync.config import get_sync_options
                
                # Get or create channel for this account
                from communications.models import Channel
                channel, created = Channel.objects.get_or_create(
                    unipile_account_id=instance.unipile_account_id,
                    channel_type='whatsapp',
                    defaults={
                        'name': f'WhatsApp - {instance.account_name}',
                        'auth_status': 'authenticated',
                        'is_active': True,
                        'created_by': instance.user
                    }
                )
                
                # Trigger background sync
                logger.info(f"🚀 Triggering comprehensive sync for {instance.unipile_account_id}")
                
                # Get tenant schema if in multi-tenant environment
                tenant_schema = None
                if hasattr(instance, '_state') and hasattr(instance._state, 'db'):
                    from django.db import connection
                    if hasattr(connection, 'tenant'):
                        tenant_schema = connection.tenant.schema_name
                
                # Queue the sync task with centralized config
                sync_options = get_sync_options()  # Use defaults for auto-sync
                
                result = sync_account_comprehensive_background.delay(
                    channel_id=str(channel.id),
                    user_id=str(instance.user.id),
                    sync_options=sync_options,
                    tenant_schema=tenant_schema
                )
                
                logger.info(f"✅ Queued sync task {result.id} for {instance.unipile_account_id}")
                
                # Mark that we've initiated the initial sync
                # Update last_sync_at to prevent re-triggering
                # Use update() to avoid triggering the signal again
                UserChannelConnection.objects.filter(pk=instance.pk).update(
                    last_sync_at=django_timezone.now()
                )
                logger.info(f"📝 Marked initial sync timestamp for {instance.unipile_account_id}")
                
            else:
                # Other channel types not yet implemented
                logger.info(f"ℹ️ Auto-sync not implemented for {instance.channel_type} channels")
                
        except Exception as e:
            logger.error(f"❌ Error during auto-sync signal for {instance.unipile_account_id}: {e}")
            # Don't raise the exception to avoid breaking the save operation
    else:
        logger.debug(f"⏭️ Skipping auto-sync for {instance.unipile_account_id} - no sync needed")


@receiver(post_save, sender=UserChannelConnection)
def log_connection_changes(sender, instance, created, **kwargs):
    """
    Log important connection changes for debugging
    """
    if created:
        logger.info(f"🆕 UserChannelConnection created: {instance.id}")
        logger.info(f"   User: {instance.user.email}")
        logger.info(f"   Channel: {instance.channel_type}")
        logger.info(f"   Account Status: {instance.account_status}")
        logger.info(f"   Auth Status: {instance.auth_status}")
        logger.info(f"   UniPile Account ID: {instance.unipile_account_id or 'Not assigned'}")
    else:
        logger.debug(f"🔄 UserChannelConnection updated: {instance.id}")
        logger.debug(f"   Account Status: {instance.account_status}")
        logger.debug(f"   Auth Status: {instance.auth_status}")
        logger.debug(f"   Config Keys: {len(instance.connection_config.keys()) if instance.connection_config else 0}")
        logger.debug(f"   Provider Keys: {len(instance.provider_config.keys()) if instance.provider_config else 0}")