"""
Celery tasks for communication tracking and analytics
Background tasks for metrics updates and reporting
"""
import logging
from datetime import datetime, timedelta, date
from typing import Optional, List

from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction

from ..models import Channel, Message
from .models import CampaignTracking, PerformanceMetrics
from .manager import communication_tracker
from .analytics import communication_analyzer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def update_daily_metrics(self, channel_id: Optional[str] = None, target_date: Optional[str] = None):
    """
    Update daily performance metrics for a specific channel or all channels
    """
    try:
        # Parse target date
        if target_date:
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            target_date_obj = timezone.now().date()
        
        # Get channel if specified
        channel = None
        if channel_id:
            try:
                channel = Channel.objects.get(id=channel_id)
            except Channel.DoesNotExist:
                logger.error(f"Channel {channel_id} not found")
                return
        
        # Update metrics
        with transaction.atomic():
            metrics = communication_tracker.update_performance_metrics(
                date=target_date_obj,
                channel=channel
            )
        
        logger.info(f"Updated daily metrics for {target_date_obj} - {channel.name if channel else 'all channels'}")
        return {
            'status': 'success',
            'date': target_date_obj.isoformat(),
            'channel': channel.name if channel else 'all',
            'messages_sent': metrics.messages_sent
        }
        
    except Exception as e:
        logger.error(f"Failed to update daily metrics: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def update_hourly_metrics(self, channel_id: Optional[str] = None, target_datetime: Optional[str] = None):
    """
    Update hourly performance metrics for a specific channel or all channels
    """
    try:
        # Parse target datetime
        if target_datetime:
            target_dt = datetime.fromisoformat(target_datetime)
        else:
            target_dt = timezone.now()
        
        target_date = target_dt.date()
        target_hour = target_dt.hour
        
        # Get channel if specified
        channel = None
        if channel_id:
            try:
                channel = Channel.objects.get(id=channel_id)
            except Channel.DoesNotExist:
                logger.error(f"Channel {channel_id} not found")
                return
        
        # Update metrics
        with transaction.atomic():
            metrics = communication_tracker.update_performance_metrics(
                date=target_date,
                hour=target_hour,
                channel=channel
            )
        
        logger.info(f"Updated hourly metrics for {target_date} {target_hour}:00 - {channel.name if channel else 'all channels'}")
        return {
            'status': 'success',
            'datetime': target_dt.isoformat(),
            'channel': channel.name if channel else 'all',
            'messages_sent': metrics.messages_sent
        }
        
    except Exception as e:
        logger.error(f"Failed to update hourly metrics: {e}")
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@shared_task
def update_campaign_metrics(campaign_id: str):
    """
    Update performance metrics for a specific campaign
    """
    try:
        campaign = CampaignTracking.objects.get(id=campaign_id)
        
        if not campaign.actual_start:
            logger.warning(f"Campaign {campaign.name} has not started yet")
            return
        
        # Get campaign date range
        start_date = campaign.actual_start.date()
        end_date = campaign.actual_end.date() if campaign.actual_end else timezone.now().date()
        
        # Update metrics for each day in the campaign
        current_date = start_date
        while current_date <= end_date:
            with transaction.atomic():
                communication_tracker.update_performance_metrics(
                    date=current_date,
                    campaign=campaign
                )
            current_date += timedelta(days=1)
        
        logger.info(f"Updated campaign metrics for {campaign.name}")
        return {
            'status': 'success',
            'campaign': campaign.name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
    except CampaignTracking.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
    except Exception as e:
        logger.error(f"Failed to update campaign metrics: {e}")


@shared_task
def cleanup_old_tracking_data(days_to_keep: int = 90):
    """
    Clean up old tracking data to manage database size
    Keep detailed tracking for specified number of days, aggregate older data
    """
    try:
        cutoff_date = timezone.now().date() - timedelta(days=days_to_keep)
        
        from .models import CommunicationTracking, DeliveryTracking, ReadTracking, ResponseTracking
        
        # Count records before cleanup
        tracking_count = CommunicationTracking.objects.filter(created_at__date__lt=cutoff_date).count()
        delivery_count = DeliveryTracking.objects.filter(created_at__date__lt=cutoff_date).count()
        read_count = ReadTracking.objects.filter(created_at__date__lt=cutoff_date).count()
        response_count = ResponseTracking.objects.filter(created_at__date__lt=cutoff_date).count()
        
        # Delete old records
        with transaction.atomic():
            CommunicationTracking.objects.filter(created_at__date__lt=cutoff_date).delete()
            DeliveryTracking.objects.filter(created_at__date__lt=cutoff_date).delete()
            ReadTracking.objects.filter(created_at__date__lt=cutoff_date).delete()
            ResponseTracking.objects.filter(created_at__date__lt=cutoff_date).delete()
        
        logger.info(f"Cleaned up old tracking data: {tracking_count + delivery_count + read_count + response_count} records")
        return {
            'status': 'success',
            'cutoff_date': cutoff_date.isoformat(),
            'deleted_records': {
                'communication_tracking': tracking_count,
                'delivery_tracking': delivery_count,
                'read_tracking': read_count,
                'response_tracking': response_count
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old tracking data: {e}")


@shared_task
def generate_performance_reports():
    """
    Generate daily performance reports for all active channels and campaigns
    """
    try:
        reports_generated = 0
        
        # Generate channel reports
        active_channels = Channel.objects.filter(is_active=True)
        for channel in active_channels:
            try:
                report = communication_analyzer.generate_performance_report(
                    channel=channel,
                    start_date=timezone.now().date() - timedelta(days=1),
                    end_date=timezone.now().date()
                )
                
                # Store report (could be in database, file system, or sent via email)
                cache_key = f"daily_report_{channel.id}_{timezone.now().date()}"
                cache.set(cache_key, report, 86400)  # Cache for 24 hours
                
                reports_generated += 1
                
            except Exception as e:
                logger.error(f"Failed to generate report for channel {channel.name}: {e}")
        
        # Generate campaign reports for active campaigns
        active_campaigns = CampaignTracking.objects.filter(status='active')
        for campaign in active_campaigns:
            try:
                report = communication_analyzer.generate_performance_report(
                    campaign=campaign
                )
                
                # Store campaign report
                cache_key = f"campaign_report_{campaign.id}_{timezone.now().date()}"
                cache.set(cache_key, report, 86400)
                
                reports_generated += 1
                
            except Exception as e:
                logger.error(f"Failed to generate report for campaign {campaign.name}: {e}")
        
        logger.info(f"Generated {reports_generated} performance reports")
        return {
            'status': 'success',
            'reports_generated': reports_generated,
            'date': timezone.now().date().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to generate performance reports: {e}")


@shared_task
def analyze_performance_trends():
    """
    Analyze performance trends and generate insights for all channels
    """
    try:
        insights_generated = 0
        
        # Analyze trends for each active channel
        active_channels = Channel.objects.filter(is_active=True)
        for channel in active_channels:
            try:
                insights = communication_analyzer.analyze_performance_trends(
                    channel=channel,
                    days=30
                )
                
                # Store insights
                cache_key = f"performance_insights_{channel.id}"
                cache.set(cache_key, insights, 3600)  # Cache for 1 hour
                
                insights_generated += 1
                
            except Exception as e:
                logger.error(f"Failed to analyze trends for channel {channel.name}: {e}")
        
        # Generate overall channel comparison
        try:
            comparison = communication_analyzer.generate_channel_comparison(days=30)
            cache.set('channel_comparison', comparison, 3600)
            
        except Exception as e:
            logger.error(f"Failed to generate channel comparison: {e}")
        
        logger.info(f"Generated insights for {insights_generated} channels")
        return {
            'status': 'success',
            'insights_generated': insights_generated
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze performance trends: {e}")


@shared_task
def process_webhook_events(events: List[dict]):
    """
    Process incoming webhook events from external providers
    """
    try:
        processed_count = 0
        
        for event in events:
            try:
                message_id = event.get('message_id')
                event_type = event.get('event_type')
                
                if not message_id or not event_type:
                    logger.warning(f"Invalid webhook event: {event}")
                    continue
                
                # Import signal handler
                from .signals import handle_unipile_delivery_webhook
                
                # Process the event
                handle_unipile_delivery_webhook(message_id, event)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process webhook event {event}: {e}")
        
        logger.info(f"Processed {processed_count} webhook events")
        return {
            'status': 'success',
            'processed_count': processed_count,
            'total_events': len(events)
        }
        
    except Exception as e:
        logger.error(f"Failed to process webhook events: {e}")


# Periodic task schedules (to be configured in Celery beat)
"""
CELERY_BEAT_SCHEDULE = {
    'update-hourly-metrics': {
        'task': 'communications.tracking.tasks.update_hourly_metrics',
        'schedule': crontab(minute=5),  # Run at 5 minutes past each hour
    },
    'update-daily-metrics': {
        'task': 'communications.tracking.tasks.update_daily_metrics',
        'schedule': crontab(hour=1, minute=0),  # Run daily at 1 AM
    },
    'generate-performance-reports': {
        'task': 'communications.tracking.tasks.generate_performance_reports',
        'schedule': crontab(hour=6, minute=0),  # Run daily at 6 AM
    },
    'analyze-performance-trends': {
        'task': 'communications.tracking.tasks.analyze_performance_trends',
        'schedule': crontab(hour=8, minute=0),  # Run daily at 8 AM
    },
    'cleanup-old-tracking-data': {
        'task': 'communications.tracking.tasks.cleanup_old_tracking_data',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Run weekly on Sunday at 2 AM
        'kwargs': {'days_to_keep': 90}
    },
}
"""