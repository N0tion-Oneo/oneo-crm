"""
REST API Views for Content Management System
"""
from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
from api.permissions import WorkflowPermission

from .models import (
    ContentLibrary, ContentAsset, ContentTag, ContentUsage, 
    ContentApproval, ContentType, ContentStatus, ContentVisibility
)
from .serializers import (
    ContentLibrarySerializer, ContentLibraryListSerializer,
    ContentAssetSerializer, ContentAssetListSerializer, ContentAssetCreateSerializer,
    ContentTagSerializer, ContentUsageSerializer, ContentApprovalSerializer,
    ContentRenderSerializer, ContentAnalyticsSerializer, LibraryAnalyticsSerializer
)
from .manager import content_manager


class ContentLibraryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing content libraries"""
    
    queryset = ContentLibrary.objects.filter(is_active=True)
    permission_classes = [WorkflowPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['visibility', 'requires_approval', 'parent_library']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return ContentLibraryListSerializer
        return ContentLibrarySerializer
    
    def get_queryset(self):
        """Filter libraries based on user access"""
        return content_manager.get_accessible_libraries(self.request.user)
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary="Get library analytics",
        responses={200: LibraryAnalyticsSerializer}
    )
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a content library"""
        library = self.get_object()
        analytics_data = content_manager.get_library_analytics(library)
        
        serializer = LibraryAnalyticsSerializer(analytics_data)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get library tree structure",
        responses={200: ContentLibrarySerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get hierarchical tree structure of libraries"""
        # Get root libraries only
        root_libraries = self.get_queryset().filter(parent_library__isnull=True)
        serializer = ContentLibrarySerializer(root_libraries, many=True)
        return Response(serializer.data)


class ContentAssetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing content assets"""
    
    queryset = ContentAsset.objects.filter(is_current_version=True)
    permission_classes = [WorkflowPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['content_type', 'status', 'visibility', 'library']
    search_fields = ['name', 'description', 'content_text']
    ordering_fields = ['name', 'created_at', 'usage_count', 'last_used_at']
    ordering = ['-usage_count', '-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return ContentAssetCreateSerializer
        elif self.action == 'list':
            return ContentAssetListSerializer
        return ContentAssetSerializer
    
    def get_queryset(self):
        """Filter assets based on user access and filters"""
        user = self.request.user
        
        # Base accessibility filter
        queryset = ContentAsset.objects.filter(
            Q(visibility=ContentVisibility.PUBLIC) |
            Q(visibility=ContentVisibility.ORGANIZATION) |
            Q(created_by=user) |
            Q(library__allowed_users=user),
            is_current_version=True
        ).distinct().select_related('library', 'created_by').prefetch_related('tags')
        
        # Additional filters from query params
        library_id = self.request.query_params.get('library_id')
        if library_id:
            queryset = queryset.filter(library_id=library_id)
        
        tags = self.request.query_params.getlist('tags')
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__name=tag)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary="Render content with variables",
        request=ContentRenderSerializer,
        responses={200: {'type': 'object', 'properties': {
            'rendered_content': {'type': 'string'},
            'variables_used': {'type': 'object'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """Render content asset with provided variables"""
        asset = self.get_object()
        
        serializer = ContentRenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        variables = serializer.validated_data.get('variables', {})
        workflow_context = serializer.validated_data.get('workflow_context', {})
        
        rendered_content = content_manager.render_content(
            asset, 
            variables, 
            workflow_context
        )
        
        return Response({
            'rendered_content': rendered_content,
            'variables_used': variables,
            'content_type': asset.content_type,
            'template_variables': asset.template_variables
        })
    
    @extend_schema(
        summary="Get content analytics",
        responses={200: ContentAnalyticsSerializer}
    )
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get usage analytics for content asset"""
        asset = self.get_object()
        analytics_data = content_manager.get_content_analytics(asset)
        
        serializer = ContentAnalyticsSerializer(analytics_data)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get content variables",
        responses={200: {'type': 'array', 'items': {'type': 'object'}}}
    )
    @action(detail=True, methods=['get'])
    def variables(self, request, pk=None):
        """Get available variables for content asset"""
        asset = self.get_object()
        variables = content_manager.get_content_variables(asset)
        
        return Response({'variables': variables})
    
    @extend_schema(
        summary="Create new version of content",
        responses={201: ContentAssetSerializer}
    )
    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """Create a new version of existing content"""
        current_asset = self.get_object()
        
        # Mark current version as not current
        current_asset.is_current_version = False
        current_asset.save(update_fields=['is_current_version'])
        
        # Create new version
        new_version_data = request.data.copy()
        new_version_data['parent_version'] = str(current_asset.id)
        new_version_data['library'] = str(current_asset.library.id)
        
        # Calculate new version number
        import re
        version_match = re.match(r'(\d+)\.(\d+)', current_asset.version)
        if version_match:
            major, minor = map(int, version_match.groups())
            new_version = f"{major}.{minor + 1}"
        else:
            new_version = "2.0"
        
        new_version_data['version'] = new_version
        
        serializer = ContentAssetCreateSerializer(data=new_version_data)
        serializer.is_valid(raise_exception=True)
        
        new_asset = serializer.save(
            created_by=request.user,
            parent_version=current_asset
        )
        
        return Response(
            ContentAssetSerializer(new_asset).data,
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        summary="Get content for workflow builder",
        parameters=[
            OpenApiParameter(name='content_type', type=str, location='query'),
            OpenApiParameter(name='library_id', type=str, location='query'),
            OpenApiParameter(name='tags', type=str, location='query', many=True),
        ],
        responses={200: ContentAssetListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def for_workflow(self, request):
        """Get content assets available for workflow builder"""
        content_type = request.query_params.get('content_type')
        library_id = request.query_params.get('library_id')
        tags = request.query_params.getlist('tags')
        
        assets = content_manager.get_content_for_workflow(
            user=request.user,
            content_type=content_type,
            library_id=library_id,
            tags=tags
        )
        
        serializer = ContentAssetListSerializer(assets, many=True)
        return Response(serializer.data)


class ContentTagViewSet(viewsets.ModelViewSet):
    """ViewSet for managing content tags"""
    
    queryset = ContentTag.objects.all()
    serializer_class = ContentTagSerializer
    permission_classes = [WorkflowPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'usage_count', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary="Get popular tags",
        responses={200: ContentTagSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular tags by usage"""
        popular_tags = self.get_queryset().order_by('-usage_count')[:20]
        serializer = ContentTagSerializer(popular_tags, many=True)
        return Response(serializer.data)


class ContentUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing content usage analytics"""
    
    queryset = ContentUsage.objects.all()
    serializer_class = ContentUsageSerializer
    permission_classes = [WorkflowPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['content_asset', 'workflow_id', 'node_type', 'usage_type']
    ordering_fields = ['execution_count', 'last_execution', 'success_rate']
    ordering = ['-execution_count']
    
    @extend_schema(
        summary="Get usage summary",
        responses={200: {'type': 'object'}}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get overall usage summary"""
        queryset = self.get_queryset()
        
        total_executions = sum(usage.execution_count for usage in queryset)
        unique_workflows = queryset.values('workflow_id').distinct().count()
        unique_assets = queryset.values('content_asset').distinct().count()
        
        return Response({
            'total_executions': total_executions,
            'unique_workflows_using_content': unique_workflows,
            'unique_assets_in_use': unique_assets,
            'total_usage_records': queryset.count()
        })


class ContentApprovalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing content approvals"""
    
    queryset = ContentApproval.objects.all()
    serializer_class = ContentApprovalSerializer
    permission_classes = [WorkflowPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'assigned_to', 'content_asset']
    ordering_fields = ['created_at', 'responded_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter approvals based on user role"""
        user = self.request.user
        
        # Users can see approvals they requested or are assigned to
        return self.queryset.filter(
            Q(requested_by=user) | Q(assigned_to=user)
        )
    
    def perform_create(self, serializer):
        """Set requested_by to current user"""
        serializer.save(requested_by=self.request.user)
    
    @extend_schema(
        summary="Approve content",
        request={'type': 'object', 'properties': {
            'response_message': {'type': 'string'}
        }},
        responses={200: ContentApprovalSerializer}
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve content asset"""
        approval = self.get_object()
        
        if approval.assigned_to != request.user:
            return Response(
                {'error': 'You are not assigned to this approval'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        approval.status = 'approved'
        approval.response_message = request.data.get('response_message', '')
        approval.responded_at = timezone.now()
        approval.save()
        
        # Update content asset status
        approval.content_asset.status = ContentStatus.APPROVED
        approval.content_asset.approved_by = request.user
        approval.content_asset.approved_at = timezone.now()
        approval.content_asset.save()
        
        serializer = ContentApprovalSerializer(approval)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Reject content",
        request={'type': 'object', 'properties': {
            'response_message': {'type': 'string'},
            'changes_requested': {'type': 'array', 'items': {'type': 'string'}}
        }},
        responses={200: ContentApprovalSerializer}
    )
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject content asset"""
        approval = self.get_object()
        
        if approval.assigned_to != request.user:
            return Response(
                {'error': 'You are not assigned to this approval'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        approval.status = 'rejected'
        approval.response_message = request.data.get('response_message', '')
        approval.changes_requested = request.data.get('changes_requested', [])
        approval.responded_at = timezone.now()
        approval.save()
        
        # Update content asset status
        approval.content_asset.status = ContentStatus.REJECTED
        approval.content_asset.save()
        
        serializer = ContentApprovalSerializer(approval)
        return Response(serializer.data)