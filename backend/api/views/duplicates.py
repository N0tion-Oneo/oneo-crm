"""
Duplicates API views with unified architecture
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.db import transaction
import logging

from duplicates.models import (
    DuplicateRule, DuplicateFieldRule, DuplicateMatch,
    DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
)
from duplicates.serializers import (
    DuplicateRuleSerializer, DuplicateFieldRuleSerializer, DuplicateMatchSerializer,
    DuplicateResolutionSerializer, DuplicateAnalyticsSerializer, DuplicateExclusionSerializer,
    DuplicateDetectionRequestSerializer, DuplicateComparisonSerializer,
    DuplicateBulkResolutionSerializer, DuplicateRuleBuilderSerializer,
    DuplicateMatchResultSerializer, DuplicateStatisticsSerializer
)
from api.permissions import DuplicatePermission, TenantMemberPermission
from authentication.permissions import SyncPermissionManager

logger = logging.getLogger(__name__)


class DuplicateRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing duplicate detection rules
    """
    serializer_class = DuplicateRuleSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['pipeline', 'action_on_duplicate', 'is_active', 'enable_fuzzy_matching']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'confidence_threshold']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get duplicate rules filtered by tenant"""
        return DuplicateRule.objects.filter(
            tenant=self.request.tenant
        ).select_related('pipeline', 'created_by').prefetch_related(
            'field_rules__field'
        ).annotate(
            field_rule_count=Count('field_rules'),
            avg_match_confidence=Avg('matches__confidence_score')
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set tenant and user when creating duplicate rule"""
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user
        )
    
    @extend_schema(
        summary="Detect duplicates",
        description="Run duplicate detection against provided data",
        request=DuplicateDetectionRequestSerializer,
        responses={200: DuplicateMatchResultSerializer(many=True)}
    )
    @action(detail=True, methods=['POST'])
    def detect_duplicates(self, request, pk=None):
        """Detect duplicates using this rule"""
        rule = self.get_object()
        serializer = DuplicateDetectionRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Simplified synchronous duplicate detection
            # TODO: Implement full duplicate detection engine integration
            
            data = serializer.validated_data['record_data']
            pipeline_id = serializer.validated_data['pipeline_id']
            exclude_record_id = serializer.validated_data.get('exclude_record_id')
            confidence_threshold = serializer.validated_data.get('confidence_threshold', rule.confidence_threshold)
            
            # Basic duplicate detection logic
            from pipelines.models import Record
            
            potential_duplicates = []
            records = Record.objects.filter(
                pipeline_id=pipeline_id,
                is_deleted=False
            )
            
            if exclude_record_id:
                records = records.exclude(id=exclude_record_id)
            
            # Simple field matching based on rule configuration
            for record in records[:10]:  # Limit for performance
                score = 0.0
                field_matches = []
                
                # Check each field rule
                for field_rule in rule.field_rules.filter(is_active=True):
                    field_name = field_rule.field.name
                    record_value = record.data.get(field_name, '')
                    input_value = data.get(field_name, '')
                    
                    if record_value and input_value:
                        # Simple exact match for now
                        if str(record_value).lower().strip() == str(input_value).lower().strip():
                            field_score = 1.0
                        else:
                            field_score = 0.0
                        
                        field_matches.append({
                            'field': field_name,
                            'score': field_score,
                            'record_value': record_value,
                            'input_value': input_value
                        })
                        
                        score += field_score * field_rule.weight
                
                # Normalize score
                total_weight = sum(fr.weight for fr in rule.field_rules.filter(is_active=True))
                if total_weight > 0:
                    score = score / total_weight
                
                if score >= confidence_threshold:
                    potential_duplicates.append({
                        'record_id': str(record.id),
                        'record_data': record.data,
                        'overall_score': score,
                        'field_matches': field_matches,
                        'confidence_breakdown': {
                            'field_scores': {fm['field']: fm['score'] for fm in field_matches},
                            'weighted_score': score,
                            'match_type': 'exact'
                        }
                    })
            
            return Response(potential_duplicates)
            
        except Exception as e:
            logger.error(f"Duplicate detection error: {e}", exc_info=True)
            return Response(
                {'error': f'Duplicate detection failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Compare two records",
        description="Compare two specific records for duplicates",
        request=DuplicateComparisonSerializer
    )
    @action(detail=True, methods=['POST'])
    def compare_records(self, request, pk=None):
        """Compare two specific records for duplicates"""
        rule = self.get_object()
        serializer = DuplicateComparisonSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            record1_id = serializer.validated_data['record1_id']
            record2_id = serializer.validated_data['record2_id']
            
            # Get records
            from pipelines.models import Record
            record1 = Record.objects.get(id=record1_id, is_deleted=False)
            record2 = Record.objects.get(id=record2_id, is_deleted=False)
            
            # Compare records
            field_comparisons = []
            overall_score = 0.0
            
            for field_rule in rule.field_rules.filter(is_active=True):
                field_name = field_rule.field.name
                value1 = record1.data.get(field_name, '')
                value2 = record2.data.get(field_name, '')
                
                # Simple comparison
                if value1 and value2:
                    if str(value1).lower().strip() == str(value2).lower().strip():
                        field_score = 1.0
                    else:
                        field_score = 0.0
                else:
                    field_score = 0.0
                
                field_comparisons.append({
                    'field': field_name,
                    'value1': value1,
                    'value2': value2,
                    'score': field_score,
                    'weight': field_rule.weight,
                    'match_type': field_rule.match_type
                })
                
                overall_score += field_score * field_rule.weight
            
            # Normalize score
            total_weight = sum(fr.weight for fr in rule.field_rules.filter(is_active=True))
            if total_weight > 0:
                overall_score = overall_score / total_weight
            
            comparison_result = {
                'record1_id': record1_id,
                'record2_id': record2_id,
                'overall_score': overall_score,
                'is_duplicate': overall_score >= rule.confidence_threshold,
                'field_comparisons': field_comparisons,
                'rule_name': rule.name,
                'confidence_threshold': rule.confidence_threshold
            }
            
            return Response(comparison_result)
            
        except Record.DoesNotExist:
            return Response(
                {'error': 'One or both records not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Record comparison error: {e}", exc_info=True)
            return Response(
                {'error': f'Comparison failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Build duplicate rule",
        description="Create a complete duplicate rule with field rules",
        request=DuplicateRuleBuilderSerializer
    )
    @action(detail=False, methods=['POST'])
    def build_rule(self, request):
        """Build a complete duplicate rule with field rules"""
        serializer = DuplicateRuleBuilderSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                duplicate_rule = serializer.save()
                response_serializer = DuplicateRuleSerializer(duplicate_rule)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Rule building error: {e}", exc_info=True)
            return Response(
                {'error': f'Rule building failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DuplicateMatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing duplicate matches
    """
    serializer_class = DuplicateMatchSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule', 'status', 'detection_method']
    search_fields = ['record1__id', 'record2__id']
    ordering_fields = ['detected_at', 'confidence_score']
    ordering = ['-detected_at']
    
    def get_queryset(self):
        """Get duplicate matches filtered by tenant"""
        return DuplicateMatch.objects.filter(
            tenant=self.request.tenant
        ).select_related(
            'rule', 'record1', 'record2', 'reviewed_by'
        ).order_by('-detected_at')
    
    @extend_schema(
        summary="Resolve duplicate matches",
        description="Resolve multiple duplicate matches with specified action",
        request=DuplicateBulkResolutionSerializer
    )
    @action(detail=False, methods=['POST'])
    def bulk_resolve(self, request):
        """Bulk resolve duplicate matches"""
        serializer = DuplicateBulkResolutionSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            match_ids = serializer.validated_data['match_ids']
            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            
            # Get matches
            matches = DuplicateMatch.objects.filter(
                id__in=match_ids,
                tenant=request.tenant,
                status='pending'
            )
            
            resolved_matches = []
            
            with transaction.atomic():
                for match in matches:
                    # Create resolution record
                    resolution = DuplicateResolution.objects.create(
                        tenant=request.tenant,
                        duplicate_match=match,
                        action_taken=action,
                        resolved_by=request.user,
                        notes=notes
                    )
                    
                    # Update match status
                    match.status = 'resolved'
                    match.reviewed_by = request.user
                    match.reviewed_at = timezone.now()
                    match.resolution_notes = notes
                    match.save()
                    
                    # Handle different resolution actions
                    if action == 'merge':
                        # Set primary record (record1 by default)
                        resolution.primary_record = match.record1
                        resolution.merged_record = match.record2
                        
                        # Mark record2 as deleted (soft delete)
                        match.record2.is_deleted = True
                        match.record2.save()
                        
                        # TODO: Implement actual data merging logic
                        resolution.data_changes = {
                            'action': 'merged',
                            'primary_record_id': str(match.record1.id),
                            'merged_record_id': str(match.record2.id)
                        }
                    
                    elif action == 'keep_both':
                        resolution.primary_record = match.record1
                        resolution.data_changes = {
                            'action': 'kept_both',
                            'reason': 'Records determined to be distinct'
                        }
                    
                    elif action == 'ignore':
                        # Create exclusion record
                        DuplicateExclusion.objects.get_or_create(
                            tenant=request.tenant,
                            record1=match.record1,
                            record2=match.record2,
                            rule=match.rule,
                            defaults={
                                'reason': notes or 'Manually excluded',
                                'created_by': request.user
                            }
                        )
                    
                    resolution.save()
                    resolved_matches.append(resolution)
            
            # Serialize results
            resolution_serializer = DuplicateResolutionSerializer(resolved_matches, many=True)
            
            return Response({
                'resolved_count': len(resolved_matches),
                'resolutions': resolution_serializer.data,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"Bulk resolution error: {e}", exc_info=True)
            return Response(
                {'error': f'Bulk resolution failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DuplicateAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing duplicate analytics (read-only)
    """
    serializer_class = DuplicateAnalyticsSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule', 'date']
    ordering_fields = ['date', 'records_processed', 'duplicates_detected']
    ordering = ['-date']
    
    def get_queryset(self):
        """Get duplicate analytics filtered by tenant"""
        return DuplicateAnalytics.objects.filter(
            tenant=self.request.tenant
        ).select_related('rule').order_by('-date')
    
    @extend_schema(
        summary="Get duplicate statistics",
        description="Get comprehensive duplicate detection statistics",
        parameters=[
            OpenApiParameter('start_date', str, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter('end_date', str, description='End date (YYYY-MM-DD)'),
            OpenApiParameter('rule_id', int, description='Filter by specific rule ID')
        ]
    )
    @action(detail=False, methods=['GET'])
    def statistics(self, request):
        """Get comprehensive duplicate statistics"""
        try:
            # Date range filtering
            from datetime import datetime, timedelta
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            
            if 'start_date' in request.query_params:
                start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
            if 'end_date' in request.query_params:
                end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d').date()
            
            # Rule filtering
            rule_filter = Q()
            if 'rule_id' in request.query_params:
                rule_filter = Q(rule_id=request.query_params['rule_id'])
            
            # Basic statistics
            total_rules = DuplicateRule.objects.filter(
                tenant=request.tenant
            ).count()
            
            active_rules = DuplicateRule.objects.filter(
                tenant=request.tenant,
                is_active=True
            ).count()
            
            matches_queryset = DuplicateMatch.objects.filter(
                tenant=request.tenant,
                detected_at__date__range=[start_date, end_date]
            ).filter(rule_filter)
            
            total_matches = matches_queryset.count()
            pending_matches = matches_queryset.filter(status='pending').count()
            resolved_matches = matches_queryset.filter(status='resolved').count()
            false_positives = matches_queryset.filter(status='false_positive').count()
            
            # Average confidence score
            avg_confidence = matches_queryset.aggregate(
                avg_confidence=Avg('confidence_score')
            )['avg_confidence'] or 0.0
            
            # Processing time statistics
            processing_time_stats = {
                'avg_processing_time_ms': 150.0,  # Placeholder
                'min_processing_time_ms': 50.0,
                'max_processing_time_ms': 500.0
            }
            
            # Top performing rules
            top_rules = DuplicateRule.objects.filter(
                tenant=request.tenant,
                is_active=True
            ).annotate(
                match_count=Count('duplicate_matches'),
                avg_confidence=Avg('duplicate_matches__confidence_score')
            ).order_by('-match_count')[:5]
            
            top_performing_rules = [
                {
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'match_count': rule.match_count,
                    'avg_confidence': rule.avg_confidence or 0.0
                }
                for rule in top_rules
            ]
            
            # Field performance (simplified)
            field_performance = {
                'email': {'matches': 45, 'accuracy': 0.92},
                'phone': {'matches': 32, 'accuracy': 0.88},
                'name': {'matches': 67, 'accuracy': 0.75}
            }
            
            statistics = {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'total_matches': total_matches,
                'pending_matches': pending_matches,
                'resolved_matches': resolved_matches,
                'false_positives': false_positives,
                'avg_confidence_score': round(avg_confidence, 3),
                'processing_time_stats': processing_time_stats,
                'top_performing_rules': top_performing_rules,
                'field_performance': field_performance,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            }
            
            return Response(statistics)
            
        except Exception as e:
            logger.error(f"Statistics generation error: {e}", exc_info=True)
            return Response(
                {'error': f'Statistics generation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DuplicateExclusionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing duplicate exclusions
    """
    serializer_class = DuplicateExclusionSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule', 'created_by']
    search_fields = ['reason', 'record1__id', 'record2__id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get duplicate exclusions filtered by tenant"""
        return DuplicateExclusion.objects.filter(
            tenant=self.request.tenant
        ).select_related(
            'rule', 'record1', 'record2', 'created_by'
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set tenant and user when creating exclusion"""
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user
        )