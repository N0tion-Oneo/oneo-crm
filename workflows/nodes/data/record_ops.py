"""
Record Operations Node Processor - Create, update, find, and manage records
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class RecordCreateProcessor(AsyncNodeProcessor):
    """Process record creation nodes"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "RECORD_CREATE"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process record creation node"""
        
        node_data = node_config.get('data', {})
        pipeline_id = node_data.get('pipeline_id')
        record_data = node_data.get('record_data', {})
        
        if not pipeline_id:
            raise ValueError("Record create node requires pipeline_id")
        
        # Format record data with context
        formatted_data = {}
        for key, value in record_data.items():
            formatted_data[key] = self._format_template(str(value), context)
        
        # Create record
        try:
            from pipelines.models import Pipeline, Record
            
            pipeline = await sync_to_async(Pipeline.objects.get)(id=pipeline_id)
            
            # Get execution user
            execution = context.get('execution')
            user = execution.triggered_by if execution else None
            
            record = await sync_to_async(Record.objects.create)(
                pipeline=pipeline,
                data=formatted_data,
                created_by=user
            )
            
            return {
                'success': True,
                'record_id': record.id,
                'record_data': record.data,
                'pipeline_id': pipeline_id
            }
            
        except Exception as e:
            logger.error(f"Record creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'pipeline_id': pipeline_id
            }
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template string with context variables"""
        if not template:
            return ''
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate record creation node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('pipeline_id'):
            return False
        
        record_data = node_data.get('record_data', {})
        if not isinstance(record_data, dict):
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record creation node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        checkpoint.update({
            'pipeline_id': node_data.get('pipeline_id'),
            'record_data_template': node_data.get('record_data', {})
        })
        
        return checkpoint


class RecordUpdateProcessor(AsyncNodeProcessor):
    """Process record update nodes"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "RECORD_UPDATE"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process record update node"""
        
        node_data = node_config.get('data', {})
        record_id_source = node_data.get('record_id_source', '')
        update_data = node_data.get('update_data', {})
        
        # Get record ID from context
        record_id = self._get_nested_value(context, record_id_source)
        if not record_id:
            raise ValueError("Record update node requires record_id")
        
        # Format update data with context
        formatted_data = {}
        for key, value in update_data.items():
            formatted_data[key] = self._format_template(str(value), context)
        
        try:
            from pipelines.models import Record
            
            record = await sync_to_async(Record.objects.get)(id=record_id, is_deleted=False)
            
            # Update record data
            record.data.update(formatted_data)
            await sync_to_async(record.save)()
            
            return {
                'success': True,
                'record_id': record.id,
                'updated_fields': list(formatted_data.keys()),
                'new_data': record.data
            }
            
        except Exception as e:
            logger.error(f"Record update failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'record_id': record_id
            }
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template string with context variables"""
        if not template:
            return ''
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate record update node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('record_id_source'):
            return False
        
        update_data = node_data.get('update_data', {})
        if not isinstance(update_data, dict) or not update_data:
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record update node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        checkpoint.update({
            'record_id_source': node_data.get('record_id_source'),
            'update_data_template': node_data.get('update_data', {}),
            'resolved_record_id': self._get_nested_value(context, node_data.get('record_id_source', ''))
        })
        
        return checkpoint


class RecordFindProcessor(AsyncNodeProcessor):
    """Process record find/search nodes"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "RECORD_FIND"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process record find node"""
        
        node_data = node_config.get('data', {})
        pipeline_id = node_data.get('pipeline_id')
        search_criteria = node_data.get('search_criteria', {})
        limit = node_data.get('limit', 10)
        return_first_only = node_data.get('return_first_only', False)
        
        if not pipeline_id:
            raise ValueError("Record find node requires pipeline_id")
        
        # Format search criteria with context
        formatted_criteria = {}
        for key, value in search_criteria.items():
            formatted_criteria[key] = self._format_template(str(value), context)
        
        try:
            from pipelines.models import Pipeline, Record
            from django.db.models import Q
            
            pipeline = await sync_to_async(Pipeline.objects.get)(id=pipeline_id)
            
            # Build query
            query = Q(pipeline=pipeline, is_deleted=False)
            
            # Add search criteria
            for field_name, field_value in formatted_criteria.items():
                if field_value:  # Only add non-empty criteria
                    # Support both exact match and contains search
                    if node_data.get('exact_match', False):
                        query &= Q(**{f'data__{field_name}': field_value})
                    else:
                        query &= Q(**{f'data__{field_name}__icontains': field_value})
            
            # Execute query
            queryset = Record.objects.filter(query)[:limit]
            records = await sync_to_async(list)(queryset)
            
            if return_first_only and records:
                return {
                    'success': True,
                    'found': True,
                    'record': {
                        'id': records[0].id,
                        'data': records[0].data,
                        'created_at': records[0].created_at.isoformat()
                    },
                    'total_found': len(records)
                }
            else:
                return {
                    'success': True,
                    'found': len(records) > 0,
                    'records': [
                        {
                            'id': record.id,
                            'data': record.data,
                            'created_at': record.created_at.isoformat()
                        }
                        for record in records
                    ],
                    'total_found': len(records)
                }
                
        except Exception as e:
            logger.error(f"Record find failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'found': False,
                'pipeline_id': pipeline_id
            }
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format template string with context variables"""
        if not template:
            return ''
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate record find node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        if not node_data.get('pipeline_id'):
            return False
        
        search_criteria = node_data.get('search_criteria', {})
        if not isinstance(search_criteria, dict):
            return False
        
        # Validate limit
        limit = node_data.get('limit', 10)
        if not isinstance(limit, int) or limit <= 0:
            return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record find node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        checkpoint.update({
            'pipeline_id': node_data.get('pipeline_id'),
            'search_criteria_template': node_data.get('search_criteria', {}),
            'limit': node_data.get('limit', 10),
            'return_first_only': node_data.get('return_first_only', False)
        })
        
        return checkpoint