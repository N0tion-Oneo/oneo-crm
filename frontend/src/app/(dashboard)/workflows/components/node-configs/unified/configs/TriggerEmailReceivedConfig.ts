import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Mail, Filter, Settings, FileText } from 'lucide-react';

export const TriggerEmailReceivedConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_EMAIL_RECEIVED,
  category: 'trigger',
  label: 'Email Received',
  description: 'Trigger when an email is received',
  icon: Mail,

  sections: [
    {
      id: 'basic',
      label: 'Basic Configuration',
      icon: Mail,
      fields: [
        {
          key: 'name',
          label: 'Trigger Name',
          type: 'text',
          required: true,
          placeholder: 'e.g., Support Email Handler',
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
          key: 'email_account',
          label: 'Email Account',
          type: 'select',
          required: true,
          placeholder: 'Select connected email account',
          options: [], // Will be populated dynamically
          optionsSource: 'unipileAccounts',
          optionsFilter: (account) => ['gmail', 'outlook', 'office365'].includes(account.channelType),
          optionsMap: (account) => ({
            value: account.id,
            label: `${account.accountName} (${account.channelType})`
          })
        }
      ]
    },
    {
      id: 'filters',
      label: 'Email Filters',
      icon: Filter,
      collapsed: true,
      fields: [
        {
          key: 'filter_type',
          label: 'Filter Type',
          type: 'select',
          defaultValue: 'all',
          options: [
            { value: 'all', label: 'All Emails' },
            { value: 'from', label: 'From Specific Sender' },
            { value: 'to', label: 'To Specific Recipient' },
            { value: 'subject', label: 'Subject Contains' },
            { value: 'body', label: 'Body Contains' },
            { value: 'has_attachment', label: 'Has Attachments' },
            { value: 'custom', label: 'Custom Rules' }
          ]
        },
        {
          key: 'from_filter',
          label: 'From Email',
          type: 'text',
          showWhen: (config) => config.filter_type === 'from',
          placeholder: 'sender@example.com or *@example.com',
          helpText: 'Use * for wildcard matching'
        },
        {
          key: 'to_filter',
          label: 'To Email',
          type: 'text',
          showWhen: (config) => config.filter_type === 'to',
          placeholder: 'recipient@example.com'
        },
        {
          key: 'subject_filter',
          label: 'Subject Contains',
          type: 'text',
          showWhen: (config) => config.filter_type === 'subject',
          placeholder: 'Keywords to search in subject'
        },
        {
          key: 'body_filter',
          label: 'Body Contains',
          type: 'text',
          showWhen: (config) => config.filter_type === 'body',
          placeholder: 'Keywords to search in body'
        },
        {
          key: 'custom_rules',
          label: 'Custom Filter Rules',
          type: 'json',
          showWhen: (config) => config.filter_type === 'custom',
          placeholder: '{\n  "from": ["*@important.com"],\n  "subject_contains": ["urgent", "priority"],\n  "has_attachment": true\n}',
          helpText: 'Advanced filter rules in JSON format'
        },
        {
          key: 'folder_filter',
          label: 'Folder/Label',
          type: 'text',
          placeholder: 'Inbox, Sent, or custom folder',
          helpText: 'Only process emails from specific folder'
        },
        {
          key: 'ignore_replies',
          label: 'Ignore Replies',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Skip emails that are replies to existing threads'
        }
      ]
    },
    {
      id: 'attachments',
      label: 'Attachments',
      icon: FileText,
      collapsed: true,
      fields: [
        {
          key: 'process_attachments',
          label: 'Process Attachments',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Extract and make attachments available to workflow'
        },
        {
          key: 'attachment_types',
          label: 'Allowed Attachment Types',
          type: 'multiselect',
          showWhen: (config) => config.process_attachments === true,
          options: [
            { value: 'pdf', label: 'PDF' },
            { value: 'doc', label: 'Word Documents' },
            { value: 'xls', label: 'Excel Spreadsheets' },
            { value: 'image', label: 'Images' },
            { value: 'zip', label: 'Archives' },
            { value: 'all', label: 'All Types' }
          ]
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
          key: 'mark_as_read',
          label: 'Mark as Read',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Mark email as read after processing'
        },
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
    { key: 'email_id', type: 'string', label: 'Email ID' },
    { key: 'from', type: 'string', label: 'From Address' },
    { key: 'to', type: 'array', label: 'To Addresses' },
    { key: 'cc', type: 'array', label: 'CC Addresses' },
    { key: 'subject', type: 'string', label: 'Subject' },
    { key: 'body_text', type: 'string', label: 'Body (Plain Text)' },
    { key: 'body_html', type: 'string', label: 'Body (HTML)' },
    { key: 'attachments', type: 'array', label: 'Attachments' },
    { key: 'received_at', type: 'datetime', label: 'Received At' },
    { key: 'thread_id', type: 'string', label: 'Thread ID' },
    { key: 'is_reply', type: 'boolean', label: 'Is Reply' }
  ]
};