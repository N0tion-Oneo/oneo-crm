"""
Signal handlers for workflow recovery system
Automatic checkpoint creation and recovery triggering based on workflow events
"""
import logging
from typing import Dict, Any

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from ..models import WorkflowExecution, WorkflowExecutionLog
from .models import RecoveryConfiguration, CheckpointType
from .tasks import auto_create_checkpoint, auto_recover_failed_execution

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WorkflowExecution)
def handle_workflow_execution_change(sender, instance: WorkflowExecution, created: bool, **kwargs):
    """Handle workflow execution status changes"""
    if created:
        return  # Don't process newly created executions
    
    try:
        # Get recovery configuration
        config = RecoveryConfiguration.objects.filter(is_active=True).first()
        if not config:
            return
        
        # Handle failed executions
        if instance.status == 'failed' and config.auto_recovery_enabled:
            # Check if this execution has already been processed
            from .models import WorkflowRecoveryLog
            existing_recovery = WorkflowRecoveryLog.objects.filter(
                execution=instance,
                trigger_reason='execution_failed'
            ).exists()
            
            if not existing_recovery:
                # Trigger automatic recovery
                auto_recover_failed_execution.delay(
                    execution_id=str(instance.id),
                    trigger_reason='execution_failed'
                )
                logger.info(f"Queued auto-recovery for failed execution {instance.id}")
        
        # Handle completed executions - create final checkpoint
        elif instance.status == 'completed' and config.auto_checkpoint_enabled:
            # Check if final checkpoint already exists
            final_checkpoint_exists = instance.checkpoints.filter(
                checkpoint_type=CheckpointType.AUTO,
                description__icontains='completion'
            ).exists()
            
            if not final_checkpoint_exists:
                auto_create_checkpoint.delay(
                    execution_id=str(instance.id),
                    checkpoint_type=CheckpointType.AUTO
                )
                logger.info(f"Queued completion checkpoint for execution {instance.id}")
                
    except Exception as e:
        logger.error(f"Failed to handle workflow execution change: {e}")


@receiver(post_save, sender=WorkflowExecutionLog)
def handle_node_execution_completion(sender, instance: WorkflowExecutionLog, created: bool, **kwargs):
    """Handle individual node execution completion for checkpoint creation"""
    if not created or instance.status != 'completed':
        return
    
    try:
        # Get recovery configuration
        config = RecoveryConfiguration.objects.filter(is_active=True).first()
        if not config or not config.auto_checkpoint_enabled:
            return
        
        execution = instance.execution
        
        # Check if we should create a checkpoint based on node interval
        completed_nodes = execution.logs.filter(status='completed').count()
        
        # Create checkpoint every N nodes as configured
        if completed_nodes % config.checkpoint_interval_nodes == 0:
            # Check if checkpoint for this interval already exists
            existing_checkpoint = execution.checkpoints.filter(
                sequence_number=completed_nodes // config.checkpoint_interval_nodes
            ).exists()
            
            if not existing_checkpoint:
                auto_create_checkpoint.delay(
                    execution_id=str(execution.id),
                    checkpoint_type=CheckpointType.NODE_COMPLETION
                )
                logger.info(f"Queued interval checkpoint for execution {execution.id} at node {completed_nodes}")
        
        # Create milestone checkpoint for specific node types
        milestone_node_types = ['approval', 'decision', 'integration', 'external_api']
        if instance.node_type in milestone_node_types:
            auto_create_checkpoint.delay(
                execution_id=str(execution.id),
                checkpoint_type=CheckpointType.MILESTONE
            )
            logger.info(f"Queued milestone checkpoint for {instance.node_type} node in execution {execution.id}")
            
    except Exception as e:
        logger.error(f"Failed to handle node execution completion: {e}")


@receiver(post_save, sender=WorkflowExecutionLog)
def handle_node_execution_failure(sender, instance: WorkflowExecutionLog, created: bool, **kwargs):
    """Handle node execution failures for error boundary checkpoints"""
    if not created or instance.status != 'failed':
        return
    
    try:
        # Get recovery configuration
        config = RecoveryConfiguration.objects.filter(is_active=True).first()
        if not config or not config.auto_checkpoint_enabled:
            return
        
        execution = instance.execution
        
        # Create error boundary checkpoint before the failed node
        # This allows recovery to restart from just before the failure
        auto_create_checkpoint.delay(
            execution_id=str(execution.id),
            checkpoint_type=CheckpointType.ERROR_BOUNDARY
        )
        logger.info(f"Queued error boundary checkpoint for failed node {instance.node_name} in execution {execution.id}")
        
        # Also trigger automatic recovery if enabled
        if config.auto_recovery_enabled:
            auto_recover_failed_execution.delay(
                execution_id=str(execution.id),
                trigger_reason='node_error'
            )
            logger.info(f"Queued auto-recovery for node failure in execution {execution.id}")
            
    except Exception as e:
        logger.error(f"Failed to handle node execution failure: {e}")


@receiver(post_save, sender=RecoveryConfiguration)
def handle_recovery_configuration_change(sender, instance: RecoveryConfiguration, created: bool, **kwargs):
    """Handle recovery configuration changes"""
    if not created:
        return
    
    try:
        # If this configuration is being activated, deactivate others
        if instance.is_active:
            RecoveryConfiguration.objects.exclude(pk=instance.pk).update(is_active=False)
            logger.info(f"Activated recovery configuration: {instance.config_name}")
        
        # Log configuration changes
        logger.info(f"Recovery configuration {'created' if created else 'updated'}: {instance.config_name}")
        
    except Exception as e:
        logger.error(f"Failed to handle recovery configuration change: {e}")


# Custom signal for manual checkpoint creation
class CheckpointSignals:
    """Custom signals for checkpoint management"""
    
    @staticmethod
    def manual_checkpoint_requested(execution_id: str, user_id: str, **kwargs):
        """Handle manual checkpoint creation request"""
        try:
            checkpoint_type = kwargs.get('checkpoint_type', CheckpointType.MANUAL)
            description = kwargs.get('description', f'Manual checkpoint by user {user_id}')
            is_milestone = kwargs.get('is_milestone', False)
            
            auto_create_checkpoint.delay(
                execution_id=execution_id,
                checkpoint_type=checkpoint_type
            )
            
            logger.info(f"Queued manual checkpoint for execution {execution_id} by user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle manual checkpoint request: {e}")
    
    @staticmethod
    def recovery_strategy_performance_update(strategy_id: str, was_successful: bool, **kwargs):
        """Handle recovery strategy performance updates"""
        try:
            from .models import RecoveryStrategy
            
            strategy = RecoveryStrategy.objects.get(pk=strategy_id)
            
            # Update usage statistics
            strategy.usage_count += 1
            if was_successful:
                strategy.success_count += 1
            
            strategy.last_used_at = timezone.now()
            strategy.save()
            
            # Calculate new success rate
            success_rate = (strategy.success_count / strategy.usage_count) * 100
            
            logger.info(f"Updated strategy {strategy.name} performance: {success_rate:.1f}% success rate")
            
            # If success rate drops below threshold, consider deactivating
            if strategy.usage_count >= 10 and success_rate < 20:
                logger.warning(f"Strategy {strategy.name} has low success rate ({success_rate:.1f}%), consider review")
            
        except Exception as e:
            logger.error(f"Failed to update recovery strategy performance: {e}")
    
    @staticmethod
    def checkpoint_usage_tracked(checkpoint_id: str, usage_type: str, **kwargs):
        """Handle checkpoint usage tracking"""
        try:
            from .models import WorkflowCheckpoint
            
            checkpoint = WorkflowCheckpoint.objects.get(pk=checkpoint_id)
            
            # Update checkpoint metadata
            if not hasattr(checkpoint, 'usage_metadata'):
                checkpoint.usage_metadata = {}
            
            usage_count = checkpoint.usage_metadata.get('usage_count', 0) + 1
            checkpoint.usage_metadata.update({
                'usage_count': usage_count,
                'last_used_at': timezone.now().isoformat(),
                'last_usage_type': usage_type
            })
            
            # Note: This would require adding a usage_metadata field to the model
            # checkpoint.save()
            
            logger.info(f"Tracked checkpoint {checkpoint_id} usage: {usage_type}")
            
        except Exception as e:
            logger.error(f"Failed to track checkpoint usage: {e}")


# Create global signal handler instance
checkpoint_signals = CheckpointSignals()


# Signal handlers for external systems integration
def notify_external_monitoring_system(event_type: str, data: Dict[str, Any]):
    """Notify external monitoring systems of recovery events"""
    try:
        # This is a placeholder for external system integration
        # Could send webhooks, metrics to Prometheus, logs to external systems, etc.
        
        logger.info(f"Recovery event: {event_type} - {data}")
        
        # Example: Send to monitoring system
        # monitoring_client.send_event(event_type, data)
        
    except Exception as e:
        logger.error(f"Failed to notify external monitoring: {e}")


def handle_recovery_completion(recovery_log_id: str, was_successful: bool):
    """Handle recovery completion events"""
    try:
        from .models import WorkflowRecoveryLog
        
        recovery_log = WorkflowRecoveryLog.objects.get(pk=recovery_log_id)
        
        # Notify external systems
        notify_external_monitoring_system('recovery_completed', {
            'recovery_log_id': recovery_log_id,
            'execution_id': str(recovery_log.execution.id),
            'workflow_id': str(recovery_log.workflow.id),
            'workflow_name': recovery_log.workflow.name,
            'recovery_type': recovery_log.recovery_type,
            'was_successful': was_successful,
            'duration_seconds': recovery_log.duration_seconds,
            'attempt_number': recovery_log.attempt_number
        })
        
        # Update strategy performance
        if recovery_log.strategy:
            checkpoint_signals.recovery_strategy_performance_update(
                strategy_id=str(recovery_log.strategy.id),
                was_successful=was_successful
            )
        
        logger.info(f"Processed recovery completion: {recovery_log_id} - {'success' if was_successful else 'failure'}")
        
    except Exception as e:
        logger.error(f"Failed to handle recovery completion: {e}")


def handle_replay_completion(replay_session_id: str, status: str):
    """Handle replay session completion events"""
    try:
        from .models import WorkflowReplaySession
        
        replay_session = WorkflowReplaySession.objects.get(pk=replay_session_id)
        
        # Notify external systems
        notify_external_monitoring_system('replay_completed', {
            'replay_session_id': replay_session_id,
            'original_execution_id': str(replay_session.original_execution.id),
            'replay_execution_id': str(replay_session.replay_execution.id) if replay_session.replay_execution else None,
            'workflow_id': str(replay_session.workflow.id),
            'workflow_name': replay_session.workflow.name,
            'replay_type': replay_session.replay_type,
            'status': status,
            'duration_seconds': replay_session.duration_seconds,
            'debug_mode': replay_session.debug_mode
        })
        
        logger.info(f"Processed replay completion: {replay_session_id} - {status}")
        
    except Exception as e:
        logger.error(f"Failed to handle replay completion: {e}")


# Register additional signal handlers
def register_recovery_signals():
    """Register additional recovery-related signals"""
    try:
        # Connect custom handlers
        # These would be called from appropriate places in the recovery system
        pass
        
    except Exception as e:
        logger.error(f"Failed to register recovery signals: {e}")


# Initialize signals on import
register_recovery_signals()