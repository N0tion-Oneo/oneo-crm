"""
Base node processor for workflow execution with support for reusable workflows
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from django.utils import timezone
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class BaseNodeProcessor(ABC):
    """Base class for all node processors"""

    # Configuration schema - override in subclasses
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self):
        # Use the class attribute if defined, otherwise None
        self.node_type = getattr(self.__class__, 'node_type', None)
        self.supports_replay = True
        self.supports_checkpoints = True
    
    @abstractmethod
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a node with given configuration and context

        Args:
            node_config: Node configuration from workflow definition
            context: Current execution context

        Returns:
            Dict containing node output data
        """
        pass

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Get the configuration schema for this node type

        Returns:
            JSON schema for node configuration
        """
        return cls.CONFIG_SCHEMA

    @classmethod
    def get_required_fields(cls) -> list:
        """
        Get list of required fields from schema

        Returns:
            List of required field names
        """
        return cls.CONFIG_SCHEMA.get('required', [])

    @classmethod
    def get_optional_fields(cls) -> list:
        """
        Get list of optional fields from schema

        Returns:
            List of optional field names
        """
        properties = cls.CONFIG_SCHEMA.get('properties', {})
        required = set(cls.get_required_fields())
        return [field for field in properties.keys() if field not in required]
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Validate node inputs before processing using schema

        Args:
            node_config: Node configuration
            context: Execution context

        Returns:
            True if inputs are valid, False otherwise
        """
        try:
            # Get the node's configuration data
            config_data = node_config.get('data', {}).get('config', {})

            # Check required fields from schema
            required_fields = self.get_required_fields()
            for field in required_fields:
                if field not in config_data:
                    logger.warning(f"Required field '{field}' missing in {self.node_type} configuration")
                    return False

            # Validate field types if specified in schema
            properties = self.CONFIG_SCHEMA.get('properties', {})
            for field_name, field_value in config_data.items():
                if field_name in properties:
                    field_schema = properties[field_name]
                    if not self._validate_field_type(field_name, field_value, field_schema):
                        logger.warning(f"Field '{field_name}' validation failed in {self.node_type}")
                        return False

            return True
        except Exception as e:
            logger.error(f"Validation error in {self.node_type}: {e}")
            return False

    def _validate_field_type(self, field_name: str, value: Any, field_schema: Dict[str, Any]) -> bool:
        """
        Validate a field value against its schema

        Args:
            field_name: Name of the field being validated
            value: Field value to validate
            field_schema: Field schema definition

        Returns:
            True if valid, False otherwise
        """
        field_type = field_schema.get('type', 'string')

        # Handle null values
        if value is None:
            return field_schema.get('nullable', False)

        # Type validation
        if field_type == 'string':
            # Accept integers for ID fields and convert them
            if isinstance(value, int):
                # Allow integers for fields that look like IDs
                if 'id' in field_name.lower() or field_name in ['pipeline', 'workflow', 'user', 'tenant']:
                    return True
            if not isinstance(value, str):
                return False
            # Check string constraints
            if 'minLength' in field_schema and len(value) < field_schema['minLength']:
                return False
            if 'maxLength' in field_schema and len(value) > field_schema['maxLength']:
                return False
            if 'enum' in field_schema and value not in field_schema['enum']:
                return False

        elif field_type == 'number' or field_type == 'integer':
            if not isinstance(value, (int, float)):
                return False
            if field_type == 'integer' and not isinstance(value, int):
                return False
            # Check number constraints
            if 'minimum' in field_schema and value < field_schema['minimum']:
                return False
            if 'maximum' in field_schema and value > field_schema['maximum']:
                return False

        elif field_type == 'boolean':
            if not isinstance(value, bool):
                return False

        elif field_type == 'array':
            if not isinstance(value, list):
                return False
            # Check array constraints
            if 'minItems' in field_schema and len(value) < field_schema['minItems']:
                return False
            if 'maxItems' in field_schema and len(value) > field_schema['maxItems']:
                return False

        elif field_type == 'object':
            if not isinstance(value, dict):
                return False

        return True
    
    async def prepare_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare and transform inputs for node processing
        
        Args:
            node_config: Node configuration
            context: Execution context
            
        Returns:
            Prepared input data
        """
        input_mapping = node_config.get('data', {}).get('input_mapping', {})
        prepared_inputs = {}
        
        for input_key, context_path in input_mapping.items():
            value = self._get_nested_value(context, context_path)
            if value is not None:
                prepared_inputs[input_key] = value
        
        return prepared_inputs
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create checkpoint data for replay functionality
        
        Args:
            node_config: Node configuration
            context: Current execution context
            
        Returns:
            Checkpoint data
        """
        if not self.supports_checkpoints:
            return {}
        
        return {
            'node_id': node_config.get('id'),
            'node_type': self.node_type,
            'context_snapshot': context.copy(),
            'timestamp': timezone.now().isoformat()
        }
    
    async def restore_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore execution state from checkpoint data
        
        Args:
            checkpoint_data: Previously saved checkpoint data
            
        Returns:
            Restored context
        """
        if not self.supports_replay:
            raise ValueError(f"Node type {self.node_type} does not support replay")
        
        return checkpoint_data.get('context_snapshot', {})
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get nested value from dictionary using dot notation

        Args:
            data: Dictionary to search
            path: Dot-notation path (e.g., 'user.profile.name')

        Returns:
            Found value or None
        """
        if not path:
            return None

        # Handle template variables like {{trigger_data.contact_email}} or {trigger_data.contact_email}
        if path.startswith('{{') and path.endswith('}}'):
            path = path[2:-2].strip()
        elif path.startswith('{') and path.endswith('}'):
            path = path[1:-1].strip()
        
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set nested value in dictionary using dot notation

        Args:
            data: Dictionary to modify
            path: Dot-notation path
            value: Value to set
        """
        keys = path.split('.')
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def format_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        Format template string with context variables

        Supports {variable.path} syntax with nested path resolution.
        This is the standard template format for all workflow nodes.

        Args:
            template: Template string with {variable.path} placeholders
            context: Context dictionary with nested values

        Returns:
            Formatted string with variables replaced
        """
        if not template:
            return ''

        import re

        # Find all template variables in {var.path} format
        pattern = r'\{([^}]+)\}'

        def replace_variable(match):
            var_path = match.group(1).strip()

            # Use _get_nested_value to resolve the path
            value = self._get_nested_value(context, var_path)

            if value is not None:
                return str(value)
            else:
                # Keep the original template if variable not found
                logger.warning(f"Template variable not found in context: {var_path}")
                return match.group(0)

        try:
            # Replace all template variables
            result = re.sub(pattern, replace_variable, template)
            return result
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return template
    
    async def log_execution(self, node_config: Dict[str, Any], result: Dict[str, Any], 
                          execution_time_ms: int, success: bool, error: Optional[str] = None):
        """
        Log node execution for monitoring and debugging
        
        Args:
            node_config: Node configuration
            result: Execution result
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
            error: Error message if execution failed
        """
        log_data = {
            'node_id': node_config.get('id'),
            'node_type': self.node_type,
            'execution_time_ms': execution_time_ms,
            'success': success,
            'timestamp': timezone.now().isoformat()
        }
        
        if error:
            log_data['error'] = error
        
        if success:
            logger.info(f"Node {node_config.get('id')} executed successfully in {execution_time_ms}ms")
        else:
            logger.error(f"Node {node_config.get('id')} failed: {error}")
    
    async def handle_error(self, node_config: Dict[str, Any], context: Dict[str, Any], 
                          error: Exception) -> Dict[str, Any]:
        """
        Handle node execution errors
        
        Args:
            node_config: Node configuration
            context: Execution context
            error: The exception that occurred
            
        Returns:
            Error result data
        """
        error_result = {
            'success': False,
            'error': str(error),
            'error_type': type(error).__name__,
            'node_id': node_config.get('id'),
            'node_type': self.node_type
        }
        
        # Check if node has error handling configuration
        error_handling = node_config.get('data', {}).get('error_handling', {})
        
        if error_handling.get('continue_on_error', False):
            error_result['continue_execution'] = True
        
        if error_handling.get('retry_count', 0) > 0:
            error_result['retry_config'] = {
                'max_retries': error_handling['retry_count'],
                'retry_delay_ms': error_handling.get('retry_delay_ms', 1000)
            }
        
        return error_result


class AsyncNodeProcessor(BaseNodeProcessor):
    """Base class for async node processors with built-in timing and error handling"""
    
    async def execute(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute node with timing, validation, and error handling
        
        Args:
            node_config: Node configuration
            context: Execution context
            
        Returns:
            Node execution result
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not await self.validate_inputs(node_config, context):
                raise ValueError("Node input validation failed")
            
            # Create checkpoint if supported
            checkpoint = None
            if self.supports_checkpoints:
                checkpoint = await self.create_checkpoint(node_config, context)
            
            # Process the node - extract config data for process method
            config_data = node_config.get('data', {}).get('config', {})
            result = await self.process(config_data, context)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Log successful execution
            await self.log_execution(node_config, result, execution_time_ms, True)
            
            # Add metadata to result, preserving the success value from the processor
            result.update({
                'execution_time_ms': execution_time_ms,
                'node_id': node_config.get('id'),
                'checkpoint': checkpoint
            })

            # Only set success to True if it wasn't already set by the processor
            if 'success' not in result:
                result['success'] = True
            
            return result
            
        except Exception as error:
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Log failed execution
            await self.log_execution(node_config, {}, execution_time_ms, False, str(error))
            
            # Handle error
            error_result = await self.handle_error(node_config, context, error)
            error_result['execution_time_ms'] = execution_time_ms
            
            return error_result