import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Calendar, Clock, Settings, RefreshCw } from 'lucide-react';

export const TriggerDateReachedConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_DATE_REACHED,
  category: 'trigger',
  label: 'Date Reached',
  description: 'Trigger workflow when a specific date/time is reached',
  icon: Calendar,

  sections: [
    {
      id: 'basic',
      label: 'Basic Configuration',
      icon: Calendar,
      fields: [
        {
          key: 'name',
          label: 'Trigger Name',
          type: 'text',
          required: true,
          placeholder: 'e.g., Contract Renewal Reminder',
          validation: {
            minLength: 3,
            maxLength: 100
          }
        },
        {
          key: 'description',
          label: 'Description',
          type: 'textarea',
          placeholder: 'Describe when this trigger should fire',
          rows: 3
        },
        {
          key: 'trigger_mode',
          label: 'Trigger Mode',
          type: 'select',
          required: true,
          defaultValue: 'specific_date',
          options: [
            { value: 'specific_date', label: 'Specific Date/Time' },
            { value: 'field_based', label: 'Based on Record Field' },
            { value: 'relative', label: 'Relative to Field' }
          ]
        }
      ]
    },
    {
      id: 'date_config',
      label: 'Date Configuration',
      icon: Clock,
      fields: [
        {
          key: 'specific_date',
          label: 'Target Date/Time',
          type: 'datetime',
          required: true,
          showWhen: (config) => config.trigger_mode === 'specific_date',
          placeholder: 'Select date and time'
        },
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'select',
          required: true,
          showWhen: (config) => config.trigger_mode !== 'specific_date',
          placeholder: 'Select pipeline',
          options: [] // Will be populated dynamically
        },
        {
          key: 'date_field',
          label: 'Date Field',
          type: 'field-select',
          required: true,
          showWhen: (config) => config.trigger_mode !== 'specific_date',
          placeholder: 'Select date field',
          fieldFilter: (field) => ['date', 'datetime'].includes(field.type)
        },
        {
          key: 'offset_value',
          label: 'Offset',
          type: 'number',
          showWhen: (config) => config.trigger_mode === 'relative',
          defaultValue: 0,
          placeholder: 'e.g., -7 for 7 days before'
        },
        {
          key: 'offset_unit',
          label: 'Offset Unit',
          type: 'select',
          showWhen: (config) => config.trigger_mode === 'relative',
          defaultValue: 'days',
          options: [
            { value: 'minutes', label: 'Minutes' },
            { value: 'hours', label: 'Hours' },
            { value: 'days', label: 'Days' },
            { value: 'weeks', label: 'Weeks' },
            { value: 'months', label: 'Months' }
          ]
        },
        {
          key: 'timezone',
          label: 'Timezone',
          type: 'select',
          required: true,
          defaultValue: 'UTC',
          options: [
            { value: 'UTC', label: 'UTC' },
            { value: 'America/New_York', label: 'Eastern Time' },
            { value: 'America/Chicago', label: 'Central Time' },
            { value: 'America/Denver', label: 'Mountain Time' },
            { value: 'America/Los_Angeles', label: 'Pacific Time' },
            { value: 'Europe/London', label: 'London' },
            { value: 'Europe/Paris', label: 'Paris' },
            { value: 'Asia/Tokyo', label: 'Tokyo' }
          ]
        }
      ]
    },
    {
      id: 'recurrence',
      label: 'Recurrence',
      icon: RefreshCw,
      collapsed: true,
      fields: [
        {
          key: 'recurrence',
          label: 'Enable Recurrence',
          type: 'boolean',
          defaultValue: false
        },
        {
          key: 'recurrence_pattern',
          label: 'Recurrence Pattern',
          type: 'select',
          showWhen: (config) => config.recurrence === true,
          defaultValue: 'daily',
          options: [
            { value: 'daily', label: 'Daily' },
            { value: 'weekly', label: 'Weekly' },
            { value: 'monthly', label: 'Monthly' },
            { value: 'yearly', label: 'Yearly' }
          ]
        },
        {
          key: 'recurrence_interval',
          label: 'Repeat Every',
          type: 'number',
          showWhen: (config) => config.recurrence === true,
          defaultValue: 1,
          min: 1,
          max: 100
        }
      ]
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings,
      collapsed: true,
      fields: [
        {
          key: 'active',
          label: 'Active',
          type: 'boolean',
          defaultValue: true
        }
      ]
    }
  ],

  outputs: [
    { key: 'trigger_time', type: 'datetime', label: 'Trigger Time' },
    { key: 'scheduled_time', type: 'datetime', label: 'Scheduled Time' },
    { key: 'offset_applied', type: 'string', label: 'Offset Applied' },
    { key: 'recurrence_count', type: 'number', label: 'Recurrence Count' }
  ]
};