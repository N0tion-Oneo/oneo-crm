import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { MessageSquare } from 'lucide-react';

export const TriggerWhatsAppMessageConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_WHATSAPP_MESSAGE,
  label: 'WhatsApp Message Trigger',
  description: 'Triggers when a WhatsApp message is received',
  icon: MessageSquare,
  category: 'trigger',

  sections: [
    {
      id: 'message_filters',
      label: 'Message Filters',
      icon: MessageSquare,
      fields: [
        {
          key: 'filter_type',
          label: 'Filter Type',
          type: 'select',
          required: true,
          defaultValue: 'all',
          options: [
            { label: 'All Messages', value: 'all' },
            { label: 'From Specific Number', value: 'specific_number' },
            { label: 'First-time Messages', value: 'first_time' },
            { label: 'Group Messages', value: 'group_messages' },
            { label: 'Direct Messages Only', value: 'direct_only' }
          ],
          helpText: 'Type of WhatsApp messages to trigger on'
        },
        {
          key: 'specific_number',
          label: 'Phone Number',
          type: 'text',
          required: true,
          showWhen: (c) => c.filter_type === 'specific_number',
          placeholder: '+1234567890',
          helpText: 'Phone number to filter messages from (with country code)'
        },
        {
          key: 'contains_keywords',
          label: 'Contains Keywords',
          type: 'text',
          placeholder: 'order, help, support',
          helpText: 'Comma-separated keywords to filter messages (optional)'
        },
        {
          key: 'exclude_keywords',
          label: 'Exclude Keywords',
          type: 'text',
          placeholder: 'stop, unsubscribe',
          helpText: 'Comma-separated keywords to exclude messages (optional)'
        },
        {
          key: 'media_type_filter',
          label: 'Media Type',
          type: 'select',
          defaultValue: 'any',
          options: [
            { label: 'Any', value: 'any' },
            { label: 'Text Only', value: 'text' },
            { label: 'Images', value: 'image' },
            { label: 'Videos', value: 'video' },
            { label: 'Audio', value: 'audio' },
            { label: 'Documents', value: 'document' }
          ],
          helpText: 'Filter by message media type'
        }
      ]
    },
    {
      id: 'conversation_handling',
      label: 'Conversation Handling',
      fields: [
        {
          key: 'thread_handling',
          label: 'Thread Handling',
          type: 'select',
          defaultValue: 'all_messages',
          options: [
            { label: 'All Messages', value: 'all_messages' },
            { label: 'New Conversations Only', value: 'new_conversations' },
            { label: 'Replies Only', value: 'replies_only' }
          ],
          helpText: 'How to handle message threads'
        },
        {
          key: 'auto_mark_read',
          label: 'Auto Mark as Read',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Automatically mark processed messages as read'
        },
        {
          key: 'send_read_receipts',
          label: 'Send Read Receipts',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Send read receipts for processed messages'
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
          key: 'rate_limit',
          label: 'Rate Limit',
          type: 'number',
          defaultValue: 20,
          min: 1,
          max: 100,
          helpText: 'Maximum triggers per minute'
        },
        {
          key: 'business_hours_only',
          label: 'Business Hours Only',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Only trigger during business hours'
        },
        {
          key: 'webhook_validation',
          label: 'Validate Webhook Source',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Verify webhook comes from UniPile'
        },
        {
          key: 'handle_status_updates',
          label: 'Handle Status Updates',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Trigger on WhatsApp status updates'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (config.filter_type === 'specific_number' && !config.specific_number) {
      errors.specific_number = 'Phone number is required when filtering by specific number';
    }

    if (config.specific_number && !config.specific_number.match(/^\+?[1-9]\d{1,14}$/)) {
      errors.specific_number = 'Invalid phone number format (use international format)';
    }

    return errors;
  },

  defaults: {
    filter_type: 'all',
    media_type_filter: 'any',
    thread_handling: 'all_messages',
    auto_mark_read: false,
    send_read_receipts: true,
    rate_limit: 20,
    business_hours_only: false,
    webhook_validation: true,
    handle_status_updates: false
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};