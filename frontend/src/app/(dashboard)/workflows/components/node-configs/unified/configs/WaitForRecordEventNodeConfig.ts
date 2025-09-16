import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Database, Clock } from 'lucide-react';

export const WaitForRecordEventNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.WAIT_FOR_RECORD_EVENT,
  label: 'Wait for Record Event',
  description: 'Wait for a specific event to occur on a record',
  icon: Database,
  category: 'control',

  sections: [
    {
      id: 'event_config',
      label: 'Event Configuration',
      icon: Database,
      fields: [
        {
          key: 'event_type',
          label: 'Event Type',
          type: 'select',
          required: true,
          defaultValue: 'field_changed',
          options: [
            { label: 'Field Changed', value: 'field_changed' },
            { label: 'Status Changed', value: 'status_changed' },
            { label: 'Record Deleted', value: 'record_deleted' }
          ],
          helpText: 'Type of event to wait for'
        },
        {
          key: 'record_id',
          label: 'Record ID',
          type: 'text',
          allowExpressions: true,
          placeholder: '{{record_id}}',
          helpText: 'ID of the record to monitor (uses context record if empty)'
        },
        {
          key: 'field_name',
          label: 'Field to Monitor',
          type: 'text',
          required: true,
          showWhen: (c) => c.event_type === 'field_changed',
          placeholder: 'status, amount, assigned_to',
          helpText: 'Name of the field to monitor for changes'
        },
        {
          key: 'expected_value',
          label: 'Expected Value',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.event_type !== 'record_deleted',
          placeholder: 'completed, {{target_value}}',
          helpText: 'Optional: specific value to wait for'
        },
        {
          key: 'comparison_operator',
          label: 'Comparison',
          type: 'select',
          defaultValue: 'equals',
          showWhen: (c) => c.expected_value && c.event_type !== 'record_deleted',
          options: [
            { label: 'Equals', value: 'equals' },
            { label: 'Not Equals', value: 'not_equals' },
            { label: 'Contains', value: 'contains' },
            { label: 'Greater Than', value: 'greater_than' },
            { label: 'Less Than', value: 'less_than' }
          ],
          helpText: 'How to compare the value'
        }
      ]
    },
    {
      id: 'timeout_config',
      label: 'Timeout Settings',
      icon: Clock,
      fields: [
        {
          key: 'timeout_minutes',
          label: 'Timeout (minutes)',
          type: 'number',
          required: true,
          defaultValue: 60,
          min: 1,
          max: 10080, // 1 week
          helpText: 'Maximum time to wait for event'
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
          helpText: 'What to do if event does not occur'
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
          key: 'check_interval_seconds',
          label: 'Check Interval (seconds)',
          type: 'number',
          defaultValue: 5,
          min: 1,
          max: 60,
          helpText: 'How often to check for the event'
        },
        {
          key: 'include_related_records',
          label: 'Include Related Records',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Also monitor changes in related records'
        },
        {
          key: 'event_metadata',
          label: 'Capture Event Metadata',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Store event details in workflow context'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.event_type) {
      errors.event_type = 'Event type is required';
    }

    if (config.event_type === 'field_changed' && !config.field_name) {
      errors.field_name = 'Field name is required for field change events';
    }

    if (!config.timeout_minutes || config.timeout_minutes < 1) {
      errors.timeout_minutes = 'Timeout must be at least 1 minute';
    }

    return errors;
  },

  defaults: {
    event_type: 'field_changed',
    comparison_operator: 'equals',
    timeout_minutes: 60,
    timeout_action: 'continue',
    check_interval_seconds: 5,
    include_related_records: false,
    event_metadata: true
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};