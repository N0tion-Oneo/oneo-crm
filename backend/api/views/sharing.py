"""
API views for sharing system
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from sharing.models import SharedRecord, SharedRecordAccess
from sharing.serializers import (
    SharedRecordSerializer, SharedRecordListSerializer, 
    SharedRecordAccessSerializer, RevokeSharedRecordSerializer
)
from ..permissions import SharedRecordPermission, RecordSharingPermission


class SharedRecordFilter:
    """Custom filter for shared records"""
    
    def filter_queryset(self, request, queryset, view):
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True, expires_at__gt=timezone.now(), revoked_at__isnull=True)
        elif status_filter == 'expired':
            queryset = queryset.filter(expires_at__lte=timezone.now())
        elif status_filter == 'revoked':
            queryset = queryset.filter(revoked_at__isnull=False)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Filter by access mode
        access_mode = request.query_params.get('access_mode')
        if access_mode in ['readonly', 'editable']:
            queryset = queryset.filter(access_mode=access_mode)
        
        # Filter by date range
        created_after = request.query_params.get('created_after')
        if created_after:
            queryset = queryset.filter(created_at__date__gte=created_after)
        
        created_before = request.query_params.get('created_before')
        if created_before:
            queryset = queryset.filter(created_at__date__lte=created_before)
        
        # Filter by pipeline
        pipeline_id = request.query_params.get('pipeline_id')
        if pipeline_id:
            queryset = queryset.filter(record__pipeline_id=pipeline_id)
        
        # Filter by shared by user
        shared_by = request.query_params.get('shared_by')
        if shared_by:
            queryset = queryset.filter(shared_by_id=shared_by)
        
        return queryset


class SharedRecordHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing shared record history and analytics
    """
    serializer_class = SharedRecordListSerializer
    permission_classes = [SharedRecordPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['record__title', 'record__pipeline__name', 'shared_by__email']
    ordering_fields = ['created_at', 'expires_at', 'access_count', 'last_accessed_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get shared records that user has permission to see"""
        # Base queryset with related objects
        queryset = SharedRecord.objects.select_related(
            'record__pipeline', 'shared_by', 'revoked_by'
        ).filter(
            # Only show shares for records the user can access
            record__pipeline__in=self.get_accessible_pipelines()
        )
        
        # Apply custom filters
        filter_backend = SharedRecordFilter()
        queryset = filter_backend.filter_queryset(self.request, queryset, self)
        
        return queryset
    
    def get_accessible_pipelines(self):
        """Get pipelines the user can access"""
        from pipelines.models import Pipeline
        # This should use the same permission logic as the pipeline views
        # For now, return all pipelines - this should be refined based on user permissions
        return Pipeline.objects.all()
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve, list serializer for list"""
        if self.action == 'retrieve':
            return SharedRecordSerializer
        return SharedRecordListSerializer
    
    @extend_schema(
        summary="Revoke shared record",
        description="Revoke a shared record link, making it inaccessible",
        request=RevokeSharedRecordSerializer
    )
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a shared record"""
        shared_record = self.get_object()
        
        if shared_record.revoked_at:
            return Response(
                {'error': 'Shared record is already revoked'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not shared_record.is_valid:
            return Response(
                {'error': 'Shared record is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Revoke the share
        shared_record.revoke(revoked_by=request.user)
        
        return Response({
            'message': 'Shared record revoked successfully',
            'revoked_at': shared_record.revoked_at.isoformat(),
            'revoked_by': request.user.get_full_name() or request.user.email
        })
    
    @extend_schema(
        summary="Get access logs for shared record",
        description="Get detailed access history for a shared record"
    )
    @action(detail=True, methods=['get'])
    def access_logs(self, request, pk=None):
        """Get access logs for a shared record"""
        shared_record = self.get_object()
        
        access_logs = SharedRecordAccess.objects.filter(
            shared_record=shared_record
        ).order_by('-accessed_at')
        
        # Paginate results
        page = self.paginate_queryset(access_logs)
        if page is not None:
            serializer = SharedRecordAccessSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SharedRecordAccessSerializer(access_logs, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get sharing analytics",
        description="Get analytics and statistics for shared records"
    )
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get sharing analytics"""
        queryset = self.get_queryset()
        
        # Basic stats
        total_shares = queryset.count()
        active_shares = queryset.filter(
            is_active=True, 
            expires_at__gt=timezone.now(), 
            revoked_at__isnull=True
        ).count()
        expired_shares = queryset.filter(expires_at__lte=timezone.now()).count()
        revoked_shares = queryset.filter(revoked_at__isnull=False).count()
        
        # Access stats
        access_stats = queryset.aggregate(
            total_accesses=Count('access_count'),
            avg_accesses=Avg('access_count'),
            max_accesses=Max('access_count'),
            min_accesses=Min('access_count')
        )
        
        # Recent activity (last 30 days)
        recent_cutoff = timezone.now() - timedelta(days=30)
        recent_shares = queryset.filter(created_at__gte=recent_cutoff).count()
        recent_accesses = SharedRecordAccess.objects.filter(
            shared_record__in=queryset,
            accessed_at__gte=recent_cutoff
        ).count()
        
        # Access mode breakdown
        access_mode_stats = queryset.values('access_mode').annotate(
            count=Count('id')
        ).order_by('access_mode')
        
        return Response({
            'overview': {
                'total_shares': total_shares,
                'active_shares': active_shares,
                'expired_shares': expired_shares,
                'revoked_shares': revoked_shares
            },
            'access_statistics': access_stats,
            'recent_activity': {
                'shares_last_30_days': recent_shares,
                'accesses_last_30_days': recent_accesses
            },
            'access_mode_breakdown': list(access_mode_stats)
        })


class RecordSharingHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for getting shared history of a specific record
    """
    serializer_class = SharedRecordListSerializer
    permission_classes = [RecordSharingPermission]
    
    def get_queryset(self):
        """Get sharing history for a specific record"""
        record_id = self.kwargs.get('record_pk')
        if not record_id:
            return SharedRecord.objects.none()
        
        return SharedRecord.objects.filter(
            record_id=record_id
        ).select_related(
            'shared_by', 'revoked_by'
        ).order_by('-created_at')