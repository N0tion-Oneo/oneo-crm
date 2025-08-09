"""
API views for relationship management
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Q, Count, Prefetch
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from api.permissions import RelationshipPermission

from pipelines.models import Pipeline, Record
from .models import (
    RelationshipType, 
    Relationship, 
    PermissionTraversal, 
    RelationshipPath
)
from .serializers import (
    RelationshipTypeSerializer,
    RelationshipCreateSerializer,
    RelationshipSerializer,
    RelationshipTraversalSerializer,
    RelationshipPathSerializer,
    PermissionTraversalSerializer,
    RelationshipStatsSerializer,
)
from .permissions import RelationshipPermissionManager
from .queries import RelationshipQueryManager


class RelationshipTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing relationship types"""
    
    queryset = RelationshipType.objects.all()
    serializer_class = RelationshipTypeSerializer
    permission_classes = [RelationshipPermission]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and filters"""
        queryset = super().get_queryset()
        
        # Filter by pipeline constraints if specified
        source_pipeline = self.request.query_params.get('source_pipeline')
        target_pipeline = self.request.query_params.get('target_pipeline')
        
        if source_pipeline:
            queryset = queryset.filter(
                Q(source_pipeline_id=source_pipeline) | Q(source_pipeline__isnull=True)
            )
        
        if target_pipeline:
            queryset = queryset.filter(
                Q(target_pipeline_id=target_pipeline) | Q(target_pipeline__isnull=True)
            )
        
        # Filter by system/custom types
        type_filter = self.request.query_params.get('type')
        if type_filter == 'system':
            queryset = queryset.filter(is_system=True)
        elif type_filter == 'custom':
            queryset = queryset.filter(is_system=False)
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        """Set created_by when creating relationship type"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def compatible_pipelines(self, request, pk=None):
        """Get pipelines compatible with this relationship type"""
        relationship_type = self.get_object()
        
        # Get all pipelines that can work with this relationship type
        if relationship_type.source_pipeline:
            source_pipelines = [relationship_type.source_pipeline]
        else:
            source_pipelines = Pipeline.objects.all()
        
        if relationship_type.target_pipeline:
            target_pipelines = [relationship_type.target_pipeline]
        else:
            target_pipelines = Pipeline.objects.all()
        
        return Response({
            'source_pipelines': [{'id': p.id, 'name': p.name} for p in source_pipelines],
            'target_pipelines': [{'id': p.id, 'name': p.name} for p in target_pipelines]
        })


class RelationshipViewSet(viewsets.ModelViewSet):
    """ViewSet for managing relationships"""
    
    queryset = Relationship.objects.filter(is_deleted=False)
    permission_classes = [RelationshipPermission]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return RelationshipCreateSerializer
        return RelationshipSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions and filters"""
        queryset = super().get_queryset().select_related(
            'relationship_type', 'source_pipeline', 'target_pipeline', 'created_by'
        )
        
        # Filter by pipeline
        pipeline_id = self.request.query_params.get('pipeline')
        if pipeline_id:
            queryset = queryset.filter(
                Q(source_pipeline_id=pipeline_id) | Q(target_pipeline_id=pipeline_id)
            )
        
        # Filter by record
        record_pipeline = self.request.query_params.get('record_pipeline')
        record_id = self.request.query_params.get('record_id')
        if record_pipeline and record_id:
            queryset = queryset.filter(
                Q(source_pipeline_id=record_pipeline, source_record_id=record_id) |
                Q(target_pipeline_id=record_pipeline, target_record_id=record_id)
            )
        
        # Filter by relationship type
        relationship_type = self.request.query_params.get('relationship_type')
        if relationship_type:
            queryset = queryset.filter(relationship_type_id=relationship_type)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', 'active')
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    
    def perform_destroy(self, instance):
        """Soft delete relationship"""
        instance.delete(soft=True)
        instance.deleted_by = self.request.user
        instance.save(update_fields=['deleted_by'])
    
    @action(detail=False, methods=['post'])
    def traverse(self, request):
        """Traverse relationships from a starting record"""
        serializer = RelationshipTraversalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Get the starting record
        try:
            start_record = Record.objects.get(
                pipeline_id=data['pipeline_id'],
                id=data['record_id'],
                is_deleted=False
            )
        except Record.DoesNotExist:
            return Response(
                {'error': 'Starting record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Initialize query manager
        query_manager = RelationshipQueryManager(request.user)
        
        # Perform traversal
        try:
            results = query_manager.get_related_records(
                source_pipeline_id=data['pipeline_id'],
                source_record_id=data['record_id'],
                relationship_types=data.get('relationship_types'),
                direction=data['direction'],
                max_depth=data['max_depth'],
                include_paths=data.get('include_record_data', False),
                limit=data.get('limit')
            )
            
            return Response(results)
            
        except Exception as e:
            return Response(
                {'error': f'Traversal failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get relationship statistics"""
        # Basic counts
        total_relationships = Relationship.objects.filter(is_deleted=False).count()
        active_relationships = Relationship.objects.filter(
            is_deleted=False, status='active'
        ).count()
        relationship_types_count = RelationshipType.objects.count()
        
        # Most connected records (top 10)
        most_connected = list(
            Relationship.objects.filter(is_deleted=False, status='active')
            .values('source_pipeline__name', 'source_record_id')
            .annotate(connection_count=Count('id'))
            .order_by('-connection_count')[:10]
        )
        
        # Relationship type distribution
        type_distribution = dict(
            Relationship.objects.filter(is_deleted=False, status='active')
            .values_list('relationship_type__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_activity = list(
            Relationship.objects.filter(
                is_deleted=False,
                created_at__gte=week_ago
            )
            .values('created_at__date')
            .annotate(count=Count('id'))
            .order_by('created_at__date')
        )
        
        stats_data = {
            'total_relationships': total_relationships,
            'active_relationships': active_relationships,
            'relationship_types_count': relationship_types_count,
            'most_connected_records': most_connected,
            'relationship_distribution': type_distribution,
            'recent_activity': recent_activity
        }
        
        serializer = RelationshipStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Mark relationship as verified"""
        relationship = self.get_object()
        relationship.is_verified = True
        relationship.save(update_fields=['is_verified'])
        
        return Response({'status': 'verified'})
    
    @action(detail=True, methods=['post'])
    def update_strength(self, request, pk=None):
        """Update relationship strength"""
        relationship = self.get_object()
        strength = request.data.get('strength')
        
        if strength is None or not (0 <= float(strength) <= 1):
            return Response(
                {'error': 'Strength must be between 0 and 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        relationship.strength = strength
        relationship.save(update_fields=['strength'])
        
        return Response({'status': 'updated', 'strength': relationship.strength})


class RelationshipPathViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing relationship paths (materialized views)"""
    
    queryset = RelationshipPath.objects.all()
    serializer_class = RelationshipPathSerializer
    permission_classes = [RelationshipPermission]
    
    def get_queryset(self):
        """Filter queryset and remove expired paths"""
        queryset = super().get_queryset().select_related(
            'source_pipeline', 'target_pipeline'
        )
        
        # Remove expired paths
        queryset = queryset.filter(expires_at__gt=timezone.now())
        
        # Filter by source record
        source_pipeline = self.request.query_params.get('source_pipeline')
        source_record = self.request.query_params.get('source_record')
        if source_pipeline and source_record:
            queryset = queryset.filter(
                source_pipeline_id=source_pipeline,
                source_record_id=source_record
            )
        
        # Filter by target record
        target_pipeline = self.request.query_params.get('target_pipeline')
        target_record = self.request.query_params.get('target_record')
        if target_pipeline and target_record:
            queryset = queryset.filter(
                target_pipeline_id=target_pipeline,
                target_record_id=target_record
            )
        
        # Filter by path length
        max_length = self.request.query_params.get('max_length')
        if max_length:
            queryset = queryset.filter(path_length__lte=int(max_length))
        
        return queryset.order_by('path_length', '-path_strength')
    
    @action(detail=False, methods=['post'])
    def find_shortest_path(self, request):
        """Find shortest path between two records"""
        source_pipeline = request.data.get('source_pipeline')
        source_record = request.data.get('source_record')
        target_pipeline = request.data.get('target_pipeline')
        target_record = request.data.get('target_record')
        
        if not all([source_pipeline, source_record, target_pipeline, target_record]):
            return Response(
                {'error': 'All source and target parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try to find cached path first
        cached_path = RelationshipPath.objects.filter(
            source_pipeline_id=source_pipeline,
            source_record_id=source_record,
            target_pipeline_id=target_pipeline,
            target_record_id=target_record,
            expires_at__gt=timezone.now()
        ).order_by('path_length').first()
        
        if cached_path:
            serializer = self.get_serializer(cached_path)
            return Response({
                'cached': True,
                'path': serializer.data
            })
        
        # Compute path dynamically
        query_manager = RelationshipQueryManager(request.user)
        try:
            path = query_manager.find_shortest_path(
                source_pipeline, source_record,
                target_pipeline, target_record
            )
            
            if path:
                return Response({
                    'cached': False,
                    'path': path
                })
            else:
                return Response(
                    {'error': 'No path found between records'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            return Response(
                {'error': f'Path finding failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PermissionTraversalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing relationship traversal permissions"""
    
    queryset = PermissionTraversal.objects.all()
    serializer_class = PermissionTraversalSerializer
    permission_classes = [RelationshipPermission]
    
    def get_queryset(self):
        """Filter by user type or relationship type if specified"""
        queryset = super().get_queryset().select_related(
            'user_type', 'relationship_type'
        )
        
        user_type = self.request.query_params.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type_id=user_type)
        
        relationship_type = self.request.query_params.get('relationship_type')
        if relationship_type:
            queryset = queryset.filter(relationship_type_id=relationship_type)
        
        return queryset.order_by('user_type__name', 'relationship_type__name')


