"""
Workflow Recovery Manager
Central manager for workflow replay, recovery, and checkpoint management
"""
import logging
import json
import copy
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from django.db import transaction, models
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model

from ..models import Workflow, WorkflowExecution, WorkflowExecutionLog
from .models import (
    WorkflowCheckpoint, WorkflowRecoveryLog, RecoveryStrategy,
    WorkflowReplaySession, RecoveryConfiguration,
    CheckpointType, RecoveryStatus, RecoveryStrategyType
)

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """Data structure for checkpoint information"""
    execution_state: Dict[str, Any]
    context_data: Dict[str, Any]
    node_outputs: Dict[str, Any]
    completed_nodes: List[str]
    current_node: str
    metadata: Dict[str, Any]


class WorkflowRecoveryManager:
    """
    Central manager for workflow recovery, replay, and checkpoint operations
    Provides comprehensive recovery capabilities for failed workflow executions
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        
    # === CHECKPOINT MANAGEMENT ===
    
    def create_checkpoint(
        self,
        execution: WorkflowExecution,
        checkpoint_type: str = CheckpointType.AUTO,
        node_id: str = None,
        node_name: str = None,
        description: str = None,
        is_milestone: bool = False
    ) -> WorkflowCheckpoint:
        """Create a workflow execution checkpoint"""
        try:
            # Get current execution state
            checkpoint_data = self._capture_execution_state(execution)
            
            # Calculate checkpoint size
            state_json = json.dumps(checkpoint_data.execution_state)
            checkpoint_size = len(state_json.encode('utf-8'))
            
            # Get next sequence number
            last_checkpoint = WorkflowCheckpoint.objects.filter(
                execution=execution
            ).order_by('-sequence_number').first()
            
            sequence_number = (last_checkpoint.sequence_number + 1) if last_checkpoint else 1
            
            # Create checkpoint
            checkpoint = WorkflowCheckpoint.objects.create(
                workflow=execution.workflow,
                execution=execution,
                checkpoint_type=checkpoint_type,
                node_id=node_id or checkpoint_data.current_node,
                node_name=node_name or '',
                sequence_number=sequence_number,
                execution_state=checkpoint_data.execution_state,
                context_data=checkpoint_data.context_data,
                node_outputs=checkpoint_data.node_outputs,
                description=description or f"Checkpoint at {checkpoint_data.current_node}",
                checkpoint_size_bytes=checkpoint_size,
                is_milestone=is_milestone,
                is_recoverable=True,
                expires_at=self._calculate_checkpoint_expiry()
            )
            
            # Clean up old checkpoints if needed
            self._cleanup_old_checkpoints(execution)
            
            logger.info(f"Created checkpoint {checkpoint.id} for execution {execution.id}")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            raise
    
    def get_latest_checkpoint(self, execution: WorkflowExecution) -> Optional[WorkflowCheckpoint]:
        """Get the latest recoverable checkpoint for an execution"""
        try:
            return WorkflowCheckpoint.objects.filter(
                execution=execution,
                is_recoverable=True,
                expires_at__gt=timezone.now()
            ).order_by('-sequence_number').first()
            
        except Exception as e:
            logger.error(f"Failed to get latest checkpoint: {e}")
            return None
    
    def get_milestone_checkpoints(self, execution: WorkflowExecution) -> List[WorkflowCheckpoint]:
        """Get all milestone checkpoints for an execution"""
        try:
            return list(WorkflowCheckpoint.objects.filter(
                execution=execution,
                is_milestone=True,
                is_recoverable=True,
                expires_at__gt=timezone.now()
            ).order_by('sequence_number'))
            
        except Exception as e:
            logger.error(f"Failed to get milestone checkpoints: {e}")
            return []
    
    # === RECOVERY MANAGEMENT ===
    
    def recover_workflow(
        self,
        execution: WorkflowExecution,
        trigger_reason: str = 'execution_failed',
        user: User = None,
        strategy: RecoveryStrategy = None
    ) -> WorkflowRecoveryLog:
        """Recover a failed workflow execution"""
        try:
            # Find appropriate recovery strategy
            if not strategy:
                strategy = self._find_recovery_strategy(execution, trigger_reason)
            
            # Create recovery log
            recovery_log = WorkflowRecoveryLog.objects.create(
                workflow=execution.workflow,
                execution=execution,
                strategy=strategy,
                recovery_type=strategy.strategy_type if strategy else RecoveryStrategyType.RETRY,
                trigger_reason=trigger_reason,
                triggered_by=user,
                status=RecoveryStatus.PENDING,
                attempt_number=self._get_recovery_attempt_number(execution)
            )
            
            # Get error information
            error_info = self._extract_error_information(execution)
            recovery_log.original_error = error_info.get('error_message', '')
            recovery_log.failed_node_id = error_info.get('failed_node_id', '')
            recovery_log.failed_node_name = error_info.get('failed_node_name', '')
            recovery_log.save()
            
            # Execute recovery strategy
            try:
                recovery_log.status = RecoveryStatus.IN_PROGRESS
                recovery_log.save()
                
                success = self._execute_recovery_strategy(recovery_log, strategy)
                
                recovery_log.mark_completed(success)
                
                # Update strategy statistics
                if strategy:
                    strategy.usage_count += 1
                    if success:
                        strategy.success_count += 1
                    strategy.last_used_at = timezone.now()
                    strategy.save()
                
                logger.info(f"Recovery {'succeeded' if success else 'failed'} for execution {execution.id}")
                return recovery_log
                
            except Exception as e:
                recovery_log.mark_completed(False, str(e))
                raise
                
        except Exception as e:
            logger.error(f"Failed to recover workflow: {e}")
            raise
    
    def create_recovery_strategy(
        self,
        name: str,
        strategy_type: str,
        description: str = '',
        workflow: Workflow = None,
        node_type: str = None,
        error_patterns: List[str] = None,
        max_retry_attempts: int = 3,
        retry_delay_seconds: int = 60,
        recovery_actions: List[Dict[str, Any]] = None,
        user: User = None
    ) -> RecoveryStrategy:
        """Create a new recovery strategy"""
        try:
            strategy = RecoveryStrategy.objects.create(
                name=name,
                description=description,
                strategy_type=strategy_type,
                workflow=workflow,
                node_type=node_type,
                error_patterns=error_patterns or [],
                max_retry_attempts=max_retry_attempts,
                retry_delay_seconds=retry_delay_seconds,
                recovery_actions=recovery_actions or [],
                created_by=user
            )
            
            logger.info(f"Created recovery strategy: {strategy.name}")
            return strategy
            
        except Exception as e:
            logger.error(f"Failed to create recovery strategy: {e}")
            raise
    
    # === REPLAY MANAGEMENT ===
    
    def create_replay_session(
        self,
        original_execution: WorkflowExecution,
        replay_type: str = 'debug',
        checkpoint: WorkflowCheckpoint = None,
        modified_inputs: Dict[str, Any] = None,
        modified_context: Dict[str, Any] = None,
        skip_nodes: List[str] = None,
        purpose: str = '',
        user: User = None
    ) -> WorkflowReplaySession:
        """Create a new workflow replay session"""
        try:
            replay_session = WorkflowReplaySession.objects.create(
                workflow=original_execution.workflow,
                original_execution=original_execution,
                replay_from_checkpoint=checkpoint,
                replay_type=replay_type,
                modified_inputs=modified_inputs or {},
                modified_context=modified_context or {},
                skip_nodes=skip_nodes or [],
                debug_mode=(replay_type == 'debug'),
                purpose=purpose,
                created_by=user
            )
            
            logger.info(f"Created replay session {replay_session.id} for execution {original_execution.id}")
            return replay_session
            
        except Exception as e:
            logger.error(f"Failed to create replay session: {e}")
            raise
    
    def start_replay(self, replay_session: WorkflowReplaySession) -> WorkflowExecution:
        """Start a workflow replay session"""
        try:
            # Validate replay session
            if replay_session.status != 'created':
                raise ValueError(f"Replay session must be in 'created' status, got: {replay_session.status}")
            
            # Prepare replay execution
            replay_context = self._prepare_replay_context(replay_session)
            
            # Create new execution for replay
            replay_execution = self._create_replay_execution(replay_session, replay_context)
            
            # Update replay session
            replay_session.status = 'running'
            replay_session.started_at = timezone.now()
            replay_session.replay_execution = replay_execution
            replay_session.save()
            
            # Start workflow execution (this would integrate with your workflow engine)
            # replay_execution = workflow_engine.execute_workflow(replay_execution)
            
            logger.info(f"Started replay session {replay_session.id}")
            return replay_execution
            
        except Exception as e:
            logger.error(f"Failed to start replay: {e}")
            replay_session.status = 'failed'
            replay_session.save()
            raise
    
    def get_replay_comparison(
        self, 
        replay_session: WorkflowReplaySession
    ) -> Dict[str, Any]:
        """Compare replay execution with original execution"""
        try:
            if not replay_session.replay_execution:
                return {'error': 'Replay execution not found'}
            
            original = replay_session.original_execution
            replay = replay_session.replay_execution
            
            # Compare execution results
            comparison = {
                'session_id': str(replay_session.id),
                'original_execution': {
                    'id': str(original.id),
                    'status': original.status,
                    'duration_seconds': original.duration_seconds,
                    'error_message': original.error_message,
                    'final_output': original.final_output
                },
                'replay_execution': {
                    'id': str(replay.id),
                    'status': replay.status,
                    'duration_seconds': replay.duration_seconds,
                    'error_message': replay.error_message,
                    'final_output': replay.final_output
                },
                'differences': [],
                'node_comparisons': []
            }
            
            # Compare node execution logs
            original_logs = original.logs.all().order_by('started_at')
            replay_logs = replay.logs.all().order_by('started_at')
            
            comparison['node_comparisons'] = self._compare_node_executions(
                original_logs, replay_logs
            )
            
            # Identify key differences
            if original.status != replay.status:
                comparison['differences'].append({
                    'type': 'status_difference',
                    'original': original.status,
                    'replay': replay.status
                })
            
            if original.final_output != replay.final_output:
                comparison['differences'].append({
                    'type': 'output_difference',
                    'description': 'Final outputs differ'
                })
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to get replay comparison: {e}")
            return {'error': str(e)}
    
    # === ANALYSIS AND INSIGHTS ===
    
    def analyze_failure_patterns(
        self, 
        workflow: Workflow = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze workflow failure patterns for insights"""
        try:
            # Get failed executions
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            failed_executions = WorkflowExecution.objects.filter(
                status='failed',
                started_at__gte=start_date,
                started_at__lte=end_date
            )
            
            if workflow:
                failed_executions = failed_executions.filter(workflow=workflow)
            
            # Analyze patterns
            analysis = {
                'period_days': days,
                'workflow': workflow.name if workflow else 'All workflows',
                'total_failures': failed_executions.count(),
                'failure_patterns': {},
                'recovery_success_rate': 0.0,
                'common_failure_nodes': [],
                'failure_trends': [],
                'recommendations': []
            }
            
            if analysis['total_failures'] == 0:
                return analysis
            
            # Group failures by error patterns
            error_patterns = {}
            node_failures = {}
            
            for execution in failed_executions:
                # Extract error pattern
                error_key = self._categorize_error(execution.error_message or 'Unknown error')
                error_patterns[error_key] = error_patterns.get(error_key, 0) + 1
                
                # Find failed node
                failed_log = execution.logs.filter(status='failed').first()
                if failed_log:
                    node_key = f"{failed_log.node_type}:{failed_log.node_name}"
                    node_failures[node_key] = node_failures.get(node_key, 0) + 1
            
            analysis['failure_patterns'] = dict(sorted(
                error_patterns.items(), 
                key=lambda x: x[1], 
                reverse=True
            ))
            
            analysis['common_failure_nodes'] = [
                {'node': node, 'failures': count}
                for node, count in sorted(node_failures.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # Calculate recovery success rate
            recovery_logs = WorkflowRecoveryLog.objects.filter(
                execution__in=failed_executions,
                was_successful=True
            )
            if recovery_logs.exists():
                analysis['recovery_success_rate'] = (recovery_logs.count() / analysis['total_failures']) * 100
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_failure_recommendations(
                error_patterns, node_failures, analysis['recovery_success_rate']
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze failure patterns: {e}")
            return {'error': str(e)}
    
    def get_checkpoint_statistics(
        self, 
        workflow: Workflow = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get checkpoint usage statistics"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            checkpoints = WorkflowCheckpoint.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            if workflow:
                checkpoints = checkpoints.filter(workflow=workflow)
            
            stats = {
                'period_days': days,
                'workflow': workflow.name if workflow else 'All workflows',
                'total_checkpoints': checkpoints.count(),
                'checkpoint_types': {},
                'average_checkpoint_size_mb': 0.0,
                'checkpoint_usage': {
                    'for_recovery': 0,
                    'for_replay': 0,
                    'unused': 0
                },
                'cleanup_stats': {
                    'expired_checkpoints': 0,
                    'storage_saved_mb': 0.0
                }
            }
            
            if stats['total_checkpoints'] == 0:
                return stats
            
            # Analyze checkpoint types
            type_counts = checkpoints.values('checkpoint_type').annotate(
                count=models.Count('id')
            )
            for item in type_counts:
                stats['checkpoint_types'][item['checkpoint_type']] = item['count']
            
            # Calculate average size
            size_stats = checkpoints.aggregate(
                avg_size=models.Avg('checkpoint_size_bytes'),
                total_size=models.Sum('checkpoint_size_bytes')
            )
            if size_stats['avg_size']:
                stats['average_checkpoint_size_mb'] = size_stats['avg_size'] / (1024 * 1024)
            
            # Analyze usage
            recovery_used = checkpoints.filter(recovery_logs__isnull=False).distinct().count()
            replay_used = checkpoints.filter(replay_sessions__isnull=False).distinct().count()
            
            stats['checkpoint_usage']['for_recovery'] = recovery_used
            stats['checkpoint_usage']['for_replay'] = replay_used
            stats['checkpoint_usage']['unused'] = stats['total_checkpoints'] - recovery_used - replay_used
            
            # Cleanup statistics
            expired = WorkflowCheckpoint.objects.filter(
                expires_at__lt=timezone.now()
            )
            if workflow:
                expired = expired.filter(workflow=workflow)
            
            expired_stats = expired.aggregate(
                count=models.Count('id'),
                total_size=models.Sum('checkpoint_size_bytes')
            )
            
            stats['cleanup_stats']['expired_checkpoints'] = expired_stats['count'] or 0
            if expired_stats['total_size']:
                stats['cleanup_stats']['storage_saved_mb'] = expired_stats['total_size'] / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get checkpoint statistics: {e}")
            return {'error': str(e)}
    
    # === HELPER METHODS ===
    
    def _capture_execution_state(self, execution: WorkflowExecution) -> CheckpointData:
        """Capture current execution state for checkpoint"""
        try:
            # Get execution logs
            completed_logs = execution.logs.filter(status='completed').order_by('started_at')
            current_log = execution.logs.filter(status='running').first()
            
            # Build state data
            node_outputs = {}
            completed_nodes = []
            
            for log in completed_logs:
                completed_nodes.append(log.node_id)
                if log.output_data:
                    node_outputs[log.node_id] = log.output_data
            
            current_node = current_log.node_id if current_log else 'unknown'
            
            return CheckpointData(
                execution_state={
                    'execution_id': str(execution.id),
                    'workflow_id': str(execution.workflow.id),
                    'status': execution.status,
                    'completed_nodes': completed_nodes,
                    'current_node': current_node,
                    'execution_context': execution.execution_context or {}
                },
                context_data=execution.execution_context or {},
                node_outputs=node_outputs,
                completed_nodes=completed_nodes,
                current_node=current_node,
                metadata={
                    'checkpoint_created_at': timezone.now().isoformat(),
                    'execution_duration_seconds': execution.duration_seconds
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to capture execution state: {e}")
            raise
    
    def _calculate_checkpoint_expiry(self) -> datetime:
        """Calculate when checkpoint should expire"""
        try:
            config = RecoveryConfiguration.objects.filter(is_active=True).first()
            retention_days = config.checkpoint_retention_days if config else 30
            return timezone.now() + timedelta(days=retention_days)
        except Exception:
            return timezone.now() + timedelta(days=30)
    
    def _cleanup_old_checkpoints(self, execution: WorkflowExecution) -> None:
        """Clean up old checkpoints based on configuration"""
        try:
            config = RecoveryConfiguration.objects.filter(is_active=True).first()
            max_checkpoints = config.max_checkpoints_per_execution if config else 20
            
            # Keep only the most recent N checkpoints
            old_checkpoints = WorkflowCheckpoint.objects.filter(
                execution=execution
            ).order_by('-sequence_number')[max_checkpoints:]
            
            if old_checkpoints:
                old_checkpoint_ids = [cp.id for cp in old_checkpoints]
                WorkflowCheckpoint.objects.filter(id__in=old_checkpoint_ids).delete()
                logger.info(f"Cleaned up {len(old_checkpoint_ids)} old checkpoints for execution {execution.id}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints: {e}")
    
    def _find_recovery_strategy(
        self, 
        execution: WorkflowExecution, 
        trigger_reason: str
    ) -> Optional[RecoveryStrategy]:
        """Find the best recovery strategy for a failed execution"""
        try:
            # Get error information
            error_info = self._extract_error_information(execution)
            error_message = error_info.get('error_message', '')
            failed_node_type = error_info.get('failed_node_type', '')
            
            # Find matching strategies
            strategies = RecoveryStrategy.objects.filter(
                models.Q(workflow=execution.workflow) | models.Q(workflow__isnull=True),
                is_active=True
            ).order_by('-priority', '-success_rate')
            
            for strategy in strategies:
                if strategy.matches_error(error_message, failed_node_type):
                    return strategy
            
            # Return default retry strategy if no specific match
            default_strategy = RecoveryStrategy.objects.filter(
                workflow__isnull=True,
                strategy_type=RecoveryStrategyType.RETRY,
                is_active=True
            ).first()
            
            return default_strategy
            
        except Exception as e:
            logger.error(f"Failed to find recovery strategy: {e}")
            return None
    
    def _extract_error_information(self, execution: WorkflowExecution) -> Dict[str, Any]:
        """Extract error information from failed execution"""
        try:
            error_info = {
                'error_message': execution.error_message or 'Unknown error',
                'failed_node_id': '',
                'failed_node_name': '',
                'failed_node_type': ''
            }
            
            # Find failed node
            failed_log = execution.logs.filter(status='failed').first()
            if failed_log:
                error_info.update({
                    'failed_node_id': failed_log.node_id,
                    'failed_node_name': failed_log.node_name,
                    'failed_node_type': failed_log.node_type,
                })
                
                if failed_log.error_details:
                    error_info['error_details'] = failed_log.error_details
            
            return error_info
            
        except Exception as e:
            logger.error(f"Failed to extract error information: {e}")
            return {'error_message': 'Failed to extract error information'}
    
    def _get_recovery_attempt_number(self, execution: WorkflowExecution) -> int:
        """Get the next recovery attempt number"""
        try:
            last_attempt = WorkflowRecoveryLog.objects.filter(
                execution=execution
            ).order_by('-attempt_number').first()
            
            return (last_attempt.attempt_number + 1) if last_attempt else 1
            
        except Exception as e:
            logger.error(f"Failed to get recovery attempt number: {e}")
            return 1
    
    def _execute_recovery_strategy(
        self, 
        recovery_log: WorkflowRecoveryLog, 
        strategy: RecoveryStrategy
    ) -> bool:
        """Execute a recovery strategy"""
        try:
            if not strategy:
                return False
            
            recovery_actions = []
            
            if strategy.strategy_type == RecoveryStrategyType.RETRY:
                success = self._execute_retry_recovery(recovery_log, strategy)
                recovery_actions.append({
                    'action': 'retry',
                    'details': f"Retried from latest checkpoint with {strategy.retry_delay_seconds}s delay"
                })
                
            elif strategy.strategy_type == RecoveryStrategyType.ROLLBACK:
                success = self._execute_rollback_recovery(recovery_log, strategy)
                recovery_actions.append({
                    'action': 'rollback',
                    'details': 'Rolled back to previous stable checkpoint'
                })
                
            elif strategy.strategy_type == RecoveryStrategyType.SKIP:
                success = self._execute_skip_recovery(recovery_log, strategy)
                recovery_actions.append({
                    'action': 'skip',
                    'details': 'Skipped failed node and continued execution'
                })
                
            elif strategy.strategy_type == RecoveryStrategyType.RESTART:
                success = self._execute_restart_recovery(recovery_log, strategy)
                recovery_actions.append({
                    'action': 'restart',
                    'details': 'Restarted workflow from beginning'
                })
                
            else:
                # Manual intervention required
                success = False
                recovery_actions.append({
                    'action': 'manual_intervention',
                    'details': 'Manual intervention required - strategy marked for manual handling'
                })
            
            # Update recovery log
            recovery_log.recovery_actions_taken = recovery_actions
            recovery_log.save()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute recovery strategy: {e}")
            return False
    
    def _execute_retry_recovery(
        self, 
        recovery_log: WorkflowRecoveryLog, 
        strategy: RecoveryStrategy
    ) -> bool:
        """Execute retry recovery strategy"""
        try:
            # Get latest checkpoint
            checkpoint = self.get_latest_checkpoint(recovery_log.execution)
            if not checkpoint:
                logger.warning("No checkpoint available for retry recovery")
                return False
            
            # Create new execution from checkpoint
            new_execution = self._create_execution_from_checkpoint(
                checkpoint, recovery_log.execution
            )
            
            if new_execution:
                recovery_log.new_execution = new_execution
                recovery_log.checkpoint = checkpoint
                recovery_log.save()
                
                # Start new execution (integrate with workflow engine)
                # workflow_engine.execute_workflow(new_execution)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to execute retry recovery: {e}")
            return False
    
    def _execute_rollback_recovery(
        self, 
        recovery_log: WorkflowRecoveryLog, 
        strategy: RecoveryStrategy
    ) -> bool:
        """Execute rollback recovery strategy"""
        try:
            # Find previous stable checkpoint (not the latest one)
            checkpoints = WorkflowCheckpoint.objects.filter(
                execution=recovery_log.execution,
                is_recoverable=True,
                expires_at__gt=timezone.now()
            ).order_by('-sequence_number')[1:]  # Skip latest
            
            if not checkpoints:
                logger.warning("No previous checkpoint available for rollback")
                return False
            
            rollback_checkpoint = checkpoints[0]
            
            # Create new execution from rollback checkpoint
            new_execution = self._create_execution_from_checkpoint(
                rollback_checkpoint, recovery_log.execution
            )
            
            if new_execution:
                recovery_log.new_execution = new_execution
                recovery_log.checkpoint = rollback_checkpoint
                recovery_log.save()
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to execute rollback recovery: {e}")
            return False
    
    def _execute_skip_recovery(
        self, 
        recovery_log: WorkflowRecoveryLog, 
        strategy: RecoveryStrategy
    ) -> bool:
        """Execute skip recovery strategy"""
        try:
            # This would require integration with the workflow engine
            # to skip the failed node and continue execution
            logger.info("Skip recovery strategy would skip failed node and continue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute skip recovery: {e}")
            return False
    
    def _execute_restart_recovery(
        self, 
        recovery_log: WorkflowRecoveryLog, 
        strategy: RecoveryStrategy
    ) -> bool:
        """Execute restart recovery strategy"""
        try:
            # Create new execution from beginning
            original = recovery_log.execution
            
            new_execution = WorkflowExecution.objects.create(
                workflow=original.workflow,
                triggered_by=original.triggered_by,
                trigger_data=original.trigger_data,
                execution_context=original.execution_context,
                status='pending'
            )
            
            recovery_log.new_execution = new_execution
            recovery_log.save()
            
            # Start new execution (integrate with workflow engine)
            # workflow_engine.execute_workflow(new_execution)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute restart recovery: {e}")
            return False
    
    def _create_execution_from_checkpoint(
        self, 
        checkpoint: WorkflowCheckpoint, 
        original_execution: WorkflowExecution
    ) -> Optional[WorkflowExecution]:
        """Create a new execution from a checkpoint"""
        try:
            # Create new execution
            new_execution = WorkflowExecution.objects.create(
                workflow=checkpoint.workflow,
                triggered_by=original_execution.triggered_by,
                trigger_data=original_execution.trigger_data,
                execution_context=checkpoint.context_data,
                status='pending'
            )
            
            # The workflow engine would use the checkpoint data to resume execution
            # at the appropriate point
            
            return new_execution
            
        except Exception as e:
            logger.error(f"Failed to create execution from checkpoint: {e}")
            return None
    
    def _prepare_replay_context(self, replay_session: WorkflowReplaySession) -> Dict[str, Any]:
        """Prepare context for replay execution"""
        try:
            # Start with original execution context
            context = copy.deepcopy(replay_session.original_execution.execution_context or {})
            
            # Apply modifications
            if replay_session.modified_context:
                context.update(replay_session.modified_context)
            
            # Add replay metadata
            context['_replay_session_id'] = str(replay_session.id)
            context['_replay_type'] = replay_session.replay_type
            context['_debug_mode'] = replay_session.debug_mode
            context['_skip_nodes'] = replay_session.skip_nodes
            
            if replay_session.replay_from_checkpoint:
                context['_replay_from_checkpoint'] = str(replay_session.replay_from_checkpoint.id)
                context['_checkpoint_data'] = replay_session.replay_from_checkpoint.execution_state
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to prepare replay context: {e}")
            return {}
    
    def _create_replay_execution(
        self, 
        replay_session: WorkflowReplaySession, 
        context: Dict[str, Any]
    ) -> WorkflowExecution:
        """Create new execution for replay"""
        try:
            # Prepare trigger data
            trigger_data = copy.deepcopy(replay_session.original_execution.trigger_data or {})
            
            # Apply modified inputs
            if replay_session.modified_inputs:
                trigger_data.update(replay_session.modified_inputs)
            
            # Create new execution
            replay_execution = WorkflowExecution.objects.create(
                workflow=replay_session.workflow,
                triggered_by=replay_session.created_by,
                trigger_data=trigger_data,
                execution_context=context,
                status='pending'
            )
            
            return replay_execution
            
        except Exception as e:
            logger.error(f"Failed to create replay execution: {e}")
            raise
    
    def _compare_node_executions(
        self, 
        original_logs, 
        replay_logs
    ) -> List[Dict[str, Any]]:
        """Compare node execution logs between original and replay"""
        try:
            comparisons = []
            
            # Create lookup dictionaries
            original_dict = {log.node_id: log for log in original_logs}
            replay_dict = {log.node_id: log for log in replay_logs}
            
            # Compare all nodes
            all_nodes = set(original_dict.keys()) | set(replay_dict.keys())
            
            for node_id in all_nodes:
                orig_log = original_dict.get(node_id)
                replay_log = replay_dict.get(node_id)
                
                comparison = {
                    'node_id': node_id,
                    'node_name': orig_log.node_name if orig_log else replay_log.node_name,
                    'differences': []
                }
                
                if not orig_log:
                    comparison['differences'].append({
                        'type': 'node_added',
                        'description': 'Node executed in replay but not in original'
                    })
                elif not replay_log:
                    comparison['differences'].append({
                        'type': 'node_missing',
                        'description': 'Node executed in original but not in replay'
                    })
                else:
                    # Compare execution details
                    if orig_log.status != replay_log.status:
                        comparison['differences'].append({
                            'type': 'status_difference',
                            'original': orig_log.status,
                            'replay': replay_log.status
                        })
                    
                    if orig_log.output_data != replay_log.output_data:
                        comparison['differences'].append({
                            'type': 'output_difference',
                            'description': 'Node outputs differ'
                        })
                    
                    # Compare execution times
                    if orig_log.duration_ms and replay_log.duration_ms:
                        time_diff = abs(orig_log.duration_ms - replay_log.duration_ms)
                        if time_diff > 1000:  # More than 1 second difference
                            comparison['differences'].append({
                                'type': 'timing_difference',
                                'original_ms': orig_log.duration_ms,
                                'replay_ms': replay_log.duration_ms,
                                'difference_ms': time_diff
                            })
                
                if comparison['differences']:
                    comparisons.append(comparison)
            
            return comparisons
            
        except Exception as e:
            logger.error(f"Failed to compare node executions: {e}")
            return []
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message into pattern"""
        try:
            error_lower = error_message.lower()
            
            # Define error patterns
            patterns = {
                'timeout': ['timeout', 'timed out', 'connection timeout'],
                'connection': ['connection', 'network', 'unreachable', 'refused'],
                'authentication': ['auth', 'permission', 'unauthorized', 'forbidden'],
                'validation': ['validation', 'invalid', 'format', 'required'],
                'resource': ['memory', 'disk', 'cpu', 'resource', 'limit'],
                'external_api': ['api', 'service', 'endpoint', 'http'],
                'data': ['data', 'record', 'field', 'value', 'missing']
            }
            
            for category, keywords in patterns.items():
                if any(keyword in error_lower for keyword in keywords):
                    return category
            
            return 'unknown'
            
        except Exception:
            return 'unknown'
    
    def _generate_failure_recommendations(
        self, 
        error_patterns: Dict[str, int], 
        node_failures: Dict[str, int],
        recovery_success_rate: float
    ) -> List[str]:
        """Generate recommendations based on failure analysis"""
        recommendations = []
        
        # Analyze most common error patterns
        if error_patterns:
            most_common_error = max(error_patterns.items(), key=lambda x: x[1])
            error_type, count = most_common_error
            
            if error_type == 'timeout':
                recommendations.append(f"Consider increasing timeout values - {count} timeout failures detected")
            elif error_type == 'connection':
                recommendations.append(f"Review network connectivity and retry policies - {count} connection failures detected")
            elif error_type == 'authentication':
                recommendations.append(f"Check authentication credentials and permissions - {count} auth failures detected")
            elif error_type == 'resource':
                recommendations.append(f"Monitor system resources and scaling - {count} resource failures detected")
        
        # Analyze node failures
        if node_failures:
            most_failing_node = max(node_failures.items(), key=lambda x: x[1])
            node_name, count = most_failing_node
            recommendations.append(f"Review {node_name} node configuration - {count} failures detected")
        
        # Recovery success rate recommendations
        if recovery_success_rate < 30:
            recommendations.append("Low recovery success rate - consider creating more specific recovery strategies")
        elif recovery_success_rate > 80:
            recommendations.append("High recovery success rate - current strategies are working well")
        
        # Default recommendation
        if not recommendations:
            recommendations.append("No specific patterns detected - continue monitoring for trends")
        
        return recommendations


# Create global instance
workflow_recovery_manager = WorkflowRecoveryManager()