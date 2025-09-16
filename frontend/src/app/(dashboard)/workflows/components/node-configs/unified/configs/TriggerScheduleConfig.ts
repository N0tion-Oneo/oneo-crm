import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Calendar, Clock, RefreshCw } from 'lucide-react';

export const TriggerScheduleConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_SCHEDULE,
  label: 'Schedule Trigger',
  description: 'Trigger workflow on a recurring schedule',
  icon: Calendar,
  category: 'trigger',

  sections: [
    {
      id: 'schedule',
      label: 'Schedule Configuration',
      icon: Calendar,
      fields: [
        {
          key: 'schedule_type',
          label: 'Schedule Type',
          type: 'select',
          required: true,
          defaultValue: 'cron',
          options: [
            { label: 'Cron Expression', value: 'cron' },
            { label: 'Interval', value: 'interval' },
            { label: 'Daily', value: 'daily' },
            { label: 'Weekly', value: 'weekly' },
            { label: 'Monthly', value: 'monthly' }
          ],
          helpText: 'How to define the schedule'
        },
        {
          key: 'cron_expression',
          label: 'Cron Expression',
          type: 'text',
          required: true,
          showWhen: (c) => c.schedule_type === 'cron',
          placeholder: '0 9 * * 1-5',
          helpText: 'Cron expression (e.g., "0 9 * * 1-5" for weekdays at 9 AM)'
        },
        {
          key: 'interval_value',
          label: 'Interval',
          type: 'number',
          required: true,
          showWhen: (c) => c.schedule_type === 'interval',
          min: 1,
          placeholder: '30',
          helpText: 'Interval value'
        },
        {
          key: 'interval_unit',
          label: 'Interval Unit',
          type: 'select',
          required: true,
          showWhen: (c) => c.schedule_type === 'interval',
          defaultValue: 'minutes',
          options: [
            { label: 'Minutes', value: 'minutes' },
            { label: 'Hours', value: 'hours' },
            { label: 'Days', value: 'days' },
            { label: 'Weeks', value: 'weeks' }
          ]
        },
        {
          key: 'daily_time',
          label: 'Time of Day',
          type: 'text',
          required: true,
          showWhen: (c) => c.schedule_type === 'daily',
          placeholder: '09:00',
          helpText: 'Time in 24-hour format (HH:MM)'
        },
        {
          key: 'weekly_days',
          label: 'Days of Week',
          type: 'multiselect',
          required: true,
          showWhen: (c) => c.schedule_type === 'weekly',
          options: [
            { label: 'Monday', value: '1' },
            { label: 'Tuesday', value: '2' },
            { label: 'Wednesday', value: '3' },
            { label: 'Thursday', value: '4' },
            { label: 'Friday', value: '5' },
            { label: 'Saturday', value: '6' },
            { label: 'Sunday', value: '0' }
          ],
          helpText: 'Select days to run'
        },
        {
          key: 'weekly_time',
          label: 'Time of Day',
          type: 'text',
          required: true,
          showWhen: (c) => c.schedule_type === 'weekly',
          placeholder: '09:00',
          helpText: 'Time in 24-hour format (HH:MM)'
        },
        {
          key: 'monthly_day',
          label: 'Day of Month',
          type: 'number',
          required: true,
          showWhen: (c) => c.schedule_type === 'monthly',
          min: 1,
          max: 31,
          placeholder: '1',
          helpText: 'Day of month to run (1-31)'
        },
        {
          key: 'monthly_time',
          label: 'Time of Day',
          type: 'text',
          required: true,
          showWhen: (c) => c.schedule_type === 'monthly',
          placeholder: '09:00',
          helpText: 'Time in 24-hour format (HH:MM)'
        },
        {
          key: 'timezone',
          label: 'Timezone',
          type: 'select',
          required: true,
          defaultValue: 'UTC',
          options: [
            { label: 'UTC', value: 'UTC' },
            { label: 'America/New_York', value: 'America/New_York' },
            { label: 'America/Chicago', value: 'America/Chicago' },
            { label: 'America/Los_Angeles', value: 'America/Los_Angeles' },
            { label: 'Europe/London', value: 'Europe/London' },
            { label: 'Europe/Paris', value: 'Europe/Paris' },
            { label: 'Asia/Tokyo', value: 'Asia/Tokyo' },
            { label: 'Australia/Sydney', value: 'Australia/Sydney' }
          ],
          helpText: 'Timezone for schedule execution'
        }
      ]
    },
    {
      id: 'execution',
      label: 'Execution Settings',
      icon: RefreshCw,
      collapsed: true,
      fields: [
        {
          key: 'start_date',
          label: 'Start Date',
          type: 'datetime',
          helpText: 'When to start the schedule (optional)'
        },
        {
          key: 'end_date',
          label: 'End Date',
          type: 'datetime',
          helpText: 'When to stop the schedule (optional)'
        },
        {
          key: 'max_executions',
          label: 'Max Executions',
          type: 'number',
          min: 0,
          placeholder: '0',
          helpText: 'Maximum number of executions (0 = unlimited)'
        },
        {
          key: 'catch_up',
          label: 'Catch Up Missed Runs',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Execute missed runs when schedule resumes'
        },
        {
          key: 'concurrent_execution',
          label: 'Allow Concurrent Execution',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Allow multiple instances to run simultaneously'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Settings',
      icon: Clock,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'jitter',
          label: 'Jitter (seconds)',
          type: 'number',
          defaultValue: 0,
          min: 0,
          max: 300,
          helpText: 'Random delay to prevent simultaneous executions'
        },
        {
          key: 'retry_on_failure',
          label: 'Retry on Failure',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Retry if execution fails'
        },
        {
          key: 'retry_count',
          label: 'Retry Count',
          type: 'number',
          showWhen: (c) => c.retry_on_failure,
          defaultValue: 3,
          min: 1,
          max: 10,
          helpText: 'Number of retry attempts'
        },
        {
          key: 'timeout_minutes',
          label: 'Timeout (minutes)',
          type: 'number',
          defaultValue: 60,
          min: 1,
          max: 1440,
          helpText: 'Maximum execution time before timeout'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.schedule_type) {
      errors.schedule_type = 'Schedule type is required';
    }
    
    if (config.schedule_type === 'cron' && !config.cron_expression) {
      errors.cron_expression = 'Cron expression is required';
    }
    
    if (config.schedule_type === 'interval') {
      if (!config.interval_value) {
        errors.interval_value = 'Interval value is required';
      }
      if (!config.interval_unit) {
        errors.interval_unit = 'Interval unit is required';
      }
    }
    
    return errors;
  },

  defaults: {
    schedule_type: 'cron',
    timezone: 'UTC',
    interval_unit: 'minutes',
    catch_up: false,
    concurrent_execution: false,
    jitter: 0,
    retry_on_failure: true,
    retry_count: 3,
    timeout_minutes: 60
  },

  features: {
    supportsExpressions: false,
    supportsVariables: false,
    supportsTesting: true,
    supportsTemplates: false
  }
};