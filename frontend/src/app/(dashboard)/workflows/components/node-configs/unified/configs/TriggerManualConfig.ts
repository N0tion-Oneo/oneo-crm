import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Play, Settings } from 'lucide-react';

export const TriggerManualConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_MANUAL,
  label: 'Manual Trigger',
  description: 'Manually trigger workflow execution',
  icon: Play,
  category: 'trigger',

  sections: [
    {
      id: 'trigger_config',
      label: 'Trigger Configuration',
      icon: Play,
      fields: [
        {
          key: 'name',
          label: 'Trigger Name',
          type: 'text',
          required: true,
          placeholder: 'Manual workflow execution',
          helpText: 'Descriptive name for this trigger'
        },
        {
          key: 'description',
          label: 'Description',
          type: 'textarea',
          placeholder: 'Describe when and why this workflow should be triggered manually',
          helpText: 'Document the purpose of this manual trigger',
          rows: 3
        },
        {
          key: 'require_confirmation',
          label: 'Require Confirmation',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Ask for confirmation before executing'
        },
        {
          key: 'confirmation_message',
          label: 'Confirmation Message',
          type: 'textarea',
          showWhen: (c) => c.require_confirmation,
          placeholder: 'Are you sure you want to execute this workflow?',
          helpText: 'Message shown when confirmation is required',
          rows: 2
        }
      ]
    },
    {
      id: 'input_parameters',
      label: 'Input Parameters',
      collapsed: true,
      fields: [
        {
          key: 'require_input',
          label: 'Require Input Data',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Request input data when triggering'
        },
        {
          key: 'input_fields',
          label: 'Input Fields',
          type: 'json',
          showWhen: (c) => c.require_input,
          placeholder: '[\n  {\n    "name": "record_id",\n    "label": "Record ID",\n    "type": "text",\n    "required": true\n  }\n]',
          helpText: 'Define input fields for manual execution',
          rows: 8
        }
      ]
    },
    {
      id: 'options',
      label: 'Options',
      icon: Settings,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'allow_bulk_trigger',
          label: 'Allow Bulk Trigger',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Allow triggering for multiple records'
        },
        {
          key: 'show_in_ui',
          label: 'Show in UI',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Show trigger button in user interface'
        },
        {
          key: 'button_label',
          label: 'Button Label',
          type: 'text',
          showWhen: (c) => c.show_in_ui,
          placeholder: 'Execute Workflow',
          helpText: 'Label for the trigger button'
        },
        {
          key: 'button_color',
          label: 'Button Color',
          type: 'select',
          showWhen: (c) => c.show_in_ui,
          defaultValue: 'primary',
          options: [
            { label: 'Primary', value: 'primary' },
            { label: 'Secondary', value: 'secondary' },
            { label: 'Success', value: 'success' },
            { label: 'Warning', value: 'warning' },
            { label: 'Danger', value: 'danger' }
          ]
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    if (!config.name) {
      errors.name = 'Trigger name is required';
    }
    return errors;
  },

  defaults: {
    require_confirmation: true,
    require_input: false,
    allow_bulk_trigger: false,
    show_in_ui: true,
    button_color: 'primary'
  },

  features: {
    supportsExpressions: false,
    supportsVariables: false,
    supportsTesting: true,
    supportsTemplates: false
  }
};