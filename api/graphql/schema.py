"""
GraphQL schema with dynamic types
"""
import graphene
from graphene import relay, ObjectType, String, Int, Boolean, DateTime, JSONString, Field, List
from graphene_django import DjangoObjectType
from django.contrib.auth import get_user_model

from pipelines.models import Pipeline, Record, Field as PipelineField
from relationships.models import Relationship, RelationshipType
from authentication.permissions import AsyncPermissionManager as PermissionManager

User = get_user_model()


class UserType(DjangoObjectType):
    """GraphQL type for User"""
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_active', 'created_at')


class PipelineType(DjangoObjectType):
    """GraphQL type for Pipeline"""
    record_count = Int()
    field_count = Int()
    
    class Meta:
        model = Pipeline
        fields = ('id', 'name', 'slug', 'description', 'icon', 'color', 
                 'pipeline_type', 'is_active', 'created_at', 'updated_at')
    
    def resolve_record_count(self, info):
        return self.records.filter(is_deleted=False).count()
    
    def resolve_field_count(self, info):
        return self.fields.count()


class PipelineFieldType(DjangoObjectType):
    """GraphQL type for Pipeline Field"""
    class Meta:
        model = PipelineField
        fields = ('id', 'name', 'slug', 'field_type', 'field_config', 
                 'is_required', 'is_visible_in_list', 'display_order')


class RecordType(DjangoObjectType):
    """GraphQL type for Record"""
    pipeline = Field(PipelineType)
    
    class Meta:
        model = Record
        fields = ('id', 'title', 'status', 'data', 'created_at', 'updated_at')
    
    def resolve_pipeline(self, info):
        return self.pipeline


class RelationshipTypeType(DjangoObjectType):
    """GraphQL type for RelationshipType"""
    class Meta:
        model = RelationshipType
        fields = ('id', 'name', 'slug', 'description', 'cardinality',
                 'is_bidirectional', 'forward_label', 'reverse_label')


class RelationshipType(DjangoObjectType):
    """GraphQL type for Relationship"""
    source_record = Field(RecordType)
    target_record = Field(RecordType)
    
    class Meta:
        model = Relationship
        fields = ('id', 'relationship_type', 'metadata', 'strength', 
                 'status', 'created_at')
    
    def resolve_source_record(self, info):
        return self.source_record
    
    def resolve_target_record(self, info):
        return self.target_record


class Query(ObjectType):
    """Main GraphQL Query"""
    
    # Pipeline queries
    pipelines = List(PipelineType)
    pipeline = Field(PipelineType, id=String(required=True))
    
    # Record queries
    records = List(
        RecordType,
        pipeline_id=String(required=True),
        limit=Int(default_value=50),
        offset=Int(default_value=0),
        search=String()
    )
    record = Field(RecordType, id=String(required=True))
    
    # Relationship queries
    related_records = List(
        RecordType,
        record_id=String(required=True),
        depth=Int(default_value=1),
        relationship_types=List(String),
        direction=String(default_value="BOTH")
    )
    
    # Search
    global_search = List(
        RecordType,
        query=String(required=True),
        pipeline_ids=List(String),
        limit=Int(default_value=50)
    )
    
    # User queries
    current_user = Field(UserType)
    user_permissions = JSONString()
    
    def resolve_pipelines(self, info, **kwargs):
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        # Apply permission filtering
        permission_manager = PermissionManager(user)
        pipelines = Pipeline.objects.filter(is_active=True)
        
        if not permission_manager.has_permission('action', 'pipelines', 'read_all'):
            # Filter to accessible pipelines
            accessible_ids = []
            for pipeline in pipelines:
                if permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline.id)):
                    accessible_ids.append(pipeline.id)
            pipelines = pipelines.filter(id__in=accessible_ids)
        
        return pipelines
    
    def resolve_pipeline(self, info, id):
        user = info.context.user
        if not user.is_authenticated:
            return None
        
        try:
            pipeline = Pipeline.objects.get(id=id, is_active=True)
            
            # Check permissions
            permission_manager = PermissionManager(user)
            if not permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline.id)):
                return None
            
            return pipeline
        except Pipeline.DoesNotExist:
            return None
    
    def resolve_records(self, info, pipeline_id, limit=50, offset=0, search=None):
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        # Check pipeline permissions
        permission_manager = PermissionManager(user)
        if not permission_manager.has_permission('action', 'records', 'read', pipeline_id):
            return []
        
        # Build queryset
        queryset = Record.objects.filter(
            pipeline_id=pipeline_id,
            is_deleted=False
        ).order_by('-updated_at')
        
        # Apply search
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(data__icontains=search)
            )
        
        # Apply pagination
        return queryset[offset:offset + limit]
    
    def resolve_record(self, info, id):
        user = info.context.user
        if not user.is_authenticated:
            return None
        
        try:
            record = Record.objects.get(id=id, is_deleted=False)
            
            # Check permissions
            permission_manager = PermissionManager(user)
            if not permission_manager.has_permission('action', 'records', 'read', str(record.pipeline_id)):
                return None
            
            return record
        except Record.DoesNotExist:
            return None
    
    def resolve_related_records(self, info, record_id, depth=1, relationship_types=None, direction="BOTH"):
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        # Get source record
        try:
            record = Record.objects.get(id=record_id, is_deleted=False)
        except Record.DoesNotExist:
            return []
        
        # Check permissions
        permission_manager = PermissionManager(user)
        if not permission_manager.has_permission('action', 'records', 'read', str(record.pipeline_id)):
            return []
        
        # Use relationship query manager
        from relationships.queries import RelationshipQueryManager
        query_manager = RelationshipQueryManager(user)
        
        # Convert relationship type slugs to IDs
        relationship_type_ids = None
        if relationship_types:
            relationship_type_ids = list(
                RelationshipType.objects.filter(
                    slug__in=relationship_types
                ).values_list('id', flat=True)
            )
        
        # Get related records
        result = query_manager.get_related_records(
            source_pipeline_id=record.pipeline_id,
            source_record_id=record.id,
            relationship_types=relationship_type_ids,
            max_depth=depth,
            direction=direction.lower()
        )
        
        # Extract and return records
        records = []
        for rel in result.get('relationships', []):
            if rel.get('target_record_id'):
                try:
                    target_record = Record.objects.get(
                        id=rel['target_record_id'],
                        is_deleted=False
                    )
                    records.append(target_record)
                except Record.DoesNotExist:
                    continue
        
        return records
    
    def resolve_global_search(self, info, query, pipeline_ids=None, limit=50):
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        # Get accessible pipelines
        permission_manager = PermissionManager(user)
        accessible_pipelines = []
        
        pipelines_to_check = Pipeline.objects.filter(is_active=True)
        if pipeline_ids:
            pipelines_to_check = pipelines_to_check.filter(id__in=pipeline_ids)
        
        for pipeline in pipelines_to_check:
            if permission_manager.has_permission('action', 'records', 'read', str(pipeline.id)):
                accessible_pipelines.append(pipeline.id)
        
        # Build search queryset
        from django.db.models import Q
        queryset = Record.objects.filter(
            pipeline_id__in=accessible_pipelines,
            is_deleted=False
        ).filter(
            Q(title__icontains=query) |
            Q(data__icontains=query)
        ).order_by('-updated_at')[:limit]
        
        return queryset
    
    def resolve_current_user(self, info):
        return info.context.user if info.context.user.is_authenticated else None
    
    def resolve_user_permissions(self, info):
        user = info.context.user
        if not user.is_authenticated:
            return {}
        
        permission_manager = PermissionManager(user)
        return permission_manager.get_user_permissions()


# Input types for mutations
class CreatePipelineInput(graphene.InputObjectType):
    name = String(required=True)
    description = String()
    pipeline_type = String()
    icon = String()
    color = String()


class CreateRecordInput(graphene.InputObjectType):
    data = JSONString(required=True)
    status = String()


# Mutation responses
class CreatePipelinePayload(graphene.ObjectType):
    pipeline = Field(PipelineType)
    success = Boolean()
    errors = List(String)


class CreateRecordPayload(graphene.ObjectType):
    record = Field(RecordType)
    success = Boolean()
    errors = List(String)


class Mutation(ObjectType):
    """GraphQL Mutations"""
    
    create_pipeline = Field(
        CreatePipelinePayload,
        input=CreatePipelineInput(required=True)
    )
    
    create_record = Field(
        CreateRecordPayload,
        pipeline_id=String(required=True),
        input=CreateRecordInput(required=True)
    )
    
    def resolve_create_pipeline(self, info, input):
        user = info.context.user
        if not user.is_authenticated:
            return CreatePipelinePayload(success=False, errors=['Authentication required'])
        
        # Check permissions
        permission_manager = PermissionManager(user)
        if not permission_manager.has_permission('action', 'pipelines', 'create'):
            return CreatePipelinePayload(success=False, errors=['Permission denied'])
        
        try:
            pipeline = Pipeline.objects.create(
                name=input.name,
                description=input.description or '',
                pipeline_type=input.pipeline_type or 'custom',
                icon=input.icon or 'database',
                color=input.color or '#3B82F6',
                created_by=user
            )
            
            return CreatePipelinePayload(pipeline=pipeline, success=True)
            
        except Exception as e:
            return CreatePipelinePayload(success=False, errors=[str(e)])
    
    def resolve_create_record(self, info, pipeline_id, input):
        user = info.context.user
        if not user.is_authenticated:
            return CreateRecordPayload(success=False, errors=['Authentication required'])
        
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
        except Pipeline.DoesNotExist:
            return CreateRecordPayload(success=False, errors=['Pipeline not found'])
        
        # Check permissions
        permission_manager = PermissionManager(user)
        if not permission_manager.has_permission('action', 'records', 'create', pipeline_id):
            return CreateRecordPayload(success=False, errors=['Permission denied'])
        
        # Validate data
        validation_result = pipeline.validate_record_data(input.data)
        if not validation_result['is_valid']:
            return CreateRecordPayload(
                success=False, 
                errors=[f"{field}: {', '.join(errors)}" for field, errors in validation_result['errors'].items()]
            )
        
        try:
            record = Record.objects.create(
                pipeline=pipeline,
                data=validation_result['cleaned_data'],
                status=input.status or 'active',
                created_by=user,
                updated_by=user
            )
            
            return CreateRecordPayload(record=record, success=True)
            
        except Exception as e:
            return CreateRecordPayload(success=False, errors=[str(e)])


# Schema definition
schema = graphene.Schema(query=Query, mutation=Mutation)