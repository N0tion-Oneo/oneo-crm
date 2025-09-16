import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { UserCheck, Users, MessageSquare, Clock, Bell } from 'lucide-react';

export const ApprovalNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.APPROVAL,
  category: 'logic',
  label: 'Approval',
  description: 'Require human approval to continue workflow',
  icon: UserCheck,

  sections: [
    {
      id: 'basic',
      label: 'Basic Configuration',
      icon: UserCheck,
      fields: [
    {
      key: 'name',
      label: 'Approval Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., Manager Approval for Expense',
      validation: {
        minLength: 3,
        maxLength: 100
      }
    },
    {
      key: 'description',
      label: 'Description',
      type: 'textarea',
      placeholder: 'Describe what needs approval and why',
      rows: 3
        },
        {
          key: 'approval_type',
      label: 'Approval Type',
      type: 'select',
      required: true,
      defaultValue: 'single',
      options: [
        { value: 'single', label: 'Single Approver' },
        { value: 'all', label: 'All Approvers Must Approve' },
        { value: 'any', label: 'Any One Approver' },
        { value: 'majority', label: 'Majority Vote' },
        { value: 'weighted', label: 'Weighted Approval' }
      ]
        },
        {
          key: 'pipeline_id',
          label: 'Pipeline Context',
          type: 'pipeline',
          placeholder: 'Select pipeline for field access',
          helpText: 'Optional: Select a pipeline to access its fields'
        }
      ]
    },
    {
      id: 'approvers',
      label: 'Approver Configuration',
      icon: Users,
      fields: [
        {
          key: 'approver_type',
      label: 'Approver Selection',
      type: 'select',
      required: true,
      defaultValue: 'specific_users',
      options: [
        { value: 'specific_users', label: 'Specific Users' },
        { value: 'user_field', label: 'From Record Field' },
        { value: 'role', label: 'By Role' },
        { value: 'department', label: 'By Department' },
        { value: 'hierarchy', label: 'Manager Hierarchy' }
      ]
    },
    {
      key: 'approvers',
      label: 'Approvers',
      type: 'multiselect',
      required: true,
      showWhen: (config) => config.approver_type === 'specific_users',
      placeholder: 'Select users who can approve',
      options: [], // Will be populated dynamically
      optionsSource: 'users',
      optionsMap: (user) => ({
        value: user.id,
        label: `${user.first_name || ''} ${user.last_name || ''} (${user.email})`.trim()
      })
    },
    {
      key: 'approver_field',
      label: 'Approver Field',
      type: 'field-select',
      required: true,
      showWhen: (config) => config.approver_type === 'user_field',
      placeholder: 'Select field containing approver',
      fieldFilter: (field) => field.type === 'user' || field.type === 'relationship'
    },
    {
      key: 'role_id',
      label: 'Role',
      type: 'select',
      required: true,
      showWhen: (config) => config.approver_type === 'role',
      placeholder: 'Select role',
      options: [], // Will be populated dynamically
      optionsSource: 'userTypes',
      optionsMap: (userType) => ({
        value: userType.id,
        label: userType.name
      })
    },
    {
      key: 'department_id',
      label: 'Department',
      type: 'select',
      required: true,
      showWhen: (config) => config.approver_type === 'department',
      placeholder: 'Select department',
      options: [] // Will be populated with departments
    },
    {
      key: 'hierarchy_levels',
      label: 'Hierarchy Levels',
      type: 'number',
      showWhen: (config) => config.approver_type === 'hierarchy',
      defaultValue: 1,
      min: 1,
      max: 5,
      helperText: 'Number of management levels up'
        }
      ]
    },
    {
      id: 'message',
      label: 'Approval Message',
      icon: MessageSquare,
      fields: [
        {
          key: 'approval_message',
      label: 'Approval Request Message',
      type: 'textarea',
      required: true,
      placeholder: 'Please review and approve the following:\n\n{{summary}}',
      rows: 4,
      helperText: 'Message shown to approvers'
    },
    {
      key: 'approval_form',
      label: 'Include Approval Form',
      type: 'boolean',
      defaultValue: false,
      helperText: 'Allow approvers to provide feedback'
    },
    {
      key: 'form_fields',
      label: 'Form Fields',
      type: 'json',
      showWhen: (config) => config.approval_form === true,
      placeholder: '[\n  {"key": "comments", "label": "Comments", "type": "textarea", "required": false},\n  {"key": "amount_approved", "label": "Approved Amount", "type": "number"}\n]'
        }
      ]
    },
    {
      id: 'timeout',
      label: 'Timeout Settings',
      icon: Clock,
      collapsed: true,
      fields: [
        {
          key: 'timeout_enabled',
      label: 'Enable Timeout',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Auto-action if no response within time limit'
    },
    {
      key: 'timeout_hours',
      label: 'Timeout (Hours)',
      type: 'number',
      showWhen: (config) => config.timeout_enabled === true,
      defaultValue: 48,
      min: 1,
      max: 720,
      helperText: 'Hours to wait for approval'
    },
    {
      key: 'timeout_action',
      label: 'Timeout Action',
      type: 'select',
      showWhen: (config) => config.timeout_enabled === true,
      defaultValue: 'escalate',
      options: [
        { value: 'approve', label: 'Auto-Approve' },
        { value: 'reject', label: 'Auto-Reject' },
        { value: 'escalate', label: 'Escalate to Next Level' },
        { value: 'notify', label: 'Send Reminder' }
      ]
        }
      ]
    },
    {
      id: 'notifications',
      label: 'Notification Settings',
      icon: Bell,
      collapsed: true,
      fields: [
        {
          key: 'notification_method',
      label: 'Notification Method',
      type: 'multiselect',
      required: true,
      defaultValue: ['email', 'in_app'],
      options: [
        { value: 'email', label: 'Email' },
        { value: 'sms', label: 'SMS' },
        { value: 'in_app', label: 'In-App Notification' },
        { value: 'slack', label: 'Slack' }
      ]
    },
    {
      key: 'reminder_enabled',
      label: 'Send Reminders',
      type: 'boolean',
      defaultValue: true
    },
    {
      key: 'reminder_interval',
      label: 'Reminder Interval (Hours)',
      type: 'number',
      showWhen: (config) => config.reminder_enabled === true,
      defaultValue: 24,
      min: 1,
      max: 168
        },
        {
          key: 'approval_link',
      label: 'Generate Approval Link',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Create direct approve/reject links'
        }
      ]
    }
  ],
  outputs: [
    { key: 'approval_status', type: 'string', label: 'Approval Status' },
    { key: 'approved_by', type: 'array', label: 'Approved By' },
    { key: 'rejected_by', type: 'array', label: 'Rejected By' },
    { key: 'approval_comments', type: 'array', label: 'Comments' },
    { key: 'approval_form_data', type: 'object', label: 'Form Data' },
    { key: 'approval_timestamp', type: 'datetime', label: 'Decision Time' },
    { key: 'time_to_approval', type: 'number', label: 'Time to Approval (hours)' }
  ]
};