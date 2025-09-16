import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { GitBranch, Clock } from 'lucide-react';

export const WaitForConditionNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.WAIT_FOR_CONDITION,
  label: 'Wait for Condition',
  description: 'Wait for a complex condition to be met',
  icon: GitBranch,
  category: 'control',

  sections: [
    {
      id: 'condition_config',
      label: 'Condition Configuration',
      icon: GitBranch,
      fields: [
        {
          key: 'condition_type',
          label: 'Condition Type',
          type: 'select',
          required: true,
          defaultValue: 'expression',
          options: [
            { label: 'Expression', value: 'expression' },
            { label: 'Record Count', value: 'record_count' },
            { label: 'Aggregate Value', value: 'aggregate' }
          ],
          helpText: 'Type of condition to evaluate'
        },
        {
          key: 'expression',
          label: 'Condition Expression',
          type: 'textarea',
          required: true,
          showWhen: (c) => c.condition_type === 'expression',
          placeholder: 'context.total_amount > 1000 and context.status == "approved"',
          helpText: 'JavaScript expression to evaluate (has access to context)'
        },
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'text',
          required: true,
          showWhen: (c) => c.condition_type === 'record_count' || c.condition_type === 'aggregate',
          allowExpressions: true,
          placeholder: '{{pipeline_id}}',
          helpText: 'Pipeline to query records from'
        },
        {
          key: 'filter_conditions',
          label: 'Filter Conditions',
          type: 'json',
          showWhen: (c) => c.condition_type === 'record_count' || c.condition_type === 'aggregate',
          defaultValue: {},
          placeholder: '{"status": "active", "priority": "high"}',
          helpText: 'JSON object with field filters'
        },
        {
          key: 'expected_count',
          label: 'Expected Count',
          type: 'number',
          required: true,
          showWhen: (c) => c.condition_type === 'record_count',
          min: 0,
          defaultValue: 1,
          helpText: 'Expected number of records'
        },
        {
          key: 'count_operator',
          label: 'Count Comparison',
          type: 'select',
          required: true,
          showWhen: (c) => c.condition_type === 'record_count',
          defaultValue: 'greater_than',
          options: [
            { label: 'Equals', value: 'equals' },
            { label: 'Greater Than', value: 'greater_than' },
            { label: 'Less Than', value: 'less_than' },
            { label: 'Greater or Equal', value: 'greater_or_equal' },
            { label: 'Less or Equal', value: 'less_or_equal' }
          ],
          helpText: 'How to compare record count'
        },
        {
          key: 'aggregate_field',
          label: 'Aggregate Field',
          type: 'text',
          required: true,
          showWhen: (c) => c.condition_type === 'aggregate',
          placeholder: 'amount, score, quantity',
          helpText: 'Field to aggregate'
        },
        {
          key: 'aggregate_function',
          label: 'Aggregate Function',
          type: 'select',
          required: true,
          showWhen: (c) => c.condition_type === 'aggregate',
          defaultValue: 'sum',
          options: [
            { label: 'Sum', value: 'sum' },
            { label: 'Average', value: 'avg' },
            { label: 'Minimum', value: 'min' },
            { label: 'Maximum', value: 'max' },
            { label: 'Count', value: 'count' }
          ],
          helpText: 'Aggregation function to apply'
        },
        {
          key: 'aggregate_expected',
          label: 'Expected Value',
          type: 'number',
          required: true,
          showWhen: (c) => c.condition_type === 'aggregate',
          defaultValue: 0,
          helpText: 'Expected aggregate value (condition met when result >= this value)'
        }
      ]
    },
    {
      id: 'timing_config',
      label: 'Timing Configuration',
      icon: Clock,
      fields: [
        {
          key: 'check_interval_seconds',
          label: 'Check Interval (seconds)',
          type: 'number',
          required: true,
          defaultValue: 30,
          min: 5,
          max: 300,
          helpText: 'How often to evaluate the condition'
        },
        {
          key: 'timeout_minutes',
          label: 'Timeout (minutes)',
          type: 'number',
          required: true,
          defaultValue: 60,
          min: 1,
          max: 10080, // 1 week
          helpText: 'Maximum time to wait for condition'
        },
        {
          key: 'timeout_action',
          label: 'On Timeout',
          type: 'select',
          required: true,
          defaultValue: 'continue',
          options: [
            { label: 'Continue Workflow', value: 'continue' },
            { label: 'Fail Workflow', value: 'fail' },
            { label: 'Branch to Timeout Path', value: 'branch' }
          ],
          helpText: 'What to do if condition is not met'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Options',
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'initial_delay_seconds',
          label: 'Initial Delay (seconds)',
          type: 'number',
          defaultValue: 0,
          min: 0,
          max: 60,
          helpText: 'Wait before first check'
        },
        {
          key: 'max_checks',
          label: 'Maximum Checks',
          type: 'number',
          min: 0,
          defaultValue: 0,
          helpText: 'Maximum number of checks (0 = unlimited)'
        },
        {
          key: 'store_result',
          label: 'Store Result in Context',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Store condition result in workflow context'
        },
        {
          key: 'result_variable_name',
          label: 'Result Variable Name',
          type: 'text',
          showWhen: (c) => c.store_result,
          defaultValue: 'condition_result',
          placeholder: 'condition_result',
          helpText: 'Variable name for storing result'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.condition_type) {
      errors.condition_type = 'Condition type is required';
    }

    if (config.condition_type === 'expression' && !config.expression) {
      errors.expression = 'Expression is required';
    }

    if ((config.condition_type === 'record_count' || config.condition_type === 'aggregate') && !config.pipeline_id) {
      errors.pipeline_id = 'Pipeline ID is required for record queries';
    }

    if (config.condition_type === 'aggregate' && !config.aggregate_field) {
      errors.aggregate_field = 'Aggregate field is required';
    }

    if (!config.timeout_minutes || config.timeout_minutes < 1) {
      errors.timeout_minutes = 'Timeout must be at least 1 minute';
    }

    if (!config.check_interval_seconds || config.check_interval_seconds < 5) {
      errors.check_interval_seconds = 'Check interval must be at least 5 seconds';
    }

    return errors;
  },

  defaults: {
    condition_type: 'expression',
    count_operator: 'greater_than',
    aggregate_function: 'sum',
    expected_count: 1,
    aggregate_expected: 0,
    check_interval_seconds: 30,
    timeout_minutes: 60,
    timeout_action: 'continue',
    initial_delay_seconds: 0,
    max_checks: 0,
    store_result: true,
    result_variable_name: 'condition_result',
    filter_conditions: {}
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};