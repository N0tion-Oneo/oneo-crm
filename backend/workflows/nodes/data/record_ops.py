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
                "description": "Map fields for the new record",
                "default": {},
                "ui_hints": {
                    "widget": "field_mapper",
                    "target_pipeline_key": "pipeline_id",
                    "mapping_mode": "simple",
                    "show_required_only": False,
                    "show_when": {"field_mapping_type": "manual"}
                }
            },
            "record_data_json": {
                "type": "object",
                "description": "Field values for the new record (JSON format)",
                "default": {},
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 10,
                    "placeholder": '{\n  "name": "{{contact_name}}",\n  "email": "{{email}}",\n  "status": "new"\n}',
                    "show_when": {"field_mapping_type": "json"}
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
        source_record = config.get('source_record')
        field_overrides = config.get('field_overrides', {})
        skip_validation = config.get('skip_validation', False)

        # Get the appropriate record data based on mapping type
        if field_mapping_type == 'manual':
            record_data = config.get('record_data', {})
        elif field_mapping_type == 'json':
            record_data = config.get('record_data_json', {})
        else:  # copy type
            record_data = {}  # Will be populated from source_record

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
        "required": ["record_id_source"],
        "properties": {
            "record_id_source": {
                "type": "string",
                "description": "Path to record ID in context",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "{{trigger.record_id}} or trigger_data.record_id"
                }
            },
            "pipeline_id": {
                "type": "string",
                "description": "Pipeline of the record being updated",
                "ui_hints": {
                    "widget": "pipeline_select",
                    "placeholder": "Select pipeline",
                    "help_text": "Optional: Helps with field mapping. Leave empty to use trigger record pipeline"
                }
            },
            "update_mode": {
                "type": "string",
                "enum": ["manual", "json"],
                "default": "manual",
                "description": "How to specify update values",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "update_data": {
                "type": "object",
                "description": "Map fields to update",
                "minProperties": 0,
                "ui_hints": {
                    "widget": "field_mapper",
                    "target_pipeline_key": "pipeline_id",
                    "mapping_mode": "advanced",
                    "show_when": {"update_mode": "manual"}
                }
            },
            "update_data_json": {
                "type": "object",
                "description": "Fields to update (JSON format)",
                "minProperties": 0,
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 8,
                    "placeholder": '{\n  "status": "updated",\n  "last_modified": "{{now}}",\n  "notes": "{{trigger.notes}}"\n}',
                    "show_when": {"update_mode": "json"}
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
        update_mode = config.get('update_mode', 'manual')
        merge_strategy = config.get('merge_strategy', 'merge')
        skip_validation = config.get('skip_validation', False)

        # Get the appropriate update data based on update mode
        if update_mode == 'manual':
            update_data = config.get('update_data', {})
        else:  # json mode
            update_data = config.get('update_data_json', {})
        
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
            "search_mode": {
                "type": "string",
                "enum": ["conditions", "json"],
                "default": "conditions",
                "description": "How to specify search criteria",
                "ui_hints": {
                    "widget": "select"
                }
            },
            "search_conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "operator": {"type": "string"},
                        "value": {}
                    }
                },
                "description": "Search conditions to match records",
                "ui_hints": {
                    "widget": "condition_builder",
                    "help_text": "Define conditions that records must meet",
                    "show_when": {"search_mode": "conditions"}
                }
            },
            "search_criteria": {
                "type": "object",
                "description": "Field values to search for (JSON format)",
                "default": {},
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 6,
                    "placeholder": '{\n  "name": "{{search_name}}",\n  "email": "{{email}}",\n  "status": "active"\n}',
                    "show_when": {"search_mode": "json"}
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
        search_mode = config.get('search_mode', 'conditions')
        search_conditions = config.get('search_conditions', [])
        search_criteria = config.get('search_criteria', {})
        exact_match = config.get('exact_match', False)
        limit = config.get('limit', 10)
        return_first_only = config.get('return_first_only', False)

        if not pipeline_id:
            raise ValueError("Record find node requires pipeline_id")

        # Format search criteria based on mode
        formatted_criteria = {}
        if search_mode == 'json':
            # Format JSON search criteria with context
            for key, value in search_criteria.items():
                formatted_criteria[key] = self._format_template(str(value), context)
        
        try:
            from pipelines.models import Pipeline, Record
            from django.db.models import Q
            
            pipeline = await sync_to_async(Pipeline.objects.get)(id=pipeline_id)
            
            # Build query
            query = Q(pipeline=pipeline, is_deleted=False)

            # Add search criteria based on mode
            if search_mode == 'conditions' and search_conditions:
                # Use condition evaluator for conditions
                from workflows.utils.condition_evaluator import condition_evaluator

                # We'll need to filter records based on conditions
                # For now, convert conditions to simple queries
                for condition in search_conditions:
                    field = condition.get('field', '')
                    operator = condition.get('operator', '=')
                    value = condition.get('value', '')

                    # Format value with context
                    formatted_value = self._format_template(str(value), context) if value else value

                    if field and formatted_value is not None:
                        if operator == '=':
                            query &= Q(**{f'data__{field}': formatted_value})
                        elif operator == '!=':
                            query &= ~Q(**{f'data__{field}': formatted_value})
                        elif operator == 'contains':
                            query &= Q(**{f'data__{field}__icontains': formatted_value})
                        elif operator == 'starts_with':
                            query &= Q(**{f'data__{field}__istartswith': formatted_value})
                        elif operator == 'ends_with':
                            query &= Q(**{f'data__{field}__iendswith': formatted_value})
                        elif operator == '>':
                            query &= Q(**{f'data__{field}__gt': formatted_value})
                        elif operator == '>=':
                            query &= Q(**{f'data__{field}__gte': formatted_value})
                        elif operator == '<':
                            query &= Q(**{f'data__{field}__lt': formatted_value})
                        elif operator == '<=':
                            query &= Q(**{f'data__{field}__lte': formatted_value})
                        elif operator == 'is_empty':
                            query &= (Q(**{f'data__{field}__isnull': True}) | Q(**{f'data__{field}': ''}))
                        elif operator == 'is_not_empty':
                            query &= ~(Q(**{f'data__{field}__isnull': True}) | Q(**{f'data__{field}': ''}))
            else:
                # Use formatted_criteria for JSON mode
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