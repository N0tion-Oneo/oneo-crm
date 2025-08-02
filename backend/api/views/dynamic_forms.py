"""
Dynamic forms API views for pipeline-based form generation
"""
from typing import Optional, Dict, Any
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import Http404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from pipelines.models import Pipeline, Record
from forms.dynamic import DynamicFormGenerator, generate_pipeline_form
from ..permissions import PipelinePermission, RecordPermission, TenantMemberPermission


class DynamicFormViewSet(viewsets.ViewSet):
    """
    Dynamic form generation API for pipelines
    Supports 5 form types based on pipeline schema and business rules
    """
    permission_classes = [permissions.IsAuthenticated, TenantMemberPermission]
    
    @extend_schema(
        summary="Generate internal full form",
        description="Type 1: Generate form with all pipeline fields for internal users",
        parameters=[
            OpenApiParameter(
                name='pipeline_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='internal')
    def internal_full(self, request, pipeline_pk=None):
        """Type 1: Generate internal full form"""
        pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        
        try:
            form_schema = generate_pipeline_form(
                pipeline_id=pipeline.id,
                mode='internal_full'
            )
            return Response(form_schema)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Generate public filtered form",
        description="Type 2: Generate form with only public-visible fields",
        parameters=[
            OpenApiParameter(
                name='pipeline_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='public')
    def public_filtered(self, request, pipeline_pk=None):
        """Type 2: Generate public filtered form"""
        pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        
        try:
            form_schema = generate_pipeline_form(
                pipeline_id=pipeline.id,
                mode='public_filtered'
            )
            return Response(form_schema)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Generate stage-specific internal form",
        description="Type 3: Generate form with stage-required fields for internal users",
        parameters=[
            OpenApiParameter(
                name='pipeline_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            ),
            OpenApiParameter(
                name='stage',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Target stage name'
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='stage/(?P<stage>[^/.]+)/internal')
    def stage_internal(self, request, pipeline_pk=None, stage=None):
        """Type 3: Generate stage-specific internal form"""
        pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        
        if not stage:
            return Response(
                {'error': 'Stage parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            form_schema = generate_pipeline_form(
                pipeline_id=pipeline.id,
                mode='stage_internal',
                stage=stage
            )
            return Response(form_schema)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Generate stage-specific public form",
        description="Type 4: Generate form with stage-required AND public-visible fields",
        parameters=[
            OpenApiParameter(
                name='pipeline_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            ),
            OpenApiParameter(
                name='stage',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Target stage name'
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='stage/(?P<stage>[^/.]+)/public')
    def stage_public(self, request, pipeline_pk=None, stage=None):
        """Type 4: Generate stage-specific public form (double filtered)"""
        pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        
        if not stage:
            return Response(
                {'error': 'Stage parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            form_schema = generate_pipeline_form(
                pipeline_id=pipeline.id,
                mode='stage_public',
                stage=stage
            )
            return Response(form_schema)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Generate shared record form",
        description="Type 5: Generate form for shared record with pre-populated data",
        parameters=[
            OpenApiParameter(
                name='pipeline_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            ),
            OpenApiParameter(
                name='record_id',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Record ID'
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='records/(?P<record_id>[^/.]+)/share')
    def shared_record(self, request, pipeline_pk=None, record_id=None):
        """Type 5: Generate shared record form"""
        pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        record = get_object_or_404(Record, pk=record_id, pipeline=pipeline)
        
        try:
            form_schema = generate_pipeline_form(
                pipeline_id=pipeline.id,
                mode='shared_record',
                record_data=record.data
            )
            return Response(form_schema)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Submit form data",
        description="Submit form data to create or update pipeline records",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'form_mode': {'type': 'string'},
                    'stage': {'type': 'string'},
                    'record_id': {'type': 'string'},
                    'data': {'type': 'object'}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='submit')
    def submit_form(self, request, pipeline_pk=None):
        """Submit form data to pipeline"""
        pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        
        form_mode = request.data.get('form_mode', 'internal_full')
        stage = request.data.get('stage')
        record_id = request.data.get('record_id')
        form_data = request.data.get('data', {})
        
        if not form_data:
            return Response(
                {'error': 'Form data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate data against form schema
            generator = DynamicFormGenerator(pipeline)
            form_schema = generator.generate_form(mode=form_mode, stage=stage)
            
            # TODO: Add form validation logic here
            
            # Create or update record
            if record_id:
                # Update existing record
                record = get_object_or_404(Record, pk=record_id, pipeline=pipeline)
                record.data.update(form_data)
                record.updated_by = request.user
                record.save()
            else:
                # Create new record
                record = Record.objects.create(
                    pipeline=pipeline,
                    data=form_data,
                    created_by=request.user,
                    updated_by=request.user
                )
            
            return Response({
                'success': True,
                'record_id': record.id,
                'message': 'Form submitted successfully'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to submit form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PublicFormViewSet(viewsets.ViewSet):
    """
    Public form access without authentication
    """
    permission_classes = []  # No authentication required
    
    @extend_schema(
        summary="Get public form by pipeline slug",
        description="Get public form schema for anonymous users",
        parameters=[
            OpenApiParameter(
                name='pipeline_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Pipeline slug'
            )
        ]
    )
    def retrieve(self, request, pk=None):
        """Get public form by pipeline slug"""
        try:
            pipeline = Pipeline.objects.get(slug=pk, access_level='public')
        except Pipeline.DoesNotExist:
            raise Http404("Public form not found")
        
        try:
            form_schema = generate_pipeline_form(
                pipeline_id=pipeline.id,
                mode='public_filtered'
            )
            return Response(form_schema)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get public stage form by pipeline slug and stage",
        description="Get public stage-specific form for anonymous users",
        parameters=[
            OpenApiParameter(
                name='pipeline_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Pipeline slug'
            ),
            OpenApiParameter(
                name='stage',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Target stage name'
            )
        ]
    )
    @action(detail=True, methods=['get'], url_path='stage/(?P<stage>[^/.]+)')
    def stage_form(self, request, pk=None, stage=None):
        """Get public stage form"""
        try:
            pipeline = Pipeline.objects.get(slug=pk, access_level='public')
        except Pipeline.DoesNotExist:
            raise Http404("Public form not found")
        
        if not stage:
            return Response(
                {'error': 'Stage parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            form_schema = generate_pipeline_form(
                pipeline_id=pipeline.id,
                mode='stage_public',
                stage=stage
            )
            return Response(form_schema)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Submit public form",
        description="Submit public form data anonymously",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'stage': {'type': 'string'},
                    'data': {'type': 'object'},
                    'captcha_token': {'type': 'string'}
                }
            }
        }
    )
    @action(detail=True, methods=['post'], url_path='submit')
    def submit_public_form(self, request, pk=None):
        """Submit public form data"""
        try:
            pipeline = Pipeline.objects.get(slug=pk, access_level='public')
        except Pipeline.DoesNotExist:
            raise Http404("Public form not found")
        
        stage = request.data.get('stage')
        form_data = request.data.get('data', {})
        captcha_token = request.data.get('captcha_token')
        
        if not form_data:
            return Response(
                {'error': 'Form data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Add captcha validation
        
        try:
            # Validate against public form schema
            form_mode = 'stage_public' if stage else 'public_filtered'
            generator = DynamicFormGenerator(pipeline)
            form_schema = generator.generate_form(mode=form_mode, stage=stage)
            
            # TODO: Add form validation logic
            
            # Create record with anonymous system user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            anonymous_user, _ = User.objects.get_or_create(
                email='anonymous@system.local',
                defaults={
                    'username': 'anonymous_system',
                    'first_name': 'Anonymous',
                    'last_name': 'User',
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False
                }
            )
            
            record = Record.objects.create(
                pipeline=pipeline,
                data=form_data,
                created_by=anonymous_user,
                updated_by=anonymous_user
            )
            
            return Response({
                'success': True,
                'message': 'Form submitted successfully',
                'record_id': record.id
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to submit form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class SharedRecordViewSet(viewsets.ViewSet):
    """
    Shared record access via tokens
    """
    permission_classes = []  # Token-based access
    
    # TODO: Implement token-based record sharing
    # This will be implemented in Phase 6
    pass