"""
Background sync views for email
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from communications.models import (
    Channel, UserChannelConnection, SyncJob, SyncJobStatus
)
from communications.channels.email.sync.tasks import (
    run_email_comprehensive_sync,
    run_email_incremental_sync,
    sync_email_thread,
    sync_email_folders
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_email_background_sync(request):
    """
    Start a background email sync job
    
    Body:
        {
            "account_id": "unipile_account_id",
            "sync_type": "comprehensive" | "incremental",
            "options": {
                "max_threads": 100,
                "max_messages_per_thread": 50,
                "days_back": 30,
                "folders_to_sync": ["inbox", "sent", "drafts"]
            }
        }
    """
    try:
        account_id = request.data.get('account_id')
        sync_type = request.data.get('sync_type', 'incremental')
        options = request.data.get('options', {})
        
        if not account_id:
            return Response(
                {'error': 'account_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the connection
        try:
            connection = UserChannelConnection.objects.get(
                unipile_account_id=account_id,
                user=request.user,
                tenant=request.tenant
            )
        except UserChannelConnection.DoesNotExist:
            return Response(
                {'error': 'Email account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the channel
        channel = connection.channel
        
        # Check for existing running sync
        existing_sync = SyncJob.objects.filter(
            channel=channel,
            connection=connection,
            status=SyncJobStatus.RUNNING
        ).first()
        
        if existing_sync:
            return Response({
                'message': 'Sync already in progress',
                'sync_job_id': str(existing_sync.id),
                'celery_task_id': existing_sync.celery_task_id
            }, status=status.HTTP_200_OK)
        
        # Start the appropriate sync task
        if sync_type == 'comprehensive':
            task = run_email_comprehensive_sync.delay(
                channel_id=str(channel.id),
                connection_id=str(connection.id),
                options=options
            )
        else:  # incremental
            task = run_email_incremental_sync.delay(
                channel_id=str(channel.id),
                connection_id=str(connection.id),
                since_date=options.get('since_date')
            )
        
        logger.info(
            f"Started {sync_type} email sync for account {account_id} "
            f"(task_id={task.id})"
        )
        
        return Response({
            'message': f'{sync_type.capitalize()} sync started',
            'celery_task_id': task.id,
            'account_id': account_id,
            'sync_type': sync_type
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to start email sync: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_thread_sync(request, thread_id: str):
    """
    Start sync for a specific email thread
    
    Args:
        thread_id: Thread ID to sync
    """
    try:
        account_id = request.data.get('account_id')
        max_messages = request.data.get('max_messages', 50)
        
        if not account_id:
            return Response(
                {'error': 'account_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the connection
        try:
            connection = UserChannelConnection.objects.get(
                unipile_account_id=account_id,
                user=request.user,
                tenant=request.tenant
            )
        except UserChannelConnection.DoesNotExist:
            return Response(
                {'error': 'Email account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Start thread sync task
        task = sync_email_thread.delay(
            channel_id=str(connection.channel.id),
            thread_id=thread_id,
            max_messages=max_messages
        )
        
        logger.info(
            f"Started thread sync for {thread_id} "
            f"(task_id={task.id})"
        )
        
        return Response({
            'message': 'Thread sync started',
            'celery_task_id': task.id,
            'thread_id': thread_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to start thread sync: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_email_sync_jobs(request):
    """
    Get email sync jobs for the current user
    
    Query params:
        - account_id: Filter by account ID
        - status: Filter by status
        - limit: Number of jobs to return (default: 10)
    """
    try:
        account_id = request.GET.get('account_id')
        status_filter = request.GET.get('status')
        limit = int(request.GET.get('limit', 10))
        
        # Base query
        query = SyncJob.objects.filter(
            user=request.user,
            tenant=request.tenant,
            channel__channel_type__in=['gmail', 'outlook', 'email']
        )
        
        # Apply filters
        if account_id:
            query = query.filter(connection__unipile_account_id=account_id)
        
        if status_filter:
            query = query.filter(status=status_filter)
        
        # Get jobs
        jobs = query.order_by('-created_at')[:limit]
        
        # Format response
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'id': str(job.id),
                'status': job.status.value,
                'job_type': job.job_type.value,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'celery_task_id': job.celery_task_id,
                'result': job.result,
                'error': job.error,
                'parameters': job.parameters
            })
        
        return Response({
            'jobs': jobs_data,
            'count': len(jobs_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to get sync jobs: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_email_sync_jobs(request):
    """
    Get active (running) email sync jobs
    """
    try:
        # Get active jobs
        active_jobs = SyncJob.objects.filter(
            user=request.user,
            tenant=request.tenant,
            channel__channel_type__in=['gmail', 'outlook', 'email'],
            status=SyncJobStatus.RUNNING
        ).order_by('-created_at')
        
        # Format response
        jobs_data = []
        for job in active_jobs:
            connection_data = None
            if job.connection:
                connection_data = {
                    'id': str(job.connection.id),
                    'account_id': job.connection.unipile_account_id,
                    'display_name': job.connection.display_name
                }
            
            jobs_data.append({
                'id': str(job.id),
                'celery_task_id': job.celery_task_id,
                'job_type': job.job_type.value,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'connection': connection_data,
                'parameters': job.parameters
            })
        
        return Response({
            'active_jobs': jobs_data,
            'count': len(jobs_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to get active sync jobs: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_email_sync_job(request, sync_job_id: UUID):
    """
    Cancel an email sync job
    
    Args:
        sync_job_id: Sync job ID to cancel
    """
    try:
        # Get the sync job
        try:
            sync_job = SyncJob.objects.get(
                id=sync_job_id,
                user=request.user,
                tenant=request.tenant
            )
        except SyncJob.DoesNotExist:
            return Response(
                {'error': 'Sync job not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if job is running
        if sync_job.status != SyncJobStatus.RUNNING:
            return Response({
                'message': 'Job is not running',
                'status': sync_job.status.value
            }, status=status.HTTP_200_OK)
        
        # Cancel the Celery task
        from celery import current_app
        if sync_job.celery_task_id:
            current_app.control.revoke(
                sync_job.celery_task_id,
                terminate=True
            )
        
        # Update job status
        sync_job.status = SyncJobStatus.CANCELLED
        sync_job.completed_at = timezone.now()
        sync_job.save()
        
        logger.info(f"Cancelled sync job {sync_job_id}")
        
        return Response({
            'message': 'Sync job cancelled',
            'sync_job_id': str(sync_job_id)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to cancel sync job: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )