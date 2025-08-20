"""
Django signals for automatic account data synchronization
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync

from communications.models import UserChannelConnection

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserChannelConnection)
def auto_sync_account_details(sender, instance, created, **kwargs):
    """
    Automatically sync account details when a connection becomes active
    
    Triggers when:
    - A new connection is created with active status
    - An existing connection changes to active status
    - A connection gets a UniPile account ID for the first time
    """
    
    # Only process active, authenticated connections with UniPile account IDs
    if not (instance.is_active and 
            instance.account_status == 'active' and 
            instance.auth_status == 'authenticated' and 
            instance.unipile_account_id):
        return
    
    # Check if this connection needs account details sync
    needs_sync = False
    
    if created:
        # New connection - always sync
        needs_sync = True
        logger.info(f"🆕 New active connection detected: {instance.unipile_account_id}")
    else:
        # Existing connection - check if it just became active or got account ID
        try:
            # Get the previous state from database
            old_instance = UserChannelConnection.objects.get(pk=instance.pk)
            
            # Check if status changed to active
            if (old_instance.account_status != 'active' and instance.account_status == 'active'):
                needs_sync = True
                logger.info(f"🔄 Connection became active: {instance.unipile_account_id}")
            
            # Check if UniPile account ID was just added
            if (not old_instance.unipile_account_id and instance.unipile_account_id):
                needs_sync = True
                logger.info(f"🔗 UniPile account ID added: {instance.unipile_account_id}")
            
            # Check if account details are missing (empty config)
            if not instance.connection_config or not instance.provider_config:
                needs_sync = True
                logger.info(f"📊 Missing account configuration: {instance.unipile_account_id}")
                
        except UserChannelConnection.DoesNotExist:
            # This shouldn't happen but handle gracefully
            needs_sync = True
            logger.warning(f"⚠️ Could not find previous connection state for {instance.pk}")
    
    if needs_sync:
        # Sync account details asynchronously
        try:
            from communications.services.account_sync import account_sync_service
            
            # Use async_to_sync to call the async sync function
            sync_result = async_to_sync(account_sync_service.sync_account_details)(instance)
            
            if sync_result.get('success'):
                logger.info(f"✅ Auto-synced account details via signal for {instance.unipile_account_id}")
                logger.info(f"   📱 Phone: {sync_result.get('phone_number', 'N/A')}")
                logger.info(f"   🔗 Type: {sync_result.get('account_type', 'N/A')}")
                logger.info(f"   📊 Status: {sync_result.get('messaging_status', 'N/A')}")
            else:
                logger.warning(f"⚠️ Auto-sync failed via signal for {instance.unipile_account_id}: {sync_result.get('error')}")
                
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