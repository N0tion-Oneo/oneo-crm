"""
Email-specific Celery tasks for Communication System
"""
import logging
from typing import Optional
import asyncio

from celery import shared_task
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=2)
def sync_email_read_status_to_provider(
    self,
    message_id: int,
    tenant_schema: str,
    mark_as_read: bool = True
):
    """
    Sync email read status to the email provider (Gmail/Outlook) via UniPile
    
    Args:
        message_id: The message ID in our database
        tenant_schema: The tenant schema to use
        mark_as_read: True to mark as read, False to mark as unread
    """
    try:
        with schema_context(tenant_schema):
            from .models import Message
            from .channels.email.service import EmailService
            
            message = Message.objects.get(id=message_id)
            
            # Get the UniPile email ID from metadata
            unipile_email_id = message.metadata.get('unipile_id') if message.metadata else None
            
            # Only sync if it's an email with a UniPile ID
            if not (message.channel and message.channel.channel_type in ['email', 'gmail', 'outlook', 'office365'] and unipile_email_id):
                logger.info(f"Message {message_id} is not an email (type: {message.channel.channel_type if message.channel else 'None'}) or has no UniPile ID in metadata, skipping sync")
                return
            
            # Get the account_id from the channel
            account_id = None
            if message.channel and hasattr(message.channel, 'unipile_account_id'):
                account_id = message.channel.unipile_account_id
                logger.info(f"Using UniPile account_id: {account_id} for message {message_id}")
            else:
                logger.warning(f"No UniPile account_id found for channel {message.channel.id if message.channel else 'None'}, message {message_id}")
            
            # Run the async method
            email_service = EmailService()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    email_service.mark_email_as_read(
                        email_id=unipile_email_id,
                        account_id=account_id,
                        mark_as_read=mark_as_read
                    )
                )
                
                if result.get('success'):
                    logger.info(f"Successfully synced read status for message {message_id} to UniPile")
                else:
                    logger.warning(f"Failed to sync read status for message {message_id}: {result}")
                    
                return result
            finally:
                loop.close()
                
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
    except Exception as e:
        logger.error(f"Error syncing read status for message {message_id}: {e}")
        raise self.retry(exc=e)