"""
Authentication signals for real-time permission updates
Automatically broadcasts permission changes to connected WebSocket clients
"""
import logging
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from django.contrib.auth import get_user_model
from .models import UserType

User = get_user_model()

logger = logging.getLogger(__name__)


def get_tenant_schema():
    """Get current tenant schema name for cache key generation"""
    from django_tenants.utils import get_tenant_model
    from django.db import connection
    
    try:
        if hasattr(connection, 'tenant'):
            return connection.tenant.schema_name
        return 'public'
    except:
        return 'public'


@receiver(post_save, sender=UserType)
def on_user_type_saved(sender, instance, created, **kwargs):
    """
    Handle UserType creation/modification
    Broadcasts permission changes to all users of this type
    """
    try:
        tenant_schema = get_tenant_schema()
        
        # Get all users with this user type
        affected_users = User.objects.filter(user_type=instance)
        
        # Broadcast permission changes via WebSocket
        channel_layer = get_channel_layer()
        if channel_layer:
            message = {
                'type': 'permission_change',
                'data': {
                    'event_type': 'user_type_updated',
                    'user_type_id': instance.id,
                    'user_type_name': instance.name,
                    'affected_users': [user.id for user in affected_users],
                    'created': created,
                    'tenant_schema': tenant_schema,
                    'timestamp': instance.updated_at.isoformat() if hasattr(instance, 'updated_at') else None
                }
            }
            
            # Send to tenant-wide permission update channel
            async_to_sync(channel_layer.group_send)(
                f'tenant_permissions_{tenant_schema}',
                {
                    'type': 'send_permission_update',
                    'message': message
                }
            )
            
            # Send to individual user channels
            for user in affected_users:
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}',
                    {
                        'type': 'send_permission_update', 
                        'message': message
                    }
                )
        
        logger.info(f"Permission cache cleared and broadcast sent for UserType {instance.id} ({instance.name})")
        
    except Exception as e:
        logger.error(f"Error handling UserType save signal: {e}")


@receiver(post_delete, sender=UserType)
def on_user_type_deleted(sender, instance, **kwargs):
    """
    Handle UserType deletion
    Broadcasts permission changes and handles orphaned users
    """
    try:
        tenant_schema = get_tenant_schema()
        
        # Find users who may be affected (this is called after deletion, so they might have NULL user_type)
        potentially_affected_users = User.objects.filter(user_type__isnull=True)
        
        # Broadcast permission changes via WebSocket
        channel_layer = get_channel_layer()
        if channel_layer:
            message = {
                'type': 'permission_change',
                'data': {
                    'event_type': 'user_type_deleted',
                    'user_type_id': instance.id,
                    'user_type_name': instance.name,
                    'potentially_affected_users': [user.id for user in potentially_affected_users],
                    'tenant_schema': tenant_schema,
                    'timestamp': None  # Deletion doesn't have an updated_at
                }
            }
            
            # Send to tenant-wide permission update channel
            async_to_sync(channel_layer.group_send)(
                f'tenant_permissions_{tenant_schema}',
                {
                    'type': 'send_permission_update',
                    'message': message
                }
            )
        
        logger.info(f"Permission cache cleared and broadcast sent for deleted UserType {instance.id} ({instance.name})")
        
    except Exception as e:
        logger.error(f"Error handling UserType delete signal: {e}")


@receiver(post_save, sender=User)
def on_user_saved(sender, instance, created, **kwargs):
    """
    Handle User creation/modification
    Broadcast if user type changed
    """
    try:
        tenant_schema = get_tenant_schema()
        
        # Check if this is a user type change (not creation)
        user_type_changed = False
        if not created:
            # Get the previous version from the database to compare
            try:
                old_instance = User.objects.get(id=instance.id)
                if hasattr(old_instance, '_state') and old_instance._state.db:
                    # This means we have the previous state
                    user_type_changed = old_instance.user_type_id != instance.user_type_id
            except:
                # If we can't determine the old state, assume it changed
                user_type_changed = True
        
        # Only broadcast if user type changed or user was created
        if created or user_type_changed:
            channel_layer = get_channel_layer()
            if channel_layer:
                message = {
                    'type': 'permission_change',
                    'data': {
                        'event_type': 'user_updated' if not created else 'user_created',
                        'user_id': instance.id,
                        'user_email': instance.email,
                        'user_type_id': instance.user_type_id,
                        'user_type_name': instance.user_type.name if instance.user_type else None,
                        'user_type_changed': user_type_changed,
                        'created': created,
                        'tenant_schema': tenant_schema,
                        'timestamp': instance.updated_at.isoformat() if hasattr(instance, 'updated_at') else None
                    }
                }
                
                # Send to user's own channel
                async_to_sync(channel_layer.group_send)(
                    f'user_{instance.id}',
                    {
                        'type': 'send_permission_update',
                        'message': message
                    }
                )
                
                # If this affects multiple people (admin user changes), send to tenant channel
                if instance.user_type and instance.user_type.name in ['Admin', 'Manager']:
                    async_to_sync(channel_layer.group_send)(
                        f'tenant_permissions_{tenant_schema}',
                        {
                            'type': 'send_permission_update',
                            'message': message
                        }
                    )
        
        logger.info(f"Permission changes broadcasted for User {instance.id} ({instance.email})")
        
    except Exception as e:
        logger.error(f"Error handling User save signal: {e}")


# Note: UserType now uses JSONB base_permissions instead of M2M permissions
# Permission changes are broadcasted via the post_save signal on UserType


def trigger_manual_permission_refresh(user_id=None, user_type_id=None, tenant_schema=None):
    """
    Manual function to trigger permission refresh for specific users or user types
    Useful for administrative actions or batch updates
    """
    try:
        if not tenant_schema:
            tenant_schema = get_tenant_schema()
        
        affected_users = []
        
        if user_id:
            # Refresh specific user
            try:
                user = User.objects.get(id=user_id)
                affected_users = [user]
            except User.DoesNotExist:
                logger.warning(f"User {user_id} not found for manual permission refresh")
                return
        
        elif user_type_id:
            # Refresh all users with specific user type
            try:
                user_type = UserType.objects.get(id=user_type_id)
                affected_users = list(User.objects.filter(user_type=user_type))
            except UserType.DoesNotExist:
                logger.warning(f"UserType {user_type_id} not found for manual permission refresh")
                return
        
        else:
            # Refresh all users in tenant
            affected_users = list(User.objects.all())
        
        # Broadcast changes
        channel_layer = get_channel_layer()
        if channel_layer and affected_users:
            message = {
                'type': 'permission_change',
                'data': {
                    'event_type': 'manual_refresh',
                    'affected_users': [user.id for user in affected_users],
                    'user_id': user_id,
                    'user_type_id': user_type_id,
                    'tenant_schema': tenant_schema,
                    'timestamp': None
                }
            }
            
            # Send to tenant-wide channel
            async_to_sync(channel_layer.group_send)(
                f'tenant_permissions_{tenant_schema}',
                {
                    'type': 'send_permission_update',
                    'message': message
                }
            )
            
            # Send to individual user channels
            for user in affected_users:
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}',
                    {
                        'type': 'send_permission_update',
                        'message': message
                    }
                )
        
        logger.info(f"Manual permission refresh completed for {len(affected_users)} users")
        return len(affected_users)
        
    except Exception as e:
        logger.error(f"Error in manual permission refresh: {e}")
        return 0