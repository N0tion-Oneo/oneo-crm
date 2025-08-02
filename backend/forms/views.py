from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
import logging

from .models import (
    ValidationRule, FormTemplate, FormFieldConfiguration
)
from .serializers import (
    ValidationRuleSerializer, FormTemplateSerializer,
    FormFieldConfigurationSerializer
)
from authentication.permissions import SyncPermissionManager

logger = logging.getLogger(__name__)


class ValidationRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing validation rules
    Includes tenant isolation and permission checking
    """
    serializer_class = ValidationRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ValidationRule.objects.filter(
            tenant=self.request.tenant
        ).order_by('name')
    
    @action(detail=False, methods=['GET'])
    def rule_types(self, request):
        """Get available validation rule types"""
        rule_types = [
            {'value': choice[0], 'label': choice[1]} 
            for choice in ValidationRule.RULE_TYPE_CHOICES
        ]
        return Response(rule_types)
    
    @action(detail=True, methods=['POST'])
    def test_rule(self, request, pk=None):
        """Test a validation rule against sample data"""
        rule = self.get_object()
        test_value = request.data.get('test_value', '')
        
        try:
            # Simple synchronous validation test based on rule type
            from .validation.patterns import validate_with_pattern
            from django.core.validators import validate_email, URLValidator
            from django.core.exceptions import ValidationError as DjangoValidationError
            import re
            
            is_valid = True
            error_message = ""
            
            # Basic validation logic based on rule type
            if rule.rule_type == 'required':
                is_valid = bool(test_value and str(test_value).strip())
                if not is_valid:
                    error_message = "This field is required"
            
            elif rule.rule_type == 'min_length':
                min_length = rule.configuration.get('min_length', 0)
                is_valid = len(str(test_value)) >= min_length
                if not is_valid:
                    error_message = f"Minimum length is {min_length} characters"
            
            elif rule.rule_type == 'max_length':
                max_length = rule.configuration.get('max_length', 255)
                is_valid = len(str(test_value)) <= max_length
                if not is_valid:
                    error_message = f"Maximum length is {max_length} characters"
            
            elif rule.rule_type == 'email':
                try:
                    validate_email(test_value)
                    is_valid = True
                except DjangoValidationError:
                    is_valid = False
                    error_message = "Please enter a valid email address"
            
            elif rule.rule_type == 'regex':
                pattern = rule.configuration.get('pattern', '')
                if pattern:
                    is_valid = bool(re.match(pattern, str(test_value)))
                    if not is_valid:
                        error_message = rule.error_message or "Value does not match required pattern"
            
            else:
                # For complex async validation types, just return a placeholder
                is_valid = True
                error_message = "Advanced validation - test not available"
            
            return Response({
                'is_valid': is_valid,
                'error_message': error_message,
                'warning_message': '',
                'execution_time_ms': 0.0
            })
        except Exception as e:
            return Response(
                {'error': f'Test failed: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class FormTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing form templates
    Supports form building, validation, and analytics
    """
    serializer_class = FormTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FormTemplate.objects.filter(
            tenant=self.request.tenant
        ).select_related('pipeline').prefetch_related(
            'field_configs__pipeline_field'
        ).order_by('name')
    
    @action(detail=True, methods=['POST'])
    def validate_form(self, request, pk=None):
        """Validate form data against form template"""
        form_template = self.get_object()
        serializer = FormValidationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Simplified synchronous validation for now
            # TODO: Implement proper sync validation in unified API
            data = serializer.validated_data['data']
            
            # Basic validation - check required fields from form template
            errors = {}
            for field_config in form_template.field_configs.all():
                field_name = field_config.pipeline_field.name
                field_value = data.get(field_name)
                
                # Check if field is required but missing
                if field_config.pipeline_field.is_required and not field_value:
                    errors[field_name] = [f"This field is required"]
            
            is_valid = len(errors) == 0
            
            result = {
                'is_valid': is_valid,
                'field_results': errors,
                'cross_field_results': [],
                'duplicate_results': [],
                'execution_time_ms': 0.0,
                'total_errors': len(errors),
                'total_warnings': 0
            }
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Form validation error: {e}", exc_info=True)
            return Response(
                {'error': f'Validation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['POST'])
    def check_duplicates(self, request, pk=None):
        """Check for duplicate records"""
        form_template = self.get_object()
        serializer = DuplicateCheckRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Simplified synchronous duplicate detection for now
            # TODO: Implement proper sync duplicate detection in unified API
            
            # Return empty candidate list for now
            candidates = []
            
            return Response(candidates)
            
        except Exception as e:
            logger.error(f"Duplicate detection error: {e}", exc_info=True)
            return Response(
                {'error': f'Duplicate detection failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['POST'])
    def submit_form(self, request, pk=None):
        """Submit form data with validation and duplicate checking"""
        form_template = self.get_object()
        
        with transaction.atomic():
            try:
                # Create form submission record
                submission = FormSubmission.objects.create(
                    form_template=form_template,
                    submitted_by=request.user,
                    submission_data=request.data.get('data', {}),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    referrer=request.META.get('HTTP_REFERER', ''),
                    session_id=request.session.session_key or ''
                )
                
                # Simplified validation for now
                # TODO: Implement proper sync validation in unified API
                data = request.data.get('data', {})
                errors = {}
                
                # Basic validation - check required fields
                for field_config in form_template.field_configs.all():
                    field_name = field_config.pipeline_field.name
                    field_value = data.get(field_name)
                    
                    if field_config.pipeline_field.is_required and not field_value:
                        errors[field_name] = [f"This field is required"]
                
                is_valid = len(errors) == 0
                
                # Update submission with validation results
                submission.validation_results = {
                    'is_valid': is_valid,
                    'total_errors': len(errors),
                    'total_warnings': 0,
                    'execution_time_ms': 0.0
                }
                
                # Handle based on validation mode
                if not is_valid and form_template.validation_mode == 'strict':
                    submission.status = 'invalid'
                    submission.save()
                    return Response({
                        'success': False,
                        'validation_result': {
                            'is_valid': is_valid,
                            'field_results': errors,
                            'total_errors': len(errors)
                        },
                        'submission_id': submission.id
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Simplified duplicate checking for now
                # TODO: Implement proper sync duplicate detection in unified API
                if form_template.enable_duplicate_detection:
                    # Skip duplicate detection for now
                    submission.duplicate_matches = []
                
                # Create or update record
                from pipelines.models import Record
                if 'record_id' in request.data:
                    # Update existing record
                    record = Record.objects.get(
                        id=request.data['record_id'],
                        pipeline=form_template.pipeline
                    )
                    record.data.update(request.data.get('data', {}))
                    record.save()
                else:
                    # Create new record
                    record = Record.objects.create(
                        pipeline=form_template.pipeline,
                        data=request.data.get('data', {}),
                        created_by=request.user
                    )
                
                submission.record = record
                submission.status = 'valid'
                submission.processed_at = timezone.now()
                submission.save()
                
                return Response({
                    'success': True,
                    'record_id': record.id,
                    'submission_id': submission.id,
                    'validation_result': FormValidationResultSerializer(validation_result).data,
                    'message': form_template.success_message or 'Form submitted successfully'
                })
                
            except Exception as e:
                logger.error(f"Form submission error: {e}", exc_info=True)
                return Response(
                    {'error': f'Submission failed: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    @action(detail=True, methods=['GET'])
    def analytics(self, request, pk=None):
        """Get form analytics"""
        form_template = self.get_object()
        
        # Get date range from query params
        from datetime import datetime, timedelta
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)  # Default to 30 days
        
        if 'start_date' in request.query_params:
            start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
        if 'end_date' in request.query_params:
            end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d').date()
        
        analytics = FormAnalytics.objects.filter(
            form_template=form_template,
            date__range=[start_date, end_date]
        ).order_by('-date')
        
        serializer = FormAnalyticsSerializer(analytics, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['POST'])
    def build_form(self, request, pk=None):
        """Build form with field configurations and validation rules"""
        form_template = self.get_object()
        
        serializer = FormBuilderSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                result = serializer.save()
                return Response({
                    'success': True,
                    'form_template': FormTemplateSerializer(result['form_template']).data,
                    'field_configs': FormFieldConfigurationSerializer(
                        result['field_configs'], many=True
                    ).data
                })
        except Exception as e:
            logger.error(f"Form building error: {e}", exc_info=True)
            return Response(
                {'error': f'Form building failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FormFieldConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing form field configurations"""
    serializer_class = FormFieldConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FormFieldConfiguration.objects.filter(
            form_template__tenant=self.request.tenant
        ).select_related(
            'form_template', 'pipeline_field'
        ).prefetch_related('validations__validation_rule')
    
    @action(detail=True, methods=['POST'])
    def validate_field(self, request, pk=None):
        """Validate individual field value"""
        field_config = self.get_object()
        serializer = FieldValidationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            engine = FormValidationEngine(tenant_id=request.tenant.id)
            
            # Simplified field validation for now
            # TODO: Implement proper sync field validation in unified API
            field_value = serializer.validated_data['value']
            results = []
            
            # Basic validation based on field requirements
            if field_config.pipeline_field.is_required and not field_value:
                results.append({
                    'is_valid': False,
                    'error_message': 'This field is required',
                    'field_name': field_config.pipeline_field.name
                })
            else:
                results.append({
                    'is_valid': True,
                    'error_message': '',
                    'field_name': field_config.pipeline_field.name
                })
            
            return Response({
                'field_name': field_config.pipeline_field.name,
                'results': results,
                'overall_valid': all(r['is_valid'] for r in results)
            })
            
        except Exception as e:
            logger.error(f"Field validation error: {e}", exc_info=True)
            return Response(
                {'error': f'Field validation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FormSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing form submissions (read-only)"""
    serializer_class = FormSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FormSubmission.objects.filter(
            form_template__tenant=self.request.tenant
        ).select_related(
            'form_template', 'record', 'submitted_by'
        ).order_by('-submitted_at')


class PublicFormViewSet(viewsets.ViewSet):
    """
    ViewSet for public form access (no authentication required)
    """
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['GET'], url_path='(?P<slug>[^/.]+)')
    def get_public_form(self, request, slug=None):
        """Get public form by slug"""
        try:
            form_template = FormTemplate.objects.select_related('pipeline').prefetch_related(
                'field_configs__pipeline_field',
                'field_configs__validations__validation_rule'
            ).get(
                public_slug=slug,
                is_public=True,
                is_active=True
            )
            
            serializer = FormTemplateSerializer(form_template)
            return Response(serializer.data)
            
        except FormTemplate.DoesNotExist:
            return Response(
                {'error': 'Form not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['POST'], url_path='(?P<slug>[^/.]+)/submit')
    def submit_public_form(self, request, slug=None):
        """Submit public form"""
        serializer = PublicFormSubmissionSerializer(data={
            'form_slug': slug,
            'data': request.data.get('data', {}),
            'captcha_token': request.data.get('captcha_token', '')
        })
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        form_template = serializer.context['form_template']
        
        try:
            with transaction.atomic():
                # Create anonymous submission
                submission = FormSubmission.objects.create(
                    form_template=form_template,
                    submitted_by=None,  # Anonymous
                    submission_data=request.data.get('data', {}),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    referrer=request.META.get('HTTP_REFERER', ''),
                    session_id=request.session.session_key or ''
                )
                
                # Simplified validation for public forms
                # TODO: Implement proper sync validation in unified API
                data = request.data.get('data', {})
                errors = {}
                
                # Basic validation - check required fields
                for field_config in form_template.field_configs.all():
                    field_name = field_config.pipeline_field.name
                    field_value = data.get(field_name)
                    
                    if field_config.pipeline_field.is_required and not field_value:
                        errors[field_name] = [f"This field is required"]
                
                is_valid = len(errors) == 0
                
                submission.validation_results = {
                    'is_valid': is_valid,
                    'total_errors': len(errors),
                    'total_warnings': 0
                }
                
                if not is_valid:
                    submission.status = 'invalid'
                    submission.save()
                    return Response({
                        'success': False,
                        'errors': validation_result.field_results
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Create record
                from pipelines.models import Record
                record = Record.objects.create(
                    pipeline=form_template.pipeline,
                    data=request.data.get('data', {}),
                    created_by=None  # Anonymous
                )
                
                submission.record = record
                submission.status = 'valid'
                submission.processed_at = timezone.now()
                submission.save()
                
                response_data = {
                    'success': True,
                    'message': form_template.success_message or 'Thank you for your submission'
                }
                
                # Add redirect URL if specified
                if form_template.redirect_url:
                    response_data['redirect_url'] = form_template.redirect_url
                
                return Response(response_data)
                
        except Exception as e:
            logger.error(f"Public form submission error: {e}", exc_info=True)
            return Response(
                {'error': 'Submission failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
