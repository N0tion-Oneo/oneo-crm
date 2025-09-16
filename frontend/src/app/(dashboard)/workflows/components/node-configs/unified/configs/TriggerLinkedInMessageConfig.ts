import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Hash } from 'lucide-react';

export const TriggerLinkedInMessageConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_LINKEDIN_MESSAGE,
  label: 'LinkedIn Message Trigger',
  description: 'Triggers when a LinkedIn message is received',
  icon: Hash,
  category: 'trigger',

  sections: [
    {
      id: 'message_filters',
      label: 'Message Filters',
      icon: Hash,
      fields: [
        {
          key: 'filter_type',
          label: 'Filter Type',
          type: 'select',
          required: true,
          defaultValue: 'all',
          options: [
            { label: 'All Messages', value: 'all' },
            { label: 'From Specific Contact', value: 'specific_contact' },
            { label: 'First-time Messages', value: 'first_time' },
            { label: 'Connection Requests', value: 'connection_request' },
            { label: 'InMail Messages', value: 'inmail' }
          ],
          helpText: 'Type of LinkedIn messages to trigger on'
        },
        {
          key: 'specific_contact_id',
          label: 'Contact ID',
          type: 'text',
          required: true,
          showWhen: (c) => c.filter_type === 'specific_contact',
          placeholder: 'LinkedIn profile ID or URL',
          helpText: 'LinkedIn profile to filter messages from'
        },
        {
          key: 'contains_keywords',
          label: 'Contains Keywords',
          type: 'text',
          placeholder: 'meeting, interested, schedule',
          helpText: 'Comma-separated keywords to filter messages (optional)'
        },
        {
          key: 'exclude_keywords',
          label: 'Exclude Keywords',
          type: 'text',
          placeholder: 'unsubscribe, spam',
          helpText: 'Comma-separated keywords to exclude messages (optional)'
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
          defaultValue: 10,
          min: 1,
          max: 100,
          helpText: 'Maximum triggers per minute'
        },
        {
          key: 'ignore_automated',
          label: 'Ignore Automated Messages',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Filter out automated LinkedIn messages'
        },
        {
          key: 'webhook_validation',
          label: 'Validate Webhook Source',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Verify webhook comes from UniPile'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (config.filter_type === 'specific_contact' && !config.specific_contact_id) {
      errors.specific_contact_id = 'Contact ID is required when filtering by specific contact';
    }

    return errors;
  },

  defaults: {
    filter_type: 'all',
    thread_handling: 'all_messages',
    auto_mark_read: false,
    rate_limit: 10,
    ignore_automated: true,
    webhook_validation: true
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};