"""
Background Sync API Views
Handles background sync job management and progress tracking
"""
import logging
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.utils import timezone as django_timezone
from django.db.models import Q

from ..models import (
    SyncJob, SyncJobProgress, Channel, UserChannelConnection,
    SyncJobStatus, SyncJobType
)
from ..tasks_background_sync import (
    sync_account_comprehensive_background,
    sync_chat_specific_background
)

logger = logging.getLogger(__name__)


# =========================================================================
# SERIALIZERS
# =========================================================================

class SyncJobSerializer(ModelSerializer):
    """Serializer for SyncJob model"""
    completion_percentage = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = SyncJob
        fields = [
            'id', 'job_type', 'status', 'celery_task_id', 'progress', 
            'pagination_state', 'result_summary', 'error_details', 
            'error_count', 'estimated_duration', 'started_at', 
            'completed_at', 'last_progress_update', 'created_at',
            'completion_percentage', 'is_active', 'sync_options'
        ]
        read_only_fields = ['id', 'created_at', 'celery_task_id']


class SyncJobProgressSerializer(ModelSerializer):
    """Serializer for SyncJobProgress model"""
    completion_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = SyncJobProgress
        fields = [
            'id', 'phase_name', 'step_name', 'items_processed', 'items_total',
            'processing_time_ms', 'memory_usage_mb', 'metadata', 'step_status',
            'started_at', 'completed_at', 'completion_percentage'
        ]


# =========================================================================
# API ENDPOINTS
# =========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_background_sync(request):
    """
    Start comprehensive background sync for WhatsApp accounts
    Non-blocking alternative to the existing sync endpoint
    """
    logger.info(f"🚀 Background sync API called by user {request.user.username}")
    logger.info(f"🔍 Request headers: {dict(request.headers)}")
    logger.info(f"🔍 Request data: {request.data}")
    try:
        # Get sync options from request
        sync_options = request.data.get('sync_options', {})
        days_back = sync_options.get('days_back', 30)
        max_messages_per_chat = sync_options.get('max_messages_per_chat', 500)
        
        # Get user's WhatsApp connections
        whatsapp_connections = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type='whatsapp',
            is_active=True,
            unipile_account_id__isnull=False
        )
        
        # If no connections exist, create a test connection for demo purposes
        if not whatsapp_connections.exists():
            # Check if we have any UserChannelConnection at all
            all_connections = UserChannelConnection.objects.filter(user=request.user)
            
            if not all_connections.exists():
                # Create a test WhatsApp connection for demo
                test_connection = UserChannelConnection.objects.create(
                    user=request.user,
                    channel_type='whatsapp',
                    unipile_account_id='test_whatsapp_account_123',
                    account_name='Demo WhatsApp Account',
                    auth_status='authenticated',
                    is_active=True
                )
                logger.info(f"Created test WhatsApp connection for user {request.user.username}")
                whatsapp_connections = UserChannelConnection.objects.filter(id=test_connection.id)
            else:
                return Response({
                    'success': False,
                    'error': 'No active WhatsApp connections found. Please connect a WhatsApp account first.',
                    'available_connections': [
                        {
                            'channel_type': conn.channel_type,
                            'account_name': conn.account_name,
                            'auth_status': conn.auth_status,
                            'is_active': conn.is_active
                        } for conn in all_connections[:5]
                    ]
                }, status=status.HTTP_400_BAD_REQUEST)
        
        sync_jobs = []
        
        for connection in whatsapp_connections:
            try:
                # Get or create channel for this connection
                channel, created = Channel.objects.get_or_create(
                    unipile_account_id=connection.unipile_account_id,
                    channel_type='whatsapp',
                    defaults={
                        'name': f"WhatsApp Account {connection.account_name}",
                        'auth_status': 'authenticated',
                        'is_active': True,
                        'created_by': request.user
                    }
                )
                
                # Check for existing active sync jobs
                existing_job = SyncJob.objects.filter(
                    user=request.user,
                    channel=channel,
                    status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
                ).first()
                
                if existing_job:
                    sync_jobs.append({
                        'channel_id': str(channel.id),
                        'sync_job_id': str(existing_job.id),
                        'status': 'already_running',
                        'message': 'Sync already in progress for this account'
                    })
                    continue
                
                # Start background sync task
                enhanced_options = {
                    'days_back': days_back,
                    'max_messages_per_chat': max_messages_per_chat,
                    'conversations_per_batch': 50,
                    'messages_per_batch': 100,
                    'user_initiated': True
                }
                
                # Get tenant schema for multi-tenant support
                from django.db import connection as db_connection
                tenant_schema = db_connection.tenant.schema_name if hasattr(db_connection, 'tenant') else None
                
                if not tenant_schema:
                    logger.error(f"❌ No tenant context found - sync must be called from tenant subdomain")
                    raise ValueError("No tenant context found. Background sync must be called from a tenant subdomain (e.g., tenant.localhost:3000)")
                
                # Log current connection details
                logger.info(f"🏢 Tenant schema for background sync: {tenant_schema}")
                logger.info(f"🔍 Current DB schema: {getattr(db_connection, 'schema_name', 'unknown')}")
                logger.info(f"🔍 Has tenant: {hasattr(db_connection, 'tenant')}")
                if hasattr(db_connection, 'tenant'):
                    logger.info(f"🔍 Tenant name: {db_connection.tenant.name}")
                    logger.info(f"🔍 Tenant domain: {db_connection.tenant.domains.first() if db_connection.tenant.domains.exists() else 'No domain'}")
                
                # Start Celery task
                task = sync_account_comprehensive_background.delay(
                    channel_id=str(channel.id),
                    user_id=str(request.user.id),
                    sync_options=enhanced_options,
                    tenant_schema=tenant_schema
                )
                
                sync_jobs.append({
                    'channel_id': str(channel.id),
                    'celery_task_id': task.id,
                    'status': 'started',
                    'message': f'Background sync started for {connection.account_name}'
                })
                
                logger.info(f"🚀 Background sync started for channel {channel.id}, task {task.id}")
                
            except Exception as connection_error:
                logger.error(f"❌ Failed to start sync for connection {connection.unipile_account_id}: {connection_error}")
                sync_jobs.append({
                    'channel_id': str(channel.id) if 'channel' in locals() else 'unknown',
                    'connection_id': str(connection.id) if hasattr(connection, 'id') else connection.unipile_account_id,
                    'status': 'failed',
                    'error': str(connection_error),
                    'message': f'Failed to start sync for {connection.account_name}'
                })
        
        return Response({
            'success': True,
            'message': f'Background sync initiated for {len([job for job in sync_jobs if job["status"] == "started"])} accounts',
            'sync_jobs': sync_jobs,
            'sync_type': 'background_comprehensive'
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to start background sync: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_chat_specific_sync(request, chat_id):
    """
    Start background sync for specific chat conversation
    """
    try:
        # Get sync options from request
        sync_options = request.data.get('sync_options', {})
        
        # Find the channel for this chat
        # This assumes the chat_id is the external chat ID from UniPile
        channel_id = request.data.get('channel_id')
        if not channel_id:
            return Response({
                'success': False,
                'error': 'channel_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            channel = Channel.objects.get(id=channel_id, created_by=request.user)
        except Channel.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Channel not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check for existing active sync jobs for this chat
        existing_job = SyncJob.objects.filter(
            user=request.user,
            channel=channel,
            job_type=SyncJobType.CHAT_SPECIFIC,
            sync_options__chat_external_id=chat_id,
            status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
        ).first()
        
        if existing_job:
            return Response({
                'success': False,
                'error': 'Chat sync already in progress',
                'sync_job_id': str(existing_job.id)
            }, status=status.HTTP_409_CONFLICT)
        
        # Enhanced sync options
        enhanced_options = {
            **sync_options,
            'chat_external_id': chat_id,
            'messages_per_batch': 100,
            'user_initiated': True
        }
        
        # Get tenant schema
        from django.db import connection as db_connection
        tenant_schema = db_connection.tenant.schema_name if hasattr(db_connection, 'tenant') else None
        
        # Start background sync task
        task = sync_chat_specific_background.delay(
            channel_id=str(channel.id),
            chat_external_id=chat_id,
            user_id=str(request.user.id),
            sync_options=enhanced_options,
            tenant_schema=tenant_schema
        )
        
        logger.info(f"🎯 Chat-specific sync started for {chat_id}, task {task.id}")
        
        return Response({
            'success': True,
            'message': f'Background sync started for chat {chat_id}',
            'celery_task_id': task.id,
            'chat_id': chat_id,
            'channel_id': channel_id,
            'sync_type': 'chat_specific'
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to start chat-specific sync: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sync_jobs(request):
    """
    Get sync jobs for the current user
    Supports filtering by status, channel, job type
    """
    try:
        # Get query parameters
        status_filter = request.GET.get('status')
        channel_id = request.GET.get('channel_id')
        job_type = request.GET.get('job_type')
        limit = int(request.GET.get('limit', 20))
        
        # Build query
        queryset = SyncJob.objects.filter(user=request.user)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        
        # Get recent jobs
        jobs = queryset.order_by('-created_at')[:limit]
        
        serializer = SyncJobSerializer(jobs, many=True)
        
        return Response({
            'success': True,
            'sync_jobs': serializer.data,
            'count': len(serializer.data)
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get sync jobs: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sync_job_status(request, sync_job_id):
    """
    Get detailed status for a specific sync job
    Includes progress entries and real-time status
    """
    try:
        sync_job = SyncJob.objects.get(
            id=sync_job_id, 
            user=request.user
        )
        
        # Get progress entries
        progress_entries = SyncJobProgress.objects.filter(
            sync_job=sync_job
        ).order_by('-started_at')[:20]
        
        job_serializer = SyncJobSerializer(sync_job)
        progress_serializer = SyncJobProgressSerializer(progress_entries, many=True)
        
        return Response({
            'success': True,
            'sync_job': job_serializer.data,
            'progress_entries': progress_serializer.data,
            'is_active': sync_job.is_active,
            'completion_percentage': sync_job.completion_percentage
        })
        
    except SyncJob.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Sync job not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"❌ Failed to get sync job status: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_sync_job(request, sync_job_id):
    """
    Cancel an active sync job
    """
    try:
        sync_job = SyncJob.objects.get(
            id=sync_job_id, 
            user=request.user
        )
        
        if not sync_job.is_active:
            return Response({
                'success': False,
                'error': 'Sync job is not active'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cancel the Celery task
        if sync_job.celery_task_id:
            from celery import current_app
            current_app.control.revoke(sync_job.celery_task_id, terminate=True)
        
        # Update sync job status
        sync_job.status = SyncJobStatus.CANCELLED
        sync_job.completed_at = django_timezone.now()
        sync_job.result_summary = {
            'cancelled_at': django_timezone.now().isoformat(),
            'cancelled_by_user': True
        }
        sync_job.save(update_fields=['status', 'completed_at', 'result_summary'])
        
        logger.info(f"🛑 Sync job {sync_job_id} cancelled by user")
        
        return Response({
            'success': True,
            'message': 'Sync job cancelled successfully',
            'sync_job_id': sync_job_id
        })
        
    except SyncJob.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Sync job not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"❌ Failed to cancel sync job: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_sync_jobs(request):
    """
    Get all currently active sync jobs for the user
    Useful for dashboard display
    """
    try:
        active_jobs = SyncJob.objects.filter(
            user=request.user,
            status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
        ).select_related('channel').order_by('-created_at')
        
        serializer = SyncJobSerializer(active_jobs, many=True)
        
        return Response({
            'success': True,
            'active_sync_jobs': serializer.data,
            'count': len(serializer.data)
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get active sync jobs: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)