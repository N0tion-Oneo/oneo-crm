import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { MessageSquare, User, Settings, Clock, BarChart } from 'lucide-react';

export const SMSNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.UNIPILE_SEND_SMS,
  category: 'action',
  label: 'Send SMS',
  description: 'Send SMS message via UniPile',
  icon: MessageSquare,

  sections: [
    {
      id: 'basic',
      label: 'Basic Configuration',
      icon: MessageSquare,
      fields: [
    {
      key: 'name',
      label: 'Action Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., Send Appointment Reminder',
      validation: {
        minLength: 3,
        maxLength: 100
      }
    },
    {
      key: 'description',
      label: 'Description',
      type: 'textarea',
      placeholder: 'Describe what this SMS does',
      rows: 2
        },
        {
          key: 'sms_provider',
          label: 'SMS Provider',
          type: 'select',
          required: true,
          placeholder: 'Select SMS provider',
          options: [], // Will be populated dynamically
          optionsSource: 'unipileAccounts',
          optionsFilter: (account) => ['twilio', 'messagebird', 'sms', 'whatsapp'].includes(account.channelType),
          optionsMap: (account) => ({
            value: account.id,
            label: `${account.accountName} (${account.channelType})`
          })
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
      id: 'recipient',
      label: 'Recipient Configuration',
      icon: User,
      fields: [
        {
          key: 'recipient_type',
      label: 'Recipient Type',
      type: 'select',
      required: true,
      defaultValue: 'phone_number',
      options: [
        { value: 'phone_number', label: 'Phone Number' },
        { value: 'record_field', label: 'From Record Field' },
        { value: 'multiple', label: 'Multiple Recipients' }
      ]
    },
    {
      key: 'phone_number',
      label: 'Phone Number',
      type: 'expression',
      required: true,
      showWhen: (config) => config.recipient_type === 'phone_number',
      placeholder: '+1234567890 or {{record.phone}}',
      validation: {
        pattern: '^\\+?[1-9]\\d{1,14}$|^\\{\\{.*\\}\\}$',
        message: 'Must be a valid phone number or variable'
      }
    },
    {
      key: 'phone_field',
      label: 'Phone Field',
      type: 'field-select',
      required: true,
      showWhen: (config) => config.recipient_type === 'record_field',
      placeholder: 'Select field containing phone number',
      fieldFilter: (field) => field.type === 'phone' || field.type === 'text'
    },
    {
      key: 'multiple_recipients',
      label: 'Recipients',
      type: 'textarea',
      required: true,
      showWhen: (config) => config.recipient_type === 'multiple',
      placeholder: 'One phone number per line or comma-separated',
      rows: 4
        }
      ]
    },
    {
      id: 'content',
      label: 'Message Content',
      icon: MessageSquare,
      fields: [
        {
          key: 'message',
      label: 'Message',
      type: 'textarea',
      required: true,
      placeholder: 'Your SMS message. Use {{variables}} for dynamic content.',
      rows: 4,
      maxLength: 1600,
      helperText: 'Standard SMS: 160 chars, Long SMS: up to 1600 chars'
    },
    {
      key: 'use_template',
      label: 'Use Template',
      type: 'boolean',
      defaultValue: false
    },
    {
      key: 'template_id',
      label: 'SMS Template',
      type: 'select',
      showWhen: (config) => config.use_template === true,
      placeholder: 'Select template',
      options: [] // Will be populated from content library
        },
        {
          key: 'sender_id',
      label: 'Sender ID',
      type: 'text',
      placeholder: 'Your company name or number',
      helperText: 'Optional custom sender ID (if supported)'
    },
    {
      key: 'message_type',
      label: 'Message Type',
      type: 'select',
      defaultValue: 'promotional',
      options: [
        { value: 'promotional', label: 'Promotional' },
        { value: 'transactional', label: 'Transactional' },
        { value: 'otp', label: 'OTP/Verification' }
      ]
        }
      ]
    },
    {
      id: 'scheduling',
      label: 'Scheduling & Delivery',
      icon: Clock,
      collapsed: true,
      fields: [
        {
          key: 'schedule_send',
      label: 'Schedule Send',
      type: 'boolean',
      defaultValue: false
    },
    {
      key: 'send_at',
      label: 'Send At',
      type: 'datetime',
      showWhen: (config) => config.schedule_send === true,
      placeholder: 'Select date and time'
    },
    {
      key: 'respect_quiet_hours',
      label: 'Respect Quiet Hours',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Avoid sending during night hours (10 PM - 8 AM)'
        },
        {
          key: 'url_shortening',
      label: 'Shorten URLs',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Automatically shorten links in message'
    },
    {
      key: 'track_delivery',
      label: 'Track Delivery',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Track SMS delivery status'
    },
    {
      key: 'track_clicks',
      label: 'Track Link Clicks',
      type: 'boolean',
      defaultValue: false,
      showWhen: (config) => config.url_shortening === true,
      helperText: 'Track when recipients click shortened links'
        }
      ]
    },
    {
      id: 'tracking',
      label: 'Tracking & Replies',
      icon: BarChart,
      collapsed: true,
      fields: [
        {
          key: 'enable_replies',
      label: 'Enable Replies',
      type: 'boolean',
      defaultValue: false,
      helperText: 'Allow recipients to reply to this SMS'
    },
    {
      key: 'reply_action',
      label: 'Reply Action',
      type: 'select',
      showWhen: (config) => config.enable_replies === true,
      defaultValue: 'create_note',
      options: [
        { value: 'create_note', label: 'Create Note on Record' },
        { value: 'trigger_workflow', label: 'Trigger Another Workflow' },
        { value: 'send_notification', label: 'Send Notification' }
      ]
        }
      ]
    }
  ],
  outputs: [
    { key: 'message_id', type: 'string', label: 'Message ID' },
    { key: 'delivery_status', type: 'string', label: 'Delivery Status' },
    { key: 'sent_at', type: 'datetime', label: 'Sent At' },
    { key: 'recipient_count', type: 'number', label: 'Recipient Count' },
    { key: 'cost', type: 'number', label: 'Message Cost' }
  ]
};