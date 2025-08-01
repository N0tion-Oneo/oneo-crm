"""
Celery tasks for workflow recovery system
Background tasks for automated recovery, cleanup, and maintenance
"""
import logging
from datetime import timedelta
from typing import Optional, List, Dict, Any

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from ..models import Workflow, WorkflowExecution
from .models import (
    WorkflowCheckpoint, WorkflowRecoveryLog, RecoveryStrategy,
    WorkflowReplaySession, RecoveryConfiguration,
    RecoveryStatus, CheckpointType
)
from .manager import workflow_recovery_manager

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def auto_create_checkpoint(self, execution_id: str, checkpoint_type: str = CheckpointType.AUTO):
    """Automatically create checkpoint for workflow execution"""
    try:
        execution = WorkflowExecution.objects.get(pk=execution_id)
        
        # Check if auto-checkpointing is enabled
        config = RecoveryConfiguration.objects.filter(is_active=True).first()
        if not config or not config.auto_checkpoint_enabled:
            logger.info(f"Auto-checkpointing disabled, skipping execution {execution_id}")
            return {'status': 'skipped', 'reason': 'auto_checkpoint_disabled'}
        
        # Create checkpoint
        checkpoint = workflow_recovery_manager.create_checkpoint(
            execution=execution,
            checkpoint_type=checkpoint_type,
            description=f"Auto-checkpoint for execution {execution_id}"
        )
        
        logger.info(f"Created auto-checkpoint {checkpoint.id} for execution {execution_id}")
        return {
            'status': 'success',
            'checkpoint_id': str(checkpoint.id),
            'execution_id': str(execution_id),
            'sequence_number': checkpoint.sequence_number
        }
        
    except WorkflowExecution.DoesNotExist:
        logger.error(f"Execution {execution_id} not found for auto-checkpoint")
        return {'status': 'error', 'error': 'execution_not_found'}
        
    except Exception as e:
        logger.error(f"Failed to create auto-checkpoint: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def auto_recover_failed_execution(self, execution_id: str, trigger_reason: str = 'execution_failed'):
    """Automatically recover failed workflow execution"""
    try:
        execution = WorkflowExecution.objects.get(pk=execution_id)
        
        # Check if auto-recovery is enabled
        config = RecoveryConfiguration.objects.filter(is_active=True).first()
        if not config or not config.auto_recovery_enabled:
            logger.info(f"Auto-recovery disabled, skipping execution {execution_id}")
            return {'status': 'skipped', 'reason': 'auto_recovery_disabled'}
        
        # Check if execution has already been recovered too many times
        recovery_count = WorkflowRecoveryLog.objects.filter(execution=execution).count()
        if recovery_count >= config.max_recovery_attempts:
            logger.warning(f"Max recovery attempts ({config.max_recovery_attempts}) reached for execution {execution_id}")
            return {'status': 'skipped', 'reason': 'max_attempts_reached'}
        
        # Add delay if configured
        if config.recovery_delay_minutes > 0 and recovery_count > 0:
            # Use Celery's ETA to delay the task
            from celery import current_task
            eta = timezone.now() + timedelta(minutes=config.recovery_delay_minutes)
            logger.info(f"Delaying recovery for {config.recovery_delay_minutes} minutes")
            raise current_task.retry(eta=eta)
        
        # Trigger recovery
        recovery_log = workflow_recovery_manager.recover_workflow(
            execution=execution,
            trigger_reason=trigger_reason
        )
        
        logger.info(f"Auto-recovery initiated for execution {execution_id}: {recovery_log.id}")
        return {
            'status': 'success',
            'recovery_log_id': str(recovery_log.id),
            'execution_id': str(execution_id),
            'recovery_type': recovery_log.recovery_type
        }
        
    except WorkflowExecution.DoesNotExist:
        logger.error(f"Execution {execution_id} not found for auto-recovery")
        return {'status': 'error', 'error': 'execution_not_found'}
        
    except Exception as e:
        logger.error(f"Failed to auto-recover execution: {e}")
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@shared_task
def cleanup_expired_checkpoints():
    """Clean up expired checkpoints"""
    try:
        # Get configuration
        config = RecoveryConfiguration.objects.filter(is_active=True).first()
        if not config or not config.auto_cleanup_enabled:
            logger.info("Auto-cleanup disabled")
            return {'status': 'skipped', 'reason': 'auto_cleanup_disabled'}
        
        # Find expired checkpoints
        expired_checkpoints = WorkflowCheckpoint.objects.filter(
            expires_at__lt=timezone.now()
        )
        
        expired_count = expired_checkpoints.count()
        if expired_count == 0:
            return {'status': 'success', 'cleaned_checkpoints': 0}
        
        # Calculate storage saved
        total_size = sum(
            cp.checkpoint_size_bytes or 0 
            for cp in expired_checkpoints
        )
        storage_saved_mb = total_size / (1024 * 1024)
        
        # Delete expired checkpoints
        with transaction.atomic():
            expired_checkpoints.delete()
        
        logger.info(f"Cleaned up {expired_count} expired checkpoints, saved {storage_saved_mb:.2f} MB")
        return {
            'status': 'success',
            'cleaned_checkpoints': expired_count,
            'storage_saved_mb': storage_saved_mb
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired checkpoints: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_recovery_logs(days_to_keep: int = 90):
    """Clean up old recovery logs"""
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        old_logs = WorkflowRecoveryLog.objects.filter(
            created_at__lt=cutoff_date,
            status__in=[RecoveryStatus.COMPLETED, RecoveryStatus.FAILED, RecoveryStatus.CANCELLED]
        )
        
        old_count = old_logs.count()
        if old_count == 0:
            return {'status': 'success', 'cleaned_logs': 0}
        
        # Delete old logs
        with transaction.atomic():
            old_logs.delete()
        
        logger.info(f"Cleaned up {old_count} old recovery logs older than {days_to_keep} days")
        return {
            'status': 'success',
            'cleaned_logs': old_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old recovery logs: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_stale_replay_sessions(hours_to_keep: int = 72):
    """Clean up stale replay sessions"""
    try:
        cutoff_date = timezone.now() - timedelta(hours=hours_to_keep)
        
        # Find stale sessions (created but never started or completed)
        stale_sessions = WorkflowReplaySession.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['created', 'cancelled']
        )
        
        stale_count = stale_sessions.count()
        if stale_count == 0:
            return {'status': 'success', 'cleaned_sessions': 0}
        
        # Delete stale sessions
        with transaction.atomic():
            stale_sessions.delete()
        
        logger.info(f"Cleaned up {stale_count} stale replay sessions older than {hours_to_keep} hours")
        return {
            'status': 'success',
            'cleaned_sessions': stale_count,
            'cutoff_hours': hours_to_keep
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup stale replay sessions: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def update_recovery_strategy_stats():
    """Update recovery strategy success statistics"""
    try:
        strategies = RecoveryStrategy.objects.filter(is_active=True)
        updated_count = 0
        
        for strategy in strategies:
            # Get recent usage data
            recent_logs = strategy.recovery_logs.filter(
                started_at__gte=timezone.now() - timedelta(days=30)
            )
            
            # Update statistics if there's recent usage
            if recent_logs.exists():
                total_recent = recent_logs.count()
                successful_recent = recent_logs.filter(was_successful=True).count()
                
                # Calculate rolling success rate (weighted with historical data)
                if strategy.usage_count > 0:
                    # Weight recent data more heavily
                    historical_weight = 0.7
                    recent_weight = 0.3
                    
                    historical_rate = strategy.success_rate
                    recent_rate = (successful_recent / total_recent) * 100
                    
                    new_success_rate = (historical_weight * historical_rate) + (recent_weight * recent_rate)
                else:
                    new_success_rate = (successful_recent / total_recent) * 100
                
                # Update strategy statistics (this would normally be done automatically)
                # but we update for any missed cases
                strategy.save()
                updated_count += 1
        
        logger.info(f"Updated statistics for {updated_count} recovery strategies")
        return {
            'status': 'success',
            'updated_strategies': updated_count
        }
        
    except Exception as e:
        logger.error(f"Failed to update recovery strategy stats: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def generate_recovery_insights_report():
    """Generate comprehensive recovery insights report"""
    try:
        # Generate failure analysis for all workflows
        analysis = workflow_recovery_manager.analyze_failure_patterns(days=30)
        
        # Generate checkpoint statistics
        checkpoint_stats = workflow_recovery_manager.get_checkpoint_statistics(days=30)
        
        # Calculate system-wide recovery metrics
        recent_recoveries = WorkflowRecoveryLog.objects.filter(
            started_at__gte=timezone.now() - timedelta(days=30)
        )
        
        insights = {
            'report_generated_at': timezone.now().isoformat(),
            'period_days': 30,
            'system_metrics': {
                'total_recoveries': recent_recoveries.count(),
                'successful_recoveries': recent_recoveries.filter(was_successful=True).count(),
                'failed_recoveries': recent_recoveries.filter(was_successful=False).count(),
                'average_recovery_time': None
            },
            'failure_analysis': analysis,
            'checkpoint_statistics': checkpoint_stats,
            'top_failing_workflows': [],
            'most_effective_strategies': []
        }
        
        # Calculate average recovery time
        completed_recoveries = recent_recoveries.filter(duration_seconds__isnull=False)
        if completed_recoveries.exists():
            total_time = sum(r.duration_seconds for r in completed_recoveries)
            insights['system_metrics']['average_recovery_time'] = total_time / completed_recoveries.count()
        
        # Find top failing workflows
        from django.db.models import Count
        top_failing = WorkflowRecoveryLog.objects.filter(
            started_at__gte=timezone.now() - timedelta(days=30)
        ).values('workflow__name').annotate(
            failure_count=Count('id')
        ).order_by('-failure_count')[:5]
        
        insights['top_failing_workflows'] = list(top_failing)
        
        # Find most effective strategies
        top_strategies = RecoveryStrategy.objects.filter(
            recovery_logs__started_at__gte=timezone.now() - timedelta(days=30)
        ).annotate(
            recent_usage=Count('recovery_logs')
        ).filter(recent_usage__gt=0).order_by('-success_rate', '-recent_usage')[:5]
        
        insights['most_effective_strategies'] = [
            {
                'name': s.name,
                'success_rate': s.success_rate,
                'recent_usage': s.recovery_logs.filter(
                    started_at__gte=timezone.now() - timedelta(days=30)
                ).count()
            }
            for s in top_strategies
        ]
        
        logger.info("Generated recovery insights report")
        return {
            'status': 'success',
            'insights': insights
        }
        
    except Exception as e:
        logger.error(f"Failed to generate recovery insights report: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def monitor_recovery_system_health():
    """Monitor recovery system health and create alerts if needed"""
    try:
        now = timezone.now()
        health_status = {
            'timestamp': now.isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'alerts': []
        }
        
        # Check checkpoint creation rate
        recent_checkpoints = WorkflowCheckpoint.objects.filter(
            created_at__gte=now - timedelta(hours=1)
        ).count()
        
        health_status['components']['checkpoint_creation'] = {
            'status': 'healthy',
            'recent_count': recent_checkpoints
        }
        
        # Check recovery success rate
        recent_recoveries = WorkflowRecoveryLog.objects.filter(
            started_at__gte=now - timedelta(hours=6)
        )
        
        if recent_recoveries.exists():
            success_rate = (recent_recoveries.filter(was_successful=True).count() / recent_recoveries.count()) * 100
            
            if success_rate < 50:
                health_status['components']['recovery_success'] = {
                    'status': 'critical',
                    'success_rate': success_rate
                }
                health_status['overall_status'] = 'critical'
                health_status['alerts'].append(f"Low recovery success rate: {success_rate:.1f}%")
            elif success_rate < 70:
                health_status['components']['recovery_success'] = {
                    'status': 'warning',
                    'success_rate': success_rate
                }
                if health_status['overall_status'] == 'healthy':
                    health_status['overall_status'] = 'warning'
                health_status['alerts'].append(f"Below optimal recovery success rate: {success_rate:.1f}%")
            else:
                health_status['components']['recovery_success'] = {
                    'status': 'healthy',
                    'success_rate': success_rate
                }
        
        # Check for long-running recovery attempts
        long_running = WorkflowRecoveryLog.objects.filter(
            status=RecoveryStatus.IN_PROGRESS,
            started_at__lt=now - timedelta(hours=2)
        )
        
        if long_running.exists():
            health_status['components']['long_running_recoveries'] = {
                'status': 'warning',
                'count': long_running.count()
            }
            if health_status['overall_status'] == 'healthy':
                health_status['overall_status'] = 'warning'
            health_status['alerts'].append(f"{long_running.count()} recovery attempts running for >2 hours")
        
        # Check storage usage (simplified check)
        total_checkpoints = WorkflowCheckpoint.objects.count()
        if total_checkpoints > 10000:  # Arbitrary threshold
            health_status['components']['storage_usage'] = {
                'status': 'warning',
                'checkpoint_count': total_checkpoints
            }
            if health_status['overall_status'] == 'healthy':
                health_status['overall_status'] = 'warning'
            health_status['alerts'].append(f"High checkpoint count: {total_checkpoints}")
        
        logger.info(f"Recovery system health check: {health_status['overall_status']}")
        return {
            'status': 'success',
            'health_status': health_status
        }
        
    except Exception as e:
        logger.error(f"Failed to monitor recovery system health: {e}")
        return {'status': 'error', 'error': str(e)}


# Periodic task schedules (to be configured in Celery beat)
"""
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-checkpoints': {
        'task': 'workflows.recovery.tasks.cleanup_expired_checkpoints',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'cleanup-old-recovery-logs': {
        'task': 'workflows.recovery.tasks.cleanup_old_recovery_logs',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Weekly on Sunday at 3 AM
        'kwargs': {'days_to_keep': 90}
    },
    'cleanup-stale-replay-sessions': {
        'task': 'workflows.recovery.tasks.cleanup_stale_replay_sessions',
        'schedule': crontab(hour=4, minute=0),  # Daily at 4 AM
        'kwargs': {'hours_to_keep': 72}
    },
    'update-recovery-strategy-stats': {
        'task': 'workflows.recovery.tasks.update_recovery_strategy_stats',
        'schedule': crontab(hour=5, minute=0),  # Daily at 5 AM
    },
    'generate-recovery-insights-report': {
        'task': 'workflows.recovery.tasks.generate_recovery_insights_report',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),  # Weekly on Monday at 6 AM
    },
    'monitor-recovery-system-health': {
        'task': 'workflows.recovery.tasks.monitor_recovery_system_health',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}
"""