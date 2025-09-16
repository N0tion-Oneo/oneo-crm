import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { GitBranch, Code, Settings } from 'lucide-react';

export const ConditionNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.CONDITION,
  label: 'Condition',
  description: 'Branch workflow based on conditions',
  icon: GitBranch,
  category: 'control',

  sections: [
    {
      id: 'condition',
      label: 'Condition Configuration',
      icon: GitBranch,
      fields: [
        {
          key: 'condition_type',
          label: 'Condition Type',
          type: 'select',
          required: true,
          defaultValue: 'simple',
          options: [
            { label: 'Simple Condition', value: 'simple', description: 'Single field comparison' },
            { label: 'Expression', value: 'expression', description: 'JavaScript expression' },
            { label: 'Multiple Conditions', value: 'multiple', description: 'Complex logic with AND/OR' }
          ],
          helpText: 'Choose how to define your condition'
        },
        {
          key: 'field_type',
          label: 'Field Source',
          type: 'select',
          required: true,
          showWhen: (c) => c.condition_type === 'simple',
          defaultValue: 'variable',
          options: [
            { label: 'Variable/Expression', value: 'variable' },
            { label: 'Pipeline Field', value: 'pipeline_field' }
          ],
          helpText: 'Choose field source type'
        },
        {
          key: 'field',
          label: 'Field Expression',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: '{{record.status}}',
          showWhen: (c) => c.condition_type === 'simple' && (!c.field_type || c.field_type === 'variable'),
          helpText: 'The field or variable to check'
        },
        {
          key: 'field',
          label: 'Select Field',
          type: 'field',
          required: true,
          placeholder: 'Select a field',
          showWhen: (c) => c.condition_type === 'simple' && c.field_type === 'pipeline_field',
          helpText: 'Choose a field from the pipeline'
        },
        {
          key: 'operator',
          label: 'Operator',
          type: 'select',
          required: true,
          showWhen: (c) => c.condition_type === 'simple',
          options: [
            { label: 'Equals', value: 'equals' },
            { label: 'Not Equals', value: 'not_equals' },
            { label: 'Contains', value: 'contains' },
            { label: 'Does Not Contain', value: 'not_contains' },
            { label: 'Starts With', value: 'starts_with' },
            { label: 'Ends With', value: 'ends_with' },
            { label: 'Greater Than', value: 'greater_than' },
            { label: 'Less Than', value: 'less_than' },
            { label: 'Greater or Equal', value: 'greater_or_equal' },
            { label: 'Less or Equal', value: 'less_or_equal' },
            { label: 'Is Empty', value: 'is_empty' },
            { label: 'Is Not Empty', value: 'is_not_empty' },
            { label: 'Is Null', value: 'is_null' },
            { label: 'Is Not Null', value: 'is_not_null' },
            { label: 'Matches Regex', value: 'matches_regex' },
            { label: 'In List', value: 'in_list' },
            { label: 'Not In List', value: 'not_in_list' }
          ],
          helpText: 'How to compare the values'
        },
        {
          key: 'value_type',
          label: 'Value Type',
          type: 'select',
          showWhen: (c) => c.condition_type === 'simple' &&
                          !['is_empty', 'is_not_empty', 'is_null', 'is_not_null'].includes(c.operator),
          defaultValue: 'static',
          options: [
            { label: 'Static Value', value: 'static' },
            { label: 'Field Option', value: 'field_option' },
            { label: 'Variable/Expression', value: 'variable' }
          ],
          helpText: 'How to specify the comparison value'
        },
        {
          key: 'value',
          label: 'Value',
          type: 'text',
          allowExpressions: false,
          placeholder: 'Enter value',
          showWhen: (c) => c.condition_type === 'simple' &&
                          !['is_empty', 'is_not_empty', 'is_null', 'is_not_null'].includes(c.operator) &&
                          (!c.value_type || c.value_type === 'static'),
          helpText: 'The value to compare against'
        },
        {
          key: 'value',
          label: 'Variable/Expression',
          type: 'text',
          allowExpressions: true,
          placeholder: '{{variable}} or expression',
          showWhen: (c) => c.condition_type === 'simple' &&
                          !['is_empty', 'is_not_empty', 'is_null', 'is_not_null'].includes(c.operator) &&
                          c.value_type === 'variable',
          helpText: 'Variable or expression for comparison'
        },
        {
          key: 'value',
          label: 'Field Option Value',
          type: 'field-value',
          fieldSource: 'field',
          placeholder: 'Select option',
          showWhen: (c) => {
            const show = c.condition_type === 'simple' &&
                          !['is_empty', 'is_not_empty', 'is_null', 'is_not_null'].includes(c.operator) &&
                          c.value_type === 'field_option' &&
                          c.field_type === 'pipeline_field';
            console.log('Field-value showWhen check:', {
              condition_type: c.condition_type,
              operator: c.operator,
              value_type: c.value_type,
              field_type: c.field_type,
              shouldShow: show
            });
            return show;
          },
          helpText: 'Select from field options'
        },
        {
          key: 'case_sensitive',
          label: 'Case Sensitive',
          type: 'boolean',
          defaultValue: false,
          showWhen: (c) => c.condition_type === 'simple' && 
                          ['equals', 'not_equals', 'contains', 'not_contains', 'starts_with', 'ends_with'].includes(c.operator),
          helpText: 'Perform case-sensitive comparison'
        },
        {
          key: 'expression',
          label: 'Expression',
          type: 'code',
          required: true,
          allowExpressions: true,
          placeholder: '// JavaScript expression that returns true/false\n{{record.amount}} > 100 && {{record.status}} === "active"',
          showWhen: (c) => c.condition_type === 'expression',
          helpText: 'JavaScript expression that evaluates to true or false',
          rows: 8
        },
        {
          key: 'conditions',
          label: 'Conditions',
          type: 'json',
          required: true,
          showWhen: (c) => c.condition_type === 'multiple',
          placeholder: '[\n  {\n    "field": "{{record.status}}",\n    "operator": "equals",\n    "value": "active"\n  },\n  {\n    "field": "{{record.amount}}",\n    "operator": "greater_than",\n    "value": 100\n  }\n]',
          helpText: 'Array of condition objects',
          rows: 10
        },
        {
          key: 'logic_operator',
          label: 'Logic Operator',
          type: 'select',
          defaultValue: 'AND',
          showWhen: (c) => c.condition_type === 'multiple',
          options: [
            { label: 'AND (All conditions must be true)', value: 'AND' },
            { label: 'OR (Any condition can be true)', value: 'OR' }
          ],
          helpText: 'How to combine multiple conditions'
        }
      ]
    },
    {
      id: 'branching',
      label: 'Branching',
      icon: GitBranch,
      fields: [
        {
          key: 'true_label',
          label: 'True Branch Label',
          type: 'text',
          defaultValue: 'True',
          placeholder: 'Label for true branch',
          helpText: 'Display name for the true branch'
        },
        {
          key: 'false_label',
          label: 'False Branch Label',
          type: 'text',
          defaultValue: 'False',
          placeholder: 'Label for false branch',
          helpText: 'Display name for the false branch'
        },
        {
          key: 'default_branch',
          label: 'Default Branch',
          type: 'select',
          defaultValue: 'false',
          options: [
            { label: 'True Branch', value: 'true' },
            { label: 'False Branch', value: 'false' },
            { label: 'Stop Workflow', value: 'stop' }
          ],
          helpText: 'Which branch to take if condition evaluation fails'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Settings',
      icon: Settings,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'evaluate_null_as_false',
          label: 'Treat Null as False',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Treat null/undefined values as false'
        },
        {
          key: 'stop_on_error',
          label: 'Stop on Error',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Stop workflow if condition evaluation errors'
        },
        {
          key: 'log_evaluation',
          label: 'Log Evaluation',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Log condition evaluation for debugging'
        },
        {
          key: 'timeout_seconds',
          label: 'Evaluation Timeout (seconds)',
          type: 'number',
          defaultValue: 5,
          min: 1,
          max: 30,
          helpText: 'Maximum time for condition evaluation'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.condition_type) {
      errors.condition_type = 'Condition type is required';
    }

    if (config.condition_type === 'simple') {
      if (!config.field) {
        errors.field = 'Field is required';
      }
      if (!config.operator) {
        errors.operator = 'Operator is required';
      }
      if (!['is_empty', 'is_not_empty', 'is_null', 'is_not_null'].includes(config.operator) && !config.value) {
        errors.value = 'Value is required for this operator';
      }
    }

    if (config.condition_type === 'expression' && !config.expression) {
      errors.expression = 'Expression is required';
    }

    if (config.condition_type === 'multiple') {
      if (!config.conditions) {
        errors.conditions = 'Conditions are required';
      } else {
        try {
          if (typeof config.conditions === 'string') {
            const parsed = JSON.parse(config.conditions);
            if (!Array.isArray(parsed)) {
              errors.conditions = 'Conditions must be an array';
            }
          }
        } catch {
          errors.conditions = 'Conditions must be valid JSON array';
        }
      }
    }

    return errors;
  },

  defaults: {
    condition_type: 'simple',
    field_type: 'variable',
    value_type: 'static',
    operator: 'equals',
    case_sensitive: false,
    logic_operator: 'AND',
    true_label: 'True',
    false_label: 'False',
    default_branch: 'false',
    evaluate_null_as_false: true,
    stop_on_error: false,
    log_evaluation: false,
    timeout_seconds: 5
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};