"""
Workflow Loop Controller Node - Control workflow stage iterations and loops
"""
import logging
from typing import Dict, Any, Optional, List
from workflows.nodes.base import AsyncNodeProcessor
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WorkflowLoopController(AsyncNodeProcessor):
    """Control workflow loops and stage iterations"""

    def __init__(self):
        super().__init__()
        self.node_type = "WORKFLOW_LOOP_CONTROLLER"
        self.supports_replay = True
        self.supports_checkpoints = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process workflow loop control"""

        node_data = node_config.get('data', {})

        # Loop configuration
        loop_key = node_data.get('loop_key', 'default_loop')
        max_iterations = node_data.get('max_iterations', 10)
        exit_conditions = node_data.get('exit_conditions', [])
        loop_type = node_data.get('loop_type', 'conditional')  # conditional, count_based, time_based

        # Initialize or get loop state
        loop_state = self._get_or_initialize_loop_state(context, loop_key)

        # Increment iteration count
        loop_state['current_iteration'] += 1
        loop_state['last_iteration_time'] = timezone.now().isoformat()

        # Check if we should continue looping
        should_continue, exit_reason = await self._evaluate_loop_continuation(
            loop_state,
            max_iterations,
            exit_conditions,
            loop_type,
            node_data,
            context
        )

        # Update loop state in context
        if 'workflow_loops' not in context:
            context['workflow_loops'] = {}
        context['workflow_loops'][loop_key] = loop_state

        # Set workflow control flags
        context['should_loop'] = should_continue
        context['loop_iteration'] = loop_state['current_iteration']
        context['loop_exit_reason'] = exit_reason

        # Determine next workflow path
        if should_continue:
            next_path = node_data.get('loop_back_to', 'loop_start')
            action = 'continue_loop'
        else:
            next_path = node_data.get('exit_to', 'loop_exit')
            action = 'exit_loop'

        return {
            'success': True,
            'loop_key': loop_key,
            'current_iteration': loop_state['current_iteration'],
            'max_iterations': max_iterations,
            'should_continue': should_continue,
            'exit_reason': exit_reason,
            'action': action,
            'next_workflow_path': next_path,
            'loop_duration_seconds': self._calculate_loop_duration(loop_state),
            'iterations_remaining': max_iterations - loop_state['current_iteration'] if should_continue else 0
        }

    def _get_or_initialize_loop_state(self, context: Dict, loop_key: str) -> Dict[str, Any]:
        """Get existing loop state or initialize new one"""

        if 'workflow_loops' not in context:
            context['workflow_loops'] = {}

        if loop_key not in context['workflow_loops']:
            context['workflow_loops'][loop_key] = {
                'current_iteration': 0,
                'start_time': timezone.now().isoformat(),
                'last_iteration_time': timezone.now().isoformat(),
                'exit_checks': [],
                'custom_data': {}
            }

        return context['workflow_loops'][loop_key]

    async def _evaluate_loop_continuation(
        self,
        loop_state: Dict,
        max_iterations: int,
        exit_conditions: List[Dict],
        loop_type: str,
        node_data: Dict,
        context: Dict
    ) -> tuple[bool, str]:
        """Evaluate whether to continue the loop"""

        # Check max iterations
        if loop_state['current_iteration'] >= max_iterations:
            return False, 'max_iterations_reached'

        # Check loop type specific conditions
        if loop_type == 'count_based':
            # Simple count-based loop
            target_count = node_data.get('target_count', max_iterations)
            if loop_state['current_iteration'] >= target_count:
                return False, 'target_count_reached'

        elif loop_type == 'time_based':
            # Time-based loop
            max_duration_minutes = node_data.get('max_duration_minutes', 60)
            start_time = datetime.fromisoformat(loop_state['start_time'].replace('Z', '+00:00'))
            elapsed = (timezone.now() - start_time).total_seconds() / 60
            if elapsed >= max_duration_minutes:
                return False, 'max_duration_exceeded'

        # Check exit conditions
        for condition in exit_conditions:
            condition_type = condition.get('type')
            condition_met = False

            if condition_type == 'context_value':
                # Check if a context value matches expected
                path = condition.get('path', '')
                expected = condition.get('expected_value')
                operator = condition.get('operator', 'equals')
                actual = self._get_nested_value(context, path)
                condition_met = self._compare_values(actual, expected, operator)

            elif condition_type == 'evaluation_result':
                # Check evaluation results from AI Response Evaluator
                if 'evaluation_outcome' in context:
                    outcome = context['evaluation_outcome']
                    if outcome.get('recommended_action') == condition.get('action'):
                        condition_met = True
                    if not outcome.get('continue_conversation', True):
                        condition_met = True

            elif condition_type == 'flag_set':
                # Check if specific flags are set
                flag_name = condition.get('flag_name')
                if 'conversation_flags' in context:
                    condition_met = context['conversation_flags'].get(flag_name, False)

            elif condition_type == 'custom_function':
                # Evaluate custom condition function
                condition_met = await self._evaluate_custom_condition(condition, context)

            if condition_met:
                exit_reason = condition.get('reason', f'condition_{condition_type}_met')
                loop_state['exit_checks'].append({
                    'iteration': loop_state['current_iteration'],
                    'condition': condition_type,
                    'reason': exit_reason
                })
                return False, exit_reason

        # Default: continue looping
        return True, 'continuing'

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get nested value from object using dot notation"""
        if not path:
            return None

        keys = path.split('.')
        value = obj

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _compare_values(self, actual: Any, expected: Any, operator: str) -> bool:
        """Compare values based on operator"""

        try:
            if operator == 'equals':
                return actual == expected
            elif operator == 'not_equals':
                return actual != expected
            elif operator == 'greater_than':
                return float(actual) > float(expected)
            elif operator == 'less_than':
                return float(actual) < float(expected)
            elif operator == 'contains':
                return expected in str(actual)
            elif operator == 'not_contains':
                return expected not in str(actual)
            elif operator == 'is_true':
                return bool(actual) is True
            elif operator == 'is_false':
                return bool(actual) is False
            elif operator == 'is_null':
                return actual is None
            elif operator == 'is_not_null':
                return actual is not None
            else:
                return False
        except (ValueError, TypeError):
            return False

    async def _evaluate_custom_condition(self, condition: Dict, context: Dict) -> bool:
        """Evaluate custom condition function"""

        # This could be extended to support custom Python expressions
        # or integration with external condition evaluators
        expression = condition.get('expression', '')

        if not expression:
            return False

        try:
            # Simple expression evaluation with context
            # In production, use a safe expression evaluator
            result = eval(expression, {'context': context})
            return bool(result)
        except Exception as e:
            logger.warning(f"Custom condition evaluation failed: {e}")
            return False

    def _calculate_loop_duration(self, loop_state: Dict) -> float:
        """Calculate total loop duration in seconds"""

        try:
            start_time = datetime.fromisoformat(loop_state['start_time'].replace('Z', '+00:00'))
            return (timezone.now() - start_time).total_seconds()
        except Exception:
            return 0

    async def validate_inputs(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Validate node inputs"""
        node_data = node_config.get('data', {})

        # Check max iterations is reasonable
        max_iterations = node_data.get('max_iterations', 10)
        if max_iterations < 1 or max_iterations > 100:
            return False

        # Check loop type
        valid_types = ['conditional', 'count_based', 'time_based']
        if node_data.get('loop_type', 'conditional') not in valid_types:
            return False

        return True


class WorkflowLoopBreaker(AsyncNodeProcessor):
    """Break out of a workflow loop early"""

    def __init__(self):
        super().__init__()
        self.node_type = "WORKFLOW_LOOP_BREAKER"
        self.supports_replay = True

    async def process(self, node_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process loop break"""

        node_data = node_config.get('data', {})
        loop_key = node_data.get('loop_key', 'default_loop')
        break_reason = node_data.get('reason', 'manual_break')

        # Set loop control flags
        context['should_loop'] = False
        context['loop_exit_reason'] = break_reason

        # Update loop state if exists
        if 'workflow_loops' in context and loop_key in context['workflow_loops']:
            loop_state = context['workflow_loops'][loop_key]
            loop_state['exit_checks'].append({
                'iteration': loop_state.get('current_iteration', 0),
                'condition': 'manual_break',
                'reason': break_reason
            })

        return {
            'success': True,
            'action': 'break_loop',
            'loop_key': loop_key,
            'break_reason': break_reason,
            'next_workflow_path': node_data.get('exit_to', 'loop_exit')
        }