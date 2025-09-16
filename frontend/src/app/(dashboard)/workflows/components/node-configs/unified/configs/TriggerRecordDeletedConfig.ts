import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Trash2, Database, Filter } from 'lucide-react';

export const TriggerRecordDeletedConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_RECORD_DELETED,
  label: 'Record Deleted Trigger',
  description: 'Triggers when a record is deleted from a pipeline',
  icon: Trash2,
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
          helpText: 'The pipeline to watch for deleted records'
        },
        {
          key: 'capture_deleted_data',
          label: 'Capture Deleted Data',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include the deleted record data in the trigger'
        },
        {
          key: 'track_soft_deletes',
          label: 'Track Soft Deletes',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Trigger for soft deletes (marked as deleted)'
        },
        {
          key: 'track_hard_deletes',
          label: 'Track Hard Deletes',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Trigger for permanent deletions'
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
          helpText: 'Only trigger for records matching specific criteria before deletion'
        },
        {
          key: 'filter_conditions',
          label: 'Filter Conditions',
          type: 'json',
          showWhen: (config) => config.enable_filters,
          placeholder: '{\n  "status": "archived",\n  "age_days": {"$gt": 30}\n}',
          helpText: 'Conditions the record must have met before deletion',
          rows: 6
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
          key: 'include_deletion_reason',
          label: 'Include Deletion Reason',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Capture why the record was deleted'
        },
        {
          key: 'include_deleted_by',
          label: 'Include Deleted By',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Capture who deleted the record'
        },
        {
          key: 'ignore_bulk_deletes',
          label: 'Ignore Bulk Deletes',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Skip triggers for bulk deletion operations'
        },
        {
          key: 'archive_deleted_data',
          label: 'Archive Deleted Data',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Store deleted record data for recovery'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    if (!config.pipeline_id) {
      errors.pipeline_id = 'Pipeline selection is required';
    }
    if (!config.track_soft_deletes && !config.track_hard_deletes) {
      errors.track_soft_deletes = 'Must track at least one type of deletion';
    }
    return errors;
  },

  defaults: {
    capture_deleted_data: true,
    track_soft_deletes: true,
    track_hard_deletes: false,
    enable_filters: false,
    include_deletion_reason: true,
    include_deleted_by: true,
    ignore_bulk_deletes: false,
    archive_deleted_data: false
  },

  dependencies: {
    pipelines: true
  },

  features: {
    supportsExpressions: false,
    supportsVariables: false,
    supportsTesting: true,
    supportsTemplates: false
  }
};