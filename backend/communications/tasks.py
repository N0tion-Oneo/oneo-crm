"""
Celery tasks for Communication System
Handles background processing for messaging and channel synchronization
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django_tenants.utils import schema_context

from .models import (
    Channel, Message, CommunicationAnalytics
)
from .unipile_service import unipile_service

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=2)
def sync_channel_messages(self, channel_id: str, tenant_schema: str):
    """
    Sync messages from a specific channel via UniPile
    """
    try:
        with schema_context(tenant_schema):
            channel = Channel.objects.get(id=channel_id)
            
            logger.info(f"Syncing messages for channel {channel.name} ({channel_id})")
            
            # Use async UniPile service to sync messages
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    unipile_service.sync_account_messages(
                        account_id=channel.external_account_id,
                        channel_id=channel_id
                    )
                )
                
                logger.info(f"Synced {result.get('message_count', 0)} messages for channel {channel.name}")
                return result
                
            finally:
                loop.close()
                
    except Channel.DoesNotExist:
        logger.error(f"Channel {channel_id} not found in schema {tenant_schema}")
        return {'error': 'Channel not found'}
        
    except Exception as e:
        logger.error(f"Message sync failed for channel {channel_id}: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))


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


@shared_task
def sync_all_channels(tenant_schema: str):
    """
    Sync messages for all active channels in a tenant
    """
    try:
        with schema_context(tenant_schema):
            active_channels = Channel.objects.filter(is_active=True)
            
            logger.info(f"Syncing {len(active_channels)} channels for tenant {tenant_schema}")
            
            results = []
            for channel in active_channels:
                try:
                    # Queue individual sync tasks
                    sync_channel_messages.delay(str(channel.id), tenant_schema)
                    results.append({'channel_id': str(channel.id), 'status': 'queued'})
                except Exception as e:
                    logger.error(f"Failed to queue sync for channel {channel.id}: {e}")
                    results.append({'channel_id': str(channel.id), 'status': 'failed', 'error': str(e)})
            
            return {
                'tenant_schema': tenant_schema,
                'channels_processed': len(results),
                'results': results
            }
            
    except Exception as e:
        logger.error(f"Channel sync failed for {tenant_schema}: {e}")
        raise


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