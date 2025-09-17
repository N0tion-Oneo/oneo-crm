"""
Enhanced condition evaluator with support for grouped conditions
"""
import operator
import logging
from typing import Dict, Any, List, Union, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class GroupedConditionEvaluator:
    """
    Evaluates conditions with support for groups.

    Supports conditions like:
    - Simple: [condition1, condition2] with AND/OR
    - Grouped: [(group1_cond1, group1_cond2), (group2_cond1)] with group operators
    - Complex: (A AND B) OR (C AND D) OR E
    """

    def __init__(self):
        """Initialize the condition evaluator"""
        self.operators = {
            # Equality operators
            'equals': operator.eq,
            'not_equals': operator.ne,

            # Comparison operators
            'greater_than': operator.gt,
            'greater_than_or_equal': operator.ge,
            'less_than': operator.lt,
            'less_than_or_equal': operator.le,

            # String operators
            'contains': lambda a, b: str(b).lower() in str(a).lower() if a is not None else False,
            'not_contains': lambda a, b: str(b).lower() not in str(a).lower() if a is not None else True,
            'starts_with': lambda a, b: str(a).lower().startswith(str(b).lower()) if a is not None else False,
            'ends_with': lambda a, b: str(a).lower().endswith(str(b).lower()) if a is not None else False,

            # Empty/null operators
            'is_empty': lambda a, b: a is None or str(a).strip() == '',
            'is_not_empty': lambda a, b: a is not None and str(a).strip() != '',
            'is_null': lambda a, b: a is None,
            'is_not_null': lambda a, b: a is not None,

            # Boolean operators
            'is_true': lambda a, b: bool(a),
            'is_false': lambda a, b: not bool(a),

            # Date operators (assuming dates are strings or datetime objects)
            'before': lambda a, b: self._compare_dates(a, b, 'before'),
            'after': lambda a, b: self._compare_dates(a, b, 'after'),
            'between': lambda a, b: self._compare_dates(a, b, 'between'),

            # Change operators (for update triggers)
            'changed': lambda a, b: True,  # Any change
            'changed_to': lambda a, b: a == b,
            'changed_from': lambda a, b: a == b,
            'increased_by': lambda a, b: isinstance(a, (int, float)) and a == b,
            'decreased_by': lambda a, b: isinstance(a, (int, float)) and a == b,
        }

    def evaluate(
        self,
        conditions: Union[List[Dict], Dict],
        data: Dict[str, Any],
        logic_operator: str = 'AND',
        group_operators: Optional[Dict[int, str]] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Evaluate conditions with optional grouping.

        Args:
            conditions: List of condition dicts OR nested group structure
            data: Data to evaluate against
            logic_operator: Top-level operator (AND/OR) for combining groups
            group_operators: Dict of group_id -> operator for each group

        Returns:
            Tuple of (result, details)
        """
        # Handle nested group structure (from new UI)
        if isinstance(conditions, dict) and 'logic' in conditions and 'conditions' in conditions:
            return self._evaluate_nested_group(conditions, data)

        # Handle flat list of conditions
        if not conditions:
            return False, {'message': 'No conditions to evaluate'}

        # Handle old-style groupId-based groups
        has_groups = any(c.get('groupId') is not None for c in conditions) if isinstance(conditions, list) else False

        if not has_groups:
            # Simple evaluation without groups
            return self._evaluate_simple(conditions, data, logic_operator)
        else:
            # Grouped evaluation
            return self._evaluate_grouped(conditions, data, logic_operator, group_operators or {})

    def _evaluate_simple(
        self,
        conditions: List[Dict],
        data: Dict[str, Any],
        logic_operator: str
    ) -> tuple[bool, Dict[str, Any]]:
        """Evaluate simple conditions without groups"""
        results = []
        details = []

        for condition in conditions:
            result, detail = self._evaluate_single_condition(condition, data)
            results.append(result)
            details.append(detail)

        if logic_operator == 'AND':
            final_result = all(results)
        else:  # OR
            final_result = any(results)

        return final_result, {
            'operator': logic_operator,
            'conditions_evaluated': len(conditions),
            'conditions_met': sum(results),
            'details': details
        }

    def _evaluate_nested_group(
        self,
        group: Dict[str, Any],
        data: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any]]:
        """Evaluate nested group structure from new UI"""
        logic = group.get('logic', 'AND')
        conditions_list = group.get('conditions', [])

        if not conditions_list:
            return False, {'message': 'Empty group'}

        results = []
        details = []

        for item in conditions_list:
            # Check if it's a nested group
            if isinstance(item, dict) and 'logic' in item and 'conditions' in item:
                # Recursively evaluate nested group
                result, detail = self._evaluate_nested_group(item, data)
                results.append(result)
                details.append({
                    'type': 'group',
                    'logic': item['logic'],
                    'result': result,
                    'details': detail
                })
            else:
                # It's a simple condition
                result, detail = self._evaluate_single_condition(item, data)
                results.append(result)
                details.append(detail)

        # Apply logic operator
        if logic == 'AND':
            final_result = all(results)
        else:  # OR
            final_result = any(results)

        return final_result, {
            'logic': logic,
            'conditions_evaluated': len(conditions_list),
            'conditions_met': sum(results),
            'details': details
        }

    def _evaluate_grouped(
        self,
        conditions: List[Dict],
        data: Dict[str, Any],
        logic_operator: str,
        group_operators: Dict[int, str]
    ) -> tuple[bool, Dict[str, Any]]:
        """Evaluate grouped conditions"""
        # Group conditions by groupId
        groups = {}
        for condition in conditions:
            group_id = condition.get('groupId', 0)
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(condition)

        # Evaluate each group
        group_results = []
        group_details = []

        for group_id, group_conditions in groups.items():
            group_op = group_operators.get(group_id, 'AND')
            group_result, group_detail = self._evaluate_simple(
                group_conditions, data, group_op
            )
            group_results.append(group_result)
            group_details.append({
                'group_id': group_id,
                'operator': group_op,
                'result': group_result,
                'details': group_detail
            })

        # Combine group results
        if logic_operator == 'AND':
            final_result = all(group_results)
        else:  # OR
            final_result = any(group_results)

        return final_result, {
            'operator': logic_operator,
            'groups_evaluated': len(groups),
            'groups_met': sum(group_results),
            'group_details': group_details
        }

    def _evaluate_single_condition(
        self,
        condition: Dict,
        data: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any]]:
        """Evaluate a single condition"""
        try:
            field = condition.get('field')
            op = condition.get('operator')
            expected_value = condition.get('value')

            # Get actual value from data
            actual_value = self._get_nested_value(data, field)

            # Special handling for operators that don't need values
            no_value_ops = ['is_empty', 'is_not_empty', 'is_null', 'is_not_null',
                           'is_true', 'is_false', 'changed']
            if op in no_value_ops:
                expected_value = None

            # Handle between operator (needs value_to)
            if op == 'between':
                value_to = condition.get('value_to')
                if value_to is not None:
                    expected_value = (expected_value, value_to)

            # Evaluate the condition
            if op in self.operators:
                result = self.operators[op](actual_value, expected_value)
            else:
                logger.warning(f"Unknown operator: {op}")
                result = False

            return result, {
                'field': field,
                'operator': op,
                'expected': expected_value,
                'actual': actual_value,
                'result': result
            }

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False, {
                'error': str(e),
                'condition': condition
            }

    def _get_nested_value(self, data: Dict, field_path: str) -> Any:
        """Get value from nested dict using dot notation"""
        if not field_path:
            return None

        keys = field_path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _compare_dates(self, actual: Any, expected: Any, comparison: str) -> bool:
        """Compare date values"""
        try:
            # Convert to datetime if string
            if isinstance(actual, str):
                actual = datetime.fromisoformat(actual.replace('Z', '+00:00'))
            if isinstance(expected, str):
                expected = datetime.fromisoformat(expected.replace('Z', '+00:00'))

            if comparison == 'before':
                return actual < expected
            elif comparison == 'after':
                return actual > expected
            elif comparison == 'between':
                if isinstance(expected, tuple) and len(expected) == 2:
                    start, end = expected
                    if isinstance(start, str):
                        start = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    if isinstance(end, str):
                        end = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    return start <= actual <= end
            return False

        except Exception as e:
            logger.error(f"Date comparison error: {e}")
            return False


# Singleton instance for easy import
condition_evaluator = GroupedConditionEvaluator()