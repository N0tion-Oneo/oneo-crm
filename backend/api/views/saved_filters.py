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

from pipelines.models import SavedFilter
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
    """Permission class for saved filters"""
    
    def has_permission(self, request, view):
        """Check if user has permission to access saved filters"""
        if not request.user.is_authenticated:
            return False
        
        # For now, allow authenticated users to manage their own filters
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific saved filter"""
        # Users can only access their own filters
        if request.method in permissions.SAFE_METHODS:
            return obj.created_by == request.user
        
        # Only filter creator can modify
        return obj.created_by == request.user


class SavedFilterViewSet(viewsets.ModelViewSet):
    """ViewSet for managing saved filters"""
    
    permission_classes = [SavedFilterPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['pipeline', 'is_shareable', 'is_default', 'view_mode']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'last_used_at', 'usage_count']
    ordering = ['-last_used_at', '-created_at']
    
    def get_queryset(self):
        """Get saved filters for current user"""
        return SavedFilter.objects.filter(
            created_by=self.request.user
        ).select_related('pipeline', 'created_by')
    
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
            
            # Filter fields to only those visible in shared views
            visible_fields = []
            for field in pipeline.fields.all():
                if (field.slug in shareable_fields and 
                    field.is_visible_in_shared_list_and_detail_views):
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
                        'business_rules': field.business_rules
                    })
            
            return Response({
                'id': pipeline.id,
                'name': pipeline.name,
                'description': pipeline.description,
                'record_count': pipeline.records.count(),
                'fields': visible_fields,
                'field_groups': [],
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
                # Here you would apply the boolean query filtering
                # For now, we'll return all records (this needs proper implementation)
                pass
            
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