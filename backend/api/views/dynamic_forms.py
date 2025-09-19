"""
Dynamic forms API views for pipeline-based form generation
"""
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from pipelines.models import Pipeline, Record
from pipelines.form_generation import DynamicFormGenerator, generate_pipeline_form
from ..permissions import PipelinePermission, RecordPermission

logger = logging.getLogger(__name__)


class DynamicFormViewSet(viewsets.ViewSet):
    """
    Dynamic form generation API for pipelines
    Supports 5 form types based on pipeline schema and business rules
    """
    permission_classes = [PipelinePermission]
    
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
        summary="Get available forms for pipeline",
        description="Get list of all available forms for this pipeline including stage-specific forms",
        parameters=[
            OpenApiParameter(
                name='pipeline_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Pipeline ID'
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='available-forms')
    def available_forms(self, request, pipeline_pk=None):
        """Get list of all available forms for this pipeline"""
        pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)

        try:
            generator = DynamicFormGenerator(pipeline)
            available_stages = generator.get_available_stages()

            forms = []

            # Add base forms with structured data
            forms.append({
                'id': f'{pipeline.id}_internal_full',
                'pipeline_id': pipeline.id,
                'mode': 'internal_full',
                'stage': None,
                'label': 'All Fields (Internal)',
                'url': f'/forms/internal/{pipeline.id}',
                'field_count': pipeline.fields.filter(is_visible_in_detail=True).count(),
                'description': 'Form with all pipeline fields for internal users'
            })

            forms.append({
                'id': f'{pipeline.id}_public_filtered',
                'pipeline_id': pipeline.id,
                'mode': 'public_filtered',
                'stage': None,
                'label': 'Public Fields Only',
                'url': f'/forms/{pipeline.slug}',
                'field_count': pipeline.fields.filter(
                    is_visible_in_public_forms=True,
                    is_visible_in_detail=True
                ).count(),
                'description': 'Form with only public-visible fields'
            })

            # Add stage-specific forms
            for stage in available_stages:
                # Get fields for this stage
                stage_internal_schema = generator.generate_form(mode='stage_internal', stage=stage)
                stage_public_schema = generator.generate_form(mode='stage_public', stage=stage)

                # Internal stage form with structured data
                forms.append({
                    'id': f'{pipeline.id}_stage_internal_{stage}',
                    'pipeline_id': pipeline.id,
                    'mode': 'stage_internal',
                    'stage': stage,
                    'label': f'{stage} Stage Form (Internal)',
                    'url': f'/forms/internal/{pipeline.id}?stage={stage}',
                    'field_count': len(stage_internal_schema.fields),
                    'field_slugs': [f.field_slug for f in stage_internal_schema.fields],
                    'description': f'Stage-specific form for {stage} (internal use)'
                })

                # Public stage form with structured data
                if len(stage_public_schema.fields) > 0:
                    forms.append({
                        'id': f'{pipeline.id}_stage_public_{stage}',
                        'pipeline_id': pipeline.id,
                        'mode': 'stage_public',
                        'stage': stage,
                        'label': f'{stage} Stage Form (Public)',
                        'url': f'/forms/{pipeline.slug}/stage/{stage}',
                        'field_count': len(stage_public_schema.fields),
                        'field_slugs': [f.field_slug for f in stage_public_schema.fields],
                        'description': f'Stage-specific form for {stage} (public)'
                    })

            # Get all select fields that could be used as stage fields
            stage_fields = []
            for field in pipeline.fields.filter(field_type='select'):
                field_config = field.field_config or {}
                options = field_config.get('options', [])

                if options:
                    stage_fields.append({
                        'field_slug': field.slug,
                        'field_name': field.display_name or field.name,
                        'options': [
                            option.get('value', option) if isinstance(option, dict) else option
                            for option in options
                        ]
                    })

            return Response({
                'pipeline_id': pipeline.id,
                'pipeline_name': pipeline.name,
                'pipeline_slug': pipeline.slug,
                'forms': forms,
                'stage_fields': stage_fields,
                'total_forms': len(forms)
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to get available forms: {str(e)}'},
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

            # Build form configuration (simplified - no need for visible/required fields)
            form_config = {
                'id': f"pipeline_{pipeline.id}_{form_mode}",
                'name': f"{pipeline.name} Form ({form_mode})",
                'mode': form_mode,
                'stage': stage,
                'submitted_field_count': len(form_data.keys()),
            }

            # TODO: Add form validation logic here

            # Create or update record using FormSubmission for tracking
            if record_id:
                # Update existing record (still track as form submission for audit)
                record = get_object_or_404(Record, pk=record_id, pipeline=pipeline)

                # Store original data for tracking changes
                original_data = record.data.copy()

                # Update the record
                record.data.update(form_data)
                record.updated_by = request.user
                record.save()

                # Create FormSubmission to track the update
                from pipelines.models import FormSubmission
                form_submission = FormSubmission.objects.create(
                    record=record,
                    form_id=form_config['id'],
                    form_name=form_config['name'],
                    form_mode=form_mode,
                    submitted_data=form_data,
                    processed_data=record.data,
                    form_config=form_config,
                    submission_source='api',
                    submission_metadata={
                        'is_update': True,
                        'original_data': original_data,
                        'ip_address': request.META.get('REMOTE_ADDR'),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'endpoint': 'dynamic_forms.submit_form'
                    },
                    submitted_by=request.user
                )
            else:
                # Create new record with FormSubmission tracking
                from pipelines.models import FormSubmission

                # Use FormSubmission.create_from_form_data for consistent tracking
                form_submission, record = FormSubmission.create_from_form_data(
                    pipeline=pipeline,
                    form_data=form_data,
                    form_config=form_config,
                    user=request.user,
                    request=request
                )

            return Response({
                'success': True,
                'record_id': record.id,
                'message': 'Form submitted successfully',
                'form_submission_id': str(form_submission.id) if 'form_submission' in locals() else None
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

            # Evaluate conditional requirements based on submitted data
            from pipelines.conditional_evaluator import ConditionalRuleEvaluator
            requirements = ConditionalRuleEvaluator.get_form_requirements(
                pipeline, form_data, form_mode, stage=stage
            )

            # Build form configuration with dynamically evaluated requirements
            form_config = {
                'id': f"pipeline_{pipeline.id}_{form_mode}_public",
                'name': f"{pipeline.name} Public Form",
                'mode': form_mode,
                'stage': stage,
                'visible_fields': requirements['visible_fields'],  # Use evaluated visible fields
                'required_fields': requirements['required_fields'],  # Use evaluated required fields
                'total_fields': form_schema.total_fields,
                'visible_fields_count': len(requirements['visible_fields']),
                'required_fields_count': len(requirements['required_fields']),
                'is_public': True,
                'conditional_context': requirements.get('form_data_context', {})  # Store evaluation context
            }

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

            # Use FormSubmission.create_from_form_data for consistent tracking
            from pipelines.models import FormSubmission

            # Override form config to mark as public submission
            form_config['submission_source'] = 'public_form'

            # Create FormSubmission and Record together
            form_submission, record = FormSubmission.create_from_form_data(
                pipeline=pipeline,
                form_data=form_data,
                form_config=form_config,
                user=anonymous_user,  # Anonymous user for public forms
                request=request
            )

            # Update FormSubmission with additional public form metadata
            form_submission.submission_source = 'public_form'
            form_submission.submission_metadata.update({
                'is_public': True,
                'captcha_token': captcha_token[:20] if captcha_token else None,  # Store truncated for security
                'referrer': request.META.get('HTTP_REFERER', ''),
                'endpoint': 'public_forms.submit_public_form'
            })
            form_submission.save()

            return Response({
                'success': True,
                'message': 'Form submitted successfully',
                'record_id': record.id,
                'form_submission_id': str(form_submission.id)
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to submit form: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class SharedRecordViewSet(viewsets.ViewSet):
    """
    Encrypted shared record access with 5 working day expiry
    """
    permission_classes = []  # No authentication - encrypted token validates access
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from utils.encryption import ShareLinkEncryption
        self.encryption = ShareLinkEncryption()
    
    def get_client_ip(self, request):
        """Extract client IP for access tracking"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def get_access_count(self, encrypted_token):
        """Get access count from cache"""
        cache_key = f"shared_access:{encrypted_token[:16]}"
        access_data = cache.get(cache_key, {'count': 0})
        return access_data.get('count', 0)
    
    def track_access(self, encrypted_token, request):
        """Track access for analytics using cache"""
        client_ip = self.get_client_ip(request)
        
        # Use cache to track access without database
        cache_key = f"shared_access:{encrypted_token[:16]}"  # Truncated for cache key
        access_data = cache.get(cache_key, {'count': 0, 'ips': []})
        
        access_data['count'] += 1
        access_data['last_access'] = int(time.time())
        if client_ip and client_ip not in access_data['ips']:
            access_data['ips'].append(client_ip)
        
        # Store for 7 days (longer than share expiry for analytics)
        cache.set(cache_key, access_data, timeout=604800)
    
    @extend_schema(
        summary="Access shared record with encrypted token",
        description="Get shared record data using encrypted access token",
        parameters=[
            OpenApiParameter(
                name='encrypted_token',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Encrypted access token containing record ID, user ID, and expiry'
            )
        ]
    )
    def retrieve(self, request, pk=None):
        """Access shared record with encrypted token"""
        # URL: /api/v1/shared-records/{encrypted_token}/
        encrypted_token = pk  # The entire path parameter is the encrypted token
        
        if not encrypted_token:
            return Response(
                {'error': 'Encrypted token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate required accessor information
        accessor_name = request.data.get('accessor_name') or request.query_params.get('accessor_name')
        accessor_email = request.data.get('accessor_email') or request.query_params.get('accessor_email')
        
        if not accessor_name or not accessor_email:
            return Response(
                {
                    'error': 'Accessor name and email are required',
                    'required_fields': ['accessor_name', 'accessor_email']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(accessor_email)
        except ValidationError:
            return Response(
                {'error': 'Invalid email format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate name (minimum length)
        if len(accessor_name.strip()) < 2:
            return Response(
                {'error': 'Accessor name must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get SharedRecord from database
        try:
            from sharing.models import SharedRecord
            shared_record = SharedRecord.objects.select_related(
                'record__pipeline', 'shared_by'
            ).get(encrypted_token=encrypted_token)
        except SharedRecord.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired share link'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if share is still valid
        if not shared_record.is_valid:
            status_msg = {
                'expired': 'Share link has expired',
                'revoked': 'Share link has been revoked',
                'inactive': 'Share link is no longer active'
            }.get(shared_record.status, 'Share link is not valid')
            
            return Response(
                {'error': status_msg},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # SECURITY: Validate that accessor email matches intended recipient
        if accessor_email.lower() != shared_record.intended_recipient_email.lower():
            return Response(
                {
                    'error': 'Access denied. This share link is restricted to a specific email address.',
                    'help': 'Please ensure you are using the correct email address that this link was shared with.'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Track access
        client_ip = self.get_client_ip(request)
        shared_record.track_access(client_ip)
        
        # Also create detailed access log with user information
        from sharing.models import SharedRecordAccess
        from utils.geolocation import get_location_from_ip
        
        # Get location data from IP address
        location_data = get_location_from_ip(client_ip) if client_ip else {}
        
        SharedRecordAccess.objects.create(
            shared_record=shared_record,
            ip_address=client_ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],  # Truncate long user agents
            accessor_name=accessor_name.strip(),
            accessor_email=accessor_email.strip().lower(),
            city=location_data.get('city', ''),
            country=location_data.get('country', '')
        )
        
        # Generate form schema with populated data
        try:
            from pipelines.form_generation import generate_pipeline_form
            form_schema = generate_pipeline_form(
                pipeline_id=shared_record.record.pipeline.id,
                mode='shared_record',
                record_data=shared_record.record.data
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form schema: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Calculate time remaining
        from django.utils import timezone
        time_remaining = shared_record.time_remaining_seconds
        
        return Response({
            'record': {
                'id': shared_record.record.id,
                'pipeline': {
                    'id': shared_record.record.pipeline.id,
                    'name': shared_record.record.pipeline.name,
                    'slug': shared_record.record.pipeline.slug
                },
                'created_at': shared_record.record.created_at,
                'updated_at': shared_record.record.updated_at
            },
            'form_schema': form_schema,
            'shared_by': shared_record.shared_by.get_full_name() or shared_record.shared_by.email,
            'expires_at': int(shared_record.expires_at.timestamp()),
            'expires_datetime': shared_record.expires_at.isoformat(),
            'time_remaining_seconds': time_remaining,
            'access_mode': shared_record.access_mode,
            'access_info': {
                'created_at': int(shared_record.created_at.timestamp()),
                'access_count': shared_record.access_count,
                'last_accessed_at': shared_record.last_accessed_at.isoformat() if shared_record.last_accessed_at else None,
                'shared_record_id': str(shared_record.id)
            },
            'accessor_info': {
                'name': accessor_name.strip(),
                'email': accessor_email.strip().lower()
            }
        })
    
    @extend_schema(
        summary="Get form schema for shared record",
        description="Get form schema for shared record using encrypted token (for DynamicFormRenderer)",
        parameters=[
            OpenApiParameter(
                name='encrypted_token',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Encrypted access token'
            )
        ]
    )
    @action(detail=True, methods=['get'], url_path='form')
    def form_schema(self, request, pk=None):
        """Get form schema for shared record (for DynamicFormRenderer)"""
        encrypted_token = pk
        
        # Get SharedRecord from database
        try:
            from sharing.models import SharedRecord
            shared_record = SharedRecord.objects.select_related(
                'record__pipeline'
            ).get(encrypted_token=encrypted_token)
        except SharedRecord.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired share link'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if share is still valid
        if not shared_record.is_valid:
            status_msg = {
                'expired': 'Share link has expired',
                'revoked': 'Share link has been revoked',
                'inactive': 'Share link is no longer active'
            }.get(shared_record.status, 'Share link is not valid')
            
            return Response(
                {'error': status_msg},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate form schema with populated data
        try:
            from pipelines.form_generation import generate_pipeline_form
            form_schema = generate_pipeline_form(
                pipeline_id=shared_record.record.pipeline.id,
                mode='shared_record',
                record_data=shared_record.record.data
            )
            
            # Apply access mode restrictions
            if shared_record.access_mode == 'readonly':
                # Make all fields readonly
                for field in form_schema.get('fields', []):
                    field['is_readonly'] = True
            
            return Response(form_schema)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate form schema: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get access analytics for shared record",
        description="Get access statistics for the shared record (for debugging)",
        parameters=[
            OpenApiParameter(
                name='encrypted_token',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Encrypted access token'
            )
        ]
    )
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get access analytics for shared record"""
        encrypted_token = pk
        
        if not encrypted_token:
            return Response(
                {'error': 'Encrypted token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate token first
        payload, error = self.encryption.decrypt_share_data(encrypted_token)
        if not payload:
            return Response(
                {'error': error or 'Invalid share link'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get analytics from cache
        cache_key = f"shared_access:{encrypted_token[:16]}"
        access_data = cache.get(cache_key, {'count': 0, 'ips': []})
        
        return Response({
            'record_id': payload['record_id'],
            'access_count': access_data.get('count', 0),
            'unique_ips': len(access_data.get('ips', [])),
            'last_access': access_data.get('last_access'),
            'created_at': payload['created'],
            'expires_at': payload['expires'],
            'is_expired': time.time() > payload['expires']
        })
    
    @extend_schema(
        summary="Update shared record data",
        description="Update record data through shared link (for editable shares only)",
        parameters=[
            OpenApiParameter(
                name='encrypted_token',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Encrypted access token'
            )
        ]
    )
    def update(self, request, pk=None):
        """Update shared record data (for editable shares only)"""
        encrypted_token = pk
        
        if not encrypted_token:
            return Response(
                {'error': 'Encrypted token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate required accessor information
        accessor_name = request.data.get('accessor_name')
        accessor_email = request.data.get('accessor_email')
        form_data = request.data.get('data', {})
        
        if not accessor_name or not accessor_email:
            return Response(
                {
                    'error': 'Accessor name and email are required',
                    'required_fields': ['accessor_name', 'accessor_email']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not form_data:
            return Response(
                {'error': 'No data provided for update'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(accessor_email)
        except ValidationError:
            return Response(
                {'error': 'Invalid email format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get SharedRecord from database
        try:
            from sharing.models import SharedRecord, SharedRecordAccess
            shared_record = SharedRecord.objects.select_related(
                'record__pipeline'
            ).get(encrypted_token=encrypted_token)
        except SharedRecord.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired share link'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if share is still valid
        if not shared_record.is_valid:
            status_msg = {
                'expired': 'Share link has expired',
                'revoked': 'Share link has been revoked',
                'inactive': 'Share link is no longer active'
            }.get(shared_record.status, 'Share link is not valid')
            
            return Response(
                {'error': status_msg},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # SECURITY: Validate that accessor email matches intended recipient
        if accessor_email.lower() != shared_record.intended_recipient_email.lower():
            return Response(
                {
                    'error': 'Access denied. This share link is restricted to a specific email address.',
                    'help': 'Please ensure you are using the correct email address that this link was shared with.'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if share is editable
        if shared_record.access_mode != 'editable':
            return Response(
                {'error': 'This shared record is read-only and cannot be edited'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the record and store original data for audit logging
        record = shared_record.record
        original_data = record.data.copy()
        
        try:
            # Add context flag for external shared record update
            # This will modify how the pipeline signal creates audit logs
            record._is_shared_record_update = True
            record._external_accessor_info = {
                'accessor_name': accessor_name.strip(),
                'accessor_email': accessor_email.strip().lower(),
                'ip_address': self.get_client_ip(request)
            }
            
            # Update the record data
            record.data.update(form_data)
            record.updated_at = timezone.now()
            # Use the original sharer as updated_by to satisfy database constraint
            # The external user context is tracked via the context flags for audit logging
            record.updated_by = shared_record.shared_by
            
            record.save()
            
            # Create access log for this edit
            client_ip = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Get location data from IP address
            from utils.geolocation import get_location_from_ip
            location_data = get_location_from_ip(client_ip) if client_ip else {}
            
            SharedRecordAccess.objects.create(
                shared_record=shared_record,
                accessor_name=accessor_name.strip(),
                accessor_email=accessor_email.strip().lower(),
                ip_address=client_ip,
                user_agent=user_agent,
                city=location_data.get('city', ''),
                country=location_data.get('country', '')
            )
            
            # Log the edit in audit logs
            from sharing.signals import log_shared_record_edit
            
            # Calculate field changes for audit log
            field_changes = {}
            for field_key, new_value in form_data.items():
                old_value = original_data.get(field_key)
                if old_value != new_value:
                    field_changes[field_key] = {
                        'old': old_value,
                        'new': new_value
                    }
            
            # Log the edit with accessor information
            if field_changes:
                log_shared_record_edit(
                    user=None,  # External user
                    record=record,
                    field_changes=field_changes,
                    accessor_info={
                        'accessor_name': accessor_name.strip(),
                        'accessor_email': accessor_email.strip().lower(),
                        'ip_address': client_ip
                    }
                )
            
            # Track the access
            shared_record.track_access(client_ip)
            
            return Response({
                'success': True,
                'message': 'Record updated successfully',
                'record_id': record.id,
                'changes_count': len(field_changes),
                'accessor_info': {
                    'name': accessor_name.strip(),
                    'email': accessor_email.strip().lower()
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to update shared record {record.id}: {e}")
            return Response(
                {'error': f'Failed to update record: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )