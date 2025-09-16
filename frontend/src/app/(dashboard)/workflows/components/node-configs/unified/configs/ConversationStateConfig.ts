import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Database, Archive, Settings } from 'lucide-react';

export const ConversationStateConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.CONVERSATION_STATE,
  label: 'Conversation State',
  description: 'Manage and track conversation state across workflow nodes',
  icon: Database,
  category: 'utility',

  sections: [
    {
      id: 'state_management',
      label: 'State Management',
      icon: Database,
      fields: [
        {
          key: 'state_key',
          label: 'Conversation ID',
          type: 'expression',
          required: true,
          defaultValue: '{{record.id}}_conversation',
          placeholder: '{{customer_id}}_{{channel}} or custom_key_123',
          helpText: 'Unique identifier for this conversation state'
        },
        {
          key: 'operation',
          label: 'Operation',
          type: 'select',
          required: true,
          defaultValue: 'update',
          options: [
            { label: 'Initialize', value: 'init', description: 'Create new conversation state' },
            { label: 'Update', value: 'update', description: 'Update existing state' },
            { label: 'Read', value: 'read', description: 'Read current state' },
            { label: 'Append', value: 'append', description: 'Append to conversation history' },
            { label: 'Reset', value: 'reset', description: 'Reset conversation state' },
            { label: 'Archive', value: 'archive', description: 'Archive conversation' }
          ],
          helpText: 'What to do with the conversation state'
        },
        {
          key: 'storage_duration',
          label: 'Storage Duration',
          type: 'select',
          defaultValue: '7d',
          options: [
            { label: '1 Hour', value: '1h' },
            { label: '24 Hours', value: '24h' },
            { label: '7 Days', value: '7d' },
            { label: '30 Days', value: '30d' },
            { label: '90 Days', value: '90d' },
            { label: 'Permanent', value: 'permanent' }
          ],
          helpText: 'How long to keep the conversation state'
        }
      ]
    },
    {
      id: 'conversation_data',
      label: 'Conversation Data',
      icon: Archive,
      fields: [
        {
          key: 'conversation_history',
          label: 'Conversation History',
          type: 'expression',
          placeholder: '{{previous_messages}} or [{role: "user", content: "..."}]',
          helpText: 'Messages to add to conversation history'
        },
        {
          key: 'current_stage',
          label: 'Current Stage',
          type: 'select',
          defaultValue: 'active',
          options: [
            { label: 'Not Started', value: 'not_started' },
            { label: 'Active', value: 'active' },
            { label: 'Waiting for Response', value: 'waiting' },
            { label: 'Follow Up', value: 'follow_up' },
            { label: 'Completed', value: 'completed' },
            { label: 'Abandoned', value: 'abandoned' }
          ],
          helpText: 'Current stage of the conversation'
        },
        {
          key: 'metadata',
          label: 'Metadata',
          type: 'json',
          placeholder: '{\n  "customer_id": "{{customer.id}}",\n  "channel": "email",\n  "topic": "support"\n}',
          helpText: 'Additional metadata to store'
        },
        {
          key: 'context_variables',
          label: 'Context Variables',
          type: 'fieldGroup',
          fields: [
            {
              key: 'customer_name',
              label: 'Customer Name',
              type: 'expression',
              placeholder: '{{customer.name}}'
            },
            {
              key: 'product',
              label: 'Product/Service',
              type: 'expression',
              placeholder: '{{product.name}}'
            },
            {
              key: 'sentiment',
              label: 'Current Sentiment',
              type: 'select',
              options: [
                { label: 'Positive', value: 'positive' },
                { label: 'Neutral', value: 'neutral' },
                { label: 'Negative', value: 'negative' },
                { label: 'Unknown', value: 'unknown' }
              ]
            },
            {
              key: 'language',
              label: 'Language',
              type: 'expression',
              placeholder: '{{detected_language}} or "en"'
            }
          ]
        }
      ]
    },
    {
      id: 'metrics_tracking',
      label: 'Metrics & Tracking',
      icon: Settings,
      collapsed: true,
      fields: [
        {
          key: 'track_metrics',
          label: 'Track Metrics',
          type: 'switch',
          defaultValue: true,
          helpText: 'Track conversation metrics'
        },
        {
          key: 'metrics_to_track',
          label: 'Metrics to Track',
          type: 'multiselect',
          defaultValue: ['message_count', 'response_time'],
          options: [
            { label: 'Message Count', value: 'message_count' },
            { label: 'Response Time', value: 'response_time' },
            { label: 'Sentiment Changes', value: 'sentiment_changes' },
            { label: 'Topic Changes', value: 'topic_changes' },
            { label: 'Escalation Count', value: 'escalations' },
            { label: 'Resolution Time', value: 'resolution_time' },
            { label: 'Customer Satisfaction', value: 'satisfaction' }
          ],
          helpText: 'Which metrics to track'
        },
        {
          key: 'update_flags',
          label: 'Update Flags',
          type: 'fieldGroup',
          fields: [
            {
              key: 'is_escalated',
              label: 'Mark as Escalated',
              type: 'switch',
              defaultValue: false
            },
            {
              key: 'requires_follow_up',
              label: 'Requires Follow Up',
              type: 'switch',
              defaultValue: false
            },
            {
              key: 'is_resolved',
              label: 'Mark as Resolved',
              type: 'switch',
              defaultValue: false
            },
            {
              key: 'priority_level',
              label: 'Priority Level',
              type: 'select',
              options: [
                { label: 'Low', value: 'low' },
                { label: 'Medium', value: 'medium' },
                { label: 'High', value: 'high' },
                { label: 'Urgent', value: 'urgent' }
              ]
            }
          ]
        },
        {
          key: 'summary_enabled',
          label: 'Generate Summary',
          type: 'switch',
          defaultValue: false,
          helpText: 'Generate conversation summary'
        },
        {
          key: 'summary_length',
          label: 'Summary Length',
          type: 'select',
          defaultValue: 'medium',
          options: [
            { label: 'Brief (1-2 sentences)', value: 'brief' },
            { label: 'Medium (3-5 sentences)', value: 'medium' },
            { label: 'Detailed (full summary)', value: 'detailed' }
          ]
        }
      ]
    }
  ],

  outputs: [
    {
      key: 'state',
      label: 'Conversation State',
      type: 'object',
      description: 'Complete conversation state object'
    },
    {
      key: 'conversation_id',
      label: 'Conversation ID',
      type: 'string',
      description: 'Unique conversation identifier'
    },
    {
      key: 'history',
      label: 'Conversation History',
      type: 'array',
      description: 'Array of conversation messages'
    },
    {
      key: 'message_count',
      label: 'Message Count',
      type: 'number',
      description: 'Total number of messages'
    },
    {
      key: 'current_stage',
      label: 'Current Stage',
      type: 'string',
      description: 'Current conversation stage'
    },
    {
      key: 'metrics',
      label: 'Conversation Metrics',
      type: 'object',
      description: 'Tracked metrics and statistics'
    },
    {
      key: 'summary',
      label: 'Conversation Summary',
      type: 'string',
      description: 'AI-generated summary'
    },
    {
      key: 'last_updated',
      label: 'Last Updated',
      type: 'datetime',
      description: 'Last update timestamp'
    }
  ],

  validationRules: [
    {
      fields: ['state_key'],
      validator: (values) => {
        if (!values.state_key || values.state_key.trim().length === 0) {
          return 'Conversation ID is required';
        }
        if (values.state_key.length > 255) {
          return 'Conversation ID must be less than 255 characters';
        }
        return null;
      }
    },
    {
      fields: ['operation', 'conversation_history'],
      validator: (values) => {
        if (values.operation === 'append' && !values.conversation_history) {
          return 'Conversation history is required when appending';
        }
        return null;
      }
    }
  ]
};