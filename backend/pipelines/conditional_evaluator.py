"""
Conditional Rule Evaluator for Backend
Evaluates field conditional rules to determine visibility and requirements
"""
from typing import Dict, Any, List, Optional


class ConditionalRuleEvaluator:
    """Evaluates conditional rules for fields based on form data"""

    @staticmethod
    def evaluate_condition(rule: Dict[str, Any], form_data: Dict[str, Any]) -> bool:
        """
        Evaluate a single conditional rule against form data

        Args:
            rule: Single rule with 'field', 'condition', 'value'
            form_data: The submitted form data

        Returns:
            bool: Whether the condition is met
        """
        if not rule or 'field' not in rule or 'condition' not in rule:
            return False

        field_name = rule['field']
        condition = rule['condition']
        rule_value = rule.get('value')
        field_value = form_data.get(field_name)

        # Handle different condition types
        if condition == 'equals':
            return field_value == rule_value
        elif condition == 'not_equals':
            return field_value != rule_value
        elif condition == 'contains':
            return str(rule_value) in str(field_value or '')
        elif condition == 'not_contains':
            return str(rule_value) not in str(field_value or '')
        elif condition == 'greater_than':
            try:
                return float(field_value or 0) > float(rule_value)
            except (ValueError, TypeError):
                return False
        elif condition == 'less_than':
            try:
                return float(field_value or 0) < float(rule_value)
            except (ValueError, TypeError):
                return False
        elif condition == 'is_empty':
            return not field_value or field_value == '' or field_value is None
        elif condition == 'is_not_empty':
            return field_value and field_value != '' and field_value is not None
        elif condition == 'starts_with':
            return str(field_value or '').startswith(str(rule_value))
        elif condition == 'ends_with':
            return str(field_value or '').endswith(str(rule_value))
        else:
            return False

    @staticmethod
    def evaluate_rule_group(rule_group: Dict[str, Any], form_data: Dict[str, Any]) -> bool:
        """
        Evaluate a group of rules with AND/OR logic

        Args:
            rule_group: Dict with 'logic' (AND/OR) and 'rules' list
            form_data: The submitted form data

        Returns:
            bool: Whether the rule group conditions are met
        """
        if not rule_group or 'rules' not in rule_group:
            return True  # Empty rule group is considered true

        rules = rule_group.get('rules', [])
        if not rules:
            return True

        logic = rule_group.get('logic', 'OR')

        if logic == 'AND':
            # All rules must be true
            return all(
                ConditionalRuleEvaluator.evaluate_condition(rule, form_data)
                for rule in rules if rule
            )
        else:  # OR logic
            # At least one rule must be true
            return any(
                ConditionalRuleEvaluator.evaluate_condition(rule, form_data)
                for rule in rules if rule
            )

    @staticmethod
    def evaluate_field_requirements(field: 'Field', form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate conditional rules for a field to determine visibility and requirements

        Args:
            field: The Field model instance
            form_data: The submitted form data

        Returns:
            Dict with 'visible', 'required', and 'reason' keys
        """
        result = {
            'visible': True,
            'required': False,
            'reason': None
        }

        business_rules = field.business_rules or {}
        conditional_rules = business_rules.get('conditional_rules', {})

        if not conditional_rules:
            return result

        # Evaluate show_when conditions
        show_when = conditional_rules.get('show_when')
        if show_when:
            should_show = ConditionalRuleEvaluator.evaluate_rule_group(show_when, form_data)
            if not should_show:
                result['visible'] = False
                result['reason'] = 'Show conditions not met'
                return result

        # Evaluate hide_when conditions
        hide_when = conditional_rules.get('hide_when')
        if hide_when:
            should_hide = ConditionalRuleEvaluator.evaluate_rule_group(hide_when, form_data)
            if should_hide:
                result['visible'] = False
                result['reason'] = 'Hide condition triggered'
                return result

        # Evaluate require_when conditions
        require_when = conditional_rules.get('require_when')
        if require_when:
            should_require = ConditionalRuleEvaluator.evaluate_rule_group(require_when, form_data)
            if should_require:
                result['required'] = True

        return result