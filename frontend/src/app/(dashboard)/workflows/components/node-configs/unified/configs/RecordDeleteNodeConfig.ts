import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Trash2, Database, AlertTriangle, Archive } from 'lucide-react';

export const RecordDeleteNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.RECORD_DELETE,
  label: 'Delete Record',
  description: 'Delete or archive a record from a pipeline',
  icon: Trash2,
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
            { label: 'By Record ID', value: 'id' },
            { label: 'By Search Criteria', value: 'criteria' },
            { label: 'From Variable', value: 'variable' },
            { label: 'Multiple Records', value: 'multiple' }
          ],
          helpText: 'How to identify the record(s) to delete'
        },
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'pipeline',
          required: true,
          showWhen: (config) => ['id', 'criteria', 'multiple'].includes(config.record_source),
          placeholder: 'Select pipeline',
          helpText: 'Pipeline containing the record(s)'
        },
        {
          key: 'record_id',
          label: 'Record ID',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.record_source === 'id',
          placeholder: '{{record_id}} or specific ID',
          helpText: 'ID of the record to delete'
        },
        {
          key: 'record_variable',
          label: 'Record Variable',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.record_source === 'variable',
          placeholder: '{{variable_name}}',
          helpText: 'Variable containing the record'
        },
        {
          key: 'search_criteria',
          label: 'Search Criteria',
          type: 'json',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.record_source === 'criteria',
          placeholder: '{\n  "status": "inactive",\n  "created_at": { "$lt": "{{30_days_ago}}" }\n}',
          helpText: 'Criteria to find records to delete',
          rows: 6
        },
        {
          key: 'record_ids',
          label: 'Record IDs',
          type: 'array',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.record_source === 'multiple',
          placeholder: 'List of record IDs or {{variable}}',
          helpText: 'Multiple record IDs to delete'
        }
      ]
    },
    {
      id: 'delete_options',
      label: 'Delete Options',
      icon: Archive,
      fields: [
        {
          key: 'delete_mode',
          label: 'Delete Mode',
          type: 'select',
          required: true,
          defaultValue: 'soft',
          options: [
            { label: 'Soft Delete (Archive)', value: 'soft', description: 'Mark as deleted, can be restored' },
            { label: 'Hard Delete (Permanent)', value: 'hard', description: 'Permanently remove, cannot be restored' },
            { label: 'Move to Trash', value: 'trash', description: 'Move to trash pipeline' }
          ],
          helpText: 'How to handle the deletion'
        },
        {
          key: 'trash_pipeline',
          label: 'Trash Pipeline',
          type: 'pipeline',
          required: true,
          showWhen: (config) => config.delete_mode === 'trash',
          placeholder: 'Select trash pipeline',
          helpText: 'Pipeline to move deleted records to'
        },
        {
          key: 'cascade_delete',
          label: 'Cascade Delete',
          type: 'boolean',
          defaultValue: false,
          showWhen: (config) => config.delete_mode === 'hard',
          helpText: 'Delete related records as well'
        },
        {
          key: 'cascade_relationships',
          label: 'Relationships to Cascade',
          type: 'multiselect',
          showWhen: (config) => config.cascade_delete && config.delete_mode === 'hard',
          placeholder: 'Select relationships',
          options: [], // Will be populated with relationship types
          helpText: 'Which related records to delete'
        },
        {
          key: 'preserve_audit',
          label: 'Preserve Audit Trail',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Keep deletion record for audit purposes'
        }
      ]
    },
    {
      id: 'safety',
      label: 'Safety Checks',
      icon: AlertTriangle,
      fields: [
        {
          key: 'confirm_single',
          label: 'Confirm Single Deletion',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Require confirmation for single record'
        },
        {
          key: 'confirm_multiple',
          label: 'Confirm Multiple Deletions',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Require confirmation for multiple records'
        },
        {
          key: 'max_records',
          label: 'Maximum Records',
          type: 'number',
          defaultValue: 100,
          min: 1,
          max: 1000,
          showWhen: (config) => ['criteria', 'multiple'].includes(config.record_source),
          helpText: 'Maximum number of records to delete at once'
        },
        {
          key: 'dry_run',
          label: 'Dry Run Mode',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Test deletion without actually deleting'
        },
        {
          key: 'check_dependencies',
          label: 'Check Dependencies',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Check for dependent records before deleting'
        },
        {
          key: 'dependency_action',
          label: 'If Dependencies Found',
          type: 'select',
          showWhen: (config) => config.check_dependencies,
          defaultValue: 'abort',
          options: [
            { label: 'Abort deletion', value: 'abort' },
            { label: 'Delete anyway', value: 'force' },
            { label: 'Unlink dependencies', value: 'unlink' },
            { label: 'Archive instead', value: 'archive' }
          ],
          helpText: 'What to do if dependent records exist'
        }
      ]
    },
    {
      id: 'backup',
      label: 'Backup & Recovery',
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'create_backup',
          label: 'Create Backup',
          type: 'boolean',
          defaultValue: true,
          showWhen: (config) => config.delete_mode === 'hard',
          helpText: 'Backup record before permanent deletion'
        },
        {
          key: 'backup_location',
          label: 'Backup Location',
          type: 'select',
          showWhen: (config) => config.create_backup && config.delete_mode === 'hard',
          defaultValue: 'system',
          options: [
            { label: 'System backup', value: 'system' },
            { label: 'Export to file', value: 'file' },
            { label: 'Archive pipeline', value: 'pipeline' },
            { label: 'External storage', value: 'external' }
          ],
          helpText: 'Where to store backup'
        },
        {
          key: 'retention_days',
          label: 'Backup Retention (days)',
          type: 'number',
          showWhen: (config) => config.create_backup && config.delete_mode === 'hard',
          defaultValue: 30,
          min: 1,
          max: 365,
          helpText: 'How long to keep backups'
        },
        {
          key: 'recovery_window',
          label: 'Recovery Window (hours)',
          type: 'number',
          showWhen: (config) => config.delete_mode === 'soft',
          defaultValue: 72,
          min: 0,
          max: 720,
          helpText: 'Time window for easy recovery (0 = unlimited)'
        }
      ]
    },
    {
      id: 'notifications',
      label: 'Notifications',
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'notify_on_delete',
          label: 'Send Notifications',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Notify about deletions'
        },
        {
          key: 'notify_users',
          label: 'Notify Users',
          type: 'multiselect',
          showWhen: (config) => config.notify_on_delete,
          placeholder: 'Select users to notify',
          options: [], // Will be populated with users
          helpText: 'Users to notify about deletion'
        },
        {
          key: 'include_record_data',
          label: 'Include Record Data',
          type: 'boolean',
          showWhen: (config) => config.notify_on_delete,
          defaultValue: false,
          helpText: 'Include deleted record data in notification'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.record_source) {
      errors.record_source = 'Record source is required';
    }

    if (['id', 'criteria', 'multiple'].includes(config.record_source) && !config.pipeline_id) {
      errors.pipeline_id = 'Pipeline selection is required';
    }

    if (config.record_source === 'id' && !config.record_id) {
      errors.record_id = 'Record ID is required';
    }

    if (config.record_source === 'variable' && !config.record_variable) {
      errors.record_variable = 'Record variable is required';
    }

    if (config.record_source === 'criteria' && config.search_criteria) {
      try {
        if (typeof config.search_criteria === 'string') {
          JSON.parse(config.search_criteria);
        }
      } catch {
        errors.search_criteria = 'Search criteria must be valid JSON';
      }
    }

    if (config.record_source === 'multiple' && (!config.record_ids || config.record_ids.length === 0)) {
      errors.record_ids = 'At least one record ID is required';
    }

    if (config.delete_mode === 'trash' && !config.trash_pipeline) {
      errors.trash_pipeline = 'Trash pipeline is required';
    }

    return errors;
  },

  defaults: {
    record_source: 'trigger',
    delete_mode: 'soft',
    cascade_delete: false,
    preserve_audit: true,
    confirm_single: false,
    confirm_multiple: true,
    max_records: 100,
    dry_run: false,
    check_dependencies: true,
    dependency_action: 'abort',
    create_backup: true,
    backup_location: 'system',
    retention_days: 30,
    recovery_window: 72,
    notify_on_delete: false,
    include_record_data: false
  },

  dependencies: {
    pipelines: true,
    users: true
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};