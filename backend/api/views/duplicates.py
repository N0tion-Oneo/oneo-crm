"""
Unified duplicate detection API views with simplified AND/OR logic system
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

# Import unified models
from duplicates.models import (
    DuplicateRule, URLExtractionRule, DuplicateRuleTest, DuplicateDetectionResult,
    DuplicateMatch, DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
)
from duplicates.logic_engine import DuplicateLogicEngine

# Import unified serializers from api/serializers.py
from api.serializers import (
    URLExtractionRuleSerializer, DuplicateRuleSerializer, DuplicateRuleTestSerializer,
    RuleBuilderConfigSerializer, RuleTestRequestSerializer, URLExtractionTestSerializer
)
from duplicates.serializers import (
    DuplicateMatchSerializer, DuplicateResolutionSerializer, DuplicateAnalyticsSerializer,
    DuplicateExclusionSerializer, DuplicateBulkResolutionSerializer
)

from api.permissions import DuplicatePermission, TenantMemberPermission
from authentication.permissions import SyncPermissionManager
from pipelines.models import Pipeline

logger = logging.getLogger(__name__)


class DuplicateRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing duplicate rules with AND/OR logic
    """
    serializer_class = DuplicateRuleSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['pipeline', 'action_on_duplicate', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get duplicate rules filtered by tenant"""
        return DuplicateRule.objects.filter(
            tenant=self.request.tenant
        ).select_related('pipeline', 'created_by').prefetch_related('duplicate_test_cases').order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set tenant and user when creating duplicate rule"""
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user
        )
    
    @extend_schema(
        summary="Get rule builder configuration",
        description="Get configuration data needed for rule builder UI",
        parameters=[
            OpenApiParameter('pipeline_id', int, description='Pipeline ID to get configuration for')
        ]
    )
    @action(detail=False, methods=['GET'])
    def builder_config(self, request):
        """Get rule builder configuration data"""
        pipeline_id = request.query_params.get('pipeline_id')
        
        if not pipeline_id:
            return Response(
                {'error': 'pipeline_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = RuleBuilderConfigSerializer(
            data={'pipeline_id': pipeline_id},
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.to_representation(None))
    
    @extend_schema(
        summary="Test duplicate rule",
        description="Test duplicate rule logic against sample record data",
        request=RuleTestRequestSerializer
    )
    @action(detail=True, methods=['POST'])
    def test_rule(self, request, pk=None):
        """Test duplicate rule against sample data"""
        rule = self.get_object()
        serializer = RuleTestRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            record1_data = serializer.validated_data['record1_data']
            record2_data = serializer.validated_data['record2_data']
            
            # Initialize logic engine
            engine = DuplicateLogicEngine(request.tenant.id)
            
            # Get detailed evaluation
            detailed_result = engine._detailed_evaluate_rule(rule, record1_data, record2_data)
            
            return Response({
                'rule_name': rule.name,
                'test_data': {
                    'record1': record1_data,
                    'record2': record2_data
                },
                'result': detailed_result,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Rule test error: {e}", exc_info=True)
            return Response(
                {'error': f'Test failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Detect duplicates",
        description="Run duplicate detection against provided data",
        request=RuleTestRequestSerializer
    )
    @action(detail=True, methods=['POST'])
    def detect_duplicates(self, request, pk=None):
        """Detect duplicates using this rule against all records in pipeline"""
        rule = self.get_object()
        serializer = RuleTestRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            input_data = serializer.validated_data['record1_data']
            exclude_record_id = serializer.validated_data.get('record2_data', {}).get('exclude_record_id')
            
            # Get all records from the pipeline
            from pipelines.models import Record
            records = Record.objects.filter(
                pipeline=rule.pipeline
            )
            
            if exclude_record_id:
                records = records.exclude(id=exclude_record_id)
            
            # Initialize logic engine
            engine = DuplicateLogicEngine(request.tenant.id)
            
            potential_duplicates = []
            
            # Check against each record
            for record in records[:50]:  # Limit for performance
                try:
                    is_duplicate = engine.evaluate_rule(rule, input_data, record.data)
                    
                    if is_duplicate:
                        matched_fields = engine.get_matched_fields(rule, input_data, record.data)
                        potential_duplicates.append({
                            'record_id': str(record.id),
                            'record_data': record.data,
                            'matched_fields': matched_fields,
                            'confidence_score': 0.95  # High confidence for boolean match
                        })
                        
                except Exception as e:
                    logger.error(f"Error checking record {record.id}: {e}")
                    continue
            
            return Response({
                'rule_name': rule.name,
                'input_data': input_data,
                'duplicates_found': len(potential_duplicates),
                'potential_duplicates': potential_duplicates,
                'checked_records': min(records.count(), 50),
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Duplicate detection error: {e}", exc_info=True)
            return Response(
                {'error': f'Duplicate detection failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Clone duplicate rule",
        description="Clone an existing duplicate rule to a new pipeline"
    )
    @action(detail=True, methods=['POST'])
    def clone(self, request, pk=None):
        """Clone duplicate rule to another pipeline"""
        source_rule = self.get_object()
        
        target_pipeline_id = request.data.get('target_pipeline_id')
        new_name = request.data.get('name')
        
        if not target_pipeline_id:
            return Response(
                {'error': 'target_pipeline_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not new_name:
            return Response(
                {'error': 'name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate target pipeline
            target_pipeline = Pipeline.objects.get(
                id=target_pipeline_id
            )
            
            with transaction.atomic():
                # Clone the rule
                cloned_rule = DuplicateRule.objects.create(
                    tenant=request.tenant,
                    name=new_name,
                    description=f"Cloned from: {source_rule.name}",
                    pipeline=target_pipeline,
                    logic=source_rule.logic,
                    action_on_duplicate=source_rule.action_on_duplicate,
                    created_by=request.user
                )
                
                serializer = self.get_serializer(cloned_rule)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Target pipeline not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Rule clone error: {e}", exc_info=True)
            return Response(
                {'error': f'Clone failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Validate rule logic",
        description="Validate rule logic structure without saving"
    )
    @action(detail=False, methods=['POST'])
    def validate_logic(self, request):
        """Validate rule logic structure"""
        logic = request.data.get('logic')
        pipeline_id = request.data.get('pipeline_id')
        
        if not logic:
            return Response(
                {'error': 'logic is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not pipeline_id:
            return Response(
                {'error': 'pipeline_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate pipeline exists
            pipeline = Pipeline.objects.get(id=pipeline_id)
            
            # Create temporary rule for validation
            temp_data = {
                'name': 'temp_validation',
                'pipeline': pipeline_id,
                'logic': logic,
                'action_on_duplicate': 'warn'
            }
            
            serializer = self.get_serializer(data=temp_data, context={'request': request})
            
            if serializer.is_valid():
                return Response({
                    'valid': True,
                    'message': 'Rule logic is valid'
                })
            else:
                return Response({
                    'valid': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Pipeline not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Logic validation error: {e}", exc_info=True)
            return Response(
                {'error': f'Validation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class URLExtractionRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing URL extraction rules
    """
    serializer_class = URLExtractionRuleSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get URL extraction rules filtered by tenant"""
        return URLExtractionRule.objects.filter(
            tenant=self.request.tenant
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set tenant and user when creating URL extraction rule"""
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user
        )
    
    @extend_schema(
        summary="Test URL extraction rule",
        description="Test URL extraction rule against sample URLs",
        request=URLExtractionTestSerializer,
        responses={200: {"description": "Test results"}}
    )
    @action(detail=True, methods=['POST'])
    def test_extraction(self, request, pk=None):
        """Test URL extraction rule against sample URLs"""
        rule = self.get_object()
        serializer = URLExtractionTestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        test_urls = serializer.validated_data['test_urls']
        
        try:
            from duplicates.logic_engine import FieldMatcher
            field_matcher = FieldMatcher(request.tenant.id)
            
            results = []
            for url in test_urls:
                try:
                    extracted = field_matcher._apply_url_extraction_rule(url, rule)
                    results.append({
                        'original_url': url,
                        'extracted_value': extracted,
                        'success': extracted is not None
                    })
                except Exception as e:
                    results.append({
                        'original_url': url,
                        'error': str(e),
                        'success': False
                    })
            
            success_rate = sum(1 for r in results if r['success']) / len(results)
            
            return Response({
                'rule_name': rule.name,
                'test_results': results,
                'success_rate': success_rate,
                'total_tested': len(results)
            })
            
        except Exception as e:
            logger.error(f"URL extraction test error: {e}", exc_info=True)
            return Response(
                {'error': f'Test failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DuplicateRuleTestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing duplicate rule test cases
    """
    serializer_class = DuplicateRuleTestSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get test cases filtered by tenant (through rule)"""
        return DuplicateRuleTest.objects.filter(
            rule__tenant=self.request.tenant
        ).select_related('rule').order_by('-created_at')
    
    @extend_schema(
        summary="Run test case",
        description="Execute a test case against its associated rule"
    )
    @action(detail=True, methods=['POST'])
    def run_test(self, request, pk=None):
        """Run a specific test case"""
        test_case = self.get_object()
        
        try:
            # Initialize logic engine
            engine = DuplicateLogicEngine(request.tenant.id)
            
            # Run the test - get detailed results
            detailed_result = engine._detailed_evaluate_rule(
                test_case.rule,
                test_case.record1_data,
                test_case.record2_data
            )
            
            # Update test case with results
            test_case.last_test_result = detailed_result['is_duplicate']
            test_case.last_test_at = timezone.now()
            test_case.test_details = detailed_result
            test_case.save()
            
            # Check if result matches expectation
            passed = test_case.last_test_result == test_case.expected_result
            
            return Response({
                'test_name': test_case.name,
                'expected_result': test_case.expected_result,
                'actual_result': test_case.last_test_result,
                'passed': passed,
                'execution_details': detailed_result,
                'tested_at': test_case.last_test_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Test execution error: {e}", exc_info=True)
            return Response(
                {'error': f'Test execution failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DuplicateMatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing duplicate matches (updated for simplified system)
    """
    serializer_class = DuplicateMatchSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'detection_method']
    search_fields = ['record1__id', 'record2__id']
    ordering_fields = ['detected_at', 'confidence_score']
    ordering = ['-detected_at']
    
    def get_queryset(self):
        """Get duplicate matches filtered by tenant"""
        return DuplicateMatch.objects.filter(
            tenant=self.request.tenant
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
    ViewSet for viewing duplicate analytics (read-only, updated for simplified system)
    """
    serializer_class = DuplicateAnalyticsSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date']
    ordering_fields = ['date', 'records_processed', 'duplicates_detected']
    ordering = ['-date']
    
    def get_queryset(self):
        """Get duplicate analytics filtered by tenant"""
        return DuplicateAnalytics.objects.filter(
            tenant=self.request.tenant
        ).order_by('-date')
    
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
                rule_filter = Q(detection_rule__id=request.query_params['rule_id'])
            
            # Basic statistics - updated for simplified system
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
            
            # Top performing rules - now using correct relationship
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
                    'avg_confidence': rule.avg_confidence or 0.0,
                    'action_on_duplicate': rule.action_on_duplicate
                }
                for rule in top_rules
            ]
            
            statistics = {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'total_matches': total_matches,
                'pending_matches': pending_matches,
                'resolved_matches': resolved_matches,
                'false_positives': false_positives,
                'avg_confidence_score': round(avg_confidence, 3),
                'top_performing_rules': top_performing_rules,
                'detection_results_count': DuplicateDetectionResult.objects.filter(
                    tenant=request.tenant,
                    created_at__date__range=[start_date, end_date]
                ).count(),
                'url_extraction_rules': URLExtractionRule.objects.filter(
                    tenant=request.tenant,
                    is_active=True
                ).count(),
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
    ViewSet for managing duplicate exclusions (unchanged from original)
    """
    serializer_class = DuplicateExclusionSerializer
    permission_classes = [DuplicatePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['created_by']
    search_fields = ['reason', 'record1__id', 'record2__id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get duplicate exclusions filtered by tenant"""
        return DuplicateExclusion.objects.filter(
            tenant=self.request.tenant
        ).select_related('record1', 'record2', 'created_by').order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set tenant and user when creating exclusion"""
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user
        )