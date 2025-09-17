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

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["pipeline_id"],
        "properties": {
            "pipeline_id": {
                "type": "string",
                "description": "The pipeline to create the record in",
                "ui_hints": {
                    "widget": "pipeline_select",
                    "placeholder": "Select target pipeline"
                }
            },
            "field_mapping_type": {
                "type": "string",
                "enum": ["manual", "json", "copy"],
                "default": "json",
                "description": "How to map field values",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "record_data": {
                "type": "object",
                "description": "Field values for the new record (when field_mapping_type is 'json')",
                "default": {},
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 10,
                    "placeholder": '{\n  "name": "{{contact_name}}",\n  "email": "{{email}}",\n  "status": "new"\n}'
                }
            },
            "source_record": {
                "type": "string",
                "description": "Record to copy field values from (when field_mapping_type is 'copy')",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{trigger.record}}",
                    "show_when": {"field_mapping_type": "copy"}
                }
            },
            "field_overrides": {
                "type": "object",
                "description": "Override specific fields when copying",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 6,
                    "placeholder": '{\n  "status": "copied",\n  "source_id": "{{original.id}}"\n}',
                    "show_when": {"field_mapping_type": "copy"}
                }
            },
            "skip_validation": {
                "type": "boolean",
                "default": False,
                "description": "Skip field validation rules"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "record_create"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process record creation node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Get configuration values
        pipeline_id = config.get('pipeline_id')
        field_mapping_type = config.get('field_mapping_type', 'json')
        record_data = config.get('record_data', {})
        source_record = config.get('source_record')
        field_overrides = config.get('field_overrides', {})
        skip_validation = config.get('skip_validation', False)
        
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
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record creation node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})
        checkpoint.update({
            'pipeline_id': config.get('pipeline_id'),
            'record_data_template': config.get('record_data', {}),
            'field_mapping_type': config.get('field_mapping_type', 'json')
        })

        return checkpoint


class RecordUpdateProcessor(AsyncNodeProcessor):
    """Process record update nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["record_id_source", "update_data"],
        "properties": {
            "record_id_source": {
                "type": "string",
                "description": "Path to record ID in context (e.g., 'trigger_data.record_id')",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{trigger.record_id}} or trigger_data.record_id"
                }
            },
            "update_data": {
                "type": "object",
                "description": "Fields to update on the record",
                "minProperties": 1,
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 8,
                    "placeholder": '{\n  "status": "updated",\n  "last_modified": "{{now}}",\n  "notes": "{{trigger.notes}}"\n}'
                }
            },
            "merge_strategy": {
                "type": "string",
                "enum": ["merge", "replace"],
                "default": "merge",
                "description": "How to handle existing data (merge adds/updates fields, replace overwrites all)",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "skip_validation": {
                "type": "boolean",
                "default": False,
                "description": "Skip field validation rules"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "record_update"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process record update node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Get configuration values
        record_id_source = config.get('record_id_source', '')
        update_data = config.get('update_data', {})
        merge_strategy = config.get('merge_strategy', 'merge')
        skip_validation = config.get('skip_validation', False)
        
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
        config = node_data.get('config', {})
        checkpoint.update({
            'record_id_source': config.get('record_id_source'),
            'update_data_template': config.get('update_data', {}),
            'merge_strategy': config.get('merge_strategy', 'merge'),
            'resolved_record_id': self._get_nested_value(context, config.get('record_id_source', ''))
        })

        return checkpoint


class RecordFindProcessor(AsyncNodeProcessor):
    """Process record find/search nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["pipeline_id"],
        "properties": {
            "pipeline_id": {
                "type": "string",
                "description": "The pipeline to search in",
                "ui_hints": {
                    "widget": "pipeline_select",
                    "placeholder": "Select pipeline to search"
                }
            },
            "search_criteria": {
                "type": "object",
                "description": "Field values to search for",
                "default": {},
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 6,
                    "placeholder": '{\n  "name": "{{search_name}}",\n  "email": "{{email}}",\n  "status": "active"\n}'
                }
            },
            "exact_match": {
                "type": "boolean",
                "default": False,
                "description": "Use exact match instead of contains search"
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 100,
                "description": "Maximum number of records to return"
            },
            "return_first_only": {
                "type": "boolean",
                "default": False,
                "description": "Return only the first matching record"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "record_find"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process record find node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Get configuration values
        pipeline_id = config.get('pipeline_id')
        search_criteria = config.get('search_criteria', {})
        exact_match = config.get('exact_match', False)
        limit = config.get('limit', 10)
        return_first_only = config.get('return_first_only', False)
        
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
                    if exact_match:
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
    
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record find node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})
        checkpoint.update({
            'pipeline_id': config.get('pipeline_id'),
            'search_criteria_template': config.get('search_criteria', {}),
            'exact_match': config.get('exact_match', False),
            'limit': config.get('limit', 10),
            'return_first_only': config.get('return_first_only', False)
        })

        return checkpoint


class RecordDeleteProcessor(AsyncNodeProcessor):
    """Process record deletion nodes"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["record_id_source"],
        "properties": {
            "record_id_source": {
                "type": "string",
                "description": "Path to record ID in context (e.g., 'trigger_data.record_id')",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{trigger.record_id}} or node_123.record_id"
                }
            },
            "soft_delete": {
                "type": "boolean",
                "default": True,
                "description": "Soft delete (mark as deleted) vs hard delete (remove from database)"
            },
            "confirm_deletion": {
                "type": "boolean",
                "default": False,
                "description": "Require confirmation before deletion (for critical workflows)"
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "record_delete"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process record deletion node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})

        # Get configuration values
        record_id_source = config.get('record_id_source', '')
        soft_delete = config.get('soft_delete', True)
        confirm_deletion = config.get('confirm_deletion', False)

        # Get record ID from context
        record_id = self._get_nested_value(context, record_id_source)

        if not record_id:
            raise ValueError("Record delete node requires record_id")

        try:
            from pipelines.models import Record
            from django_tenants.utils import schema_context

            tenant_schema = context.get('tenant_schema')

            with schema_context(tenant_schema):
                record = await sync_to_async(Record.objects.get)(id=record_id)

                if soft_delete:
                    # Soft delete - mark as deleted
                    record.is_deleted = True
                    await sync_to_async(record.save)()
                    action = "soft_deleted"
                else:
                    # Hard delete - remove from database
                    await sync_to_async(record.delete)()
                    action = "hard_deleted"

                return {
                    'success': True,
                    'record_id': str(record_id),
                    'action': action,
                    'soft_delete': soft_delete
                }

        except Record.DoesNotExist:
            return {
                'success': False,
                'error': f"Record with ID {record_id} not found",
                'record_id': str(record_id)
            }
        except Exception as e:
            logger.error(f"Record deletion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'record_id': str(record_id)
            }


    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record deletion node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})
        record_id_source = config.get('record_id_source', '')

        checkpoint.update({
            'record_id_source': record_id_source,
            'soft_delete': config.get('soft_delete', True),
            'resolved_record_id': self._get_nested_value(context, record_id_source) if record_id_source else None
        })

        return checkpoint