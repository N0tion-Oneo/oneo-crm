"""
DRF views for workflow recovery system
REST API endpoints for recovery management, replay sessions, and analytics
"""
import logging
from typing import Dict, Any
from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count
from django.db import transaction

from ..models import Workflow, WorkflowExecution
from .models import (
    WorkflowCheckpoint, WorkflowRecoveryLog, RecoveryStrategy,
    WorkflowReplaySession, RecoveryConfiguration
)
from .serializers import (
    WorkflowCheckpointSerializer, WorkflowCheckpointSummarySerializer,
    WorkflowRecoveryLogSerializer, WorkflowRecoveryLogSummarySerializer,
    RecoveryStrategySerializer, WorkflowReplaySessionSerializer,
    WorkflowReplaySessionCreateSerializer, RecoveryConfigurationSerializer,
    ReplayComparisonSerializer, FailureAnalysisSerializer,
    CheckpointStatisticsSerializer, RecoveryActionSerializer,
    BulkRecoverySerializer, CheckpointCleanupSerializer
)
from .manager import workflow_recovery_manager

logger = logging.getLogger(__name__)


class WorkflowCheckpointViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow checkpoints"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get filtered queryset"""
        queryset = WorkflowCheckpoint.objects.select_related(
            'workflow', 'execution'
        ).order_by('-created_at')
        
        # Filter by workflow
        workflow_id = self.request.query_params.get('workflow_id')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        
        # Filter by execution
        execution_id = self.request.query_params.get('execution_id')
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        
        # Filter by checkpoint type
        checkpoint_type = self.request.query_params.get('checkpoint_type')
        if checkpoint_type:
            queryset = queryset.filter(checkpoint_type=checkpoint_type)
        
        # Filter by recoverable status
        is_recoverable = self.request.query_params.get('is_recoverable')
        if is_recoverable is not None:
            queryset = queryset.filter(is_recoverable=is_recoverable.lower() == 'true')
        
        # Filter by milestone status
        is_milestone = self.request.query_params.get('is_milestone')
        if is_milestone is not None:
            queryset = queryset.filter(is_milestone=is_milestone.lower() == 'true')
        
        return queryset
    
    def get_serializer_class(self):
        """Get appropriate serializer"""
        if self.action == 'list':
            return WorkflowCheckpointSummarySerializer
        return WorkflowCheckpointSerializer
    
    @action(detail=True, methods=['post'])
    def create_from_execution(self, request, pk=None):
        """Create checkpoint from execution"""
        try:
            execution = get_object_or_404(WorkflowExecution, pk=pk)
            
            checkpoint_type = request.data.get('checkpoint_type', 'manual')
            description = request.data.get('description', '')
            is_milestone = request.data.get('is_milestone', False)
            
            checkpoint = workflow_recovery_manager.create_checkpoint(
                execution=execution,
                checkpoint_type=checkpoint_type,
                description=description,
                is_milestone=is_milestone
            )
            
            serializer = WorkflowCheckpointSerializer(checkpoint)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def mark_milestone(self, request, pk=None):
        """Mark checkpoint as milestone"""
        checkpoint = self.get_object()
        checkpoint.is_milestone = True
        checkpoint.save()
        
        serializer = WorkflowCheckpointSerializer(checkpoint)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def usage_stats(self, request, pk=None):
        """Get checkpoint usage statistics"""
        checkpoint = self.get_object()
        
        stats = {
            'checkpoint_id': str(checkpoint.id),
            'recovery_usage_count': checkpoint.recovery_logs.count(),
            'replay_usage_count': checkpoint.replay_sessions.count(),
            'total_usage_count': checkpoint.recovery_logs.count() + checkpoint.replay_sessions.count(),
            'recent_usage': {
                'last_7_days': {
                    'recoveries': checkpoint.recovery_logs.filter(
                        started_at__gte=timezone.now() - timedelta(days=7)
                    ).count(),
                    'replays': checkpoint.replay_sessions.filter(
                        created_at__gte=timezone.now() - timedelta(days=7)
                    ).count()
                }
            }
        }
        
        return Response(stats)


class RecoveryStrategyViewSet(viewsets.ModelViewSet):
    """ViewSet for recovery strategies"""
    
    serializer_class = RecoveryStrategySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get filtered queryset"""
        queryset = RecoveryStrategy.objects.select_related(
            'workflow', 'created_by'
        ).order_by('-priority', '-success_rate')
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by workflow
        workflow_id = self.request.query_params.get('workflow_id')
        if workflow_id:
            queryset = queryset.filter(
                Q(workflow_id=workflow_id) | Q(workflow__isnull=True)
            )
        
        # Filter by strategy type
        strategy_type = self.request.query_params.get('strategy_type')
        if strategy_type:
            queryset = queryset.filter(strategy_type=strategy_type)
        
        # Filter by node type
        node_type = self.request.query_params.get('node_type')
        if node_type:
            queryset = queryset.filter(node_type=node_type)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by when creating strategy"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test_strategy(self, request, pk=None):
        """Test recovery strategy against sample error"""
        strategy = self.get_object()
        
        error_message = request.data.get('error_message', '')
        node_type = request.data.get('node_type', '')
        
        if not error_message:
            return Response(
                {'error': 'error_message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        matches = strategy.matches_error(error_message, node_type)
        
        return Response({
            'strategy_id': str(strategy.id),
            'strategy_name': strategy.name,
            'matches': matches,
            'error_message': error_message,
            'node_type': node_type,
            'error_patterns': strategy.error_patterns
        })
    
    @action(detail=True, methods=['get'])
    def usage_analytics(self, request, pk=None):
        """Get strategy usage analytics"""
        strategy = self.get_object()
        
        # Get usage over time
        recent_logs = strategy.recovery_logs.filter(
            started_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('started_at')
        
        analytics = {
            'strategy_id': str(strategy.id),
            'total_usage': strategy.usage_count,
            'success_rate': strategy.success_rate,
            'recent_30_days': {
                'total_attempts': recent_logs.count(),
                'successful_attempts': recent_logs.filter(was_successful=True).count(),
                'failed_attempts': recent_logs.filter(was_successful=False).count()
            },
            'most_common_errors': [],
            'average_recovery_time': None
        }
        
        # Calculate average recovery time
        completed_logs = recent_logs.filter(duration_seconds__isnull=False)
        if completed_logs.exists():
            total_time = sum(log.duration_seconds for log in completed_logs)
            analytics['average_recovery_time'] = total_time / completed_logs.count()
        
        return Response(analytics)


class WorkflowRecoveryLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for workflow recovery logs"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get filtered queryset"""
        queryset = WorkflowRecoveryLog.objects.select_related(
            'workflow', 'execution', 'strategy', 'checkpoint', 'triggered_by'
        ).order_by('-started_at')
        
        # Filter by workflow
        workflow_id = self.request.query_params.get('workflow_id')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        
        # Filter by status
        recovery_status = self.request.query_params.get('status')
        if recovery_status:
            queryset = queryset.filter(status=recovery_status)
        
        # Filter by success
        was_successful = self.request.query_params.get('was_successful')
        if was_successful is not None:
            queryset = queryset.filter(was_successful=was_successful.lower() == 'true')
        
        # Filter by recovery type
        recovery_type = self.request.query_params.get('recovery_type')
        if recovery_type:
            queryset = queryset.filter(recovery_type=recovery_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(started_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(started_at__lte=end_date)
        
        return queryset
    
    def get_serializer_class(self):
        """Get appropriate serializer"""
        if self.action == 'list':
            return WorkflowRecoveryLogSummarySerializer
        return WorkflowRecoveryLogSerializer
    
    @action(detail=False, methods=['post'])
    def trigger_recovery(self, request):
        """Trigger recovery for failed execution"""
        try:
            execution_id = request.data.get('execution_id')
            trigger_reason = request.data.get('trigger_reason', 'manual_trigger')
            strategy_id = request.data.get('strategy_id')
            
            if not execution_id:
                return Response(
                    {'error': 'execution_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            execution = get_object_or_404(WorkflowExecution, pk=execution_id)
            strategy = None
            if strategy_id:
                strategy = get_object_or_404(RecoveryStrategy, pk=strategy_id)
            
            recovery_log = workflow_recovery_manager.recover_workflow(
                execution=execution,
                trigger_reason=trigger_reason,
                user=request.user,
                strategy=strategy
            )
            
            serializer = WorkflowRecoveryLogSerializer(recovery_log)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to trigger recovery: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def bulk_recovery(self, request):
        """Trigger recovery for multiple executions"""
        serializer = BulkRecoverySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        execution_ids = data['execution_ids']
        strategy_id = data.get('strategy_id')
        trigger_reason = data['trigger_reason']
        
        strategy = None
        if strategy_id:
            strategy = get_object_or_404(RecoveryStrategy, pk=strategy_id)
        
        results = []
        for execution_id in execution_ids:
            try:
                execution = WorkflowExecution.objects.get(pk=execution_id)
                recovery_log = workflow_recovery_manager.recover_workflow(
                    execution=execution,
                    trigger_reason=trigger_reason,
                    user=request.user,
                    strategy=strategy
                )
                results.append({
                    'execution_id': str(execution_id),
                    'recovery_log_id': str(recovery_log.id),
                    'status': 'initiated'
                })
            except Exception as e:
                results.append({
                    'execution_id': str(execution_id),
                    'error': str(e),
                    'status': 'failed'
                })
        
        return Response({
            'total_executions': len(execution_ids),
            'results': results
        })


class WorkflowReplaySessionViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow replay sessions"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get filtered queryset"""
        queryset = WorkflowReplaySession.objects.select_related(
            'workflow', 'original_execution', 'replay_execution',
            'replay_from_checkpoint', 'created_by'
        ).order_by('-created_at')
        
        # Filter by workflow
        workflow_id = self.request.query_params.get('workflow_id')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        
        # Filter by replay type
        replay_type = self.request.query_params.get('replay_type')
        if replay_type:
            queryset = queryset.filter(replay_type=replay_type)
        
        # Filter by status
        replay_status = self.request.query_params.get('status')
        if replay_status:
            queryset = queryset.filter(status=replay_status)
        
        # Filter by debug mode
        debug_mode = self.request.query_params.get('debug_mode')
        if debug_mode is not None:
            queryset = queryset.filter(debug_mode=debug_mode.lower() == 'true')
        
        return queryset
    
    def get_serializer_class(self):
        """Get appropriate serializer"""
        if self.action == 'create':
            return WorkflowReplaySessionCreateSerializer
        return WorkflowReplaySessionSerializer
    
    def perform_create(self, serializer):
        """Set created_by when creating replay session"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start_replay(self, request, pk=None):
        """Start a replay session"""
        try:
            replay_session = self.get_object()
            
            if replay_session.status != 'created':
                return Response(
                    {'error': f'Cannot start replay in status: {replay_session.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            replay_execution = workflow_recovery_manager.start_replay(replay_session)
            
            serializer = WorkflowReplaySessionSerializer(replay_session)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to start replay: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def comparison(self, request, pk=None):
        """Get comparison between original and replay execution"""
        replay_session = self.get_object()
        
        if not replay_session.replay_execution:
            return Response(
                {'error': 'Replay execution not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            comparison_data = workflow_recovery_manager.get_replay_comparison(replay_session)
            serializer = ReplayComparisonSerializer(data=comparison_data)
            
            if serializer.is_valid():
                return Response(serializer.data)
            else:
                return Response(comparison_data)
                
        except Exception as e:
            logger.error(f"Failed to get replay comparison: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancel_replay(self, request, pk=None):
        """Cancel a running replay session"""
        replay_session = self.get_object()
        
        if replay_session.status not in ['created', 'running']:
            return Response(
                {'error': f'Cannot cancel replay in status: {replay_session.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        replay_session.status = 'cancelled'
        replay_session.completed_at = timezone.now()
        replay_session.save()
        
        serializer = WorkflowReplaySessionSerializer(replay_session)
        return Response(serializer.data)


class RecoveryConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for recovery configuration"""
    
    serializer_class = RecoveryConfigurationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get filtered queryset"""
        return RecoveryConfiguration.objects.order_by('-is_active', 'config_name')
    
    def perform_create(self, serializer):
        """Set created_by when creating configuration"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate configuration and deactivate others"""
        configuration = self.get_object()
        
        with transaction.atomic():
            # Deactivate all other configurations
            RecoveryConfiguration.objects.exclude(pk=pk).update(is_active=False)
            
            # Activate this configuration
            configuration.is_active = True
            configuration.save()
        
        serializer = RecoveryConfigurationSerializer(configuration)
        return Response(serializer.data)


class RecoveryAnalyticsViewSet(viewsets.ViewSet):
    """ViewSet for recovery analytics and insights"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def failure_analysis(self, request):
        """Get workflow failure analysis"""
        workflow_id = request.query_params.get('workflow_id')
        days = int(request.query_params.get('days', 30))
        
        workflow = None
        if workflow_id:
            workflow = get_object_or_404(Workflow, pk=workflow_id)
        
        try:
            analysis_data = workflow_recovery_manager.analyze_failure_patterns(
                workflow=workflow, days=days
            )
            
            serializer = FailureAnalysisSerializer(data=analysis_data)
            if serializer.is_valid():
                return Response(serializer.data)
            else:
                return Response(analysis_data)
                
        except Exception as e:
            logger.error(f"Failed to get failure analysis: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def checkpoint_statistics(self, request):
        """Get checkpoint usage statistics"""
        workflow_id = request.query_params.get('workflow_id')
        days = int(request.query_params.get('days', 30))
        
        workflow = None
        if workflow_id:
            workflow = get_object_or_404(Workflow, pk=workflow_id)
        
        try:
            stats_data = workflow_recovery_manager.get_checkpoint_statistics(
                workflow=workflow, days=days
            )
            
            serializer = CheckpointStatisticsSerializer(data=stats_data)
            if serializer.is_valid():
                return Response(serializer.data)
            else:
                return Response(stats_data)
                
        except Exception as e:
            logger.error(f"Failed to get checkpoint statistics: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def recovery_trends(self, request):
        """Get recovery trends and patterns"""
        days = int(request.query_params.get('days', 30))
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get recovery logs within date range
        recovery_logs = WorkflowRecoveryLog.objects.filter(
            started_at__gte=start_date,
            started_at__lte=end_date
        )
        
        # Calculate trends
        trends = {
            'period_days': days,
            'total_recoveries': recovery_logs.count(),
            'success_rate': 0.0,
            'recovery_types': {},
            'trigger_reasons': {},
            'daily_stats': []
        }
        
        if trends['total_recoveries'] > 0:
            successful = recovery_logs.filter(was_successful=True).count()
            trends['success_rate'] = (successful / trends['total_recoveries']) * 100
            
            # Group by recovery type
            type_counts = recovery_logs.values('recovery_type').annotate(
                count=Count('id')
            )
            for item in type_counts:
                trends['recovery_types'][item['recovery_type']] = item['count']
            
            # Group by trigger reason
            reason_counts = recovery_logs.values('trigger_reason').annotate(
                count=Count('id')
            )
            for item in reason_counts:
                trends['trigger_reasons'][item['trigger_reason']] = item['count']
        
        return Response(trends)
    
    @action(detail=False, methods=['post'])
    def cleanup_checkpoints(self, request):
        """Clean up old checkpoints"""
        serializer = CheckpointCleanupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        workflow_id = data.get('workflow_id')
        days_old = data['days_old']
        cleanup_type = data['cleanup_type']
        dry_run = data['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        # Build query
        query = Q(created_at__lt=cutoff_date)
        if workflow_id:
            query &= Q(workflow_id=workflow_id)
        
        if cleanup_type == 'expired':
            query &= Q(expires_at__lt=timezone.now())
        elif cleanup_type == 'unused':
            query &= Q(recovery_logs__isnull=True, replay_sessions__isnull=True)
        
        checkpoints = WorkflowCheckpoint.objects.filter(query)
        
        result = {
            'cleanup_type': cleanup_type,
            'days_old': days_old,
            'workflow_id': str(workflow_id) if workflow_id else None,
            'dry_run': dry_run,
            'checkpoints_found': checkpoints.count(),
            'total_size_mb': 0.0
        }
        
        # Calculate total size
        total_size = sum(
            cp.checkpoint_size_bytes or 0 
            for cp in checkpoints
        )
        result['total_size_mb'] = total_size / (1024 * 1024)
        
        if not dry_run:
            deleted_count = checkpoints.count()
            checkpoints.delete()
            result['checkpoints_deleted'] = deleted_count
            result['action'] = 'deleted'
        else:
            result['action'] = 'dry_run_only'
        
        return Response(result)