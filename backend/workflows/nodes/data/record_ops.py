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
            "record_data": {
                "type": "object",
                "description": "Map fields for the new record",
                "default": {},
                "ui_hints": {
                    "widget": "field_mapper",
                    "target_pipeline_key": "pipeline_id",
                    "show_required_only": False
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

        # node_config is already the extracted config when called from execute()
        config = node_config

        # Get configuration values
        pipeline_id = config.get('pipeline_id')
        record_data = config.get('record_data', {})
        skip_validation = config.get('skip_validation', False)

        if not pipeline_id:
            raise ValueError("Record create node requires pipeline_id")

        # Format record data with context
        formatted_data = {}
        for key, value in record_data.items():
            formatted_data[key] = self.format_template(str(value), context)
        
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
            
            record_id = str(record.id)
            return {
                'success': True,
                'entity_type': 'record',
                'entity_id': record_id,  # Primary identifier
                'record_id': record_id,  # Explicit ID for easy access
                'pipeline_id': pipeline_id,
                'record_data': record.data,
                'created_at': record.created_at.isoformat(),
                'related_ids': {
                    'record_id': record_id,
                    'pipeline_id': pipeline_id
                }
            }
            
        except Exception as e:
            logger.error(f"Record creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'pipeline_id': pipeline_id
            }
    
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record creation node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        # In checkpoint, node_config is the full node config with data structure
        config = node_config.get('data', {}).get('config', {})
        checkpoint.update({
            'pipeline_id': config.get('pipeline_id'),
            'record_data_template': config.get('record_data', {})
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
                    "help_text": "Optional: Validates the record belongs to this pipeline. Must match the record's actual pipeline for field mapping to work correctly."
                }
            },
            "update_data": {
                "type": "object",
                "description": "Map fields to update",
                "minProperties": 0,
                "ui_hints": {
                    "widget": "field_mapper",
                    "target_pipeline_key": "pipeline_id"
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

        # node_config is already the extracted config when called from execute()
        config = node_config

        # Get configuration values
        record_id_source = config.get('record_id_source', '')
        pipeline_id = config.get('pipeline_id')  # Extract pipeline_id for validation
        update_data = config.get('update_data', {})
        merge_strategy = config.get('merge_strategy', 'merge')
        skip_validation = config.get('skip_validation', False)
        
        # Get record ID from context or use direct value
        # Handle different formats of record_id_source:
        # 1. Template variable: {{record_id}} or {{node.field}}
        # 2. Context path: trigger_data.record_id
        # 3. Direct ID: 296 or uuid

        # Clean up template syntax if present
        cleaned_source = record_id_source
        if cleaned_source.startswith('{{') and cleaned_source.endswith('}}'):
            cleaned_source = cleaned_source[2:-2].strip()

        # First try to get it from context using the path
        record_id = self._get_nested_value(context, cleaned_source)

        # If not found in context and record_id_source looks like an ID, use it directly
        # This handles test scenarios where an ID is passed directly
        if not record_id and cleaned_source:
            # Check if it looks like a direct ID (numeric or UUID-like)
            if cleaned_source.isdigit() or '-' in cleaned_source:
                record_id = cleaned_source

        # Also check if there's a record in context (common in test scenarios)
        if not record_id and 'record' in context:
            if isinstance(context['record'], dict) and 'id' in context['record']:
                record_id = context['record']['id']
            elif hasattr(context.get('record'), 'id'):
                record_id = context['record'].id

        if not record_id:
            logger.error(f"Could not resolve record_id from source: '{record_id_source}', context keys: {list(context.keys())}")
            raise ValueError(f"Record update node requires record_id. Got source: '{record_id_source}'")
        
        # Format update data with context
        formatted_data = {}
        for key, value in update_data.items():
            formatted_data[key] = self.format_template(str(value), context) if isinstance(value, str) else value

        try:
            from pipelines.models import Record

            record = await sync_to_async(Record.objects.get)(id=record_id, is_deleted=False)

            # Validate pipeline if specified
            if pipeline_id and str(record.pipeline_id) != str(pipeline_id):
                logger.error(
                    f"Pipeline mismatch: Record {record_id} belongs to pipeline {record.pipeline_id}, "
                    f"but pipeline {pipeline_id} was specified"
                )
                raise ValueError(
                    f"Record {record_id} belongs to pipeline {record.pipeline_id}, not {pipeline_id}. "
                    f"Please ensure the correct pipeline is selected."
                )

            # Update record data based on merge strategy
            if merge_strategy == 'replace':
                record.data = formatted_data
            else:  # merge
                record.data.update(formatted_data)

            await sync_to_async(record.save)()
            
            record_id = str(record.id)
            return {
                'success': True,
                'entity_type': 'record',
                'entity_id': record_id,  # Primary identifier
                'record_id': record_id,  # Explicit ID for easy access
                'pipeline_id': str(record.pipeline_id),
                'updated_fields': list(formatted_data.keys()),
                'new_data': record.data,
                'updated_at': record.updated_at.isoformat(),
                'related_ids': {
                    'record_id': record_id,
                    'pipeline_id': str(record.pipeline_id)
                }
            }
            
        except Exception as e:
            logger.error(f"Record update failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'record_id': record_id
            }
    
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate record update node inputs"""
        # In validate_inputs, node_config is the full node config with data structure
        config = node_config.get('data', {}).get('config', {})

        # Check required fields
        if not config.get('record_id_source'):
            return False

        # update_data should be a dict, but can be empty (minProperties: 0 in schema)
        update_data = config.get('update_data', {})
        if not isinstance(update_data, dict):
            return False

        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record update node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        # In checkpoint, node_config is the full node config with data structure
        config = node_config.get('data', {}).get('config', {})
        checkpoint.update({
            'record_id_source': config.get('record_id_source'),
            'pipeline_id': config.get('pipeline_id'),  # Include pipeline_id in checkpoint
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
                    "help_text": "Define conditions that records must meet"
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

        # node_config is already the extracted config when called from execute()
        config = node_config

        # Get configuration values
        pipeline_id = config.get('pipeline_id')
        search_conditions = config.get('search_conditions', [])
        exact_match = config.get('exact_match', False)
        limit = config.get('limit', 10)
        return_first_only = config.get('return_first_only', False)

        if not pipeline_id:
            raise ValueError("Record find node requires pipeline_id")

        try:
            from pipelines.models import Pipeline, Record
            from django.db.models import Q

            pipeline = await sync_to_async(Pipeline.objects.get)(id=pipeline_id)

            # Build query
            query = Q(pipeline=pipeline, is_deleted=False)

            # Add search conditions
            if search_conditions:
                # Use condition evaluator for conditions
                from workflows.utils.condition_evaluator import condition_evaluator

                # We'll need to filter records based on conditions
                # For now, convert conditions to simple queries
                for condition in search_conditions:
                    field = condition.get('field', '')
                    operator = condition.get('operator', '=')
                    value = condition.get('value', '')

                    # Format value with context
                    formatted_value = self.format_template(str(value), context) if value else value

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
            
            # Execute query
            queryset = Record.objects.filter(query)[:limit]
            records = await sync_to_async(list)(queryset)
            
            if return_first_only and records:
                record_id = str(records[0].id)
                return {
                    'success': True,
                    'entity_type': 'record',
                    'entity_id': record_id,  # Primary identifier
                    'found': True,
                    'record_id': record_id,  # Explicit ID for easy access
                    'pipeline_id': pipeline_id,
                    'record': {
                        'id': record_id,
                        'data': records[0].data,
                        'created_at': records[0].created_at.isoformat()
                    },
                    'total_found': len(records),
                    'related_ids': {
                        'record_id': record_id,
                        'pipeline_id': pipeline_id
                    }
                }
            else:
                record_ids = [str(record.id) for record in records]
                return {
                    'success': True,
                    'entity_type': 'record_list',
                    'entity_ids': record_ids,  # Array of identifiers
                    'found': len(records) > 0,
                    'record_ids': record_ids,  # Explicit IDs for easy access
                    'pipeline_id': pipeline_id,
                    'records': [
                        {
                            'id': str(record.id),
                            'data': record.data,
                            'created_at': record.created_at.isoformat()
                        }
                        for record in records
                    ],
                    'total_found': len(records),
                    'related_ids': {
                        'record_ids': record_ids,
                        'pipeline_id': pipeline_id
                    }
                }
                
        except Exception as e:
            logger.error(f"Record find failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'found': False,
                'pipeline_id': pipeline_id
            }
    
    
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for record find node"""
        checkpoint = await super().create_checkpoint(node_config, context)

        # In checkpoint, node_config is the full node config with data structure
        config = node_config.get('data', {}).get('config', {})
        checkpoint.update({
            'pipeline_id': config.get('pipeline_id'),
            'search_conditions': config.get('search_conditions', []),
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

        # node_config is already the extracted config when called from execute()
        config = node_config

        # Get configuration values
        record_id_source = config.get('record_id_source', '')
        soft_delete = config.get('soft_delete', True)
        confirm_deletion = config.get('confirm_deletion', False)

        # Get record ID from context or use direct value
        # Handle different formats of record_id_source:
        # 1. Template variable: {{record_id}} or {{node.field}}
        # 2. Context path: trigger_data.record_id
        # 3. Direct ID: 296 or uuid

        # Clean up template syntax if present
        cleaned_source = record_id_source
        if cleaned_source.startswith('{{') and cleaned_source.endswith('}}'):
            cleaned_source = cleaned_source[2:-2].strip()

        # First try to get it from context using the path
        record_id = self._get_nested_value(context, cleaned_source)

        # If not found in context and record_id_source looks like an ID, use it directly
        # This handles test scenarios where an ID is passed directly
        if not record_id and cleaned_source:
            # Check if it looks like a direct ID (numeric or UUID-like)
            if cleaned_source.isdigit() or '-' in cleaned_source:
                record_id = cleaned_source

        # Also check if there's a record in context (common in test scenarios)
        if not record_id and 'record' in context:
            if isinstance(context['record'], dict) and 'id' in context['record']:
                record_id = context['record']['id']
            elif hasattr(context.get('record'), 'id'):
                record_id = context['record'].id

        if not record_id:
            logger.error(f"Could not resolve record_id from source: '{record_id_source}', context keys: {list(context.keys())}")
            raise ValueError(f"Record delete node requires record_id. Got source: '{record_id_source}'")

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

        # In checkpoint, node_config is the full node config with data structure
        config = node_config.get('data', {}).get('config', {})
        record_id_source = config.get('record_id_source', '')

        checkpoint.update({
            'record_id_source': record_id_source,
            'soft_delete': config.get('soft_delete', True),
            'resolved_record_id': self._get_nested_value(context, record_id_source) if record_id_source else None
        })

        return checkpoint