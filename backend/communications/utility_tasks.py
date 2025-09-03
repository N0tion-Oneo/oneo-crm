"""
Utility Celery tasks for Communication System
"""
import logging
from typing import Optional
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django_tenants.utils import schema_context
from django.db.models import Count

from .models import Message, CommunicationAnalytics

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=2)
def cleanup_old_messages(
    self,
    days_to_keep: int = 90,
    tenant_schema: Optional[str] = None
):
    """
    Clean up old messages beyond retention period
    """
    try:
        cutoff_date = django_timezone.now() - timedelta(days=days_to_keep)
        
        if tenant_schema:
            with schema_context(tenant_schema):
                deleted_count = Message.objects.filter(
                    created_at__lt=cutoff_date
                ).delete()[0]
        else:
            deleted_count = Message.objects.filter(
                created_at__lt=cutoff_date
            ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old messages")
        return {'deleted_count': deleted_count}
        
    except Exception as e:
        logger.error(f"Message cleanup failed: {e}")
        return {'error': str(e)}


@shared_task
def update_communication_analytics(tenant_schema: Optional[str] = None):
    """
    Update communication analytics for the tenant
    """
    try:
        if tenant_schema:
            with schema_context(tenant_schema):
                # Get message counts by channel
                stats = Message.objects.values('channel__channel_type').annotate(
                    count=Count('id')
                )
                
                analytics, created = CommunicationAnalytics.objects.get_or_create(
                    defaults={'metrics': {}}
                )
                
                analytics.metrics['message_counts'] = {
                    stat['channel__channel_type']: stat['count']
                    for stat in stats
                }
                analytics.metrics['last_updated'] = django_timezone.now().isoformat()
                analytics.save()
                
                return {'status': 'success', 'metrics': analytics.metrics}
        else:
            logger.warning("No tenant schema provided for analytics update")
            return {'status': 'skipped', 'reason': 'no_tenant_schema'}
            
    except Exception as e:
        logger.error(f"Analytics update failed: {e}")
        return {'error': str(e)}