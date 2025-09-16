import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { CheckSquare, Calendar, User, AlertCircle, Settings } from 'lucide-react';

export const CreateFollowUpTaskNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.CREATE_FOLLOW_UP_TASK,
  label: 'Create Follow-up Task',
  description: 'Create a task for follow-up actions',
  icon: CheckSquare,
  category: 'action',

  sections: [
    {
      id: 'task_details',
      label: 'Task Details',
      icon: CheckSquare,
      fields: [
        {
          key: 'task_title',
          label: 'Task Title',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: 'Follow up with {{contact.name}}',
          helpText: 'Title of the task to create'
        },
        {
          key: 'description',
          label: 'Task Description',
          type: 'textarea',
          required: false,
          allowExpressions: true,
          placeholder: 'Contact expressed interest in {{product}}. Schedule a demo call.',
          helpText: 'Detailed description of what needs to be done',
          rows: 4
        },
        {
          key: 'task_type',
          label: 'Task Type',
          type: 'select',
          required: true,
          defaultValue: 'follow_up',
          options: [
            { label: 'Follow-up Call', value: 'follow_up_call' },
            { label: 'Follow-up Email', value: 'follow_up_email' },
            { label: 'Meeting', value: 'meeting' },
            { label: 'Review', value: 'review' },
            { label: 'Data Entry', value: 'data_entry' },
            { label: 'Research', value: 'research' },
            { label: 'Custom Task', value: 'custom' }
          ],
          helpText: 'Type of follow-up task'
        },
        {
          key: 'custom_task_type',
          label: 'Custom Task Type',
          type: 'text',
          showWhen: (config) => config.task_type === 'custom',
          placeholder: 'Enter custom task type',
          helpText: 'Specify your custom task type'
        }
      ]
    },
    {
      id: 'scheduling',
      label: 'Scheduling',
      icon: Calendar,
      fields: [
        {
          key: 'due_date_type',
          label: 'Due Date Type',
          type: 'select',
          required: true,
          defaultValue: 'relative',
          options: [
            { label: 'Relative (from now)', value: 'relative' },
            { label: 'Specific Date', value: 'specific' },
            { label: 'From Field Value', value: 'field' },
            { label: 'Business Days', value: 'business_days' }
          ],
          helpText: 'How to set the due date'
        },
        {
          key: 'relative_days',
          label: 'Days from Now',
          type: 'number',
          required: true,
          defaultValue: 1,
          showWhen: (config) => config.due_date_type === 'relative',
          min: 0,
          max: 365,
          helpText: 'Number of days from task creation'
        },
        {
          key: 'business_days',
          label: 'Business Days from Now',
          type: 'number',
          required: true,
          defaultValue: 1,
          showWhen: (config) => config.due_date_type === 'business_days',
          min: 0,
          max: 100,
          helpText: 'Number of business days (excluding weekends)'
        },
        {
          key: 'specific_date',
          label: 'Specific Due Date',
          type: 'date',
          required: true,
          showWhen: (config) => config.due_date_type === 'specific',
          helpText: 'Exact date when task is due'
        },
        {
          key: 'date_field',
          label: 'Date Field',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.due_date_type === 'field',
          placeholder: '{{record.follow_up_date}}',
          helpText: 'Field containing the due date'
        },
        {
          key: 'due_time',
          label: 'Due Time',
          type: 'time',
          required: false,
          helpText: 'Optional specific time for the task'
        },
        {
          key: 'reminder',
          label: 'Set Reminder',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Send reminder before due date'
        },
        {
          key: 'reminder_minutes',
          label: 'Reminder Time (minutes before)',
          type: 'select',
          showWhen: (config) => config.reminder === true,
          defaultValue: '60',
          options: [
            { label: '15 minutes', value: '15' },
            { label: '30 minutes', value: '30' },
            { label: '1 hour', value: '60' },
            { label: '2 hours', value: '120' },
            { label: '1 day', value: '1440' },
            { label: '2 days', value: '2880' }
          ],
          helpText: 'When to send reminder'
        }
      ]
    },
    {
      id: 'assignment',
      label: 'Assignment',
      icon: User,
      fields: [
        {
          key: 'assignment_type',
          label: 'Assignment Type',
          type: 'select',
          required: true,
          defaultValue: 'specific_user',
          options: [
            { label: 'Specific User', value: 'specific_user' },
            { label: 'Current User', value: 'current_user' },
            { label: 'Record Owner', value: 'record_owner' },
            { label: 'Team', value: 'team' },
            { label: 'Round Robin', value: 'round_robin' },
            { label: 'From Field', value: 'field' }
          ],
          helpText: 'Who to assign the task to'
        },
        {
          key: 'assigned_to',
          label: 'Assign To',
          type: 'user_select',
          required: true,
          showWhen: (config) => config.assignment_type === 'specific_user',
          helpText: 'Select user to assign task to'
        },
        {
          key: 'team_id',
          label: 'Team',
          type: 'team_select',
          required: true,
          showWhen: (config) => config.assignment_type === 'team',
          helpText: 'Select team to assign task to'
        },
        {
          key: 'assignment_field',
          label: 'Assignment Field',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.assignment_type === 'field',
          placeholder: '{{record.assigned_user_id}}',
          helpText: 'Field containing user ID to assign to'
        },
        {
          key: 'round_robin_pool',
          label: 'Round Robin Pool',
          type: 'multiselect',
          required: true,
          showWhen: (config) => config.assignment_type === 'round_robin',
          placeholder: 'Select users for round robin',
          helpText: 'Users to rotate assignments between',
          options: [] // Will be populated with users
        }
      ]
    },
    {
      id: 'priority',
      label: 'Priority & Settings',
      icon: AlertCircle,
      fields: [
        {
          key: 'priority',
          label: 'Priority',
          type: 'select',
          required: true,
          defaultValue: 'medium',
          options: [
            { label: 'Low', value: 'low' },
            { label: 'Medium', value: 'medium' },
            { label: 'High', value: 'high' },
            { label: 'Urgent', value: 'urgent' }
          ],
          helpText: 'Task priority level'
        },
        {
          key: 'status',
          label: 'Initial Status',
          type: 'select',
          required: true,
          defaultValue: 'pending',
          options: [
            { label: 'Pending', value: 'pending' },
            { label: 'In Progress', value: 'in_progress' },
            { label: 'Waiting', value: 'waiting' },
            { label: 'Scheduled', value: 'scheduled' }
          ],
          helpText: 'Initial status of the task'
        },
        {
          key: 'category',
          label: 'Task Category',
          type: 'select',
          defaultValue: 'sales',
          options: [
            { label: 'Sales', value: 'sales' },
            { label: 'Support', value: 'support' },
            { label: 'Marketing', value: 'marketing' },
            { label: 'Operations', value: 'operations' },
            { label: 'Other', value: 'other' }
          ],
          helpText: 'Category for task organization'
        },
        {
          key: 'tags',
          label: 'Tags',
          type: 'array',
          placeholder: 'Add tags',
          helpText: 'Tags for task filtering and organization',
          arrayConfig: {
            addLabel: 'Add Tag',
            itemLabel: 'Tag',
            fields: [
              {
                key: 'tag',
                label: 'Tag',
                type: 'text',
                placeholder: 'Enter tag'
              }
            ]
          }
        }
      ]
    },
    {
      id: 'context',
      label: 'Context & Relationships',
      icon: Settings,
      fields: [
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'pipeline_select',
          required: false,
          helpText: 'Pipeline to associate task with'
        },
        {
          key: 'related_record_id',
          label: 'Related Record',
          type: 'text',
          allowExpressions: true,
          placeholder: '{{record.id}}',
          helpText: 'ID of related record (contact, deal, etc.)'
        },
        {
          key: 'related_record_type',
          label: 'Related Record Type',
          type: 'text',
          placeholder: 'contact',
          helpText: 'Type of related record'
        },
        {
          key: 'additional_context',
          label: 'Additional Context',
          type: 'json',
          placeholder: '{"key": "value"}',
          helpText: 'Additional context data for the task'
        },
        {
          key: 'notification_settings',
          label: 'Notifications',
          type: 'object',
          fields: [
            {
              key: 'notify_assignee',
              label: 'Notify Assignee',
              type: 'boolean',
              defaultValue: true,
              helpText: 'Send notification to assigned user'
            },
            {
              key: 'notify_creator',
              label: 'Notify Creator',
              type: 'boolean',
              defaultValue: false,
              helpText: 'Send notification to task creator'
            },
            {
              key: 'notification_channels',
              label: 'Notification Channels',
              type: 'multiselect',
              defaultValue: ['email'],
              options: [
                { label: 'Email', value: 'email' },
                { label: 'In-App', value: 'in_app' },
                { label: 'SMS', value: 'sms' },
                { label: 'Slack', value: 'slack' }
              ],
              helpText: 'How to send notifications'
            }
          ]
        }
      ]
    }
  ]
};