"""
DataLoader implementations for efficient data fetching in GraphQL
Prevents N+1 query problems by batching database queries
"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from asgiref.sync import sync_to_async
import strawberry
from strawberry.dataloader import DataLoader

from pipelines.models import Pipeline, Record, Field as PipelineField
from relationships.models import Relationship, RelationshipType
from django.contrib.auth import get_user_model

User = get_user_model()


class PipelineLoader:
    """DataLoader for efficient Pipeline loading"""
    
    @staticmethod
    async def load_pipelines(pipeline_ids: List[int]) -> List[Optional[Pipeline]]:
        """Batch load pipelines by IDs"""
        pipelines = await sync_to_async(list)(
            Pipeline.objects.filter(id__in=pipeline_ids, is_active=True)
        )
        
        # Create a mapping of ID to pipeline
        pipeline_map = {pipeline.id: pipeline for pipeline in pipelines}
        
        # Return pipelines in the same order as requested IDs
        return [pipeline_map.get(pipeline_id) for pipeline_id in pipeline_ids]


class RecordLoader:
    """DataLoader for efficient Record loading"""
    
    @staticmethod
    async def load_records(record_ids: List[int]) -> List[Optional[Record]]:
        """Batch load records by IDs"""
        records = await sync_to_async(list)(
            Record.objects.filter(
                id__in=record_ids, 
                is_deleted=False
            ).select_related('pipeline')
        )
        
        record_map = {record.id: record for record in records}
        return [record_map.get(record_id) for record_id in record_ids]
    
    @staticmethod
    async def load_records_by_pipeline(pipeline_ids: List[int]) -> List[List[Record]]:
        """Batch load records grouped by pipeline ID"""
        records = await sync_to_async(list)(
            Record.objects.filter(
                pipeline_id__in=pipeline_ids,
                is_deleted=False
            ).select_related('pipeline').order_by('-updated_at')
        )
        
        # Group records by pipeline ID
        records_by_pipeline = defaultdict(list)
        for record in records:
            records_by_pipeline[record.pipeline_id].append(record)
        
        # Return records in the same order as requested pipeline IDs
        return [records_by_pipeline[pipeline_id] for pipeline_id in pipeline_ids]


class PipelineFieldLoader:
    """DataLoader for efficient PipelineField loading"""
    
    @staticmethod
    async def load_fields_by_pipeline(pipeline_ids: List[int]) -> List[List[PipelineField]]:
        """Batch load fields grouped by pipeline ID"""
        fields = await sync_to_async(list)(
            PipelineField.objects.filter(
                pipeline_id__in=pipeline_ids
            ).order_by('display_order')
        )
        
        # Group fields by pipeline ID
        fields_by_pipeline = defaultdict(list)
        for field in fields:
            fields_by_pipeline[field.pipeline_id].append(field)
        
        return [fields_by_pipeline[pipeline_id] for pipeline_id in pipeline_ids]


class RelationshipLoader:
    """DataLoader for efficient Relationship loading"""
    
    @staticmethod
    async def load_relationships_by_source(record_ids: List[int]) -> List[List[Relationship]]:
        """Batch load relationships grouped by source record ID"""
        relationships = await sync_to_async(list)(
            Relationship.objects.filter(
                source_record_id__in=record_ids,
                is_deleted=False
            ).select_related('relationship_type', 'target_record')
        )
        
        relationships_by_source = defaultdict(list)
        for relationship in relationships:
            relationships_by_source[relationship.source_record_id].append(relationship)
        
        return [relationships_by_source[record_id] for record_id in record_ids]
    
    @staticmethod
    async def load_relationships_by_target(record_ids: List[int]) -> List[List[Relationship]]:
        """Batch load relationships grouped by target record ID"""
        relationships = await sync_to_async(list)(
            Relationship.objects.filter(
                target_record_id__in=record_ids,
                is_deleted=False
            ).select_related('relationship_type', 'source_record')
        )
        
        relationships_by_target = defaultdict(list)
        for relationship in relationships:
            relationships_by_target[relationship.target_record_id].append(relationship)
        
        return [relationships_by_target[record_id] for record_id in record_ids]


class UserLoader:
    """DataLoader for efficient User loading"""
    
    @staticmethod
    async def load_users(user_ids: List[int]) -> List[Optional[User]]:
        """Batch load users by IDs"""
        users = await sync_to_async(list)(
            User.objects.filter(id__in=user_ids, is_active=True)
        )
        
        user_map = {user.id: user for user in users}
        return [user_map.get(user_id) for user_id in user_ids]


class RecordCountLoader:
    """DataLoader for efficient record count loading"""
    
    @staticmethod
    async def load_record_counts(pipeline_ids: List[int]) -> List[int]:
        """Batch load record counts for pipelines"""
        from django.db.models import Count
        
        pipeline_counts = await sync_to_async(list)(
            Pipeline.objects.filter(
                id__in=pipeline_ids
            ).annotate(
                record_count=Count('records', filter={'records__is_deleted': False})
            ).values('id', 'record_count')
        )
        
        # Create mapping of pipeline ID to count
        count_map = {item['id']: item['record_count'] for item in pipeline_counts}
        
        return [count_map.get(pipeline_id, 0) for pipeline_id in pipeline_ids]


class DataLoaderManager:
    """Manager class to create and manage DataLoader instances"""
    
    def __init__(self):
        self.pipeline_loader = DataLoader(PipelineLoader.load_pipelines)
        self.record_loader = DataLoader(RecordLoader.load_records)
        self.records_by_pipeline_loader = DataLoader(RecordLoader.load_records_by_pipeline)
        self.fields_by_pipeline_loader = DataLoader(PipelineFieldLoader.load_fields_by_pipeline)
        self.relationships_by_source_loader = DataLoader(RelationshipLoader.load_relationships_by_source)
        self.relationships_by_target_loader = DataLoader(RelationshipLoader.load_relationships_by_target)
        self.user_loader = DataLoader(UserLoader.load_users)
        self.record_count_loader = DataLoader(RecordCountLoader.load_record_counts)
    
    async def get_pipeline(self, pipeline_id: int) -> Optional[Pipeline]:
        """Get a pipeline using DataLoader"""
        return await self.pipeline_loader.load(pipeline_id)
    
    async def get_record(self, record_id: int) -> Optional[Record]:
        """Get a record using DataLoader"""
        return await self.record_loader.load(record_id)
    
    async def get_records_for_pipeline(self, pipeline_id: int) -> List[Record]:
        """Get records for a pipeline using DataLoader"""
        return await self.records_by_pipeline_loader.load(pipeline_id)
    
    async def get_fields_for_pipeline(self, pipeline_id: int) -> List[PipelineField]:
        """Get fields for a pipeline using DataLoader"""
        return await self.fields_by_pipeline_loader.load(pipeline_id)
    
    async def get_outgoing_relationships(self, record_id: int) -> List[Relationship]:
        """Get outgoing relationships for a record using DataLoader"""
        return await self.relationships_by_source_loader.load(record_id)
    
    async def get_incoming_relationships(self, record_id: int) -> List[Relationship]:
        """Get incoming relationships for a record using DataLoader"""
        return await self.relationships_by_target_loader.load(record_id)
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user using DataLoader"""
        return await self.user_loader.load(user_id)
    
    async def get_record_count(self, pipeline_id: int) -> int:
        """Get record count for a pipeline using DataLoader"""
        return await self.record_count_loader.load(pipeline_id)


def get_dataloader_manager(context) -> DataLoaderManager:
    """Get or create DataLoader manager for the current request context"""
    if not hasattr(context, 'dataloader_manager'):
        context.dataloader_manager = DataLoaderManager()
    return context.dataloader_manager