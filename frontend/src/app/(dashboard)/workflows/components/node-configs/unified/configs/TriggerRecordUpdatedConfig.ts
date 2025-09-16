import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Edit, Database, Filter, GitCompare, Clock, Activity } from 'lucide-react';
import React from 'react';
import { DynamicFieldValueMatches } from '../components/DynamicFieldValueMatches';

export const TriggerRecordUpdatedConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_RECORD_UPDATED,
  label: 'Record Updated Trigger',
  description: 'Triggers when a record is updated in a pipeline',
  icon: Edit,
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
          helpText: 'The pipeline to watch for record updates'
        },
        {
          key: 'update_type',
          label: 'Update Type',
          type: 'select',
          defaultValue: 'any_field',
          options: [
            { label: 'Any field change', value: 'any_field' },
            { label: 'Specific fields only', value: 'specific_fields' },
            { label: 'Status changes only', value: 'status_only' },
            { label: 'Status progression', value: 'status_progression' }
          ],
          helpText: 'What type of updates to track'
        },
        {
          key: 'tracked_fields',
          label: 'Tracked Fields',
          type: 'multiselect',
          showWhen: (config) => config.update_type === 'specific_fields',
          required: true,
          placeholder: 'Select fields to track',
          options: [], // Will be populated based on selected pipeline
          helpText: 'Only trigger when these specific fields change'
        },
        {
          key: 'status_field',
          label: 'Status Field',
          type: 'field',
          showWhen: (config) => ['status_only', 'status_progression'].includes(config.update_type),
          required: true,
          placeholder: 'Select status field',
          options: [], // Will be populated with pipeline fields
          helpText: 'The field that represents status'
        },
        {
          key: 'include_old_values',
          label: 'Include Previous Values',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include the previous field values in trigger data'
        }
      ]
    },
    {
      id: 'change_detection',
      label: 'Change Detection',
      icon: GitCompare,
      collapsed: true,
      fields: [
        {
          key: 'detect_specific_changes',
          label: 'Detect Specific Changes',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Only trigger for specific value changes'
        },
        {
          key: 'field_value_matches',
          label: 'Field Value Matches',
          type: 'custom',
          showWhen: (config) => config.detect_specific_changes,
          helpText: 'Configure value matching for each tracked field',
          customRender: (props) => React.createElement(DynamicFieldValueMatches, {
            value: props.value,
            onChange: props.onChange,
            config: props.config,
            pipelineFields: props.pipelineFields
          })
        },
        {
          key: 'trigger_condition',
          label: 'Trigger Condition',
          type: 'select',
          showWhen: (config) => config.update_type === 'specific_fields' && config.tracked_fields?.length > 1,
          defaultValue: 'any',
          options: [
            { label: 'Any field changes', value: 'any' },
            { label: 'All fields must change', value: 'all' }
          ],
          helpText: 'When to trigger with multiple tracked fields'
        },
        {
          key: 'comparison_mode',
          label: 'Comparison Mode',
          type: 'select',
          defaultValue: 'deep',
          options: [
            { label: 'Deep Comparison', value: 'deep' },
            { label: 'Shallow Comparison', value: 'shallow' },
            { label: 'Case-insensitive', value: 'case_insensitive' }
          ],
          helpText: 'How to detect if values have changed'
        }
      ]
    },
    {
      id: 'status_progression',
      label: 'Status Progression',
      icon: Activity,
      showWhen: (config) => config.update_type === 'status_progression',
      collapsed: true,
      fields: [
        {
          key: 'progression_mode',
          label: 'Progression Mode',
          type: 'select',
          defaultValue: 'any_change',
          options: [
            { label: 'Any status change', value: 'any_change' },
            { label: 'Forward progression only', value: 'forward' },
            { label: 'Backward movement only', value: 'backward' },
            { label: 'Specific transitions', value: 'specific' }
          ],
          helpText: 'Type of status progression to track'
        },
        {
          key: 'status_order',
          label: 'Status Order',
          type: 'array',
          showWhen: (config) => ['forward', 'backward'].includes(config.progression_mode),
          placeholder: 'Define status progression order',
          helpText: 'Order statuses from first to last stage'
        },
        {
          key: 'from_statuses',
          label: 'From Status(es)',
          type: 'multiselect',
          showWhen: (config) => config.progression_mode === 'specific',
          placeholder: 'Any status',
          options: [], // Will be populated with field options
          helpText: 'Previous status values (leave empty for any)'
        },
        {
          key: 'to_statuses',
          label: 'To Status(es)',
          type: 'multiselect',
          showWhen: (config) => config.progression_mode === 'specific',
          required: true,
          placeholder: 'Select target statuses',
          options: [], // Will be populated with field options
          helpText: 'New status values to trigger on'
        },
        {
          key: 'skip_allowed',
          label: 'Allow Skipping Stages',
          type: 'boolean',
          showWhen: (config) => ['forward', 'backward'].includes(config.progression_mode),
          defaultValue: true,
          helpText: 'Allow jumping over intermediate statuses'
        }
      ]
    },
    {
      id: 'timing',
      label: 'Timing & Debouncing',
      icon: Clock,
      collapsed: true,
      fields: [
        {
          key: 'minimum_change_interval',
          label: 'Minimum Change Interval (seconds)',
          type: 'number',
          defaultValue: 0,
          min: 0,
          max: 3600,
          helpText: 'Ignore rapid consecutive updates (debouncing)'
        },
        {
          key: 'time_in_status',
          label: 'Time in Previous Status',
          type: 'select',
          showWhen: (config) => ['status_only', 'status_progression'].includes(config.update_type),
          defaultValue: 'any',
          options: [
            { label: 'Any duration', value: 'any' },
            { label: 'Minimum time', value: 'min' },
            { label: 'Maximum time', value: 'max' },
            { label: 'Time range', value: 'range' }
          ],
          helpText: 'Require specific time in previous status'
        },
        {
          key: 'min_time_hours',
          label: 'Minimum Time (hours)',
          type: 'number',
          showWhen: (config) => ['min', 'range'].includes(config.time_in_status),
          min: 0,
          placeholder: '24',
          helpText: 'Minimum hours in previous status'
        },
        {
          key: 'max_time_hours',
          label: 'Maximum Time (hours)',
          type: 'number',
          showWhen: (config) => ['max', 'range'].includes(config.time_in_status),
          min: 0,
          placeholder: '168',
          helpText: 'Maximum hours in previous status'
        },
        {
          key: 'business_hours_only',
          label: 'Business Hours Only',
          type: 'boolean',
          showWhen: (config) => config.time_in_status !== 'any',
          defaultValue: false,
          helpText: 'Only count business hours for timing'
        }
      ]
    },
    {
      id: 'filters',
      label: 'Record & User Filters',
      icon: Filter,
      collapsed: true,
      fields: [
        {
          key: 'enable_filters',
          label: 'Enable Record Filters',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Only trigger for records matching specific criteria'
        },
        {
          key: 'filter_conditions',
          label: 'Filter Conditions',
          type: 'json',
          showWhen: (config) => config.enable_filters,
          placeholder: '{\n  "status": "active",\n  "priority": "high"\n}',
          helpText: 'JSON object defining filter conditions',
          rows: 6
        },
        {
          key: 'record_age',
          label: 'Record Age Requirement',
          type: 'select',
          defaultValue: 'any',
          options: [
            { label: 'Any age', value: 'any' },
            { label: 'New records only (< 24h)', value: 'new' },
            { label: 'Existing records only (> 24h)', value: 'existing' },
            { label: 'Custom age range', value: 'custom' }
          ],
          helpText: 'Only trigger for records of certain age'
        },
        {
          key: 'min_age_hours',
          label: 'Minimum Age (hours)',
          type: 'number',
          showWhen: (config) => config.record_age === 'custom',
          min: 0,
          placeholder: '24',
          helpText: 'Minimum record age in hours'
        },
        {
          key: 'max_age_hours',
          label: 'Maximum Age (hours)',
          type: 'number',
          showWhen: (config) => config.record_age === 'custom',
          min: 0,
          placeholder: '168',
          helpText: 'Maximum record age in hours'
        },
        {
          key: 'user_restriction',
          label: 'User Restriction',
          type: 'select',
          defaultValue: 'any',
          options: [
            { label: 'Any user', value: 'any' },
            { label: 'Manual changes only', value: 'manual' },
            { label: 'System/automation only', value: 'system' },
            { label: 'Exclude system updates', value: 'no_system' },
            { label: 'Specific users', value: 'specific' }
          ],
          helpText: 'Filter by who made the change'
        },
        {
          key: 'specific_users',
          label: 'Specific Users',
          type: 'multiselect',
          showWhen: (config) => config.user_restriction === 'specific',
          placeholder: 'Select users',
          options: [], // Will be populated with users
          helpText: 'Only trigger for changes by these users'
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
          key: 'batch_updates',
          label: 'Batch Updates',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Process multiple updates in a single workflow run'
        },
        {
          key: 'batch_size',
          label: 'Batch Size',
          type: 'number',
          showWhen: (config) => config.batch_updates,
          defaultValue: 10,
          min: 1,
          max: 100,
          helpText: 'Maximum number of updates to process in one batch'
        },
        {
          key: 'batch_window',
          label: 'Batch Window (seconds)',
          type: 'number',
          showWhen: (config) => config.batch_updates,
          defaultValue: 5,
          min: 1,
          max: 60,
          helpText: 'Time window to collect updates for batching'
        },
        {
          key: 'include_metadata',
          label: 'Include Change Metadata',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include who changed it, when, and from what values'
        },
        {
          key: 'include_history',
          label: 'Include Full History',
          type: 'boolean',
          showWhen: (config) => ['status_only', 'status_progression'].includes(config.update_type),
          defaultValue: false,
          helpText: 'Include full change history for the tracked fields'
        },
        {
          key: 'cooldown_minutes',
          label: 'Cooldown Period (minutes)',
          type: 'number',
          defaultValue: 0,
          min: 0,
          max: 1440,
          helpText: 'Minimum time between triggers for same record'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.pipeline_id) {
      errors.pipeline_id = 'Pipeline selection is required';
    }

    if (config.update_type === 'specific_fields' && (!config.tracked_fields || config.tracked_fields.length === 0)) {
      errors.tracked_fields = 'Select at least one field to track';
    }

    if (['status_only', 'status_progression'].includes(config.update_type) && !config.status_field) {
      errors.status_field = 'Status field selection is required';
    }

    if (config.progression_mode === 'specific' && (!config.to_statuses || config.to_statuses.length === 0)) {
      errors.to_statuses = 'Select at least one target status';
    }

    if (['forward', 'backward'].includes(config.progression_mode) &&
        (!config.status_order || config.status_order.length < 2)) {
      errors.status_order = 'Define at least 2 statuses in order';
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

    if (config.time_in_status === 'range') {
      if (config.min_time_hours && config.max_time_hours &&
          config.min_time_hours >= config.max_time_hours) {
        errors.max_time_hours = 'Maximum time must be greater than minimum';
      }
    }

    if (config.record_age === 'custom') {
      if (config.min_age_hours && config.max_age_hours &&
          config.min_age_hours >= config.max_age_hours) {
        errors.max_age_hours = 'Maximum age must be greater than minimum age';
      }
    }

    return errors;
  },

  defaults: {
    update_type: 'any_field',
    include_old_values: true,
    detect_specific_changes: false,
    trigger_condition: 'any',
    comparison_mode: 'deep',
    progression_mode: 'any_change',
    skip_allowed: true,
    minimum_change_interval: 0,
    time_in_status: 'any',
    business_hours_only: false,
    enable_filters: false,
    record_age: 'any',
    user_restriction: 'any',
    batch_updates: false,
    batch_size: 10,
    batch_window: 5,
    include_metadata: true,
    include_history: false,
    cooldown_minutes: 0
  },

  dependencies: {
    pipelines: true,
    fields: true,
    users: true
  },

  features: {
    supportsExpressions: false,
    supportsVariables: false,
    supportsTesting: true,
    supportsTemplates: false
  }
};