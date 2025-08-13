"""
Sharing-related signal handlers for audit logging
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings

from .models import SharedRecord, SharedRecordAccess
from core.models import AuditLog

logger = logging.getLogger(__name__)


def create_sharing_audit_log(user, action, record_id, details=None, ip_address=None):
    """
    Create audit log entry for sharing-related activities
    
    Args:
        user: User performing the action (can be None for external access)
        action: Action being performed (e.g., 'shared', 'accessed', 'revoked')
        record_id: ID of the record being shared/accessed
        details: Dictionary with additional details about the action
        ip_address: IP address for the action
    """
    try:
        changes = details or {}
        changes.update({
            'timestamp': timezone.now().isoformat(),
            'action_type': 'sharing_activity'
        })
        
        if ip_address:
            changes['ip_address'] = ip_address
            
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name='Record',
            object_id=str(record_id),
            changes=changes,
            ip_address=ip_address
        )
        
        logger.info(f"SHARING_AUDIT_LOG: {action} for record {record_id} by {user.email if user else 'external user'}")
        
    except Exception as e:
        logger.error(f"Failed to create sharing audit log: {e}")


@receiver(post_save, sender=SharedRecord)
def handle_shared_record_creation(sender, instance, created, **kwargs):
    """Handle shared record creation and updates"""
    
    if created:
        # Calculate human-readable expiry
        from datetime import datetime
        expires_date = instance.expires_at.strftime('%B %d, %Y at %I:%M %p')
        
        # Get sharer name
        sharer_name = instance.shared_by.get_full_name() or instance.shared_by.email
        
        # Create rich description
        access_description = "read and edit" if instance.access_mode == 'editable' else "view only"
        
        # Log when a record is shared
        create_sharing_audit_log(
            user=instance.shared_by,
            action='shared_record',
            record_id=instance.record.id,
            details={
                'share_id': str(instance.id),
                'access_mode': instance.access_mode,
                'access_description': access_description,
                'expires_at': instance.expires_at.isoformat(),
                'expires_date_formatted': expires_date,
                'working_days_remaining': 5,  # Default working days
                'encrypted_token': instance.encrypted_token[:20] + '...',  # Truncated for security
                'shared_by': sharer_name,
                'shared_by_email': instance.shared_by.email,
                'intended_recipient_email': instance.intended_recipient_email,
                'pipeline_name': instance.record.pipeline.name,
                'record_title': getattr(instance.record, 'title', f'Record {instance.record.id}'),
                'sharing_type': 'internal_user',
                'primary_message': f'Shared record with {instance.intended_recipient_email} ({access_description} access)',
                'secondary_message': f'Created by {sharer_name} • Expires {expires_date}',
                'action_icon': 'share',
                'action_color': 'blue'
            }
        )
    
    # Log when a shared record is revoked
    elif instance.revoked_at and hasattr(instance, '_was_revoked'):
        create_sharing_audit_log(
            user=instance.revoked_by,
            action='share_revoked',
            record_id=instance.record.id,
            details={
                'share_id': str(instance.id),
                'access_mode': instance.access_mode,
                'revoked_at': instance.revoked_at.isoformat(),
                'revoked_by': instance.revoked_by.get_full_name() if instance.revoked_by else 'System',
                'original_expires_at': instance.expires_at.isoformat(),
                'access_count': instance.access_count,
                'intended_recipient_email': instance.intended_recipient_email,
                'pipeline_name': instance.record.pipeline.name,
                'record_title': getattr(instance.record, 'title', f'Record {instance.record.id}'),
                'message': f'Share link for {instance.intended_recipient_email} revoked after {instance.access_count} access{"es" if instance.access_count != 1 else ""}'
            }
        )


@receiver(post_save, sender=SharedRecordAccess)
def handle_shared_record_access(sender, instance, created, **kwargs):
    """Handle external user access to shared records"""
    
    if created:
        # Format access time
        access_time = instance.accessed_at.strftime('%B %d, %Y at %I:%M %p')
        
        # Get location string
        location_parts = []
        if instance.city:
            location_parts.append(instance.city)
        if instance.country:
            location_parts.append(instance.country)
        
        if location_parts:
            location_str = ', '.join(location_parts)
        elif instance.ip_address:
            location_str = f"IP: {instance.ip_address}"
        else:
            location_str = 'Unknown location'
        
        # Get shared by name
        shared_by_name = instance.shared_record.shared_by.get_full_name() or instance.shared_record.shared_by.email
        
        # Create access description
        access_description = "read and edit" if instance.shared_record.access_mode == 'editable' else "view only"
        
        # Log when someone accesses a shared record
        create_sharing_audit_log(
            user=None,  # External user, no Django user account
            action='external_access',
            record_id=instance.shared_record.record.id,
            details={
                'share_id': str(instance.shared_record.id),
                'access_id': str(instance.id),
                'accessor_name': instance.accessor_name,
                'accessor_email': instance.accessor_email,
                'access_mode': instance.shared_record.access_mode,
                'access_description': access_description,
                'accessed_at': instance.accessed_at.isoformat(),
                'access_time_formatted': access_time,
                'ip_address': instance.ip_address,
                'user_agent': instance.user_agent[:100] if instance.user_agent else None,  # Truncate long user agents
                'country': instance.country,
                'city': instance.city,
                'location': location_str,
                'pipeline_name': instance.shared_record.record.pipeline.name,
                'record_title': getattr(instance.shared_record.record, 'title', f'Record {instance.shared_record.record.id}'),
                'shared_by': shared_by_name,
                'shared_by_email': instance.shared_record.shared_by.email,
                'intended_recipient_email': instance.shared_record.intended_recipient_email,
                'email_verified': instance.accessor_email.lower() == instance.shared_record.intended_recipient_email.lower(),
                'sharing_type': 'external_user',
                'primary_message': f'External user {instance.accessor_name} accessed shared record',
                'secondary_message': f'{instance.accessor_email} • {location_str} • {access_time}',
                'action_icon': 'eye',
                'action_color': 'green'
            },
            ip_address=instance.ip_address
        )
        
        # Update the shared record's access tracking
        SharedRecord.objects.filter(id=instance.shared_record.id).update(
            last_accessed_at=timezone.now(),
            last_accessed_ip=instance.ip_address
        )


@receiver(post_delete, sender=SharedRecord)
def handle_shared_record_deletion(sender, instance, **kwargs):
    """Handle shared record deletion"""
    
    create_sharing_audit_log(
        user=getattr(instance, 'deleted_by', None),
        action='share_deleted',
        record_id=instance.record.id,
        details={
            'share_id': str(instance.id),
            'access_mode': instance.access_mode,
            'was_active': instance.is_active,
            'access_count': instance.access_count,
            'expires_at': instance.expires_at.isoformat(),
            'intended_recipient_email': instance.intended_recipient_email,
            'pipeline_name': instance.record.pipeline.name,
            'record_title': getattr(instance.record, 'title', f'Record {instance.record.id}'),
            'message': f'Share link for {instance.intended_recipient_email} deleted (had {instance.access_count} access{"es" if instance.access_count != 1 else ""})'
        }
    )


# Additional helper function for manual audit logging from views
def log_shared_record_edit(user, record, field_changes, accessor_info=None):
    """
    Log when a shared record is edited by an external user
    
    Args:
        user: Django user (None for external users)
        record: Record instance being edited
        field_changes: Dictionary of field changes
        accessor_info: Dictionary with accessor_name, accessor_email, ip_address for external users
    """
    
    # Format field changes for display
    field_changes_summary = []
    field_changes_detailed = []
    
    for field_name, change_data in field_changes.items():
        if isinstance(change_data, dict) and 'old' in change_data and 'new' in change_data:
            old_val = change_data['old']
            new_val = change_data['new']
            
            if old_val != new_val:
                # Clean field name for display
                display_field_name = field_name.replace('-', ' ').replace('_', ' ').title()
                
                if old_val is None or old_val == "":
                    summary = f"{display_field_name}: {new_val} (added)"
                    detailed = f"Added {display_field_name}: {new_val}"
                elif new_val is None or new_val == "":
                    summary = f"{display_field_name}: {old_val} (removed)"
                    detailed = f"Removed {display_field_name} (was: {old_val})"
                else:
                    summary = f"{display_field_name}: {old_val} → {new_val}"
                    detailed = f"Changed {display_field_name} from '{old_val}' to '{new_val}'"
                
                field_changes_summary.append(summary)
                field_changes_detailed.append(detailed)
    
    # Get current time for formatting
    from django.utils import timezone
    edit_time = timezone.now().strftime('%B %d, %Y at %I:%M %p')
    
    # Get location from IP if available
    location_str = "Unknown location"
    if accessor_info and accessor_info.get('ip_address'):
        location_str = f"IP: {accessor_info.get('ip_address')}"
    
    details = {
        'field_changes': field_changes,
        'changes_summary': field_changes_summary,
        'changes_detailed': field_changes_detailed,
        'total_changes': len(field_changes_summary),
        'pipeline_name': record.pipeline.name,
        'record_title': getattr(record, 'title', f'Record {record.id}'),
        'edit_source': 'shared_record_form',
        'edit_time_formatted': edit_time
    }
    
    # Add accessor information for external users
    if accessor_info:
        accessor_name = accessor_info.get('accessor_name')
        accessor_email = accessor_info.get('accessor_email')
        
        details.update({
            'accessor_name': accessor_name,
            'accessor_email': accessor_email,
            'external_user': True,
            'sharing_type': 'external_user',
            'location': location_str,
            'primary_message': f'External user {accessor_name} edited shared record',
            'secondary_message': f'{accessor_email} • {len(field_changes_summary)} field{"s" if len(field_changes_summary) != 1 else ""} changed • {edit_time}',
            'action_icon': 'edit',
            'action_color': 'orange'
        })
    else:
        user_name = user.get_full_name() if user else "Unknown user"
        details.update({
            'sharing_type': 'internal_user',
            'primary_message': f'{user_name} edited record via shared link',
            'secondary_message': f'{len(field_changes_summary)} field{"s" if len(field_changes_summary) != 1 else ""} changed • {edit_time}',
            'action_icon': 'edit',
            'action_color': 'orange'
        })
    
    create_sharing_audit_log(
        user=user,
        action='external_edit',
        record_id=record.id,
        details=details,
        ip_address=accessor_info.get('ip_address') if accessor_info else None
    )