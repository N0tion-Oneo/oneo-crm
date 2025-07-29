"""
Modern Strawberry GraphQL schema with async support for Oneo CRM
Replaces Graphene implementation with better async performance and Django integration
"""
import strawberry
import strawberry_django
from strawberry import auto, field
from strawberry_django import type as strawberry_type

from typing import List, Optional
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from pipelines.models import Pipeline, Record, Field as PipelineField
from relationships.models import Relationship, RelationshipType
from authentication.permissions import AsyncPermissionManager
from .dataloaders import get_dataloader_manager
from .extensions import DEFAULT_EXTENSIONS

User = get_user_model()


@strawberry_type(User)
class UserType:
    """GraphQL type for User with async support"""
    id: auto
    email: auto
    first_name: auto
    last_name: auto
    is_active: auto
    created_at: auto


@strawberry_type(Pipeline)
class PipelineType:
    """GraphQL type for Pipeline with computed fields"""
    id: auto
    name: auto
    slug: auto
    description: auto
    icon: auto
    color: auto
    pipeline_type: auto
    is_active: auto
    created_at: auto
    updated_at: auto
    
    @field
    async def record_count(self, info) -> int:
        """Get active record count for this pipeline using DataLoader"""
        dataloader_manager = get_dataloader_manager(info.context)
        return await dataloader_manager.get_record_count(self.id)
    
    @field
    async def field_count(self, info) -> int:
        """Get field count for this pipeline using DataLoader"""
        dataloader_manager = get_dataloader_manager(info.context)
        fields = await dataloader_manager.get_fields_for_pipeline(self.id)
        return len(fields)


@strawberry_type(PipelineField)
class PipelineFieldType:
    """GraphQL type for Pipeline Field"""
    id: auto
    name: auto
    slug: auto
    field_type: auto
    field_config: auto
    is_required: auto
    is_visible_in_list: auto
    display_order: auto


@strawberry_type(Record)
class RecordType:
    """GraphQL type for Record with dynamic data"""
    id: auto
    title: auto
    status: auto
    data: auto
    created_at: auto
    updated_at: auto
    
    pipeline: PipelineType


@strawberry_type(RelationshipType)
class RelationshipTypeType:
    """GraphQL type for RelationshipType"""
    id: auto
    name: auto
    slug: auto
    description: auto
    cardinality: auto
    is_bidirectional: auto
    forward_label: auto
    reverse_label: auto


@strawberry_type(Relationship)
class RelationshipGraphQLType:
    """GraphQL type for Relationship"""
    id: auto
    relationship_type: RelationshipTypeType
    metadata: auto
    strength: auto
    status: auto
    created_at: auto
    
    source_record: RecordType
    target_record: RecordType


@strawberry.input
class CreatePipelineInput:
    """Input type for creating pipelines"""
    name: str
    description: Optional[str] = None
    pipeline_type: Optional[str] = "custom"
    icon: Optional[str] = "database"
    color: Optional[str] = "#3B82F6"


@strawberry.input
class CreateRecordInput:
    """Input type for creating records"""
    data: strawberry.scalars.JSON
    status: Optional[str] = "active"


@strawberry.type
class CreatePipelinePayload:
    """Payload for pipeline creation mutation"""
    pipeline: Optional[PipelineType] = None
    success: bool = False
    errors: List[str] = strawberry.field(default_factory=list)


@strawberry.type
class CreateRecordPayload:
    """Payload for record creation mutation"""
    record: Optional[RecordType] = None
    success: bool = False
    errors: List[str] = strawberry.field(default_factory=list)


@strawberry.type
class Query:
    """Main GraphQL Query with async resolvers"""
    
    @field
    async def pipelines(self, info) -> List[PipelineType]:
        """Get all accessible pipelines for the current user"""
        user = info.context.request.user
        if not user.is_authenticated:
            return []
        
        permission_manager = AsyncPermissionManager(user)
        
        # Get all active pipelines
        pipelines = await sync_to_async(
            lambda: list(Pipeline.objects.filter(is_active=True))
        )()
        
        # Filter based on permissions
        accessible_pipelines = []
        for pipeline in pipelines:
            has_permission = await permission_manager.has_permission(
                'action', 'pipelines', 'read', str(pipeline.id)
            )
            if has_permission:
                accessible_pipelines.append(pipeline)
        
        return accessible_pipelines
    
    @field
    async def pipeline(self, info, id: strawberry.ID) -> Optional[PipelineType]:
        """Get a specific pipeline by ID"""
        user = info.context.request.user
        if not user.is_authenticated:
            return None
        
        try:
            pipeline = await sync_to_async(
                Pipeline.objects.get
            )(id=id, is_active=True)
            
            permission_manager = AsyncPermissionManager(user)
            has_permission = await permission_manager.has_permission(
                'action', 'pipelines', 'read', str(pipeline.id)
            )
            
            return pipeline if has_permission else None
            
        except Pipeline.DoesNotExist:
            return None
    
    @field
    async def records(
        self, 
        info, 
        pipeline_id: strawberry.ID,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[RecordType]:
        """Get records for a specific pipeline"""
        user = info.context.request.user
        if not user.is_authenticated:
            return []
        
        permission_manager = AsyncPermissionManager(user)
        has_permission = await permission_manager.has_permission(
            'action', 'records', 'read', str(pipeline_id)
        )
        
        if not has_permission:
            return []
        
        # Build query
        queryset = Record.objects.filter(
            pipeline_id=pipeline_id,
            is_deleted=False
        ).select_related('pipeline').order_by('-updated_at')
        
        # Apply search if provided
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(data__icontains=search)
            )
        
        # Apply pagination
        records = await sync_to_async(
            lambda: list(queryset[offset:offset + limit])
        )()
        
        return records
    
    @field
    async def record(self, info, id: strawberry.ID) -> Optional[RecordType]:
        """Get a specific record by ID"""
        user = info.context.request.user
        if not user.is_authenticated:
            return None
        
        try:
            record = await sync_to_async(
                Record.objects.select_related('pipeline').get
            )(id=id, is_deleted=False)
            
            permission_manager = AsyncPermissionManager(user)
            has_permission = await permission_manager.has_permission(
                'action', 'records', 'read', str(record.pipeline_id)
            )
            
            return record if has_permission else None
            
        except Record.DoesNotExist:
            return None
    
    @field
    async def related_records(
        self,
        info,
        record_id: strawberry.ID,
        depth: int = 1,
        relationship_types: Optional[List[str]] = None,
        direction: str = "BOTH"
    ) -> List[RecordType]:
        """Get related records using relationship traversal"""
        user = info.context.request.user
        if not user.is_authenticated:
            return []
        
        # Get source record first
        try:
            record = await sync_to_async(
                Record.objects.get
            )(id=record_id, is_deleted=False)
        except Record.DoesNotExist:
            return []
        
        # Check permissions for source record
        permission_manager = AsyncPermissionManager(user)
        has_permission = await permission_manager.has_permission(
            'action', 'records', 'read', str(record.pipeline_id)
        )
        
        if not has_permission:
            return []
        
        # Use relationship query manager
        from relationships.queries import RelationshipQueryManager
        query_manager = RelationshipQueryManager(user)
        
        # Convert relationship type slugs to IDs if provided
        relationship_type_ids = None
        if relationship_types:
            relationship_type_ids = await sync_to_async(
                lambda: list(
                    RelationshipType.objects.filter(
                        slug__in=relationship_types
                    ).values_list('id', flat=True)
                )
            )()
        
        # Get related records
        result = await sync_to_async(query_manager.get_related_records)(
            source_pipeline_id=record.pipeline_id,
            source_record_id=record.id,
            relationship_types=relationship_type_ids,
            max_depth=depth,
            direction=direction.lower()
        )
        
        # Extract records from result
        records = []
        for rel in result.get('relationships', []):
            target_record_id = rel.get('target_record_id')
            if target_record_id:
                try:
                    target_record = await sync_to_async(
                        Record.objects.get
                    )(id=target_record_id, is_deleted=False)
                    records.append(target_record)
                except Record.DoesNotExist:
                    continue
        
        return records
    
    @field
    async def global_search(
        self,
        info,
        query: str,
        pipeline_ids: Optional[List[strawberry.ID]] = None,
        limit: int = 50
    ) -> List[RecordType]:
        """Global search across all accessible records"""
        user = info.context.request.user
        if not user.is_authenticated:
            return []
        
        permission_manager = AsyncPermissionManager(user)
        
        # Get accessible pipelines
        accessible_pipelines = []
        pipelines_to_check = Pipeline.objects.filter(is_active=True)
        
        if pipeline_ids:
            pipelines_to_check = pipelines_to_check.filter(id__in=pipeline_ids)
        
        pipelines = await sync_to_async(list)(pipelines_to_check)
        
        for pipeline in pipelines:
            has_permission = await permission_manager.has_permission(
                'action', 'records', 'read', str(pipeline.id)
            )
            if has_permission:
                accessible_pipelines.append(pipeline.id)
        
        if not accessible_pipelines:
            return []
        
        # Build search queryset
        from django.db.models import Q
        queryset = Record.objects.filter(
            pipeline_id__in=accessible_pipelines,
            is_deleted=False
        ).filter(
            Q(title__icontains=query) | Q(data__icontains=query)
        ).select_related('pipeline').order_by('-updated_at')[:limit]
        
        records = await sync_to_async(list)(queryset)
        return records
    
    @field
    async def current_user(self, info) -> Optional[UserType]:
        """Get the current authenticated user"""
        user = info.context.request.user
        return user if user.is_authenticated else None
    
    @field
    async def user_permissions(self, info) -> strawberry.scalars.JSON:
        """Get permissions for the current user"""
        user = info.context.request.user
        if not user.is_authenticated:
            return {}
        
        permission_manager = AsyncPermissionManager(user)
        return await permission_manager.get_user_permissions()


@strawberry.type
class Mutation:
    """GraphQL Mutations with async support"""
    
    @strawberry.mutation
    async def create_pipeline(
        self, 
        info, 
        input: CreatePipelineInput
    ) -> CreatePipelinePayload:
        """Create a new pipeline"""
        user = info.context.request.user
        if not user.is_authenticated:
            return CreatePipelinePayload(
                success=False, 
                errors=["Authentication required"]
            )
        
        permission_manager = AsyncPermissionManager(user)
        has_permission = await permission_manager.has_permission(
            'action', 'pipelines', 'create'
        )
        
        if not has_permission:
            return CreatePipelinePayload(
                success=False, 
                errors=["Permission denied"]
            )
        
        try:
            pipeline = await sync_to_async(Pipeline.objects.create)(
                name=input.name,
                description=input.description or '',
                pipeline_type=input.pipeline_type,
                icon=input.icon,
                color=input.color,
                created_by=user
            )
            
            return CreatePipelinePayload(
                pipeline=pipeline, 
                success=True
            )
            
        except Exception as e:
            return CreatePipelinePayload(
                success=False, 
                errors=[str(e)]
            )
    
    @strawberry.mutation
    async def create_record(
        self, 
        info, 
        pipeline_id: strawberry.ID,
        input: CreateRecordInput
    ) -> CreateRecordPayload:
        """Create a new record in a pipeline"""
        user = info.context.request.user
        if not user.is_authenticated:
            return CreateRecordPayload(
                success=False, 
                errors=["Authentication required"]
            )
        
        try:
            pipeline = await sync_to_async(Pipeline.objects.get)(id=pipeline_id)
        except Pipeline.DoesNotExist:
            return CreateRecordPayload(
                success=False, 
                errors=["Pipeline not found"]
            )
        
        permission_manager = AsyncPermissionManager(user)
        has_permission = await permission_manager.has_permission(
            'action', 'records', 'create', str(pipeline_id)
        )
        
        if not has_permission:
            return CreateRecordPayload(
                success=False, 
                errors=["Permission denied"]
            )
        
        # Validate data
        validation_result = await sync_to_async(pipeline.validate_record_data)(input.data)
        
        if not validation_result['is_valid']:
            errors = []
            for field, field_errors in validation_result['errors'].items():
                errors.append(f"{field}: {', '.join(field_errors)}")
            
            return CreateRecordPayload(
                success=False, 
                errors=errors
            )
        
        try:
            record = await sync_to_async(Record.objects.create)(
                pipeline=pipeline,
                data=validation_result['cleaned_data'],
                status=input.status,
                created_by=user,
                updated_by=user
            )
            
            return CreateRecordPayload(
                record=record, 
                success=True
            )
            
        except Exception as e:
            return CreateRecordPayload(
                success=False, 
                errors=[str(e)]
            )


# Schema definition with extensions (subscriptions will be added later)
schema = strawberry.Schema(
    query=Query, 
    mutation=Mutation,
    extensions=DEFAULT_EXTENSIONS
)