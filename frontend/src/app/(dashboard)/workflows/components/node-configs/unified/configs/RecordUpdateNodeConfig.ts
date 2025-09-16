import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Edit, Database, Settings } from 'lucide-react';

export const RecordUpdateNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.RECORD_UPDATE,
  label: 'Update Record',
  description: 'Update an existing record in a pipeline',
  icon: Edit,
  category: 'data',

  sections: [
    {
      id: 'record_selection',
      label: 'Record Selection',
      icon: Database,
      fields: [
        {
          key: 'record_source',
          label: 'Record Source',
          type: 'select',
          required: true,
          defaultValue: 'trigger',
          options: [
            { label: 'From Trigger', value: 'trigger' },
            { label: 'From Previous Node', value: 'previous' },
            { label: 'Find by ID', value: 'id' },
            { label: 'Find by Criteria', value: 'criteria' },
            { label: 'From Variable', value: 'variable' }
          ],
          helpText: 'How to identify the record to update'
        },
        {
          key: 'record_id',
          label: 'Record ID',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.record_source === 'id',
          placeholder: '{{record_id}} or specific ID',
          helpText: 'ID of the record to update'
        },
        {
          key: 'record_variable',
          label: 'Record Variable',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.record_source === 'variable',
          placeholder: '{{variable_name}}',
          helpText: 'Variable containing the record'
        },
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'pipeline',
          required: true,
          showWhen: (c) => ['id', 'criteria'].includes(c.record_source),
          placeholder: 'Select pipeline',
          helpText: 'Pipeline containing the record'
        },
        {
          key: 'search_criteria',
          label: 'Search Criteria',
          type: 'json',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.record_source === 'criteria',
          placeholder: '{\n  "email": "{{email}}",\n  "status": "active"\n}',
          helpText: 'Criteria to find the record',
          rows: 6
        }
      ]
    },
    {
      id: 'update_fields',
      label: 'Fields to Update',
      fields: [
        {
          key: 'update_mode',
          label: 'Update Mode',
          type: 'select',
          required: true,
          defaultValue: 'merge',
          options: [
            { label: 'Merge (Update specified fields)', value: 'merge' },
            { label: 'Replace (Replace entire record)', value: 'replace' },
            { label: 'Increment (Add to numeric fields)', value: 'increment' },
            { label: 'Append (Add to array fields)', value: 'append' }
          ],
          helpText: 'How to apply the updates'
        },
        {
          key: 'update_method',
          label: 'Update Method',
          type: 'select',
          defaultValue: 'json',
          options: [
            { label: 'JSON (Advanced)', value: 'json' },
            { label: 'Individual Fields', value: 'individual' }
          ],
          helpText: 'How to specify field updates'
        },
        {
          key: 'field_updates',
          label: 'Field Updates',
          type: 'json',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.update_method === 'json' || !c.update_method,
          placeholder: '{\n  "status": "{{new_status}}",\n  "updated_at": "{{now}}",\n  "notes": "Updated by workflow"\n}',
          helpText: 'Fields and their new values',
          rows: 8
        },
        {
          key: 'update_field_1',
          label: 'Field 1',
          type: 'field',
          showWhen: (c) => c.update_method === 'individual',
          placeholder: 'Select field to update',
          helpText: 'First field to update'
        },
        {
          key: 'update_value_type_1',
          label: 'Value Type',
          type: 'select',
          showWhen: (c) => c.update_method === 'individual' && c.update_field_1,
          defaultValue: 'static',
          options: [
            { label: 'Static Value', value: 'static' },
            { label: 'Field Option', value: 'field_option' },
            { label: 'Variable/Expression', value: 'variable' }
          ]
        },
        {
          key: 'update_value_1',
          label: 'Value',
          type: 'text',
          showWhen: (c) => c.update_method === 'individual' && c.update_field_1 && c.update_value_type_1 === 'static',
          placeholder: 'Enter value'
        },
        {
          key: 'update_value_1',
          label: 'Value',
          type: 'field-value',
          fieldSource: 'update_field_1',
          showWhen: (c) => c.update_method === 'individual' && c.update_field_1 && c.update_value_type_1 === 'field_option',
          placeholder: 'Select option'
        },
        {
          key: 'update_value_1',
          label: 'Value',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.update_method === 'individual' && c.update_field_1 && c.update_value_type_1 === 'variable',
          placeholder: '{{variable_name}}'
        },
        {
          key: 'update_field_2',
          label: 'Field 2',
          type: 'field',
          showWhen: (c) => c.update_method === 'individual' && c.update_field_1,
          placeholder: 'Select field to update',
          helpText: 'Second field to update (optional)'
        },
        {
          key: 'update_value_type_2',
          label: 'Value Type',
          type: 'select',
          showWhen: (c) => c.update_method === 'individual' && c.update_field_2,
          defaultValue: 'static',
          options: [
            { label: 'Static Value', value: 'static' },
            { label: 'Field Option', value: 'field_option' },
            { label: 'Variable/Expression', value: 'variable' }
          ]
        },
        {
          key: 'update_value_2',
          label: 'Value',
          type: 'text',
          showWhen: (c) => c.update_method === 'individual' && c.update_field_2 && c.update_value_type_2 === 'static',
          placeholder: 'Enter value'
        },
        {
          key: 'update_value_2',
          label: 'Value',
          type: 'field-value',
          fieldSource: 'update_field_2',
          showWhen: (c) => c.update_method === 'individual' && c.update_field_2 && c.update_value_type_2 === 'field_option',
          placeholder: 'Select option'
        },
        {
          key: 'update_value_2',
          label: 'Value',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.update_method === 'individual' && c.update_field_2 && c.update_value_type_2 === 'variable',
          placeholder: '{{variable_name}}'
        },
        {
          key: 'increment_fields',
          label: 'Fields to Increment',
          type: 'json',
          showWhen: (c) => c.update_mode === 'increment',
          allowExpressions: true,
          placeholder: '{\n  "view_count": 1,\n  "score": {{score_change}}\n}',
          helpText: 'Numeric fields and increment values',
          rows: 4
        },
        {
          key: 'append_fields',
          label: 'Fields to Append',
          type: 'json',
          showWhen: (c) => c.update_mode === 'append',
          allowExpressions: true,
          placeholder: '{\n  "tags": ["workflow-processed"],\n  "history": {{new_entry}}\n}',
          helpText: 'Array fields and values to append',
          rows: 4
        }
      ]
    },
    {
      id: 'validation',
      label: 'Validation',
      collapsed: true,
      fields: [
        {
          key: 'skip_validation',
          label: 'Skip Validation',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Skip field validation rules'
        },
        {
          key: 'validate_required',
          label: 'Validate Required Fields',
          type: 'boolean',
          defaultValue: true,
          showWhen: (c) => !c.skip_validation,
          helpText: 'Ensure required fields are present'
        },
        {
          key: 'fail_on_not_found',
          label: 'Fail if Record Not Found',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Throw error if record doesn\'t exist'
        },
        {
          key: 'create_if_not_found',
          label: 'Create if Not Found',
          type: 'boolean',
          defaultValue: false,
          showWhen: (c) => !c.fail_on_not_found,
          helpText: 'Create new record if not found'
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
          key: 'return_updated',
          label: 'Return Updated Record',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include the updated record in output'
        },
        {
          key: 'return_previous',
          label: 'Return Previous Values',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Include previous field values in output'
        },
        {
          key: 'trigger_webhooks',
          label: 'Trigger Webhooks',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Trigger pipeline webhooks for this update'
        },
        {
          key: 'trigger_workflows',
          label: 'Trigger Other Workflows',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Allow other workflows to trigger from this update'
        },
        {
          key: 'audit_update',
          label: 'Audit Update',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Log this update in audit trail'
        },
        {
          key: 'update_timestamp',
          label: 'Update Timestamp Field',
          type: 'text',
          defaultValue: 'updated_at',
          placeholder: 'updated_at',
          helpText: 'Field to update with current timestamp'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.record_source) {
      errors.record_source = 'Record source is required';
    }
    
    if (config.record_source === 'id' && !config.record_id) {
      errors.record_id = 'Record ID is required';
    }
    
    if (config.record_source === 'criteria' && !config.search_criteria) {
      errors.search_criteria = 'Search criteria is required';
    }
    
    if (!config.field_updates && config.update_mode !== 'increment' && config.update_mode !== 'append') {
      errors.field_updates = 'Field updates are required';
    }
    
    return errors;
  },

  defaults: {
    record_source: 'trigger',
    update_mode: 'merge',
    skip_validation: false,
    validate_required: true,
    fail_on_not_found: true,
    create_if_not_found: false,
    return_updated: true,
    return_previous: false,
    trigger_webhooks: true,
    trigger_workflows: false,
    audit_update: true,
    update_timestamp: 'updated_at'
  },

  dependencies: {
    pipelines: true,
    fields: true
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};