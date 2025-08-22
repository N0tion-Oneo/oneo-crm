"""
WebSocket Consumers for Real-time Sync Progress Updates
Handles sync job progress broadcasting and status updates
"""
import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .models import SyncJob, SyncJobStatus

User = get_user_model()
logger = logging.getLogger(__name__)


class SyncProgressConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time sync progress updates
    URL pattern: /ws/sync-progress/{sync_job_id}/
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get sync job ID from URL
        self.sync_job_id = self.scope['url_route']['kwargs']['sync_job_id']
        self.sync_group_name = f"sync_progress_{self.sync_job_id}"
        
        # Check if user is authenticated
        user = self.scope.get('user')
        if not user or isinstance(user, AnonymousUser):
            logger.warning(f"❌ Unauthenticated sync progress connection attempt for job {self.sync_job_id}")
            await self.close(code=4001)  # Unauthorized
            return
        
        # Verify user has access to this sync job
        try:
            sync_job = await self.get_sync_job(self.sync_job_id, user)
            if not sync_job:
                logger.warning(f"❌ User {user.id} attempted to access sync job {self.sync_job_id} without permission")
                await self.close(code=4003)  # Forbidden
                return
        except Exception as e:
            logger.error(f"❌ Error verifying sync job access: {e}")
            await self.close(code=4000)  # Bad Request
            return
        
        # Join sync progress group
        await self.channel_layer.group_add(
            self.sync_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial sync job status
        try:
            initial_status = await self.get_sync_job_status(sync_job)
            await self.send_json({
                'type': 'sync_initial_status',
                'sync_job_id': str(self.sync_job_id),
                **initial_status
            })
        except Exception as e:
            logger.error(f"❌ Failed to send initial sync status: {e}")
        
        logger.info(f"✅ Sync progress WebSocket connected: job {self.sync_job_id}, user {user.id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave sync progress group
        if hasattr(self, 'sync_group_name'):
            await self.channel_layer.group_discard(
                self.sync_group_name,
                self.channel_name
            )
        
        logger.info(f"🔌 Sync progress WebSocket disconnected: job {getattr(self, 'sync_job_id', 'unknown')}, code {close_code}")
    
    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        message_type = content.get('type')
        
        if message_type == 'get_status':
            # Client requesting current status
            try:
                user = self.scope.get('user')
                sync_job = await self.get_sync_job(self.sync_job_id, user)
                if sync_job:
                    status = await self.get_sync_job_status(sync_job)
                    await self.send_json({
                        'type': 'sync_status_update',
                        'sync_job_id': str(self.sync_job_id),
                        **status
                    })
            except Exception as e:
                logger.error(f"❌ Failed to get sync status: {e}")
                await self.send_json({
                    'type': 'error',
                    'message': 'Failed to get sync status'
                })
        
        elif message_type == 'cancel_sync':
            # Client requesting to cancel sync
            try:
                user = self.scope.get('user')
                sync_job = await self.get_sync_job(self.sync_job_id, user)
                if sync_job and sync_job.is_active:
                    await self.cancel_sync_job(sync_job)
                    await self.send_json({
                        'type': 'sync_cancelled',
                        'sync_job_id': str(self.sync_job_id),
                        'message': 'Sync job cancelled successfully'
                    })
                else:
                    await self.send_json({
                        'type': 'error',
                        'message': 'Sync job not active or not found'
                    })
            except Exception as e:
                logger.error(f"❌ Failed to cancel sync: {e}")
                await self.send_json({
                    'type': 'error',
                    'message': 'Failed to cancel sync'
                })
        
        else:
            logger.warning(f"⚠️ Unknown message type: {message_type}")
    
    # WebSocket message handlers (called by group_send)
    async def sync_progress_update(self, event):
        """Send sync progress update to WebSocket"""
        await self.send_json({
            'type': 'sync_progress_update',
            **event
        })
    
    async def sync_status_changed(self, event):
        """Send sync status change to WebSocket"""
        await self.send_json({
            'type': 'sync_status_changed',
            **event
        })
    
    async def sync_completed(self, event):
        """Send sync completion notification"""
        await self.send_json({
            'type': 'sync_completed',
            **event
        })
    
    async def sync_failed(self, event):
        """Send sync failure notification"""
        await self.send_json({
            'type': 'sync_failed',
            **event
        })
    
    # Database helper methods
    @database_sync_to_async
    def get_sync_job(self, sync_job_id, user):
        """Get sync job if user has access"""
        try:
            return SyncJob.objects.get(id=sync_job_id, user=user)
        except SyncJob.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_sync_job_status(self, sync_job):
        """Get current sync job status and progress"""
        return {
            'status': sync_job.status,
            'progress': sync_job.progress,
            'completion_percentage': sync_job.completion_percentage,
            'is_active': sync_job.is_active,
            'started_at': sync_job.started_at.isoformat() if sync_job.started_at else None,
            'completed_at': sync_job.completed_at.isoformat() if sync_job.completed_at else None,
            'last_progress_update': sync_job.last_progress_update.isoformat(),
            'error_details': sync_job.error_details,
            'result_summary': sync_job.result_summary
        }
    
    @database_sync_to_async
    def cancel_sync_job(self, sync_job):
        """Cancel sync job and revoke Celery task"""
        from celery import current_app
        from django.utils import timezone
        
        # Revoke Celery task
        if sync_job.celery_task_id:
            current_app.control.revoke(sync_job.celery_task_id, terminate=True)
        
        # Update sync job status
        sync_job.status = SyncJobStatus.CANCELLED
        sync_job.completed_at = timezone.now()
        sync_job.result_summary = {
            'cancelled_at': timezone.now().isoformat(),
            'cancelled_by_websocket': True
        }
        sync_job.save(update_fields=['status', 'completed_at', 'result_summary'])


class SyncOverviewConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for sync overview/dashboard
    URL pattern: /ws/sync-overview/
    Shows all active sync jobs for the user
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Check if user is authenticated
        user = self.scope.get('user')
        if not user or isinstance(user, AnonymousUser):
            logger.warning("❌ Unauthenticated sync overview connection attempt")
            await self.close(code=4001)  # Unauthorized
            return
        
        self.user_id = str(user.id)
        self.sync_overview_group = f"sync_overview_{self.user_id}"
        
        # Join sync overview group
        await self.channel_layer.group_add(
            self.sync_overview_group,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial active sync jobs
        try:
            active_jobs = await self.get_active_sync_jobs(user)
            await self.send_json({
                'type': 'sync_overview_initial',
                'active_sync_jobs': active_jobs
            })
        except Exception as e:
            logger.error(f"❌ Failed to send initial sync overview: {e}")
        
        logger.info(f"✅ Sync overview WebSocket connected: user {user.id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'sync_overview_group'):
            await self.channel_layer.group_discard(
                self.sync_overview_group,
                self.channel_name
            )
        
        logger.info(f"🔌 Sync overview WebSocket disconnected: user {getattr(self, 'user_id', 'unknown')}, code {close_code}")
    
    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        message_type = content.get('type')
        
        if message_type == 'get_active_jobs':
            # Client requesting current active jobs
            try:
                user = self.scope.get('user')
                active_jobs = await self.get_active_sync_jobs(user)
                await self.send_json({
                    'type': 'sync_overview_update',
                    'active_sync_jobs': active_jobs
                })
            except Exception as e:
                logger.error(f"❌ Failed to get active sync jobs: {e}")
                await self.send_json({
                    'type': 'error',
                    'message': 'Failed to get active sync jobs'
                })
        
        else:
            logger.warning(f"⚠️ Unknown overview message type: {message_type}")
    
    # WebSocket message handlers
    async def sync_job_started(self, event):
        """Notify when new sync job starts"""
        await self.send_json({
            'type': 'sync_job_started',
            **event
        })
    
    async def sync_job_completed(self, event):
        """Notify when sync job completes"""
        await self.send_json({
            'type': 'sync_job_completed',
            **event
        })
    
    async def sync_job_failed(self, event):
        """Notify when sync job fails"""
        await self.send_json({
            'type': 'sync_job_failed',
            **event
        })
    
    async def sync_overview_update(self, event):
        """Send overview update"""
        await self.send_json({
            'type': 'sync_overview_update',
            **event
        })
    
    # Database helper methods
    @database_sync_to_async
    def get_active_sync_jobs(self, user):
        """Get all active sync jobs for user"""
        active_jobs = SyncJob.objects.filter(
            user=user,
            status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
        ).select_related('channel').order_by('-created_at')[:10]
        
        result = []
        for job in active_jobs:
            result.append({
                'sync_job_id': str(job.id),
                'job_type': job.job_type,
                'status': job.status,
                'channel_name': job.channel.name,
                'channel_type': job.channel.channel_type,
                'progress': job.progress,
                'completion_percentage': job.completion_percentage,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'last_progress_update': job.last_progress_update.isoformat()
            })
        
        return result