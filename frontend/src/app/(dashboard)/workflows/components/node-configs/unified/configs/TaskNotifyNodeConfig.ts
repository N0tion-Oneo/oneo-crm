import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Bell, User, Calendar } from 'lucide-react';

export const TaskNotifyNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TASK_NOTIFY,
  label: 'Create Task / Notify',
  description: 'Create a task or send a notification',
  icon: Bell,
  category: 'action',

  sections: [
    {
      id: 'action_type',
      label: 'Action Type',
      icon: Bell,
      fields: [
        {
          key: 'action',
          label: 'Action',
          type: 'select',
          required: true,
          defaultValue: 'notification',
          options: [
            { label: 'Send Notification', value: 'notification' },
            { label: 'Create Task', value: 'task' },
            { label: 'Both', value: 'both' }
          ],
          helpText: 'What action to perform'
        }
      ]
    },
    {
      id: 'notification',
      label: 'Notification Settings',
      showWhen: (c) => c.action === 'notification' || c.action === 'both',
      fields: [
        {
          key: 'notification_type',
          label: 'Notification Type',
          type: 'select',
          required: true,
          defaultValue: 'info',
          options: [
            { label: 'Info', value: 'info' },
            { label: 'Success', value: 'success' },
            { label: 'Warning', value: 'warning' },
            { label: 'Error', value: 'error' },
            { label: 'Alert', value: 'alert' }
          ],
          helpText: 'Type of notification'
        },
        {
          key: 'notification_title',
          label: 'Notification Title',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: 'Workflow Update: {{workflow_name}}',
          helpText: 'Title of the notification'
        },
        {
          key: 'notification_message',
          label: 'Notification Message',
          type: 'textarea',
          required: true,
          allowExpressions: true,
          placeholder: 'Record {{record.name}} has been processed successfully',
          helpText: 'Notification message content',
          rows: 3
        },
        {
          key: 'notification_channels',
          label: 'Notification Channels',
          type: 'multiselect',
          defaultValue: ['in_app'],
          options: [
            { label: 'In-App', value: 'in_app' },
            { label: 'Email', value: 'email' },
            { label: 'SMS', value: 'sms' },
            { label: 'Push', value: 'push' },
            { label: 'Slack', value: 'slack' }
          ],
          helpText: 'Where to send the notification'
        }
      ]
    },
    {
      id: 'task',
      label: 'Task Settings',
      icon: Calendar,
      showWhen: (c) => c.action === 'task' || c.action === 'both',
      fields: [
        {
          key: 'task_title',
          label: 'Task Title',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: 'Follow up on {{record.name}}',
          helpText: 'Title of the task'
        },
        {
          key: 'task_description',
          label: 'Task Description',
          type: 'textarea',
          allowExpressions: true,
          placeholder: 'Review and approve the changes made to {{record.name}}',
          helpText: 'Detailed task description',
          rows: 4
        },
        {
          key: 'task_priority',
          label: 'Priority',
          type: 'select',
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
          key: 'task_due_date',
          label: 'Due Date',
          type: 'select',
          defaultValue: 'relative',
          options: [
            { label: 'Relative (from now)', value: 'relative' },
            { label: 'Specific Date', value: 'specific' },
            { label: 'From Variable', value: 'variable' }
          ],
          helpText: 'How to set the due date'
        },
        {
          key: 'due_in_days',
          label: 'Due In (days)',
          type: 'number',
          showWhen: (c) => c.task_due_date === 'relative',
          defaultValue: 1,
          min: 0,
          max: 365,
          helpText: 'Days from now when task is due'
        },
        {
          key: 'specific_due_date',
          label: 'Due Date',
          type: 'datetime',
          showWhen: (c) => c.task_due_date === 'specific',
          helpText: 'Specific due date and time'
        },
        {
          key: 'due_date_variable',
          label: 'Due Date Variable',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.task_due_date === 'variable',
          placeholder: '{{due_date}}',
          helpText: 'Variable containing the due date'
        },
        {
          key: 'task_status',
          label: 'Initial Status',
          type: 'select',
          defaultValue: 'pending',
          options: [
            { label: 'Pending', value: 'pending' },
            { label: 'In Progress', value: 'in_progress' },
            { label: 'Waiting', value: 'waiting' },
            { label: 'Deferred', value: 'deferred' }
          ],
          helpText: 'Initial status of the task'
        }
      ]
    },
    {
      id: 'assignment',
      label: 'Assignment',
      icon: User,
      showWhen: (c) => c.action === 'task' || c.action === 'both' || c.action === 'notification',
      fields: [
        {
          key: 'assignment_type',
          label: 'Assign To',
          type: 'select',
          required: true,
          defaultValue: 'user',
          options: [
            { label: 'Specific User', value: 'user' },
            { label: 'User Role', value: 'role' },
            { label: 'Team', value: 'team' },
            { label: 'From Variable', value: 'variable' },
            { label: 'Record Owner', value: 'owner' }
          ],
          helpText: 'Who to assign the task/notification to'
        },
        {
          key: 'assigned_user',
          label: 'User',
          type: 'user',
          required: true,
          showWhen: (c) => c.assignment_type === 'user',
          helpText: 'Select a specific user'
        },
        {
          key: 'assigned_role',
          label: 'Role',
          type: 'select',
          required: true,
          showWhen: (c) => c.assignment_type === 'role',
          options: [
            { label: 'Admin', value: 'admin' },
            { label: 'Manager', value: 'manager' },
            { label: 'User', value: 'user' },
            { label: 'Viewer', value: 'viewer' }
          ],
          helpText: 'Assign to all users with this role'
        },
        {
          key: 'assigned_team',
          label: 'Team',
          type: 'team',
          required: true,
          showWhen: (c) => c.assignment_type === 'team',
          helpText: 'Select a team'
        },
        {
          key: 'assignment_variable',
          label: 'Assignment Variable',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.assignment_type === 'variable',
          placeholder: '{{assigned_to}}',
          helpText: 'Variable containing user/team ID'
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
          key: 'link_to_record',
          label: 'Link to Record',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Link task/notification to current record'
        },
        {
          key: 'record_variable',
          label: 'Record Variable',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.link_to_record,
          defaultValue: '{{record}}',
          placeholder: '{{record}}',
          helpText: 'Variable containing the record to link'
        },
        {
          key: 'send_reminders',
          label: 'Send Reminders',
          type: 'boolean',
          defaultValue: false,
          showWhen: (c) => c.action === 'task' || c.action === 'both',
          helpText: 'Send reminder notifications for tasks'
        },
        {
          key: 'reminder_before_hours',
          label: 'Reminder Before (hours)',
          type: 'number',
          showWhen: (c) => c.send_reminders,
          defaultValue: 24,
          min: 1,
          max: 168,
          helpText: 'Hours before due date to send reminder'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.action) {
      errors.action = 'Action type is required';
    }
    
    if ((config.action === 'notification' || config.action === 'both') && !config.notification_title) {
      errors.notification_title = 'Notification title is required';
    }
    
    if ((config.action === 'task' || config.action === 'both') && !config.task_title) {
      errors.task_title = 'Task title is required';
    }
    
    if (!config.assignment_type) {
      errors.assignment_type = 'Assignment is required';
    }
    
    return errors;
  },

  defaults: {
    action: 'notification',
    notification_type: 'info',
    notification_channels: ['in_app'],
    task_priority: 'medium',
    task_due_date: 'relative',
    due_in_days: 1,
    task_status: 'pending',
    assignment_type: 'user',
    link_to_record: true,
    record_variable: '{{record}}',
    send_reminders: false,
    reminder_before_hours: 24
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};