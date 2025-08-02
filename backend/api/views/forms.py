"""
Forms API views - simplified and clean
"""
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend

from forms.models import (
    ValidationRule, FormTemplate, FormFieldConfiguration
)
from forms.serializers import (
    ValidationRuleSerializer, FormTemplateSerializer,
    FormFieldConfigurationSerializer
)
from api.permissions import FormPermission, ValidationRulePermission


class ValidationRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing validation rules with proper tenant isolation
    """
    serializer_class = ValidationRuleSerializer
    permission_classes = [permissions.IsAuthenticated, ValidationRulePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Get validation rules filtered by tenant"""
        return ValidationRule.objects.filter(
            tenant=self.request.tenant
        ).select_related('tenant', 'created_by').order_by('name')
    
    def perform_create(self, serializer):
        """Set tenant and user when creating validation rule"""
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user
        )


class FormTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing form templates
    """
    serializer_class = FormTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, FormPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['form_type', 'is_active', 'pipeline']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Get form templates filtered by tenant"""
        return FormTemplate.objects.filter(
            tenant=self.request.tenant
        ).select_related('pipeline').prefetch_related(
            'field_configs__pipeline_field'
        ).order_by('name')
    
    def perform_create(self, serializer):
        """Set tenant and user when creating form template"""
        serializer.save(
            tenant=self.request.tenant,
            created_by=self.request.user
        )


class FormFieldConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing form field configurations
    """
    serializer_class = FormFieldConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated, FormPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['form_template', 'is_visible', 'is_readonly', 'is_active']
    search_fields = ['custom_label', 'custom_help_text']
    ordering_fields = ['display_order', 'created_at']
    ordering = ['display_order', 'id']
    
    def get_queryset(self):
        """Get field configurations filtered by tenant"""
        return FormFieldConfiguration.objects.filter(
            form_template__tenant=self.request.tenant
        ).select_related(
            'form_template', 'pipeline_field'
        )