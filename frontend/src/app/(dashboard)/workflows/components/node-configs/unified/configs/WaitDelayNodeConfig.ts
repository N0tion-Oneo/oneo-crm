import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Clock, Calendar } from 'lucide-react';

export const WaitDelayNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.WAIT_DELAY,
  label: 'Wait / Delay',
  description: 'Pause workflow execution for a specified time',
  icon: Clock,
  category: 'control',

  sections: [
    {
      id: 'delay_config',
      label: 'Delay Configuration',
      icon: Clock,
      fields: [
        {
          key: 'delay_type',
          label: 'Delay Type',
          type: 'select',
          required: true,
          defaultValue: 'duration',
          options: [
            { label: 'Fixed Duration', value: 'duration' },
            { label: 'Until Specific Time', value: 'until_time' },
            { label: 'Until Date/Time', value: 'until_datetime' },
            { label: 'Dynamic Duration', value: 'dynamic' },
            { label: 'Business Hours', value: 'business_hours' }
          ],
          helpText: 'Type of delay to apply'
        },
        {
          key: 'duration_value',
          label: 'Duration',
          type: 'number',
          required: true,
          showWhen: (c) => c.delay_type === 'duration',
          min: 1,
          defaultValue: 5,
          helpText: 'Duration value'
        },
        {
          key: 'duration_unit',
          label: 'Duration Unit',
          type: 'select',
          required: true,
          showWhen: (c) => c.delay_type === 'duration',
          defaultValue: 'minutes',
          options: [
            { label: 'Seconds', value: 'seconds' },
            { label: 'Minutes', value: 'minutes' },
            { label: 'Hours', value: 'hours' },
            { label: 'Days', value: 'days' },
            { label: 'Weeks', value: 'weeks' }
          ]
        },
        {
          key: 'until_time',
          label: 'Time',
          type: 'text',
          required: true,
          showWhen: (c) => c.delay_type === 'until_time',
          placeholder: '14:30',
          helpText: 'Time to wait until (24-hour format)'
        },
        {
          key: 'until_datetime',
          label: 'Date and Time',
          type: 'datetime',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.delay_type === 'until_datetime',
          helpText: 'Specific date and time to wait until'
        },
        {
          key: 'dynamic_duration',
          label: 'Dynamic Duration',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.delay_type === 'dynamic',
          placeholder: '{{delay_seconds}}',
          helpText: 'Variable containing delay duration in seconds'
        },
        {
          key: 'business_hours_delay',
          label: 'Business Hours Delay',
          type: 'number',
          required: true,
          showWhen: (c) => c.delay_type === 'business_hours',
          min: 1,
          defaultValue: 1,
          helpText: 'Number of business hours to wait'
        }
      ]
    },
    {
      id: 'business_hours',
      label: 'Business Hours Settings',
      icon: Calendar,
      showWhen: (c) => c.delay_type === 'business_hours',
      fields: [
        {
          key: 'business_days',
          label: 'Business Days',
          type: 'multiselect',
          defaultValue: ['1', '2', '3', '4', '5'],
          options: [
            { label: 'Monday', value: '1' },
            { label: 'Tuesday', value: '2' },
            { label: 'Wednesday', value: '3' },
            { label: 'Thursday', value: '4' },
            { label: 'Friday', value: '5' },
            { label: 'Saturday', value: '6' },
            { label: 'Sunday', value: '0' }
          ],
          helpText: 'Days considered as business days'
        },
        {
          key: 'business_start_time',
          label: 'Business Start Time',
          type: 'text',
          defaultValue: '09:00',
          placeholder: '09:00',
          helpText: 'Business hours start time (24-hour format)'
        },
        {
          key: 'business_end_time',
          label: 'Business End Time',
          type: 'text',
          defaultValue: '17:00',
          placeholder: '17:00',
          helpText: 'Business hours end time (24-hour format)'
        },
        {
          key: 'timezone',
          label: 'Timezone',
          type: 'select',
          defaultValue: 'UTC',
          options: [
            { label: 'UTC', value: 'UTC' },
            { label: 'America/New_York', value: 'America/New_York' },
            { label: 'America/Chicago', value: 'America/Chicago' },
            { label: 'America/Los_Angeles', value: 'America/Los_Angeles' },
            { label: 'Europe/London', value: 'Europe/London' },
            { label: 'Europe/Paris', value: 'Europe/Paris' }
          ],
          helpText: 'Timezone for business hours'
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
          key: 'skip_weekends',
          label: 'Skip Weekends',
          type: 'boolean',
          defaultValue: false,
          showWhen: (c) => c.delay_type !== 'business_hours',
          helpText: 'Skip weekend days when calculating delay'
        },
        {
          key: 'skip_holidays',
          label: 'Skip Holidays',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Skip configured holidays'
        },
        {
          key: 'jitter_seconds',
          label: 'Jitter (seconds)',
          type: 'number',
          defaultValue: 0,
          min: 0,
          max: 300,
          helpText: 'Random variation to add to delay'
        },
        {
          key: 'max_wait_time',
          label: 'Max Wait Time (hours)',
          type: 'number',
          min: 1,
          max: 720,
          helpText: 'Maximum time to wait (safety limit)'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.delay_type) {
      errors.delay_type = 'Delay type is required';
    }
    
    if (config.delay_type === 'duration') {
      if (!config.duration_value) {
        errors.duration_value = 'Duration value is required';
      }
      if (!config.duration_unit) {
        errors.duration_unit = 'Duration unit is required';
      }
    }
    
    if (config.delay_type === 'until_time' && !config.until_time) {
      errors.until_time = 'Time is required';
    }
    
    if (config.delay_type === 'until_datetime' && !config.until_datetime) {
      errors.until_datetime = 'Date and time is required';
    }
    
    return errors;
  },

  defaults: {
    delay_type: 'duration',
    duration_value: 5,
    duration_unit: 'minutes',
    business_days: ['1', '2', '3', '4', '5'],
    business_start_time: '09:00',
    business_end_time: '17:00',
    timezone: 'UTC',
    business_hours_delay: 1,
    skip_weekends: false,
    skip_holidays: false,
    jitter_seconds: 0
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};