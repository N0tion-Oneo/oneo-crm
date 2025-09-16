import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Linkedin, MessageSquare, Settings, User, Clock } from 'lucide-react';

export const LinkedInNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.UNIPILE_SEND_LINKEDIN,
  category: 'action',
  label: 'Send LinkedIn Message',
  description: 'Send a LinkedIn message or InMail',
  icon: Linkedin,

  sections: [
    {
      id: 'basic',
      label: 'Basic Configuration',
      icon: Linkedin,
      fields: [
    {
      key: 'name',
      label: 'Action Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., Send LinkedIn Connection Request',
      validation: {
        minLength: 3,
        maxLength: 100
      }
    },
    {
      key: 'description',
      label: 'Description',
      type: 'textarea',
      placeholder: 'Describe what this action does',
      rows: 2
        },
        {
          key: 'linkedin_account',
          label: 'LinkedIn Account',
          type: 'select',
          required: true,
          placeholder: 'Select connected LinkedIn account',
          options: [], // Will be populated dynamically
          optionsSource: 'unipileAccounts',
          optionsFilter: (account) => account.channelType === 'linkedin',
          optionsMap: (account) => ({
            value: account.id,
            label: account.accountName || 'LinkedIn Account'
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
          key: 'message_type',
      label: 'Message Type',
      type: 'select',
      required: true,
      defaultValue: 'message',
      options: [
        { value: 'message', label: 'Direct Message' },
        { value: 'inmail', label: 'InMail' },
        { value: 'connection_request', label: 'Connection Request' }
      ]
    },
    {
      key: 'recipient_type',
      label: 'Recipient Type',
      type: 'select',
      required: true,
      defaultValue: 'profile_url',
      options: [
        { value: 'profile_url', label: 'LinkedIn Profile URL' },
        { value: 'email', label: 'Email Address' },
        { value: 'name', label: 'Full Name' },
        { value: 'record_field', label: 'From Record Field' }
      ]
    },
    {
      key: 'recipient_value',
      label: 'Recipient',
      type: 'expression',
      required: true,
      placeholder: '{{record.linkedin_url}} or https://linkedin.com/in/username',
      showWhen: (config) => config.recipient_type !== 'record_field'
    },
    {
      key: 'recipient_field',
      label: 'Recipient Field',
      type: 'field-select',
      required: true,
      showWhen: (config) => config.recipient_type === 'record_field',
      placeholder: 'Select field containing LinkedIn info'
        }
      ]
    },
    {
      id: 'content',
      label: 'Message Content',
      icon: MessageSquare,
      fields: [
        {
          key: 'connection_note',
      label: 'Connection Note',
      type: 'textarea',
      showWhen: (config) => config.message_type === 'connection_request',
      placeholder: "Hi {{record.first_name}}, I'd like to connect...",
      rows: 3,
      maxLength: 300,
      helperText: 'Max 300 characters for connection requests'
    },
    {
      key: 'message_content',
      label: 'Message Content',
      type: 'textarea',
      required: true,
      showWhen: (config) => config.message_type !== 'connection_request',
      placeholder: 'Your message content here. Use {{variables}} for dynamic content.',
      rows: 6
    },
    {
      key: 'use_template',
      label: 'Use Template',
      type: 'boolean',
      defaultValue: false
    },
    {
      key: 'template_id',
      label: 'Message Template',
      type: 'select',
      showWhen: (config) => config.use_template === true,
      placeholder: 'Select template',
      options: [] // Will be populated from content library
        },
        {
          key: 'personalization',
      label: 'Enable Personalization',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Use AI to personalize message based on profile'
    },
    {
      key: 'personalization_fields',
      label: 'Personalization Data',
      type: 'multiselect',
      showWhen: (config) => config.personalization === true,
      placeholder: 'Select fields to use for personalization',
      options: [] // Will be populated with available fields
        }
      ]
    },
    {
      id: 'scheduling',
      label: 'Scheduling & Tracking',
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
      key: 'track_opens',
      label: 'Track Opens',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Track when recipient opens the message'
    },
    {
      key: 'track_responses',
      label: 'Track Responses',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Monitor for recipient responses'
    },
    {
      key: 'follow_up',
      label: 'Enable Follow-up',
      type: 'boolean',
      defaultValue: false,
      helperText: 'Automatically send follow-up if no response'
        },
        {
          key: 'follow_up_days',
      label: 'Follow-up After (Days)',
      type: 'number',
      showWhen: (config) => config.follow_up === true,
      defaultValue: 3,
      min: 1,
      max: 30
        }
      ]
    }
  ],
  outputs: [
    { key: 'message_id', type: 'string', label: 'Message ID' },
    { key: 'conversation_id', type: 'string', label: 'Conversation ID' },
    { key: 'recipient_profile', type: 'object', label: 'Recipient Profile' },
    { key: 'sent_at', type: 'datetime', label: 'Sent At' },
    { key: 'delivery_status', type: 'string', label: 'Delivery Status' }
  ]
};