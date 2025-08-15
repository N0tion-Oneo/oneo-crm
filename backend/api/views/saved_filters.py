"""
API views for saved filters and sharing functionality
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from pipelines.models import SavedFilter, Pipeline
from sharing.models import SharedFilter
from .serializers import (
    SavedFilterSerializer, 
    SavedFilterListSerializer,
    SharedFilterSerializer,
    SharedFilterCreateSerializer,
    SharedFilterAccessSerializer
)
from utils.encryption import ShareLinkEncryption


class SavedFilterPermission(permissions.BasePermission):
    """Enhanced permission class for saved filters"""
    
    def has_permission(self, request, view):
        """Check if user has permission to access saved filters"""
        from authentication.permissions import SyncPermissionManager
        
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'create':
            return permission_manager.has_permission('action', 'filters', 'create_filters')
        elif view.action == 'list':
            return True  # Users can see filters they have access to
        elif view.action in ['share']:
            # Sharing permissions checked at object level
            return True
        else:
            return True  # Other actions checked at object level
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific saved filter"""
        from authentication.permissions import SyncPermissionManager
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'use_filter', 'analytics']:
            # Can access if filter allows it
            return obj.can_user_access(request.user)
        elif view.action in ['update', 'partial_update']:
            # Can edit if owner OR has edit permission and filter is accessible
            if obj.created_by == request.user:
                return True
            return (obj.can_user_access(request.user) and 
                   permission_manager.has_permission('action', 'filters', 'edit_filters'))
        elif view.action == 'destroy':
            # Can delete if owner OR has delete permission
            if obj.created_by == request.user:
                return True
            return permission_manager.has_permission('action', 'filters', 'delete_filters')
        elif view.action in ['share', 'shares']:
            # Can share if has access to filter and sharing permission
            if not obj.can_user_access(request.user):
                return False
            return permission_manager.has_permission('action', 'sharing', 'create_shared_views')
        elif view.action == 'set_default':
            # Only owner can set as default
            return obj.created_by == request.user
        elif view.action == 'revoke':
            # Can revoke if has permission and is the creator
            if not permission_manager.has_permission('action', 'sharing', 'revoke_shared_views_forms'):
                return False
            # For SharedFilter objects, check if user created the share
            if hasattr(obj, 'shared_by'):
                return obj.shared_by == request.user
            # For SavedFilter objects, check if user created the filter
            return obj.created_by == request.user
        
        return False


class SavedFilterViewSet(viewsets.ModelViewSet):
    """ViewSet for managing saved filters"""
    
    permission_classes = [SavedFilterPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['pipeline', 'is_shareable', 'is_default', 'view_mode']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'last_used_at', 'usage_count']
    ordering = ['-last_used_at', '-created_at']
    
    def get_queryset(self):
        """Get saved filters based on access level"""
        from django.db.models import Q
        from authentication.permissions import SyncPermissionManager
        
        user = self.request.user
        permission_manager = SyncPermissionManager(user)
        
        # Base queryset with related objects
        queryset = SavedFilter.objects.select_related('pipeline', 'created_by')
        
        # Build access conditions
        access_conditions = Q()
        
        # Always include own filters
        access_conditions |= Q(created_by=user)
        
        # Include pipeline_users filters if user has pipeline access
        accessible_pipeline_ids = []
        for pipeline_id in SavedFilter.objects.values_list('pipeline_id', flat=True).distinct():
            if permission_manager.has_permission('action', 'pipelines', 'access', pipeline_id):
                accessible_pipeline_ids.append(pipeline_id)
        
        if accessible_pipeline_ids:
            access_conditions |= Q(
                access_level='pipeline_users',
                pipeline_id__in=accessible_pipeline_ids
            )
        
        # Include private filters of others if user has edit_filters permission
        if permission_manager.has_permission('action', 'filters', 'edit_filters'):
            access_conditions |= Q(access_level='private')
        
        return queryset.filter(access_conditions)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return SavedFilterListSerializer
        return SavedFilterSerializer
    
    def perform_create(self, serializer):
        """Create a new saved filter"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def use_filter(self, request, pk=None):
        """Track usage of a saved filter"""
        saved_filter = self.get_object()
        saved_filter.track_usage()
        
        return Response({
            'message': 'Filter usage tracked',
            'usage_count': saved_filter.usage_count,
            'last_used_at': saved_filter.last_used_at
        })
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set this filter as the default for the pipeline"""
        saved_filter = self.get_object()
        
        with transaction.atomic():
            # Remove default from other filters for this pipeline
            SavedFilter.objects.filter(
                pipeline=saved_filter.pipeline,
                created_by=request.user,
                is_default=True
            ).exclude(id=saved_filter.id).update(is_default=False)
            
            # Set this filter as default
            saved_filter.is_default = True
            saved_filter.save(update_fields=['is_default'])
        
        return Response({
            'message': 'Filter set as default',
            'is_default': True
        })
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Create a share link for the saved filter"""
        saved_filter = self.get_object()
        
        # Check if filter can be shared
        can_share, reason = saved_filter.can_be_shared()
        if not can_share:
            return Response(
                {'error': f'Filter cannot be shared: {reason}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SharedFilterCreateSerializer(
            data=request.data,
            context={'request': request, 'saved_filter': saved_filter}
        )
        
        if serializer.is_valid():
            # Generate encrypted token
            encryption = ShareLinkEncryption()
            expires_timestamp = int(serializer.validated_data['expires_at'].timestamp())
            
            encrypted_token = encryption.encrypt_share_data(
                record_id=str(saved_filter.id),
                user_id=request.user.id,
                expires_timestamp=expires_timestamp,
                access_mode=serializer.validated_data['access_mode']
            )
            
            # Create the shared filter
            shared_filter = serializer.save(
                saved_filter=saved_filter,
                shared_by=request.user,
                encrypted_token=encrypted_token
            )
            
            return Response(
                SharedFilterSerializer(shared_filter, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def shares(self, request, pk=None):
        """Get all shares for this saved filter"""
        saved_filter = self.get_object()
        shares = saved_filter.shares.all().order_by('-created_at')
        
        serializer = SharedFilterSerializer(
            shares, 
            many=True, 
            context={'request': request}
        )
        
        return Response(serializer.data)


class SharedFilterViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing filter shares"""
    
    permission_classes = [SavedFilterPermission]
    serializer_class = SharedFilterSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['access_mode', 'is_active']
    ordering_fields = ['created_at', 'expires_at', 'access_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get shared filters for current user"""
        return SharedFilter.objects.filter(
            shared_by=self.request.user
        ).select_related('saved_filter', 'shared_by')
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a shared filter"""
        shared_filter = self.get_object()
        
        # Check if user has permission to revoke shares
        from authentication.permissions import SyncPermissionManager
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'sharing', 'revoke_shared_views_forms'):
            raise PermissionDenied("You don't have permission to revoke shared filters")
        
        # Check if user is the creator of the share
        if shared_filter.shared_by != request.user:
            raise PermissionDenied("You can only revoke shares you created")
        
        shared_filter.revoke(revoked_by=request.user)
        
        return Response({
            'message': 'Share revoked',
            'status': shared_filter.status
        })
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a shared filter"""
        shared_filter = self.get_object()
        
        return Response({
            'access_count': shared_filter.access_count,
            'last_accessed_at': shared_filter.last_accessed_at,
            'time_remaining_seconds': shared_filter.time_remaining_seconds,
            'status': shared_filter.status,
            'is_valid': shared_filter.is_valid
        })
    
    @action(detail=True, methods=['get'], url_path='access-logs')
    def access_logs(self, request, pk=None):
        """Get access logs for a shared filter"""
        shared_filter = self.get_object()
        
        # SharedFilter doesn't have detailed access logs like SharedRecord
        # Return basic access information instead
        return Response({
            'results': [],
            'count': 0,
            'message': 'Detailed access logs are not available for shared filters. Use analytics endpoint for basic access information.'
        })


class PublicFilterAccessViewSet(viewsets.GenericViewSet):
    """Public viewset for accessing shared filters via token"""
    
    permission_classes = []  # No authentication required for public access
    
    def retrieve(self, request, pk=None):
        """Access a shared filter via encrypted token"""
        try:
            # Decrypt the token
            encryption = ShareLinkEncryption()
            payload, error = encryption.decrypt_share_data(pk)
            
            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the shared filter
            try:
                saved_filter_id = payload['record_id']
                shared_filter = SharedFilter.objects.get(
                    saved_filter__id=saved_filter_id,
                    encrypted_token=pk,
                    is_active=True
                )
            except SharedFilter.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired share link'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if share is still valid
            if not shared_filter.is_valid:
                return Response(
                    {'error': f'Share link is {shared_filter.status}'},
                    status=status.HTTP_410_GONE
                )
            
            # Return the filter configuration for public access
            saved_filter = shared_filter.saved_filter
            
            # Filter visible fields to only those allowed in shared views
            shareable_fields = list(saved_filter.get_shareable_fields())
            
            return Response({
                'id': str(saved_filter.id),
                'name': saved_filter.name,
                'description': saved_filter.description,
                'pipeline': {
                    'id': saved_filter.pipeline.id,
                    'name': saved_filter.pipeline.name,
                    'slug': saved_filter.pipeline.slug
                },
                'filter_config': saved_filter.filter_config,
                'view_mode': saved_filter.view_mode,
                'visible_fields': shareable_fields,  # Only shareable fields
                'sort_config': saved_filter.sort_config,
                'access_mode': shared_filter.access_mode,
                'expires_at': shared_filter.expires_at,
                'time_remaining_seconds': shared_filter.time_remaining_seconds
            })
            
        except Exception as e:
            return Response(
                {'error': 'Invalid share link format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def access(self, request, pk=None):
        """Record access to a shared filter"""
        try:
            # Decrypt the token
            encryption = ShareLinkEncryption()
            payload, error = encryption.decrypt_share_data(pk)
            
            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the shared filter
            try:
                saved_filter_id = payload['record_id']
                shared_filter = SharedFilter.objects.get(
                    saved_filter__id=saved_filter_id,
                    encrypted_token=pk,
                    is_active=True
                )
            except SharedFilter.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired share link'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate access data
            serializer = SharedFilterAccessSerializer(
                data=request.data,
                context={'shared_filter': shared_filter}
            )
            
            if not serializer.is_valid():
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Track the access
            ip_address = request.META.get('REMOTE_ADDR')
            shared_filter.track_access(ip_address=ip_address)
            
            return Response({
                'message': 'Access granted',
                'access_count': shared_filter.access_count,
                'last_accessed_at': shared_filter.last_accessed_at
            })
            
        except Exception as e:
            return Response(
                {'error': 'Invalid share link format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def pipeline(self, request, pk=None):
        """Get pipeline details for a shared filter"""
        try:
            # Decrypt the token and get shared filter
            encryption = ShareLinkEncryption()
            payload, error = encryption.decrypt_share_data(pk)
            
            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                saved_filter_id = payload['record_id']
                shared_filter = SharedFilter.objects.get(
                    saved_filter__id=saved_filter_id,
                    encrypted_token=pk,
                    is_active=True
                )
            except SharedFilter.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired share link'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if share is still valid
            if not shared_filter.is_valid:
                return Response(
                    {'error': f'Share link is {shared_filter.status}'},
                    status=status.HTTP_410_GONE
                )
            
            # Get pipeline details
            pipeline = shared_filter.saved_filter.pipeline
            shareable_fields = list(shared_filter.saved_filter.get_shareable_fields())
            
            # Filter fields to only those visible in shared views and collect field groups
            visible_fields = []
            field_group_ids = set()
            
            for field in pipeline.fields.all():
                if (field.slug in shareable_fields and 
                    field.is_visible_in_shared_list_and_detail_views):
                    if field.field_group:
                        field_group_ids.add(field.field_group.id)
                        
                    visible_fields.append({
                        'id': field.id,
                        'name': field.slug,
                        'display_name': field.name,
                        'field_type': field.field_type,
                        'is_visible_in_list': True,
                        'is_visible_in_detail': True,
                        'display_order': field.display_order,
                        'field_config': field.field_config,
                        'original_slug': field.slug,
                        'business_rules': field.business_rules,
                        'field_group': field.field_group.id if field.field_group else None,
                        'field_group_name': field.field_group.name if field.field_group else None,
                        'field_group_color': field.field_group.color if field.field_group else None,
                        'field_group_icon': field.field_group.icon if field.field_group else None,
                        'field_group_display_order': field.field_group.display_order if field.field_group else 0
                    })
            
            # Get the actual field groups used by visible fields
            field_groups = []
            if field_group_ids:
                from pipelines.models import FieldGroup
                for group in FieldGroup.objects.filter(id__in=field_group_ids):
                    field_groups.append({
                        'id': group.id,
                        'name': group.name,
                        'description': group.description,
                        'color': group.color,
                        'icon': group.icon,
                        'display_order': group.display_order,
                        'field_count': sum(1 for field in visible_fields if field.get('field_group') == group.id)
                    })
            
            return Response({
                'id': pipeline.id,
                'name': pipeline.name,
                'description': pipeline.description,
                'record_count': pipeline.records.count(),
                'fields': visible_fields,
                'field_groups': field_groups,
                'stages': []
            })
            
        except Exception as e:
            return Response(
                {'error': 'Invalid share link format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def records(self, request, pk=None):
        """Get records for a shared filter"""
        try:
            # Decrypt the token and get shared filter
            encryption = ShareLinkEncryption()
            payload, error = encryption.decrypt_share_data(pk)
            
            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                saved_filter_id = payload['record_id']
                shared_filter = SharedFilter.objects.get(
                    saved_filter__id=saved_filter_id,
                    encrypted_token=pk,
                    is_active=True
                )
            except SharedFilter.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired share link'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if share is still valid
            if not shared_filter.is_valid:
                return Response(
                    {'error': f'Share link is {shared_filter.status}'},
                    status=status.HTTP_410_GONE
                )
            
            # Get filtered records
            saved_filter = shared_filter.saved_filter
            pipeline = saved_filter.pipeline
            
            # Apply the saved filter to get records (exclude soft deleted)
            queryset = pipeline.records.filter(is_deleted=False)
            
            # Apply filter config if available
            if saved_filter.filter_config:
                # Apply the boolean query filtering using our existing filter validation logic
                filtered_records = []
                for record in queryset:
                    if self._record_matches_filter(record, saved_filter):
                        filtered_records.append(record.id)
                
                # Filter queryset to only include matching records
                if filtered_records:
                    queryset = queryset.filter(id__in=filtered_records)
                else:
                    # No records match the filter
                    queryset = queryset.none()
            
            # Get shareable fields only
            shareable_fields = list(saved_filter.get_shareable_fields())
            
            # Paginate results
            page_size = min(int(request.GET.get('page_size', 50)), 100)  # Max 100 records
            page = int(request.GET.get('page', 1))
            start = (page - 1) * page_size
            end = start + page_size
            
            total_records = queryset.count()
            records = queryset[start:end]
            
            # Format record data - only include shareable fields
            record_data = []
            for record in records:
                # Create data dict with only shareable fields
                data_dict = {}
                for field_name in shareable_fields:
                    if field_name in record.data:
                        data_dict[field_name] = record.data[field_name]
                
                # Use the same structure as regular API endpoints
                record_dict = {
                    'id': record.id,
                    'data': data_dict,
                    'created_at': record.created_at.isoformat() if record.created_at else None,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None
                }
                record_data.append(record_dict)
            
            return Response({
                'results': record_data,
                'count': total_records,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_records + page_size - 1) // page_size,
                'has_next': end < total_records,
                'has_previous': page > 1
            })
            
        except Exception as e:
            return Response(
                {'error': 'Invalid share link format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], url_path='related-pipeline/(?P<target_pipeline_id>[^/.]+)')
    def related_pipeline(self, request, pk=None, target_pipeline_id=None):
        """Get related pipeline details for cross-pipeline access in shared views"""
        try:
            # Decrypt the token and get shared filter
            encryption = ShareLinkEncryption()
            payload, error = encryption.decrypt_share_data(pk)
            
            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                saved_filter_id = payload['record_id']
                shared_filter = SharedFilter.objects.get(
                    saved_filter__id=saved_filter_id,
                    encrypted_token=pk,
                    is_active=True
                )
            except SharedFilter.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired share link'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if share is still valid
            if not shared_filter.is_valid:
                return Response(
                    {'error': f'Share link is {shared_filter.status}'},
                    status=status.HTTP_410_GONE
                )
            
            # Get the target pipeline
            try:
                from pipelines.models import Pipeline
                target_pipeline = Pipeline.objects.get(id=target_pipeline_id)
            except Pipeline.DoesNotExist:
                return Response(
                    {'error': 'Target pipeline not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Security check: Only allow access to pipelines in the same tenant
            source_pipeline = shared_filter.saved_filter.pipeline
            if target_pipeline.id != source_pipeline.id:
                # For cross-pipeline access, we need to ensure both are in the same tenant
                # This is enforced by Django's tenant isolation, but let's be explicit
                if hasattr(source_pipeline, 'tenant') and hasattr(target_pipeline, 'tenant'):
                    if source_pipeline.tenant != target_pipeline.tenant:
                        return Response(
                            {'error': 'Cross-tenant access not allowed'},
                            status=status.HTTP_403_FORBIDDEN
                        )
            
            # Get fields that are marked as visible in shared views for the target pipeline
            shareable_fields = target_pipeline.fields.filter(
                is_visible_in_shared_list_and_detail_views=True
            )
            
            if not shareable_fields.exists():
                return Response(
                    {'error': 'No shareable fields found in target pipeline'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get field groups for the visible fields
            field_group_ids = set()
            visible_fields = []
            
            for field in shareable_fields:
                if field.field_group:
                    field_group_ids.add(field.field_group.id)
                    
                visible_fields.append({
                    'id': field.id,
                    'name': field.slug,
                    'display_name': field.name,
                    'field_type': field.field_type,
                    'is_visible_in_list': True,
                    'is_visible_in_detail': True,
                    'is_visible_in_shared_list_and_detail_views': True,
                    'display_order': field.display_order,
                    'field_config': field.field_config,
                    'original_slug': field.slug,
                    'business_rules': field.business_rules,
                    'field_group': field.field_group.id if field.field_group else None,
                    'field_group_name': field.field_group.name if field.field_group else None,
                    'field_group_color': field.field_group.color if field.field_group else None,
                    'field_group_icon': field.field_group.icon if field.field_group else None,
                    'field_group_display_order': field.field_group.display_order if field.field_group else 0
                })
            
            # Get the actual field groups used by visible fields
            field_groups = []
            if field_group_ids:
                from pipelines.models import FieldGroup
                for group in FieldGroup.objects.filter(id__in=field_group_ids):
                    field_groups.append({
                        'id': group.id,
                        'name': group.name,
                        'description': group.description,
                        'color': group.color,
                        'icon': group.icon,
                        'display_order': group.display_order,
                        'field_count': sum(1 for field in visible_fields if field.get('field_group') == group.id)
                    })
            
            return Response({
                'id': target_pipeline.id,
                'name': target_pipeline.name,
                'description': target_pipeline.description,
                'record_count': target_pipeline.records.filter(is_deleted=False).count(),
                'fields': visible_fields,
                'field_groups': field_groups,
                'stages': []  # Pipeline model doesn't have stages - use empty array
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to access related pipeline: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='related-record/(?P<target_pipeline_id>[^/.]+)/(?P<target_record_id>[^/.]+)')
    def related_record(self, request, pk=None, target_pipeline_id=None, target_record_id=None):
        """Get related record details for cross-pipeline access in shared views"""
        try:
            # Decrypt the token and get shared filter
            encryption = ShareLinkEncryption()
            payload, error = encryption.decrypt_share_data(pk)
            
            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                saved_filter_id = payload['record_id']
                shared_filter = SharedFilter.objects.get(
                    saved_filter__id=saved_filter_id,
                    encrypted_token=pk,
                    is_active=True
                )
            except SharedFilter.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired share link'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if share is still valid
            if not shared_filter.is_valid:
                return Response(
                    {'error': f'Share link is {shared_filter.status}'},
                    status=status.HTTP_410_GONE
                )
            
            # Get the target pipeline and record
            try:
                from pipelines.models import Pipeline, Record
                target_pipeline = Pipeline.objects.get(id=target_pipeline_id)
                target_record = Record.objects.get(
                    id=target_record_id,
                    pipeline=target_pipeline,
                    is_deleted=False
                )
            except Pipeline.DoesNotExist:
                return Response(
                    {'error': 'Target pipeline not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Record.DoesNotExist:
                return Response(
                    {'error': 'Target record not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Security check: Only allow access to pipelines in the same tenant
            source_pipeline = shared_filter.saved_filter.pipeline
            if target_pipeline.id != source_pipeline.id:
                # For cross-pipeline access, we need to ensure both are in the same tenant
                # This is enforced by Django's tenant isolation, but let's be explicit
                if hasattr(source_pipeline, 'tenant') and hasattr(target_pipeline, 'tenant'):
                    if source_pipeline.tenant != target_pipeline.tenant:
                        return Response(
                            {'error': 'Cross-tenant access not allowed'},
                            status=status.HTTP_403_FORBIDDEN
                        )
            
            # Get fields that are marked as visible in shared views for the target pipeline
            shareable_fields = target_pipeline.fields.filter(
                is_visible_in_shared_list_and_detail_views=True
            )
            
            if not shareable_fields.exists():
                return Response(
                    {'error': 'No shareable fields found in target pipeline'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Filter record data to only include shareable fields
            shareable_field_slugs = list(shareable_fields.values_list('slug', flat=True))
            filtered_record_data = {}
            
            for field_slug in shareable_field_slugs:
                if field_slug in target_record.data:
                    filtered_record_data[field_slug] = target_record.data[field_slug]
            
            return Response({
                'id': target_record.id,
                'title': target_record.title,  # Add title at root level to match private API
                'data': filtered_record_data,
                'stage': getattr(target_record, 'stage', None),
                'tags': getattr(target_record, 'tags', []),
                'created_at': target_record.created_at.isoformat() if target_record.created_at else None,
                'updated_at': target_record.updated_at.isoformat() if target_record.updated_at else None,
                'created_by': {
                    'id': target_record.created_by.id,
                    'first_name': target_record.created_by.first_name,
                    'last_name': target_record.created_by.last_name,
                    'email': target_record.created_by.email
                } if target_record.created_by else None
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to access related record: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='records/(?P<record_id>[^/.]+)')
    def update_record(self, request, pk=None, record_id=None):
        """Update a record through shared filter access"""
        try:
            # Decrypt the token and get shared filter
            encryption = ShareLinkEncryption()
            payload, error = encryption.decrypt_share_data(pk)
            
            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                saved_filter_id = payload['record_id']
                shared_filter = SharedFilter.objects.get(
                    saved_filter__id=saved_filter_id,
                    encrypted_token=pk,
                    is_active=True
                )
            except SharedFilter.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired share link'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if share is still valid
            if not shared_filter.is_valid:
                return Response(
                    {'error': f'Share link is {shared_filter.status}'},
                    status=status.HTTP_410_GONE
                )
            
            # Check access mode - only allow updates for filtered_edit mode
            if shared_filter.access_mode != 'filtered_edit':
                return Response(
                    {'error': f'Record editing not allowed. Your access mode is "{shared_filter.access_mode}". Only "filtered_edit" mode allows record updates.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Log access
            shared_filter.track_access()
            
            # Get the record
            try:
                from pipelines.models import Record
                record = Record.objects.get(
                    id=record_id,
                    pipeline=shared_filter.saved_filter.pipeline,
                    is_deleted=False
                )
            except Record.DoesNotExist:
                return Response(
                    {'error': 'Record not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if record passes the filter criteria
            saved_filter = shared_filter.saved_filter
            if not self._record_matches_filter(record, saved_filter):
                return Response(
                    {'error': 'Record is not accessible through this filtered view'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get the data to update
            data = request.data.get('data', {})
            if not data:
                return Response(
                    {'error': 'No data provided for update'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate that only allowed fields are being updated
            # For shared filters, we restrict to fields that are in shared_fields or visible_fields
            allowed_fields = set(shared_filter.shared_fields or saved_filter.visible_fields or [])
            if allowed_fields:
                invalid_fields = set(data.keys()) - allowed_fields
                if invalid_fields:
                    return Response(
                        {'error': f'Cannot update fields {list(invalid_fields)}. Only these fields are editable: {list(allowed_fields)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Update the record data
            for field_name, value in data.items():
                if hasattr(record, 'data') and isinstance(record.data, dict):
                    record.data[field_name] = value
                else:
                    # Handle case where record.data might not be initialized
                    record.data = {field_name: value}
            
            # Save the record
            record.save(update_fields=['data', 'updated_at'])
            
            # Return the updated record data
            return Response({
                'id': record.id,
                'data': record.data,
                'updated_at': record.updated_at.isoformat(),
                'message': 'Record updated successfully'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to update record: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _record_matches_filter(self, record, saved_filter):
        """
        Check if a record matches the saved filter criteria.
        
        Args:
            record: The Record instance to check
            saved_filter: The SavedFilter instance with filter_config
        
        Returns:
            bool: True if record matches filter criteria, False otherwise
        """
        # If no filter config, all records match
        if not saved_filter.filter_config:
            return True
        
        filter_config = saved_filter.filter_config
        groups = filter_config.get('groups', [])
        group_logic = filter_config.get('groupLogic', 'AND')
        
        # If no groups, all records match
        if not groups:
            return True
        
        group_results = []
        
        for group in groups:
            filters = group.get('filters', [])
            logic = group.get('logic', 'AND')
            
            if not filters:
                # Empty group matches all records
                group_results.append(True)
                continue
            
            filter_results = []
            
            for filter_item in filters:
                field_name = filter_item.get('field')
                operator = filter_item.get('operator')
                value = filter_item.get('value')
                
                # Get the field value from record data
                record_value = record.data.get(field_name)
                
                # Evaluate the filter condition
                matches = self._evaluate_filter_condition(record_value, operator, value)
                filter_results.append(matches)
            
            # Apply group logic (AND/OR)
            if logic.upper() == 'AND':
                group_result = all(filter_results)
            else:  # OR
                group_result = any(filter_results)
            
            group_results.append(group_result)
        
        # Apply group logic (AND/OR)
        if group_logic.upper() == 'AND':
            return all(group_results)
        else:  # OR
            return any(group_results)
    
    def _evaluate_filter_condition(self, record_value, operator, filter_value):
        """
        Evaluate a single filter condition.
        
        Args:
            record_value: The value from the record
            operator: The filter operator (e.g., 'contains', 'equals', 'gt')
            filter_value: The value to compare against
        
        Returns:
            bool: True if condition matches, False otherwise
        """
        # Handle null/empty values
        if record_value is None:
            record_value = ""
        
        try:
            if operator == 'contains':
                # Special handling for user field arrays (JSON objects)
                if isinstance(record_value, list):
                    # Try to parse filter_value as JSON for user field matching
                    try:
                        import json
                        filter_obj = json.loads(filter_value)
                        if 'user_id' in filter_obj:
                            # Check if any user in the array has the specified user_id
                            target_user_id = filter_obj['user_id']
                            # Handle both string and integer user_ids
                            target_user_id_int = int(target_user_id)
                            target_user_id_str = str(target_user_id)
                            
                            for user in record_value:
                                if isinstance(user, dict) and 'user_id' in user:
                                    user_id = user['user_id']
                                    if user_id == target_user_id_int or str(user_id) == target_user_id_str:
                                        return True
                            return False
                    except (json.JSONDecodeError, ValueError, KeyError):
                        pass  # Fall back to string comparison
                
                # Default string-based comparison
                record_str = str(record_value).lower() if record_value is not None else ""
                filter_str = str(filter_value).lower() if filter_value is not None else ""
                return filter_str in record_str
            elif operator == 'not_contains':
                # Default string-based comparison
                record_str = str(record_value).lower() if record_value is not None else ""
                filter_str = str(filter_value).lower() if filter_value is not None else ""
                return filter_str not in record_str
            elif operator == 'equals':
                # Default string-based comparison  
                record_str = str(record_value).lower() if record_value is not None else ""
                filter_str = str(filter_value).lower() if filter_value is not None else ""
                return record_str == filter_str
            elif operator == 'not_equals':
                # Default string-based comparison  
                record_str = str(record_value).lower() if record_value is not None else ""
                filter_str = str(filter_value).lower() if filter_value is not None else ""
                return record_str != filter_str
            elif operator == 'starts_with':
                # Default string-based comparison  
                record_str = str(record_value).lower() if record_value is not None else ""
                filter_str = str(filter_value).lower() if filter_value is not None else ""
                return record_str.startswith(filter_str)
            elif operator == 'ends_with':
                # Default string-based comparison  
                record_str = str(record_value).lower() if record_value is not None else ""
                filter_str = str(filter_value).lower() if filter_value is not None else ""
                return record_str.endswith(filter_str)
            elif operator == 'is_empty':
                # Default string-based comparison  
                record_str = str(record_value).lower() if record_value is not None else ""
                return record_str == ""
            elif operator == 'is_not_empty':
                # Default string-based comparison  
                record_str = str(record_value).lower() if record_value is not None else ""
                return record_str != ""
            elif operator in ['gt', 'greater_than']:
                # Try numeric comparison first, fall back to string
                try:
                    return float(record_value) > float(filter_value)
                except (ValueError, TypeError):
                    return record_str > filter_str
            elif operator in ['gte', 'greater_than_or_equal']:
                try:
                    return float(record_value) >= float(filter_value)
                except (ValueError, TypeError):
                    return record_str >= filter_str
            elif operator in ['lt', 'less_than']:
                try:
                    return float(record_value) < float(filter_value)
                except (ValueError, TypeError):
                    return record_str < filter_str
            elif operator in ['lte', 'less_than_or_equal']:
                try:
                    return float(record_value) <= float(filter_value)
                except (ValueError, TypeError):
                    return record_str <= filter_str
            else:
                # Unknown operator, default to false for security
                return False
        except Exception:
            # If any error occurs during comparison, default to false for security
            return False


class PipelineFilterManagementViewSet(viewsets.ViewSet):
    """Pipeline-specific filter management interface"""
    
    permission_classes = [SavedFilterPermission]
    
    def list(self, request, pipeline_pk=None):
        """Get all filters for a specific pipeline"""
        from django.db.models import Q
        from authentication.permissions import SyncPermissionManager
        
        try:
            pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Pipeline not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        user = request.user
        permission_manager = SyncPermissionManager(user)
        
        # Check if user has access to this pipeline
        if not permission_manager.has_permission('action', 'pipelines', 'access', pipeline.id):
            return Response(
                {'error': 'You do not have access to this pipeline'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get filters for this pipeline based on access levels
        queryset = SavedFilter.objects.filter(pipeline=pipeline)
        access_conditions = Q()
        
        # Always include own filters
        access_conditions |= Q(created_by=user)
        
        # Include pipeline_users filters
        access_conditions |= Q(access_level='pipeline_users')
        
        # Include private filters of others if user has edit_filters permission
        if permission_manager.has_permission('action', 'filters', 'edit_filters'):
            access_conditions |= Q(access_level='private')
        
        filters = queryset.filter(access_conditions).select_related('created_by')
        
        serializer = SavedFilterListSerializer(filters, many=True, context={'request': request})
        
        return Response({
            'pipeline': {
                'id': pipeline.id,
                'name': pipeline.name,
                'slug': pipeline.slug
            },
            'filters': serializer.data,
            'user_permissions': {
                'can_create_filters': permission_manager.has_permission('action', 'filters', 'create_filters'),
                'can_edit_filters': permission_manager.has_permission('action', 'filters', 'edit_filters'),
                'can_delete_filters': permission_manager.has_permission('action', 'filters', 'delete_filters'),
                'can_create_shares': permission_manager.has_permission('action', 'sharing', 'create_shared_views'),
                'can_revoke_shares': permission_manager.has_permission('action', 'sharing', 'revoke_shared_views_forms')
            }
        })
    
    @action(detail=False, methods=['get'])
    def analytics(self, request, pipeline_pk=None):
        """Get filter usage analytics for pipeline"""
        from django.db.models import Count, Avg, Max
        from authentication.permissions import SyncPermissionManager
        
        try:
            pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Pipeline not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'pipelines', 'access', pipeline.id):
            return Response(
                {'error': 'You do not have access to this pipeline'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get analytics for filters in this pipeline
        filters = SavedFilter.objects.filter(pipeline=pipeline)
        
        analytics = {
            'total_filters': filters.count(),
            'filters_by_access_level': {
                'private': filters.filter(access_level='private').count(),
                'pipeline_users': filters.filter(access_level='pipeline_users').count(),
            },
            'most_used_filters': filters.order_by('-usage_count')[:5].values(
                'id', 'name', 'usage_count', 'created_by__email'
            ),
            'recent_filters': filters.order_by('-created_at')[:5].values(
                'id', 'name', 'created_at', 'created_by__email'
            ),
            'sharing_stats': {
                'shareable_filters': filters.filter(is_shareable=True).count(),
                'active_shares': SharedFilter.objects.filter(
                    saved_filter__pipeline=pipeline,
                    is_active=True
                ).count()
            }
        }
        
        return Response(analytics)
    
    @action(detail=False, methods=['post'])
    def bulk_update_access(self, request, pipeline_pk=None):
        """Bulk update access levels for multiple filters"""
        from authentication.permissions import SyncPermissionManager
        
        try:
            pipeline = get_object_or_404(Pipeline, pk=pipeline_pk)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Pipeline not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'filters', 'edit_filters'):
            return Response(
                {'error': 'You do not have permission to edit filters'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        filter_ids = request.data.get('filter_ids', [])
        new_access_level = request.data.get('access_level')
        
        if not filter_ids or not new_access_level:
            return Response(
                {'error': 'filter_ids and access_level are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_access_level not in ['private', 'pipeline_users']:
            return Response(
                {'error': 'Invalid access_level'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update filters
        updated_count = SavedFilter.objects.filter(
            id__in=filter_ids,
            pipeline=pipeline
        ).update(access_level=new_access_level)
        
        return Response({
            'message': f'Updated {updated_count} filters',
            'updated_count': updated_count
        })