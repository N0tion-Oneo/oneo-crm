import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Plus, Database, Settings } from 'lucide-react';

export const RecordCreateNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.RECORD_CREATE,
  label: 'Create Record',
  description: 'Create a new record in a pipeline',
  icon: Plus,
  category: 'data',

  sections: [
    {
      id: 'record_config',
      label: 'Record Configuration',
      icon: Database,
      fields: [
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'pipeline',
          required: true,
          placeholder: 'Select target pipeline',
          helpText: 'The pipeline to create the record in'
        },
        {
          key: 'field_mapping_type',
          label: 'Field Mapping Type',
          type: 'select',
          defaultValue: 'manual',
          options: [
            { label: 'Manual Mapping', value: 'manual' },
            { label: 'JSON Object', value: 'json' },
            { label: 'Copy from Source', value: 'copy' }
          ],
          helpText: 'How to map field values'
        },
        {
          key: 'field_values',
          label: 'Field Values',
          type: 'json',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.field_mapping_type === 'json',
          placeholder: '{\n  "name": "{{contact_name}}",\n  "email": "{{email}}",\n  "status": "new",\n  "created_date": "{{now}}"\n}',
          helpText: 'Field values for the new record',
          rows: 10
        },
        {
          key: 'source_record',
          label: 'Source Record',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.field_mapping_type === 'copy',
          placeholder: '{{trigger.record}}',
          helpText: 'Record to copy field values from'
        },
        {
          key: 'field_overrides',
          label: 'Field Overrides',
          type: 'json',
          allowExpressions: true,
          showWhen: (c) => c.field_mapping_type === 'copy',
          placeholder: '{\n  "status": "copied",\n  "source_id": "{{original.id}}"\n}',
          helpText: 'Override specific fields when copying',
          rows: 6
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
          key: 'check_duplicates',
          label: 'Check for Duplicates',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Check if similar record already exists'
        },
        {
          key: 'duplicate_fields',
          label: 'Duplicate Check Fields',
          type: 'multiselect',
          showWhen: (c) => c.check_duplicates,
          options: [], // Will be populated based on pipeline
          helpText: 'Fields to use for duplicate detection'
        },
        {
          key: 'on_duplicate',
          label: 'On Duplicate Found',
          type: 'select',
          showWhen: (c) => c.check_duplicates,
          defaultValue: 'error',
          options: [
            { label: 'Throw Error', value: 'error' },
            { label: 'Update Existing', value: 'update' },
            { label: 'Skip Creation', value: 'skip' },
            { label: 'Create Anyway', value: 'create' }
          ],
          helpText: 'Action when duplicate is found'
        }
      ]
    },
    {
      id: 'relationships',
      label: 'Relationships',
      collapsed: true,
      fields: [
        {
          key: 'create_relationships',
          label: 'Create Relationships',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Automatically create relationships'
        },
        {
          key: 'parent_record',
          label: 'Parent Record',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.create_relationships,
          placeholder: '{{trigger.record.id}}',
          helpText: 'Parent record to link to'
        },
        {
          key: 'relationship_type',
          label: 'Relationship Type',
          type: 'select',
          showWhen: (c) => c.create_relationships,
          options: [
            { label: 'Child Of', value: 'child_of' },
            { label: 'Related To', value: 'related_to' },
            { label: 'Linked With', value: 'linked_with' }
          ],
          helpText: 'Type of relationship to create'
        },
        {
          key: 'copy_relationships',
          label: 'Copy Relationships',
          type: 'boolean',
          defaultValue: false,
          showWhen: (c) => c.field_mapping_type === 'copy',
          helpText: 'Copy relationships from source record'
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
          key: 'return_created',
          label: 'Return Created Record',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include the created record in output'
        },
        {
          key: 'trigger_webhooks',
          label: 'Trigger Webhooks',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Trigger pipeline webhooks for this creation'
        },
        {
          key: 'trigger_workflows',
          label: 'Trigger Other Workflows',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Allow other workflows to trigger from this creation'
        },
        {
          key: 'audit_creation',
          label: 'Audit Creation',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Log this creation in audit trail'
        },
        {
          key: 'set_owner',
          label: 'Set Record Owner',
          type: 'text',
          allowExpressions: true,
          placeholder: '{{user.id}} or specific user ID',
          helpText: 'User to set as record owner'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.pipeline_id) {
      errors.pipeline_id = 'Pipeline selection is required';
    }
    
    if (config.field_mapping_type === 'json' && !config.field_values) {
      errors.field_values = 'Field values are required';
    }
    
    if (config.field_mapping_type === 'copy' && !config.source_record) {
      errors.source_record = 'Source record is required';
    }
    
    if (config.field_values) {
      try {
        if (typeof config.field_values === 'string') {
          JSON.parse(config.field_values);
        }
      } catch {
        errors.field_values = 'Field values must be valid JSON';
      }
    }
    
    return errors;
  },

  defaults: {
    field_mapping_type: 'manual',
    skip_validation: false,
    check_duplicates: true,
    on_duplicate: 'error',
    create_relationships: false,
    copy_relationships: false,
    return_created: true,
    trigger_webhooks: true,
    trigger_workflows: true,
    audit_creation: true
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