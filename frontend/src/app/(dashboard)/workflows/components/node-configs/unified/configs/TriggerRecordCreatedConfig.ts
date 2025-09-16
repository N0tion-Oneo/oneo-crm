import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Plus, Database, Filter } from 'lucide-react';

export const TriggerRecordCreatedConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_RECORD_CREATED,
  label: 'Record Created Trigger',
  description: 'Triggers when a new record is created in a pipeline',
  icon: Plus,
  category: 'trigger',

  sections: [
    {
      id: 'trigger_source',
      label: 'Trigger Source',
      icon: Database,
      fields: [
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'pipeline',
          required: true,
          placeholder: 'Select pipeline to monitor',
          helpText: 'The pipeline to watch for new records'
        },
        {
          key: 'include_all_fields',
          label: 'Include All Fields',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include all fields from the created record in the trigger data'
        },
        {
          key: 'selected_fields',
          label: 'Selected Fields',
          type: 'multiselect',
          showWhen: (config) => !config.include_all_fields,
          placeholder: 'Select fields to include',
          options: [], // Will be populated based on selected pipeline
          helpText: 'Choose which fields to include in the trigger data'
        }
      ]
    },
    {
      id: 'filters',
      label: 'Filters',
      icon: Filter,
      collapsed: true,
      fields: [
        {
          key: 'enable_filters',
          label: 'Enable Filters',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Only trigger for records matching specific criteria'
        },
        {
          key: 'filter_conditions',
          label: 'Filter Conditions',
          type: 'json',
          showWhen: (config) => config.enable_filters,
          placeholder: '{\n  "status": "new",\n  "priority": "high"\n}',
          helpText: 'JSON object defining filter conditions',
          rows: 6
        },
        {
          key: 'filter_logic',
          label: 'Filter Logic',
          type: 'select',
          showWhen: (config) => config.enable_filters,
          defaultValue: 'AND',
          options: [
            { label: 'All conditions must match (AND)', value: 'AND' },
            { label: 'Any condition can match (OR)', value: 'OR' }
          ],
          helpText: 'How to combine multiple filter conditions'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Settings',
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'batch_records',
          label: 'Batch Records',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Process multiple records in a single workflow run'
        },
        {
          key: 'batch_size',
          label: 'Batch Size',
          type: 'number',
          showWhen: (config) => config.batch_records,
          defaultValue: 10,
          min: 1,
          max: 100,
          helpText: 'Maximum number of records to process in one batch'
        },
        {
          key: 'batch_delay',
          label: 'Batch Delay (seconds)',
          type: 'number',
          showWhen: (config) => config.batch_records,
          defaultValue: 5,
          min: 1,
          max: 60,
          helpText: 'Wait time before processing a batch'
        },
        {
          key: 'ignore_test_records',
          label: 'Ignore Test Records',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Skip records marked as test data'
        },
        {
          key: 'trigger_for_api_created',
          label: 'Trigger for API-Created Records',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include records created via API'
        },
        {
          key: 'trigger_for_import',
          label: 'Trigger for Imported Records',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Include records created via bulk import'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.pipeline_id) {
      errors.pipeline_id = 'Pipeline selection is required';
    }

    if (config.enable_filters && config.filter_conditions) {
      try {
        if (typeof config.filter_conditions === 'string') {
          JSON.parse(config.filter_conditions);
        }
      } catch {
        errors.filter_conditions = 'Filter conditions must be valid JSON';
      }
    }

    return errors;
  },

  defaults: {
    include_all_fields: true,
    enable_filters: false,
    filter_logic: 'AND',
    batch_records: false,
    batch_size: 10,
    batch_delay: 5,
    ignore_test_records: true,
    trigger_for_api_created: true,
    trigger_for_import: false
  },

  dependencies: {
    pipelines: true,
    fields: true
  },

  features: {
    supportsExpressions: false, // Triggers don't need expressions
    supportsVariables: false,
    supportsTesting: true,
    supportsTemplates: false
  }
};