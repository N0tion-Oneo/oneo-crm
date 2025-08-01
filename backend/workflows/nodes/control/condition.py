"""
Condition Node Processor - Conditional logic and branching
"""
import logging
from typing import Dict, Any, Union
from workflows.nodes.base import AsyncNodeProcessor

logger = logging.getLogger(__name__)


class ConditionProcessor(AsyncNodeProcessor):
    """Process conditional logic nodes for workflow branching"""
    
    def __init__(self):
        super().__init__()
        self.node_type = "CONDITION"
        self.supports_replay = True
        self.supports_checkpoints = True
    
    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process conditional logic node"""
        
        node_data = node_config.get('data', {})
        conditions = node_data.get('conditions', [])
        default_output = node_data.get('default_output', 'false')
        
        if not conditions:
            return {
                'output': default_output,
                'condition_met': False,
                'message': 'No conditions defined'
            }
        
        # Evaluate each condition
        for i, condition in enumerate(conditions):
            try:
                result = await self._evaluate_single_condition(condition, context)
                
                if result:
                    return {
                        'output': condition.get('output', 'true'),
                        'condition_met': True,
                        'matched_condition_index': i,
                        'matched_condition': condition,
                        'evaluation_details': self._get_evaluation_details(condition, context)
                    }
                    
            except Exception as e:
                logger.error(f"Error evaluating condition {i}: {e}")
                continue
        
        # No conditions matched
        return {
            'output': default_output,
            'condition_met': False,
            'total_conditions_evaluated': len(conditions)
        }
    
    async def _evaluate_single_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate a single condition"""
        
        # Get left side value
        left_config = condition.get('left', {})
        left_value = await self._resolve_condition_value(left_config, context)
        
        # Get operator
        operator = condition.get('operator', '==')
        
        # Get right side value
        right_config = condition.get('right')
        right_value = await self._resolve_condition_value(right_config, context)
        
        # Evaluate the condition
        return self._evaluate_condition(left_value, operator, right_value)
    
    async def _resolve_condition_value(self, value_config: Union[Dict, Any], context: Dict[str, Any]) -> Any:
        """Resolve a condition value from configuration"""
        
        if isinstance(value_config, dict):
            # Complex value configuration
            if 'context_path' in value_config:
                # Value from context path
                path = value_config['context_path']
                return self._get_nested_value(context, path)
            
            elif 'literal' in value_config:
                # Literal value
                return value_config['literal']
            
            elif 'function' in value_config:
                # Function call
                return await self._evaluate_function(value_config['function'], value_config.get('args', []), context)
            
            else:
                # Treat the dict itself as the value
                return value_config
        else:
            # Simple value - could be literal or template
            if isinstance(value_config, str) and value_config.startswith('{') and value_config.endswith('}'):
                # Template variable
                path = value_config[1:-1]  # Remove { }
                return self._get_nested_value(context, path)
            else:
                # Literal value
                return value_config
    
    def _evaluate_condition(self, left_value: Any, operator: str, right_value: Any) -> bool:
        """Evaluate condition with given operator"""
        
        try:
            if operator == '==':
                return left_value == right_value
            
            elif operator == '!=':
                return left_value != right_value
            
            elif operator == '>':
                return self._to_number(left_value) > self._to_number(right_value)
            
            elif operator == '>=':
                return self._to_number(left_value) >= self._to_number(right_value)
            
            elif operator == '<':
                return self._to_number(left_value) < self._to_number(right_value)
            
            elif operator == '<=':
                return self._to_number(left_value) <= self._to_number(right_value)
            
            elif operator == 'contains':
                return str(right_value).lower() in str(left_value).lower()
            
            elif operator == 'not_contains':
                return str(right_value).lower() not in str(left_value).lower()
            
            elif operator == 'starts_with':
                return str(left_value).startswith(str(right_value))
            
            elif operator == 'ends_with':
                return str(left_value).endswith(str(right_value))
            
            elif operator == 'in':
                if isinstance(right_value, (list, tuple)):
                    return left_value in right_value
                else:
                    return str(left_value) in str(right_value)
            
            elif operator == 'not_in':
                if isinstance(right_value, (list, tuple)):
                    return left_value not in right_value
                else:
                    return str(left_value) not in str(right_value)
            
            elif operator == 'exists':
                return left_value is not None and left_value != ''
            
            elif operator == 'not_exists':
                return left_value is None or left_value == ''
            
            elif operator == 'is_empty':
                if isinstance(left_value, (list, dict)):
                    return len(left_value) == 0
                return left_value is None or str(left_value).strip() == ''
            
            elif operator == 'is_not_empty':
                if isinstance(left_value, (list, dict)):
                    return len(left_value) > 0
                return left_value is not None and str(left_value).strip() != ''
            
            elif operator == 'regex_match':
                import re
                pattern = str(right_value)
                text = str(left_value)
                return bool(re.search(pattern, text))
            
            elif operator == 'length_eq':
                return len(str(left_value)) == self._to_number(right_value)
            
            elif operator == 'length_gt':
                return len(str(left_value)) > self._to_number(right_value)
            
            elif operator == 'length_lt':
                return len(str(left_value)) < self._to_number(right_value)
            
            else:
                logger.warning(f"Unknown condition operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _to_number(self, value: Any) -> Union[int, float]:
        """Convert value to number"""
        if isinstance(value, (int, float)):
            return value
        
        try:
            # Try integer first
            return int(value)
        except (ValueError, TypeError):
            try:
                # Try float
                return float(value)
            except (ValueError, TypeError):
                # Default to 0 for non-numeric values
                return 0
    
    async def _evaluate_function(self, function_name: str, args: list, context: Dict[str, Any]) -> Any:
        """Evaluate a function call in condition"""
        
        if function_name == 'len':
            if args:
                value = await self._resolve_condition_value(args[0], context)
                return len(str(value)) if value is not None else 0
        
        elif function_name == 'lower':
            if args:
                value = await self._resolve_condition_value(args[0], context)
                return str(value).lower() if value is not None else ''
        
        elif function_name == 'upper':
            if args:
                value = await self._resolve_condition_value(args[0], context)
                return str(value).upper() if value is not None else ''
        
        elif function_name == 'now':
            from django.utils import timezone
            return timezone.now().isoformat()
        
        elif function_name == 'today':
            from django.utils import timezone
            return timezone.now().date().isoformat()
        
        elif function_name == 'count':
            if args:
                value = await self._resolve_condition_value(args[0], context)
                if isinstance(value, (list, dict)):
                    return len(value)
                return 1 if value is not None else 0
        
        else:
            logger.warning(f"Unknown function in condition: {function_name}")
            return None
    
    def _get_evaluation_details(self, condition: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about condition evaluation"""
        return {
            'left_value': self._get_nested_value(context, condition.get('left', {}).get('context_path', '')),
            'operator': condition.get('operator'),
            'right_value': condition.get('right'),
            'expected_output': condition.get('output', 'true')
        }
    
    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate condition node inputs"""
        node_data = node_config.get('data', {})
        conditions = node_data.get('conditions', [])
        
        if not conditions:
            return False
        
        # Validate each condition
        for condition in conditions:
            if not isinstance(condition, dict):
                return False
            
            # Check required fields
            if 'operator' not in condition:
                return False
            
            # Validate operator
            valid_operators = [
                '==', '!=', '>', '>=', '<', '<=',
                'contains', 'not_contains', 'starts_with', 'ends_with',
                'in', 'not_in', 'exists', 'not_exists',
                'is_empty', 'is_not_empty', 'regex_match',
                'length_eq', 'length_gt', 'length_lt'
            ]
            
            if condition['operator'] not in valid_operators:
                return False
        
        return True
    
    async def create_checkpoint(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for condition node"""
        checkpoint = await super().create_checkpoint(node_config, context)
        
        node_data = node_config.get('data', {})
        checkpoint.update({
            'conditions_count': len(node_data.get('conditions', [])),
            'default_output': node_data.get('default_output', 'false'),
            'context_snapshot_for_evaluation': {
                key: value for key, value in context.items() 
                if not key.startswith('_') and isinstance(value, (str, int, float, bool, list, dict))
            }
        })
        
        return checkpoint