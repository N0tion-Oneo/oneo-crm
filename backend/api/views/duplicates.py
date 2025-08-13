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
        """Get duplicate rules filtered by tenant and pipeline if accessed via nested route"""
        queryset = DuplicateRule.objects.filter(
            tenant=self.request.tenant
        ).select_related('pipeline', 'created_by').prefetch_related('duplicate_test_cases').order_by('-created_at')
        
        # If accessed via nested pipeline route, filter by pipeline
        pipeline_pk = self.kwargs.get('pipeline_pk')
        if pipeline_pk:
            queryset = queryset.filter(pipeline_id=pipeline_pk)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set tenant, user, and pipeline when creating duplicate rule"""
        try:
            save_kwargs = {
                'tenant': self.request.tenant,
                'created_by': self.request.user
            }
            
            # If accessed via nested pipeline route, auto-set pipeline
            pipeline_pk = self.kwargs.get('pipeline_pk')
            if pipeline_pk:
                from pipelines.models import Pipeline
                pipeline = Pipeline.objects.get(id=pipeline_pk)
                save_kwargs['pipeline'] = pipeline
            
            serializer.save(**save_kwargs)
        except Exception as e:
            logger.error(f"Failed to create duplicate rule: {e}", exc_info=True)
            raise
    
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
    def test_rule(self, request, pk=None, pipeline_pk=None):
        """Test duplicate rule against sample data"""
        rule = self.get_object()
        serializer = RuleTestRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            record1_data = serializer.validated_data['record1_data']
            record2_data = serializer.validated_data['record2_data']
            
            # Initialize logic engine
            # In multi-tenant architecture, tenant context is managed by schema
            tenant_id = getattr(request, 'tenant', None)
            tenant_id = getattr(tenant_id, 'id', None) if tenant_id else None
            engine = DuplicateLogicEngine(tenant_id)
            
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
            logger.error(f"Rule data: {rule}")
            logger.error(f"Record 1 data: {record1_data}")
            logger.error(f"Record 2 data: {record2_data}")
            logger.error(f"Rule logic: {getattr(rule, 'logic', None)}")
            return Response(
                {'error': f'Test failed: {str(e)}', 'debug_info': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Detect duplicates",
        description="Run duplicate detection against provided data",
        request=RuleTestRequestSerializer
    )
    @action(detail=True, methods=['POST'])
    def detect_duplicates(self, request, pk=None, pipeline_pk=None):
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
            # In multi-tenant architecture, tenant context is managed by schema
            tenant_id = getattr(request, 'tenant', None)
            tenant_id = getattr(tenant_id, 'id', None) if tenant_id else None
            engine = DuplicateLogicEngine(tenant_id)
            
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
    def clone(self, request, pk=None, pipeline_pk=None):
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
        summary="Get duplicate count for record",
        description="Get count of unresolved duplicate matches for a specific record",
        parameters=[
            OpenApiParameter('record_id', int, description='Record ID to check duplicates for')
        ]
    )
    @action(detail=False, methods=['GET'])
    def record_duplicate_count(self, request):
        """Get duplicate count for a specific record"""
        record_id = request.query_params.get('record_id')
        
        if not record_id:
            return Response(
                {'error': 'record_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get unresolved duplicate matches for this record
            matches_count = DuplicateMatch.objects.filter(
                tenant=request.tenant,
                status='pending'
            ).filter(
                Q(record1_id=record_id) | Q(record2_id=record_id)
            ).count()
            
            return Response({
                'record_id': record_id,
                'duplicate_count': matches_count,
                'has_duplicates': matches_count > 0
            })
            
        except Exception as e:
            logger.error(f"Error getting duplicate count for record {record_id}: {e}", exc_info=True)
            return Response(
                {'error': f'Failed to get duplicate count: {str(e)}'}, 
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
        """Get URL extraction rules filtered by tenant and pipeline if accessed via nested route"""
        queryset = URLExtractionRule.objects.filter(
            tenant=self.request.tenant
        ).order_by('-created_at')
        
        # If accessed via nested pipeline route, filter by pipeline
        pipeline_pk = self.kwargs.get('pipeline_pk')
        if pipeline_pk:
            queryset = queryset.filter(pipeline_id=pipeline_pk)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set tenant, user, and pipeline when creating URL extraction rule"""
        try:
            save_kwargs = {
                'tenant': self.request.tenant,
                'created_by': self.request.user
            }
            
            # If accessed via nested pipeline route, auto-set pipeline
            pipeline_pk = self.kwargs.get('pipeline_pk')
            if pipeline_pk:
                from pipelines.models import Pipeline
                pipeline = Pipeline.objects.get(id=pipeline_pk)
                save_kwargs['pipeline'] = pipeline
            
            serializer.save(**save_kwargs)
        except Exception as e:
            logger.error(f"Failed to create URL extraction rule: {e}", exc_info=True)
            raise
    
    @extend_schema(
        summary="Test URL extraction rule",
        description="Test URL extraction rule against sample URLs",
        request=URLExtractionTestSerializer,
        responses={200: {"description": "Test results"}}
    )
    @action(detail=True, methods=['POST'])
    def test_extraction(self, request, pk=None, pipeline_pk=None):
        """Test URL extraction rule against sample URLs"""
        rule = self.get_object()
        serializer = URLExtractionTestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        test_urls = serializer.validated_data['test_urls']
        
        try:
            from duplicates.logic_engine import FieldMatcher
            # In multi-tenant architecture, tenant context is managed by schema
            tenant_id = getattr(request, 'tenant', None)
            tenant_id = getattr(tenant_id, 'id', None) if tenant_id else None
            field_matcher = FieldMatcher(tenant_id)
            
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
    
    @extend_schema(
        summary="Live URL testing with Smart URL Processor",
        description="Test URLs in real-time using intelligent URL processor without database storage",
        request={
            "type": "object", 
            "properties": {
                "test_urls": {"type": "array", "items": {"type": "string"}},
                "template_name": {"type": "string", "required": False},
                "custom_template": {"type": "object", "required": False}
            },
            "required": ["test_urls"]
        },
        responses={200: {"description": "Live test results with processing steps"}}
    )
    @action(detail=False, methods=['POST'])
    def live_test(self, request):
        """Live URL testing with Smart URL Processor - no database storage"""
        try:
            test_urls = request.data.get('test_urls', [])
            template_name = request.data.get('template_name')
            custom_template_data = request.data.get('custom_template')
            
            if not test_urls:
                return Response(
                    {'error': 'test_urls is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize Smart URL Processor
            from duplicates.smart_url_processor import SmartURLProcessor, URLTemplate
            processor = SmartURLProcessor()
            
            # Handle custom template if provided
            custom_template = None
            if custom_template_data:
                try:
                    custom_template = URLTemplate(
                        name=custom_template_data.get('name', 'Custom Template'),
                        domains=custom_template_data.get('domains', []),
                        path_patterns=custom_template_data.get('path_patterns', []),
                        identifier_regex=custom_template_data.get('identifier_regex', '([^/]+)'),
                        normalization_rules=custom_template_data.get('normalization_rules', {}),
                        mobile_schemes=custom_template_data.get('mobile_schemes', [])
                    )
                except Exception as e:
                    return Response(
                        {'error': f'Invalid custom template: {str(e)}'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Process all URLs using smart processor
            if len(test_urls) > 1:
                # Bulk testing
                results = processor.test_urls(test_urls, template_name, custom_template)
            else:
                # Single URL processing with detailed steps
                result = processor.normalize_url(test_urls[0], template_name, custom_template)
                results = {
                    'success_rate': 1.0 if result.success else 0.0,
                    'total_tested': 1,
                    'successful': 1 if result.success else 0,
                    'failed': 0 if result.success else 1,
                    'results': [result._asdict()],
                    'template_used': template_name or 'custom_template'
                }
            
            # Add available templates for frontend
            available_templates = list(processor.templates.keys())
            
            return Response({
                'processing_results': results,
                'available_templates': available_templates,
                'test_metadata': {
                    'total_urls': len(test_urls),
                    'template_used': template_name or 'custom_template',
                    'custom_template_provided': custom_template is not None,
                    'timestamp': timezone.now().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Live URL test error: {e}", exc_info=True)
            return Response(
                {'error': f'Live test failed: {str(e)}'}, 
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
    def run_test(self, request, pk=None, pipeline_pk=None):
        """Run a specific test case"""
        test_case = self.get_object()
        
        try:
            # Initialize logic engine
            # In multi-tenant architecture, tenant context is managed by schema
            tenant_id = getattr(request, 'tenant', None)
            tenant_id = getattr(tenant_id, 'id', None) if tenant_id else None
            engine = DuplicateLogicEngine(tenant_id)
            
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
        """Get duplicate matches filtered by tenant and pipeline if accessed via nested route"""
        queryset = DuplicateMatch.objects.filter(
            tenant=self.request.tenant
        ).order_by('-detected_at')
        
        # If accessed via nested pipeline route, filter by pipeline via rule relationship
        pipeline_pk = self.kwargs.get('pipeline_pk')
        if pipeline_pk:
            queryset = queryset.filter(rule__pipeline_id=pipeline_pk)
        
        # Filter by record_id if provided (for duplicate indicator checking)
        record_id = self.request.query_params.get('record_id')
        if record_id:
            queryset = queryset.filter(
                Q(record1_id=record_id) | Q(record2_id=record_id)
            )
        
        return queryset
    
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
    
    @extend_schema(
        summary="Merge records with field-level control",
        description="Merge two records with granular field-level decisions",
        request={
            'type': 'object',
            'properties': {
                'match_id': {'type': 'integer', 'description': 'Duplicate match ID'},
                'primary_record_id': {'type': 'integer', 'description': 'Record to keep as primary'},
                'field_decisions': {
                    'type': 'object',
                    'description': 'Field-level merge decisions',
                    'additionalProperties': {
                        'type': 'object',
                        'properties': {
                            'source': {'type': 'string', 'enum': ['left', 'right', 'custom']},
                            'value': {'description': 'Custom value if source is custom'}
                        }
                    }
                },
                'notes': {'type': 'string', 'description': 'Merge notes'}
            },
            'required': ['match_id', 'primary_record_id', 'field_decisions']
        }
    )
    @action(detail=False, methods=['POST'])
    def merge_records(self, request):
        """Merge records with field-level control"""
        try:
            match_id = request.data.get('match_id')
            primary_record_id = request.data.get('primary_record_id')
            field_decisions = request.data.get('field_decisions', {})
            notes = request.data.get('notes', '')
            
            if not match_id or not primary_record_id:
                return Response(
                    {'error': 'match_id and primary_record_id are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the duplicate match
            try:
                match = DuplicateMatch.objects.get(
                    id=match_id,
                    tenant=request.tenant,
                    status='pending'
                )
            except DuplicateMatch.DoesNotExist:
                return Response(
                    {'error': 'Duplicate match not found or already resolved'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Determine primary and secondary records
            if primary_record_id == match.record1.id:
                primary_record = match.record1
                secondary_record = match.record2
            elif primary_record_id == match.record2.id:
                primary_record = match.record2
                secondary_record = match.record1
            else:
                return Response(
                    {'error': 'primary_record_id must match one of the records in the duplicate match'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Apply field-level merge decisions
                merged_data = primary_record.data.copy()
                merge_audit = {
                    'original_primary_data': primary_record.data.copy(),
                    'original_secondary_data': secondary_record.data.copy(),
                    'field_decisions': field_decisions,
                    'merge_timestamp': timezone.now().isoformat()
                }
                
                for field_name, decision in field_decisions.items():
                    source = decision.get('source', 'left')
                    
                    if source == 'left':
                        # Keep primary record's value (already in merged_data)
                        pass
                    elif source == 'right':
                        # Use secondary record's value
                        if field_name in secondary_record.data:
                            merged_data[field_name] = secondary_record.data[field_name]
                    elif source == 'custom':
                        # Use custom value
                        merged_data[field_name] = decision.get('value')
                
                # Update primary record with merged data
                primary_record.data = merged_data
                primary_record.save()
                
                # Soft delete secondary record
                secondary_record.is_deleted = True
                secondary_record.save()
                
                # Create resolution record
                resolution = DuplicateResolution.objects.create(
                    tenant=request.tenant,
                    duplicate_match=match,
                    action_taken='merge',
                    resolved_by=request.user,
                    notes=notes,
                    primary_record=primary_record,
                    merged_record=secondary_record,
                    data_changes={
                        'action': 'field_level_merge',
                        'primary_record_id': str(primary_record.id),
                        'merged_record_id': str(secondary_record.id),
                        'merge_audit': merge_audit
                    }
                )
                
                # Update match status
                match.status = 'merged'
                match.reviewed_by = request.user
                match.reviewed_at = timezone.now()
                match.resolution_notes = f"Merged with field-level control. {notes}".strip()
                match.save()
                
                return Response({
                    'success': True,
                    'merged_record_id': str(primary_record.id),
                    'deleted_record_id': str(secondary_record.id),
                    'resolution_id': resolution.id,
                    'merge_summary': {
                        'fields_merged': len(field_decisions),
                        'primary_record': str(primary_record.id),
                        'secondary_record': str(secondary_record.id)
                    }
                })
                
        except Exception as e:
            logger.error(f"Record merge error: {e}", exc_info=True)
            return Response(
                {'error': f'Record merge failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Rollback a resolved duplicate match",
        description="Undo a duplicate resolution and restore original state",
        request={
            'type': 'object',
            'properties': {
                'resolution_id': {'type': 'integer', 'description': 'Resolution ID to rollback'},
                'notes': {'type': 'string', 'description': 'Rollback reason/notes'}
            },
            'required': ['resolution_id']
        }
    )
    @action(detail=False, methods=['POST'])
    def rollback_resolution(self, request):
        """Rollback a duplicate match resolution"""
        try:
            resolution_id = request.data.get('resolution_id')
            rollback_notes = request.data.get('notes', '')
            
            if not resolution_id:
                return Response(
                    {'error': 'resolution_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the resolution
            try:
                from duplicates.models import DuplicateResolution
                resolution = DuplicateResolution.objects.get(
                    id=resolution_id,
                    tenant=request.tenant
                )
            except DuplicateResolution.DoesNotExist:
                return Response(
                    {'error': 'Resolution not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            match = resolution.duplicate_match
            
            # Check if match can be rolled back
            if match.status == 'pending':
                return Response(
                    {'error': 'Match is already in pending state'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                rollback_successful = False
                rollback_details = {
                    'original_action': resolution.action_taken,
                    'rollback_timestamp': timezone.now().isoformat(),
                    'rollback_by': request.user.username
                }
                
                # Rollback based on the original action
                if resolution.action_taken == 'merge':
                    # Restore the merged/deleted record
                    if resolution.merged_record and resolution.merged_record.is_deleted:
                        # Get the merge audit data to restore original state
                        merge_audit = resolution.data_changes.get('merge_audit', {})
                        
                        # Restore the deleted record
                        resolution.merged_record.is_deleted = False
                        resolution.merged_record.save()
                        
                        # Restore primary record's original data if we have it
                        if 'original_primary_data' in merge_audit and resolution.primary_record:
                            resolution.primary_record.data = merge_audit['original_primary_data']
                            resolution.primary_record.save()
                        
                        rollback_details['restored_record_id'] = str(resolution.merged_record.id)
                        rollback_details['primary_record_restored'] = 'original_primary_data' in merge_audit
                        rollback_successful = True
                    
                elif resolution.action_taken == 'ignore':
                    # Remove exclusion if it exists
                    from duplicates.models import DuplicateExclusion
                    exclusions = DuplicateExclusion.objects.filter(
                        tenant=request.tenant,
                        record1=match.record1,
                        record2=match.record2
                    )
                    exclusion_count = exclusions.count()
                    exclusions.delete()
                    
                    rollback_details['exclusions_removed'] = exclusion_count
                    rollback_successful = True
                    
                elif resolution.action_taken == 'keep_both':
                    # Just reset to pending state
                    rollback_successful = True
                
                if rollback_successful:
                    # Reset the match to pending state
                    match.status = 'pending'
                    match.reviewed_by = None
                    match.reviewed_at = None
                    match.resolution_notes = f"Rolled back by {request.user.username}. {rollback_notes}".strip()
                    match.save()
                    
                    # Update resolution record with rollback info
                    resolution.data_changes['rollback'] = rollback_details
                    resolution.notes = f"{resolution.notes}\n\nROLLBACK: {rollback_notes}".strip()
                    resolution.save()
                    
                    # Create a new resolution record for the rollback
                    rollback_resolution = DuplicateResolution.objects.create(
                        tenant=request.tenant,
                        duplicate_match=match,
                        action_taken='rollback',
                        resolved_by=request.user,
                        notes=f"Rollback of {resolution.action_taken} action. {rollback_notes}".strip(),
                        data_changes={
                            'action': 'rollback',
                            'original_resolution_id': resolution.id,
                            'rollback_details': rollback_details
                        }
                    )
                    
                    return Response({
                        'success': True,
                        'match_id': str(match.id),
                        'original_action': resolution.action_taken,
                        'rollback_resolution_id': rollback_resolution.id,
                        'rollback_details': rollback_details,
                        'message': f'Successfully rolled back {resolution.action_taken} action'
                    })
                else:
                    return Response(
                        {'error': f'Unable to rollback {resolution.action_taken} action'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
        except Exception as e:
            logger.error(f"Rollback error: {e}", exc_info=True)
            return Response(
                {'error': f'Rollback failed: {str(e)}'}, 
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
                rule_filter = Q(rule__id=request.query_params['rule_id'])
            
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