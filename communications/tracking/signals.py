"""
Signal handlers for automatic communication tracking
Automatically tracks delivery, read, and response events
"""
import logging
from typing import Dict, Any

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from ..models import Message, MessageStatus, MessageDirection
from .models import CommunicationTracking, DeliveryTracking, ResponseTracking
from .manager import communication_tracker

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Message)
def track_message_events(sender, instance: Message, created: bool, **kwargs):
    """
    Automatically track message events based on status changes
    """
    try:
        if created and instance.direction == MessageDirection.OUTBOUND:
            # Track new outbound message
            communication_tracker.track_delivery_attempt(
                message=instance,
                attempt_number=1
            )
        
        elif not created:
            # Check for status changes on existing messages
            if instance.status == MessageStatus.DELIVERED and hasattr(instance, '_previous_status'):
                if instance._previous_status != MessageStatus.DELIVERED:
                    # Message was just delivered
                    communication_tracker.mark_delivery_success(
                        message=instance,
                        delivered_at=timezone.now()
                    )
            
            elif instance.status == MessageStatus.FAILED and hasattr(instance, '_previous_status'):
                if instance._previous_status != MessageStatus.FAILED:
                    # Message just failed
                    communication_tracker.mark_delivery_failure(
                        message=instance,
                        error_code='delivery_failed',
                        error_message='Message delivery failed'
                    )
            
            elif instance.status == MessageStatus.READ and hasattr(instance, '_previous_status'):
                if instance._previous_status != MessageStatus.READ:
                    # Message was just read
                    communication_tracker.track_message_read(
                        message=instance,
                        read_at=timezone.now()
                    )
        
        # Track inbound messages as potential responses
        if created and instance.direction == MessageDirection.INBOUND:
            track_potential_response(instance)
            
    except Exception as e:
        logger.error(f"Failed to track message event for {instance.id}: {e}")


@receiver(pre_save, sender=Message)
def store_previous_status(sender, instance: Message, **kwargs):
    """
    Store the previous status before saving to detect changes
    """
    if instance.pk:
        try:
            previous = Message.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except Message.DoesNotExist:
            instance._previous_status = None


def track_potential_response(inbound_message: Message):
    """
    Check if an inbound message is a response to a recent outbound message
    """
    try:
        # Look for recent outbound messages in the same conversation or to the same contact
        recent_threshold = timezone.now() - timezone.timedelta(days=7)  # 7 days
        
        potential_originals = Message.objects.filter(
            direction=MessageDirection.OUTBOUND,
            created_at__gte=recent_threshold,
            channel=inbound_message.channel
        )
        
        # Filter by conversation or contact
        if inbound_message.conversation:
            potential_originals = potential_originals.filter(
                conversation=inbound_message.conversation
            )
        elif inbound_message.contact_email:
            potential_originals = potential_originals.filter(
                contact_email=inbound_message.contact_email
            )
        else:
            return  # Can't determine relationship
        
        # Find the most recent outbound message
        original_message = potential_originals.order_by('-created_at').first()
        
        if original_message:
            # Check if this response was already tracked
            existing_response = ResponseTracking.objects.filter(
                original_message=original_message,
                response_message=inbound_message
            ).exists()
            
            if not existing_response:
                # Track the response
                communication_tracker.track_response(
                    original_message=original_message,
                    response_message=inbound_message
                )
                
                logger.info(f"Tracked response from {inbound_message.id} to {original_message.id}")
            
    except Exception as e:
        logger.error(f"Failed to track potential response for {inbound_message.id}: {e}")


# Additional signal handlers for campaign tracking

@receiver(post_save, sender=Message)
def update_campaign_metrics(sender, instance: Message, created: bool, **kwargs):
    """
    Update campaign metrics when messages are sent or status changes
    """
    try:
        # Check if message is part of a campaign (via metadata or other relationship)
        campaign_id = instance.metadata.get('campaign_id') if instance.metadata else None
        
        if campaign_id and created:
            # Update campaign message count
            from .models import CampaignTracking
            try:
                campaign = CampaignTracking.objects.get(id=campaign_id)
                # Campaign metrics will be updated by the performance metrics update task
                logger.info(f"Message {instance.id} tracked for campaign {campaign.name}")
            except CampaignTracking.DoesNotExist:
                logger.warning(f"Campaign {campaign_id} not found for message {instance.id}")
                
    except Exception as e:
        logger.error(f"Failed to update campaign metrics: {e}")


# Signal handler for automatic performance metrics updates

@receiver(post_save, sender=Message)
def schedule_metrics_update(sender, instance: Message, created: bool, **kwargs):
    """
    Schedule performance metrics update when significant events occur
    """
    try:
        if created or (hasattr(instance, '_previous_status') and 
                      instance.status != instance._previous_status):
            
            # Schedule metrics update for the message date
            from django.utils import timezone
            from celery import current_app
            
            # Schedule update task (assuming Celery is configured)
            if hasattr(current_app, 'send_task'):
                current_app.send_task(
                    'communications.tasks.update_daily_metrics',
                    args=[instance.channel.id, instance.created_at.date().isoformat()],
                    countdown=60  # Delay 1 minute to batch updates
                )
            
    except Exception as e:
        logger.error(f"Failed to schedule metrics update: {e}")


# Webhook signal handlers for external tracking events

def handle_unipile_delivery_webhook(message_id: str, event_data: Dict[str, Any]):
    """
    Handle delivery webhooks from UniPile or other providers
    """
    try:
        message = Message.objects.get(external_message_id=message_id)
        
        event_type = event_data.get('event_type')
        
        if event_type == 'delivered':
            communication_tracker.mark_delivery_success(
                message=message,
                delivered_at=timezone.now(),
                delivery_time_ms=event_data.get('delivery_time_ms')
            )
            
        elif event_type == 'failed':
            communication_tracker.mark_delivery_failure(
                message=message,
                error_code=event_data.get('error_code'),
                error_message=event_data.get('error_message'),
                is_permanent=event_data.get('is_permanent', False)
            )
            
        elif event_type == 'read':
            communication_tracker.track_message_read(
                message=message,
                read_at=timezone.now(),
                user_agent=event_data.get('user_agent'),
                ip_address=event_data.get('ip_address'),
                device_info=event_data.get('device_info', {}),
                location_info=event_data.get('location_info', {})
            )
            
        logger.info(f"Processed {event_type} webhook for message {message_id}")
        
    except Message.DoesNotExist:
        logger.error(f"Message not found for webhook: {message_id}")
    except Exception as e:
        logger.error(f"Failed to handle webhook for {message_id}: {e}")


def handle_tracking_pixel_request(message_id: str, request_data: Dict[str, Any]):
    """
    Handle tracking pixel requests for read tracking
    """
    try:
        message = Message.objects.get(id=message_id)
        
        communication_tracker.track_message_read(
            message=message,
            read_at=timezone.now(),
            user_agent=request_data.get('user_agent', ''),
            ip_address=request_data.get('ip_address'),
            device_info={
                'screen_resolution': request_data.get('screen_resolution'),
                'browser': request_data.get('browser'),
                'os': request_data.get('os')
            }
        )
        
        logger.info(f"Processed tracking pixel for message {message_id}")
        
    except Message.DoesNotExist:
        logger.error(f"Message not found for tracking pixel: {message_id}")
    except Exception as e:
        logger.error(f"Failed to handle tracking pixel for {message_id}: {e}")