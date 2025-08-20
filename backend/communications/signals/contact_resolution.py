"""
Contact resolution signal handlers
Automatically triggers contact resolution when contact-related fields change in records
"""
import logging
from typing import Set, Any
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import connection as db_connection
from pipelines.models import Record

logger = logging.getLogger(__name__)

# Contact-related field names that should trigger resolution
CONTACT_TRIGGER_FIELDS = {
    'email', 'email_address', 'contact_email', 'business_email', 'work_email',
    'phone', 'phone_number', 'contact_phone', 'mobile', 'cell_phone', 'telephone',
    'website', 'company_website', 'domain', 'company_domain', 'url', 'site',
    'linkedin', 'linkedin_url', 'linkedin_profile',
    'name', 'full_name', 'contact_name', 'first_name', 'last_name'
}


@receiver(post_save, sender=Record)
def trigger_contact_resolution_on_record_update(sender, instance, created, **kwargs):
    """
    Trigger contact resolution when a record is updated with contact information
    
    This signal fires when:
    1. A record is updated (not created) 
    2. The record contains contact-related field data
    3. Contact-related fields have potentially changed
    """
    
    # Skip for new records - only process updates
    if created:
        return
    
    # Get tenant schema for task routing
    tenant_schema = db_connection.schema_name if hasattr(db_connection, 'schema_name') else None
    if not tenant_schema or tenant_schema == 'public':
        logger.debug("Skipping contact resolution trigger - not in tenant schema")
        return
    
    try:
        # Check if record has contact-related data
        if not instance.data or not isinstance(instance.data, dict):
            logger.debug(f"Record {instance.id} has no data, skipping contact resolution trigger")
            return
        
        # Check if any contact-related fields are present
        record_fields = set(instance.data.keys())
        contact_fields_present = record_fields.intersection(CONTACT_TRIGGER_FIELDS)
        
        if not contact_fields_present:
            logger.debug(f"Record {instance.id} has no contact fields, skipping resolution trigger")
            return
        
        # Check if any contact fields have actual values
        contact_values = []
        for field_name in contact_fields_present:
            value = instance.data.get(field_name)
            if value and str(value).strip():
                contact_values.append(field_name)
        
        if not contact_values:
            logger.debug(f"Record {instance.id} has empty contact fields, skipping resolution trigger")
            return
        
        logger.info(f"Record {instance.id} updated with contact data in fields: {contact_values}, triggering contact resolution")
        
        # Import here to avoid circular imports
        from ..tasks import resolve_unconnected_conversations_task
        
        # Queue contact resolution task for this tenant
        # Use small batch size for targeted resolution after record updates
        resolve_unconnected_conversations_task.delay(
            tenant_schema=tenant_schema,
            limit=10  # Small batch for responsive processing
        )
        
        logger.info(f"Queued contact resolution task for tenant {tenant_schema} after record {instance.id} update")
        
    except Exception as e:
        logger.error(f"Error triggering contact resolution for record {instance.id}: {e}")


@receiver(post_save, sender=Record)
def log_record_contact_data(sender, instance, created, **kwargs):
    """
    Log record contact data for debugging contact resolution
    """
    if not logger.isEnabledFor(logging.DEBUG):
        return
    
    try:
        if instance.data and isinstance(instance.data, dict):
            record_fields = set(instance.data.keys())
            contact_fields_present = record_fields.intersection(CONTACT_TRIGGER_FIELDS)
            
            if contact_fields_present:
                contact_data = {field: instance.data.get(field) for field in contact_fields_present}
                logger.debug(f"Record {instance.id} ({'created' if created else 'updated'}) contact data: {contact_data}")
                
    except Exception as e:
        logger.debug(f"Error logging record contact data for {instance.id}: {e}")


def has_contact_field_changes(instance, contact_fields: Set[str]) -> bool:
    """
    Check if any contact-related fields have changed by comparing with database state
    
    Args:
        instance: Record instance
        contact_fields: Set of contact field names present in record
        
    Returns:
        bool: True if contact fields have changed
    """
    try:
        # Get the current database state
        try:
            db_record = Record.objects.get(pk=instance.pk)
        except Record.DoesNotExist:
            # New record, consider it as having changes
            return True
        
        # Compare contact fields
        for field_name in contact_fields:
            current_value = instance.data.get(field_name, '')
            db_value = db_record.data.get(field_name, '') if db_record.data else ''
            
            # Normalize values for comparison
            current_normalized = str(current_value).strip().lower()
            db_normalized = str(db_value).strip().lower()
            
            if current_normalized != db_normalized:
                logger.debug(f"Contact field {field_name} changed from '{db_value}' to '{current_value}'")
                return True
        
        return False
        
    except Exception as e:
        logger.warning(f"Error checking field changes for record {instance.pk}: {e}")
        # If we can't determine changes, assume there are changes to be safe
        return True


def trigger_manual_contact_resolution(tenant_schema: str, conversation_ids: list = None, limit: int = 50):
    """
    Manually trigger contact resolution for specific conversations or all unconnected conversations
    
    Args:
        tenant_schema: Tenant schema to process
        conversation_ids: List of specific conversation IDs to process (optional)
        limit: Maximum conversations to process if no specific IDs provided
        
    Returns:
        dict: Task result information
    """
    try:
        from ..tasks import resolve_unconnected_conversations_task, resolve_conversation_contact_task
        
        if conversation_ids:
            # Process specific conversations
            results = []
            for conversation_id in conversation_ids:
                task = resolve_conversation_contact_task.delay(
                    conversation_id=str(conversation_id),
                    tenant_schema=tenant_schema
                )
                results.append({
                    'conversation_id': conversation_id,
                    'task_id': task.id
                })
            
            logger.info(f"Queued {len(results)} specific conversation resolution tasks for tenant {tenant_schema}")
            return {
                'success': True,
                'method': 'specific_conversations',
                'queued_tasks': len(results),
                'results': results
            }
        else:
            # Process all unconnected conversations
            task = resolve_unconnected_conversations_task.delay(
                tenant_schema=tenant_schema,
                limit=limit
            )
            
            logger.info(f"Queued batch contact resolution task for tenant {tenant_schema} (limit: {limit})")
            return {
                'success': True,
                'method': 'batch_processing',
                'task_id': task.id,
                'limit': limit
            }
            
    except Exception as e:
        logger.error(f"Error triggering manual contact resolution: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Utility functions for external use

def get_contact_fields_from_record(record_data: dict) -> dict:
    """
    Extract contact-related fields from record data
    
    Args:
        record_data: Record data dictionary
        
    Returns:
        dict: Contact fields and their values
    """
    if not record_data or not isinstance(record_data, dict):
        return {}
    
    contact_fields = {}
    record_fields = set(record_data.keys())
    contact_field_names = record_fields.intersection(CONTACT_TRIGGER_FIELDS)
    
    for field_name in contact_field_names:
        value = record_data.get(field_name)
        if value and str(value).strip():
            contact_fields[field_name] = value
    
    return contact_fields


def is_contact_related_update(record_data: dict) -> bool:
    """
    Check if record data contains contact-related information
    
    Args:
        record_data: Record data dictionary
        
    Returns:
        bool: True if contains contact data
    """
    contact_fields = get_contact_fields_from_record(record_data)
    return len(contact_fields) > 0


def get_supported_contact_field_names() -> Set[str]:
    """
    Get the set of field names that trigger contact resolution
    
    Returns:
        Set[str]: Contact field names
    """
    return CONTACT_TRIGGER_FIELDS.copy()