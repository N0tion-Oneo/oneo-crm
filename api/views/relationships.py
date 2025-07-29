"""
Relationship API views
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter

from relationships.models import RelationshipType, Relationship
from api.serializers import RelationshipTypeSerializer, RelationshipSerializer
from api.filters import RelationshipFilter
from api.permissions import RelationshipPermission


class RelationshipTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Relationship type management (read-only for most users)
    """
    serializer_class = RelationshipTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cardinality', 'is_bidirectional', 'is_system', 'allow_user_relationships']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def get_queryset(self):
        """Get relationship types"""
        return RelationshipType.objects.all()


class RelationshipViewSet(viewsets.ModelViewSet):
    """
    Relationship management API
    """
    serializer_class = RelationshipSerializer
    permission_classes = [permissions.IsAuthenticated, RelationshipPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RelationshipFilter
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get relationships with proper filtering"""
        return Relationship.objects.filter(
            is_deleted=False
        ).select_related(
            'relationship_type', 'source_pipeline', 'target_pipeline',
            'user', 'created_by'
        )
    
    @extend_schema(
        summary="Traverse relationships",
        description="Perform multi-hop relationship traversal",
        parameters=[
            OpenApiParameter('source_pipeline_id', int, required=True),
            OpenApiParameter('source_record_id', int, required=True),
            OpenApiParameter('max_depth', int, description='Maximum traversal depth'),
            OpenApiParameter('direction', str, description='Traversal direction (forward/reverse/both)'),
            OpenApiParameter('relationship_types', str, description='Comma-separated relationship type IDs'),
            OpenApiParameter('include_paths', bool, description='Include relationship paths in response')
        ]
    )
    @action(detail=False, methods=['get'])
    def traverse(self, request):
        """Multi-hop relationship traversal"""
        # Get parameters
        source_pipeline_id = request.query_params.get('source_pipeline_id')
        source_record_id = request.query_params.get('source_record_id')
        max_depth = int(request.query_params.get('max_depth', 3))
        direction = request.query_params.get('direction', 'both')
        relationship_types = request.query_params.get('relationship_types')
        include_paths = request.query_params.get('include_paths', 'false').lower() == 'true'
        
        if not source_pipeline_id or not source_record_id:
            return Response(
                {'error': 'source_pipeline_id and source_record_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse relationship types
        relationship_type_ids = None
        if relationship_types:
            try:
                relationship_type_ids = [int(x.strip()) for x in relationship_types.split(',')]
            except ValueError:
                return Response(
                    {'error': 'Invalid relationship_types format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Use relationship query manager
        from relationships.queries import RelationshipQueryManager
        query_manager = RelationshipQueryManager(request.user)
        
        try:
            result = query_manager.get_related_records(
                source_pipeline_id=int(source_pipeline_id),
                source_record_id=int(source_record_id),
                relationship_types=relationship_type_ids,
                max_depth=max_depth,
                direction=direction,
                include_paths=include_paths
            )
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Find shortest path",
        description="Find shortest path between two records",
        parameters=[
            OpenApiParameter('source_pipeline_id', int, required=True),
            OpenApiParameter('source_record_id', int, required=True),
            OpenApiParameter('target_pipeline_id', int, required=True),
            OpenApiParameter('target_record_id', int, required=True),
            OpenApiParameter('max_depth', int, description='Maximum search depth')
        ]
    )
    @action(detail=False, methods=['get'])
    def shortest_path(self, request):
        """Find shortest path between two records"""
        # Get parameters
        source_pipeline_id = request.query_params.get('source_pipeline_id')
        source_record_id = request.query_params.get('source_record_id')
        target_pipeline_id = request.query_params.get('target_pipeline_id')
        target_record_id = request.query_params.get('target_record_id')
        max_depth = int(request.query_params.get('max_depth', 5))
        
        required_params = [source_pipeline_id, source_record_id, target_pipeline_id, target_record_id]
        if not all(required_params):
            return Response(
                {'error': 'source_pipeline_id, source_record_id, target_pipeline_id, and target_record_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use relationship query manager
        from relationships.queries import RelationshipQueryManager
        query_manager = RelationshipQueryManager(request.user)
        
        try:
            result = query_manager.find_shortest_path(
                source_pipeline_id=int(source_pipeline_id),
                source_record_id=int(source_record_id),
                target_pipeline_id=int(target_pipeline_id),
                target_record_id=int(target_record_id),
                max_depth=max_depth
            )
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Relationship statistics",
        description="Get statistics about relationships in the system"
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get relationship statistics"""
        from django.db.models import Count, Q
        
        stats = {
            'total_relationships': Relationship.objects.filter(is_deleted=False).count(),
            'active_relationships': Relationship.objects.filter(
                is_deleted=False, 
                status='active'
            ).count(),
            'user_assignments': Relationship.objects.filter(
                is_deleted=False,
                user__isnull=False
            ).count(),
            'record_relationships': Relationship.objects.filter(
                is_deleted=False,
                user__isnull=True
            ).count(),
            'relationship_types_count': RelationshipType.objects.count(),
            'relationship_distribution': self._get_relationship_distribution(),
            'most_connected_records': self._get_most_connected_records()
        }
        
        return Response(stats)
    
    def _get_relationship_distribution(self):
        """Get distribution of relationships by type"""
        from django.db.models import Count
        
        distribution = RelationshipType.objects.annotate(
            relationship_count=Count('relationship', filter=Q(relationship__is_deleted=False))
        ).values('name', 'relationship_count').order_by('-relationship_count')
        
        return {item['name']: item['relationship_count'] for item in distribution}
    
    def _get_most_connected_records(self):
        """Get most connected records"""
        from django.db.models import Count, Q
        from pipelines.models import Record
        
        # Get records with most outgoing relationships
        outgoing = Relationship.objects.filter(
            is_deleted=False,
            user__isnull=True  # Only record-to-record relationships
        ).values(
            'source_pipeline_id', 'source_record_id'
        ).annotate(
            connection_count=Count('id')
        ).order_by('-connection_count')[:5]
        
        # Get records with most incoming relationships
        incoming = Relationship.objects.filter(
            is_deleted=False,
            user__isnull=True
        ).values(
            'target_pipeline_id', 'target_record_id'
        ).annotate(
            connection_count=Count('id')
        ).order_by('-connection_count')[:5]
        
        most_connected = []
        
        # Process outgoing relationships
        for item in outgoing:
            try:
                record = Record.objects.get(
                    pipeline_id=item['source_pipeline_id'],
                    id=item['source_record_id'],
                    is_deleted=False
                )
                most_connected.append({
                    'record_id': record.id,
                    'record_title': record.title,
                    'pipeline_name': record.pipeline.name,
                    'connection_count': item['connection_count'],
                    'direction': 'outgoing'
                })
            except Record.DoesNotExist:
                continue
        
        # Process incoming relationships
        for item in incoming:
            try:
                record = Record.objects.get(
                    pipeline_id=item['target_pipeline_id'],
                    id=item['target_record_id'],
                    is_deleted=False
                )
                most_connected.append({
                    'record_id': record.id,
                    'record_title': record.title,
                    'pipeline_name': record.pipeline.name,
                    'connection_count': item['connection_count'],
                    'direction': 'incoming'
                })
            except Record.DoesNotExist:
                continue
        
        # Sort by connection count and return top 10
        most_connected.sort(key=lambda x: x['connection_count'], reverse=True)
        return most_connected[:10]