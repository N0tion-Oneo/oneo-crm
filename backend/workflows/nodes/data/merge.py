"""
Data Merge Node Processor - Merge data from multiple sources with different strategies
"""
import logging
from typing import Dict, Any, List, Union
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class MergeDataProcessor(AsyncNodeProcessor):
    """Process data merge nodes with configurable strategies"""

    # Configuration schema
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["merge_sources"],
        "properties": {
            "merge_sources": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "oneOf": [
                        {
                            "type": "string",
                            "description": "Context path to data source"
                        },
                        {
                            "type": "object",
                            "properties": {
                                "context_path": {"type": "string"},
                                "transformations": {"type": "array"},
                                "literal": {},
                                "template": {"type": "string"}
                            }
                        }
                    ]
                },
                "description": "Data sources to merge",
                "ui_hints": {
                    "widget": "json_editor",
                    "rows": 6,
                    "placeholder": '[\n  "node_1.data",\n  {"context_path": "node_2.result"},\n  {"literal": {"status": "active"}}\n]'
                }
            },
            "merge_strategy": {
                "type": "string",
                "enum": ["combine", "override", "append", "deep_merge"],
                "default": "combine",
                "description": "How to merge the data sources",
                "ui_hints": {
                    "widget": "radio",
                    "help_text": "combine: merge all into single object, override: later sources override earlier, append: create array of all sources, deep_merge: recursive merge"
                }
            },
            "output_key": {
                "type": "string",
                "default": "merged_data",
                "description": "Key to store merged result in context",
                "ui_hints": {
                    "widget": "text",
                    "placeholder": "merged_data"
                }
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.node_type = "merge_data"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process data merge node"""

        node_data = node_config.get('data', {})
        config = node_data.get('config', {})
        merge_sources = config.get('merge_sources', [])
        merge_strategy = config.get('merge_strategy', 'combine')
        output_key = config.get('output_key', 'merged_data')
        
        if not merge_sources:
            raise ValueError("Merge data node requires merge_sources")
        
        # Perform merge based on strategy
        try:
            merged_data = await self._merge_data_sources(merge_sources, merge_strategy, context)
            
            return {
                'success': True,
                output_key: merged_data,
                'sources_processed': len(merge_sources),
                'merge_strategy': merge_strategy
            }
            
        except Exception as e:
            logger.error(f"Data merge failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'sources_attempted': len(merge_sources)
            }
    
    async def _merge_data_sources(
        self, 
        sources: List[Union[str, Dict[str, Any]]], 
        strategy: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge data from multiple sources using specified strategy"""
        
        merged_data = {}
        
        for source in sources:
            source_data = await self._extract_source_data(source, context)
            
            if source_data is not None:
                merged_data = self._apply_merge_strategy(merged_data, source_data, strategy, source)
        
        return merged_data
    
    async def _extract_source_data(self, source: Union[str, Dict[str, Any]], context: Dict[str, Any]) -> Any:
        """Extract data from a source configuration"""
        
        if isinstance(source, str):
            # Simple context path
            return self._get_nested_value(context, source)
        
        elif isinstance(source, dict):
            # Complex source configuration
            if 'context_path' in source:
                data = self._get_nested_value(context, source['context_path'])
                
                # Apply transformations if specified
                if 'transformations' in source:
                    data = await self._apply_transformations(data, source['transformations'])
                
                return data
            
            elif 'literal' in source:
                # Literal data
                return source['literal']
            
            elif 'template' in source:
                # Template-based data
                template = source['template']
                try:
                    return template.format(**context)
                except KeyError as e:
                    logger.warning(f"Template formatting failed: {e}")
                    return template
            
            else:
                # Treat the dict itself as data
                return source
        
        return None
    
    def _apply_merge_strategy(
        self, 
        merged_data: Dict[str, Any], 
        source_data: Any, 
        strategy: str, 
        source_config: Union[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply merge strategy to combine data"""
        
        if strategy == 'combine':
            # Combine dictionaries, later sources override earlier ones
            if isinstance(source_data, dict):
                merged_data.update(source_data)
            else:
                # Use source name/path as key for non-dict data
                key = source_config if isinstance(source_config, str) else str(source_config)
                merged_data[key] = source_data
        
        elif strategy == 'override':
            # Complete override - replace merged_data with source_data
            if isinstance(source_data, dict):
                merged_data = {**merged_data, **source_data}
            else:
                key = source_config if isinstance(source_config, str) else str(source_config)
                merged_data = {key: source_data}
        
        elif strategy == 'append_lists':
            # Append to lists, combine dicts, override primitives
            if isinstance(source_data, dict):
                for key, value in source_data.items():
                    if key in merged_data:
                        if isinstance(merged_data[key], list) and isinstance(value, list):
                            merged_data[key].extend(value)
                        elif isinstance(merged_data[key], dict) and isinstance(value, dict):
                            merged_data[key].update(value)
                        else:
                            merged_data[key] = value
                    else:
                        merged_data[key] = value
            else:
                key = source_config if isinstance(source_config, str) else str(source_config)
                merged_data[key] = source_data
        
        elif strategy == 'preserve_existing':
            # Only add new keys, preserve existing values
            if isinstance(source_data, dict):
                for key, value in source_data.items():
                    if key not in merged_data:
                        merged_data[key] = value
            else:
                key = source_config if isinstance(source_config, str) else str(source_config)
                if key not in merged_data:
                    merged_data[key] = source_data
        
        elif strategy == 'nested_merge':
            # Deep merge for nested dictionaries
            if isinstance(source_data, dict):
                merged_data = self._deep_merge(merged_data, source_data)
            else:
                key = source_config if isinstance(source_config, str) else str(source_config)
                merged_data[key] = source_data
        
        else:
            logger.warning(f"Unknown merge strategy: {strategy}, using 'combine'")
            # Fallback to combine strategy
            if isinstance(source_data, dict):
                merged_data.update(source_data)
            else:
                key = source_config if isinstance(source_config, str) else str(source_config)
                merged_data[key] = source_data
        
        return merged_data
    
    def _deep_merge(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Perform deep merge of two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge(result[key], value)
                elif isinstance(result[key], list) and isinstance(value, list):
                    result[key] = result[key] + value
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    async def _apply_transformations(self, data: Any, transformations: List[Dict[str, Any]]) -> Any:
        """Apply data transformations"""
        
        for transformation in transformations:
            transform_type = transformation.get('type')
            
            if transform_type == 'filter_keys':
                # Filter dictionary keys
                if isinstance(data, dict):
                    allowed_keys = transformation.get('keys', [])
                    data = {k: v for k, v in data.items() if k in allowed_keys}
            
            elif transform_type == 'rename_keys':
                # Rename dictionary keys
                if isinstance(data, dict):
                    key_mapping = transformation.get('mapping', {})
                    data = {key_mapping.get(k, k): v for k, v in data.items()}
            
            elif transform_type == 'prefix_keys':
                # Add prefix to dictionary keys
                if isinstance(data, dict):
                    prefix = transformation.get('prefix', '')
                    data = {f"{prefix}{k}": v for k, v in data.items()}
            
            elif transform_type == 'flatten':
                # Flatten nested dictionary
                if isinstance(data, dict):
                    separator = transformation.get('separator', '_')
                    data = self._flatten_dict(data, separator)
            
            elif transform_type == 'extract_field':
                # Extract specific field from data
                field_path = transformation.get('field_path', '')
                if field_path:
                    data = self._get_nested_value({'data': data}, f'data.{field_path}')
        
        return data
    
    def _flatten_dict(self, d: Dict[str, Any], separator: str = '_', parent_key: str = '') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}{separator}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, separator, new_key).items())
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate merge data node inputs"""
        node_data = node_config.get('data', {})
        
        # Check required fields
        merge_sources = node_data.get('merge_sources', [])
        if not merge_sources or not isinstance(merge_sources, list):
            return False
        
        # Validate merge strategy
        valid_strategies = ['combine', 'override', 'append_lists', 'preserve_existing', 'nested_merge']
        merge_strategy = node_data.get('merge_strategy', 'combine')
        if merge_strategy not in valid_strategies:
            return False
        
        # Validate source configurations
        for source in merge_sources:
            if isinstance(source, dict):
                # Complex source must have at least one valid field
                valid_fields = ['context_path', 'literal', 'template']
                if not any(field in source for field in valid_fields):
                    return False
            elif not isinstance(source, str):
                return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for merge data node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        checkpoint.update({
            'merge_sources': node_data.get('merge_sources', []),
            'merge_strategy': node_data.get('merge_strategy', 'combine'),
            'output_key': node_data.get('output_key', 'merged_data'),
            'sources_count': len(node_data.get('merge_sources', []))
        })
        
        return checkpoint