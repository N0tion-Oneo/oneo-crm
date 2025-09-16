import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { MessageCircle, Clock } from 'lucide-react';

export const WaitForResponseNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.WAIT_FOR_RESPONSE,
  label: 'Wait for Response',
  description: 'Wait for a communication response before continuing',
  icon: MessageCircle,
  category: 'control',

  sections: [
    {
      id: 'response_config',
      label: 'Response Configuration',
      icon: MessageCircle,
      fields: [
        {
          key: 'wait_for',
          label: 'Wait For',
          type: 'select',
          required: true,
          defaultValue: 'any_response',
          options: [
            { label: 'Any Response', value: 'any_response' },
            { label: 'Response from Specific Contact', value: 'specific_contact' },
            { label: 'Response Contains Keyword', value: 'contains_keyword' }
          ],
          helpText: 'Type of response to wait for'
        },
        {
          key: 'channel',
          label: 'Communication Channel',
          type: 'select',
          required: true,
          defaultValue: 'any',
          options: [
            { label: 'Any Channel', value: 'any' },
            { label: 'Email', value: 'email' },
            { label: 'WhatsApp', value: 'whatsapp' },
            { label: 'LinkedIn', value: 'linkedin' }
          ],
          helpText: 'Which channel to monitor for responses'
        },
        {
          key: 'specific_contact_id',
          label: 'Specific Contact',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.wait_for === 'specific_contact',
          placeholder: '{{contact_id}}',
          helpText: 'Contact ID to wait for response from'
        },
        {
          key: 'contains_keyword',
          label: 'Keyword',
          type: 'text',
          required: true,
          showWhen: (c) => c.wait_for === 'contains_keyword',
          placeholder: 'yes, no, interested, etc.',
          helpText: 'Keyword to look for in response (case-insensitive)'
        }
      ]
    },
    {
      id: 'timeout_config',
      label: 'Timeout Settings',
      icon: Clock,
      fields: [
        {
          key: 'timeout_minutes',
          label: 'Timeout (minutes)',
          type: 'number',
          required: true,
          defaultValue: 60,
          min: 1,
          max: 10080, // 1 week
          helpText: 'Maximum time to wait for response'
        },
        {
          key: 'timeout_action',
          label: 'On Timeout',
          type: 'select',
          required: true,
          defaultValue: 'continue',
          options: [
            { label: 'Continue Workflow', value: 'continue' },
            { label: 'Fail Workflow', value: 'fail' },
            { label: 'Branch to Timeout Path', value: 'branch' }
          ],
          helpText: 'What to do if no response received'
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
          key: 'exclude_auto_replies',
          label: 'Exclude Auto-Replies',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Ignore automatic responses (out-of-office, etc.)'
        },
        {
          key: 'conversation_context',
          label: 'Conversation Context',
          type: 'select',
          defaultValue: 'last_message',
          options: [
            { label: 'Last Sent Message', value: 'last_message' },
            { label: 'Entire Conversation', value: 'conversation' },
            { label: 'Specific Message ID', value: 'specific_message' }
          ],
          helpText: 'Context for waiting for response'
        },
        {
          key: 'specific_message_id',
          label: 'Message ID',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.conversation_context === 'specific_message',
          placeholder: '{{message_id}}',
          helpText: 'Specific message to wait for response to'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.wait_for) {
      errors.wait_for = 'Wait type is required';
    }

    if (config.wait_for === 'specific_contact' && !config.specific_contact_id) {
      errors.specific_contact_id = 'Contact ID is required when waiting for specific contact';
    }

    if (config.wait_for === 'contains_keyword' && !config.contains_keyword) {
      errors.contains_keyword = 'Keyword is required when waiting for keyword';
    }

    if (!config.timeout_minutes || config.timeout_minutes < 1) {
      errors.timeout_minutes = 'Timeout must be at least 1 minute';
    }

    return errors;
  },

  defaults: {
    wait_for: 'any_response',
    channel: 'any',
    timeout_minutes: 60,
    timeout_action: 'continue',
    exclude_auto_replies: true,
    conversation_context: 'last_message'
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};