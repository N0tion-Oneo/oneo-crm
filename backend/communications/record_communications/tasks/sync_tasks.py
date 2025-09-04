"""
Celery tasks for record communication synchronization
"""
import logging
from typing import Dict, Any, Optional, List

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models, connection
from django_tenants.utils import schema_context

from pipelines.models import Record
from communications.models import (
    UserChannelConnection, Conversation, Message,
    Participant, ConversationParticipant
)
from ..models import RecordCommunicationProfile, RecordSyncJob
# RecordCommunicationLink removed - using participant-based linking instead
from ..services import MessageMapper
from ..services.identifier_extractor import RecordIdentifierExtractor
from ..services.record_sync_orchestrator import RecordSyncOrchestrator
from ..utils import ProviderIdBuilder
from communications.unipile.core.client import UnipileClient

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, acks_late=True, reject_on_worker_lost=True)
def sync_record_communications(
    self,
    record_id: int,
    tenant_schema: Optional[str] = None,
    triggered_by_id: Optional[int] = None,
    trigger_reason: str = 'Scheduled sync',
    channels_to_sync: Optional[List[str]] = None
):
    """
    Celery task to sync all communications for a record.
    
    This task now uses the RecordSyncOrchestrator to fetch historical data
    from UniPile specifically for this record's identifiers.
    
    Args:
        record_id: ID of the record to sync
        tenant_schema: Tenant schema name (required for multi-tenant context)
        triggered_by_id: ID of user who triggered sync
        trigger_reason: Reason for sync
        channels_to_sync: Optional list of specific channels to sync (e.g., ['gmail', 'whatsapp'])
    """
    try:
        # Get tenant schema - use current connection if not provided
        if not tenant_schema:
            tenant_schema = connection.schema_name
            if tenant_schema == 'public':
                logger.error(f"Cannot sync record {record_id} without tenant schema")
                raise ValueError("Tenant schema is required for record sync")
        
        logger.info(f"Starting sync for record {record_id} in tenant {tenant_schema}")
        
        # Run everything within tenant schema context
        with schema_context(tenant_schema):
            # Get triggered_by user if provided
            triggered_by = None
            if triggered_by_id:
                try:
                    triggered_by = User.objects.get(id=triggered_by_id)
                except User.DoesNotExist:
                    pass
            
            # Check if there's an existing sync job for this Celery task
            # This prevents creating duplicate sync jobs
            sync_job = None
            celery_task_id = self.request.id
            if celery_task_id:
                try:
                    sync_job = RecordSyncJob.objects.get(
                        celery_task_id=celery_task_id,
                        record_id=record_id
                    )
                    logger.info(f"Found existing sync job {sync_job.id} for Celery task {celery_task_id}")
                    # Update status to running since we're starting now
                    if sync_job.status == 'pending':
                        sync_job.status = 'running'
                        sync_job.started_at = timezone.now()
                        sync_job.save(update_fields=['status', 'started_at'])
                except RecordSyncJob.DoesNotExist:
                    logger.debug(f"No existing sync job found for Celery task {celery_task_id}")
                except RecordSyncJob.MultipleObjectsReturned:
                    # If somehow there are multiple, use the most recent
                    sync_job = RecordSyncJob.objects.filter(
                        celery_task_id=celery_task_id,
                        record_id=record_id
                    ).order_by('-created_at').first()
                    logger.warning(f"Multiple sync jobs found for Celery task {celery_task_id}, using most recent")
            
            # Initialize UniPile client using global settings
            from django.conf import settings
            
            unipile_client = None
            if settings.UNIPILE_SETTINGS.is_configured():
                unipile_client = UnipileClient(
                    dsn=settings.UNIPILE_DSN,
                    access_token=settings.UNIPILE_API_KEY
                )
                logger.info(f"UniPile client initialized with DSN: {settings.UNIPILE_SETTINGS.base_url}")
            else:
                logger.warning("UniPile credentials not configured in environment, sync will be limited")
            
            # Use the orchestrator to handle the entire sync process
            orchestrator = RecordSyncOrchestrator(unipile_client)
            
            result = orchestrator.sync_record(
                record_id=record_id,
                triggered_by=triggered_by,
                trigger_reason=trigger_reason,
                sync_job=sync_job,  # Pass the existing sync job to the orchestrator
                channels_to_sync=channels_to_sync
            )
            
            if result['success']:
                logger.info(
                    f"Sync completed for record {record_id}: "
                    f"{result['total_conversations']} conversations, "
                    f"{result['total_messages']} messages"
                )
            else:
                logger.error(f"Sync failed for record {record_id}: {result.get('error')}")
                # Retry the task if it failed
                raise self.retry(exc=Exception(result.get('error')))
            
            return result
            
    except Exception as e:
        logger.error(f"Error syncing record {record_id}: {e}")
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def process_webhook_message_task(
    self,
    webhook_data: Dict[str, Any],
    channel_type: str,
    channel_id: int
):
    """
    Celery task to process webhook message and map to records.
    
    Args:
        webhook_data: Raw webhook data
        channel_type: Type of channel (email, whatsapp, etc.)
        channel_id: ID of the CommunicationConnection
    """
    try:
        logger.info(f"Processing webhook message for {channel_type}")
        
        # Process message and map to records
        message_mapper = MessageMapper()
        linked_records = message_mapper.process_webhook_message(
            webhook_data=webhook_data,
            channel_type=channel_type,
            channel_id=channel_id
        )
        
        logger.info(
            f"Webhook message processed and linked to {len(linked_records)} records"
        )
        
        return {
            'success': True,
            'linked_record_ids': [str(r.id) for r in linked_records],
            'linked_count': len(linked_records)
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook message: {e}")
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@shared_task
def sync_all_records_for_pipeline(pipeline_id: int, tenant_schema: Optional[str] = None):
    """
    Sync all records in a pipeline.
    Useful when duplicate rules change or bulk sync is needed.
    
    Args:
        pipeline_id: ID of the pipeline
    """
    try:
        # Get tenant schema - use current connection if not provided
        if not tenant_schema:
            tenant_schema = connection.schema_name
            if tenant_schema == 'public':
                logger.error(f"Cannot sync pipeline {pipeline_id} without tenant schema")
                raise ValueError("Tenant schema is required for pipeline sync")
        
        logger.info(f"Starting bulk sync for pipeline {pipeline_id} in tenant {tenant_schema}")
        
        with schema_context(tenant_schema):
            # Get all records in pipeline
            records = Record.objects.filter(
                pipeline_id=pipeline_id,
                is_deleted=False
            ).values_list('id', flat=True)
            
            # Queue sync for each record
            for record_id in records:
                sync_record_communications.delay(
                    record_id=record_id,
                    tenant_schema=tenant_schema,
                    trigger_reason=f'Bulk sync for pipeline {pipeline_id}'
                )
        
        logger.info(f"Queued sync for {len(records)} records in pipeline {pipeline_id}")
        
        return {
            'success': True,
            'records_queued': len(records)
        }
        
    except Exception as e:
        logger.error(f"Error in bulk sync for pipeline {pipeline_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_old_sync_jobs():
    """
    Cleanup old sync job records.
    Runs daily to remove jobs older than 30 days.
    """
    from ..models import RecordSyncJob
    
    try:
        # Delete jobs older than 30 days
        cutoff_date = timezone.now() - timezone.timedelta(days=30)
        deleted_count = RecordSyncJob.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Deleted {deleted_count} old sync jobs")
        
        return {
            'success': True,
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up sync jobs: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def check_stale_profiles(tenant_schema: Optional[str] = None):
    """
    Check for profiles that haven't been synced recently.
    Runs hourly to identify records that need sync.
    """
    from ..models import RecordCommunicationProfile
    
    try:
        # If tenant_schema provided, check only that tenant
        # Otherwise check all tenants (for global scheduled tasks)
        if tenant_schema:
            tenant_schemas = [tenant_schema]
        else:
            from tenants.models import Tenant
            tenant_schemas = Tenant.objects.exclude(
                schema_name='public'
            ).values_list('schema_name', flat=True)
        
        total_queued = 0
        for schema in tenant_schemas:
            with schema_context(schema):
                # Find profiles that need sync
                # - Never synced
                # - Last sync > 24 hours ago (if auto_sync enabled)
                cutoff_time = timezone.now() - timezone.timedelta(hours=24)
                
                stale_profiles = RecordCommunicationProfile.objects.filter(
                    auto_sync_enabled=True
                ).filter(
                    models.Q(last_full_sync__isnull=True) |
                    models.Q(last_full_sync__lt=cutoff_time)
                ).exclude(
                    sync_in_progress=True
                ).values_list('record_id', flat=True)[:100]  # Limit to 100 per run
                
                # Queue sync for stale profiles
                for record_id in stale_profiles:
                    sync_record_communications.delay(
                        record_id=record_id,
                        tenant_schema=schema,
                        trigger_reason='Scheduled auto-sync'
                    )
                
                total_queued += len(stale_profiles)
        
        logger.info(f"Queued sync for {total_queued} stale profiles across {len(tenant_schemas)} tenants")
        
        return {
            'success': True,
            'profiles_queued': total_queued,
            'tenants_checked': len(tenant_schemas)
        }
        
    except Exception as e:
        logger.error(f"Error checking stale profiles: {e}")
        return {
            'success': False,
            'error': str(e)
        }