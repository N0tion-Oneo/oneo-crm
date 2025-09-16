import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { MessageCircle, Target, Bot } from 'lucide-react';

export const AIConversationLoopNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.AI_CONVERSATION_LOOP,
  label: 'AI Conversation Loop',
  description: 'Manage complete AI-powered conversation flows with objective-driven evaluation',
  icon: Bot,
  category: 'ai',

  sections: [
    {
      id: 'objective',
      label: 'Conversation Objective',
      icon: Target,
      fields: [
        {
          key: 'objective',
          label: 'Objective',
          type: 'textarea',
          required: true,
          placeholder: 'Schedule a product demonstration meeting with the prospect',
          helpText: 'Clear objective for the AI to achieve through conversation'
        },
        {
          key: 'success_criteria',
          label: 'Success Criteria',
          type: 'list',
          required: true,
          defaultValue: [],
          placeholder: 'Meeting time confirmed, Calendar invite sent',
          helpText: 'Specific criteria that indicate objective achievement'
        },
        {
          key: 'initial_message_template',
          label: 'Initial Message',
          type: 'textarea',
          required: true,
          placeholder: 'Hi {name}, I noticed you downloaded our whitepaper on {topic}. I wanted to reach out...',
          helpText: 'Template for the first message. Use {field_name} for personalization'
        }
      ]
    },
    {
      id: 'channels',
      label: 'Communication Channels',
      icon: MessageCircle,
      fields: [
        {
          key: 'channels.primary',
          label: 'Primary Channel',
          type: 'select',
          required: true,
          defaultValue: 'email',
          options: [
            { label: 'Email', value: 'email' },
            { label: 'WhatsApp', value: 'whatsapp' },
            { label: 'LinkedIn', value: 'linkedin' },
            { label: 'SMS', value: 'sms' }
          ],
          helpText: 'Primary channel for communication'
        },
        {
          key: 'channels.fallback',
          label: 'Fallback Channels',
          type: 'multiselect',
          defaultValue: [],
          options: [
            { label: 'Email', value: 'email' },
            { label: 'WhatsApp', value: 'whatsapp' },
            { label: 'LinkedIn', value: 'linkedin' },
            { label: 'SMS', value: 'sms' }
          ],
          helpText: 'Alternative channels if primary fails'
        },
        {
          key: 'follow_response_channel',
          label: 'Follow Response Channel',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Continue conversation on the channel the participant responds from'
        }
      ]
    },
    {
      id: 'loop_control',
      label: 'Loop Control',
      fields: [
        {
          key: 'max_iterations',
          label: 'Maximum Iterations',
          type: 'number',
          required: true,
          defaultValue: 5,
          min: 1,
          max: 20,
          helpText: 'Maximum number of conversation turns'
        },
        {
          key: 'timeout_minutes',
          label: 'Response Timeout (minutes)',
          type: 'number',
          required: true,
          defaultValue: 1440,
          min: 30,
          max: 10080,
          helpText: 'Time to wait for response before timeout (default 24 hours)'
        },
        {
          key: 'exit_conditions.confidence_threshold',
          label: 'Success Confidence Threshold (%)',
          type: 'number',
          defaultValue: 80,
          min: 50,
          max: 100,
          helpText: 'AI confidence level required to mark objective as achieved'
        }
      ]
    },
    {
      id: 'ai_config',
      label: 'AI Configuration',
      icon: Bot,
      fields: [
        {
          key: 'ai_config.model',
          label: 'AI Model',
          type: 'select',
          required: true,
          defaultValue: 'gpt-4',
          options: [
            { label: 'GPT-4 (Most Capable)', value: 'gpt-4' },
            { label: 'GPT-4 Turbo', value: 'gpt-4-turbo-preview' },
            { label: 'GPT-3.5 Turbo (Faster)', value: 'gpt-3.5-turbo' }
          ],
          helpText: 'AI model for conversation management'
        },
        {
          key: 'ai_config.temperature',
          label: 'Creativity Level',
          type: 'number',
          defaultValue: 0.7,
          min: 0,
          max: 1,
          step: 0.1,
          helpText: 'Higher values make responses more creative (0-1)'
        },
        {
          key: 'ai_config.system_prompt',
          label: 'System Prompt',
          type: 'textarea',
          defaultValue: 'You are a helpful and professional assistant focused on achieving the conversation objective while being respectful of the participants time.',
          helpText: 'Instructions for AI behavior and tone'
        },
        {
          key: 'ai_config.tone',
          label: 'Conversation Tone',
          type: 'select',
          defaultValue: 'professional',
          options: [
            { label: 'Professional', value: 'professional' },
            { label: 'Friendly', value: 'friendly' },
            { label: 'Casual', value: 'casual' },
            { label: 'Formal', value: 'formal' },
            { label: 'Enthusiastic', value: 'enthusiastic' }
          ],
          helpText: 'Tone of voice for AI responses'
        }
      ]
    },
    {
      id: 'exit_handling',
      label: 'Exit Conditions',
      collapsed: true,
      fields: [
        {
          key: 'exit_conditions.opt_out_phrases',
          label: 'Opt-out Phrases',
          type: 'list',
          defaultValue: ['unsubscribe', 'stop', 'not interested', 'remove me'],
          placeholder: 'Add opt-out phrase',
          helpText: 'Phrases that indicate participant wants to stop'
        },
        {
          key: 'exit_conditions.human_handoff_triggers',
          label: 'Human Handoff Triggers',
          type: 'list',
          defaultValue: ['speak to human', 'talk to someone', 'urgent', 'complaint'],
          placeholder: 'Add handoff trigger',
          helpText: 'Phrases that trigger human intervention'
        },
        {
          key: 'exit_conditions.on_timeout',
          label: 'On Timeout Action',
          type: 'select',
          defaultValue: 'end',
          options: [
            { label: 'End Conversation', value: 'end' },
            { label: 'Send Follow-up', value: 'follow_up' },
            { label: 'Create Task', value: 'create_task' }
          ],
          helpText: 'Action when participant doesnt respond'
        },
        {
          key: 'exit_conditions.on_max_iterations',
          label: 'On Max Iterations',
          type: 'select',
          defaultValue: 'handoff',
          options: [
            { label: 'End Conversation', value: 'end' },
            { label: 'Human Handoff', value: 'handoff' },
            { label: 'Schedule Follow-up', value: 'schedule_followup' }
          ],
          helpText: 'Action when max iterations reached'
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
          key: 'store_conversation',
          label: 'Store Conversation',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Save conversation to database'
        },
        {
          key: 'update_record',
          label: 'Update Record Fields',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Update record with conversation outcomes'
        },
        {
          key: 'record_field_mapping',
          label: 'Field Mapping',
          type: 'json',
          showWhen: (c) => c.update_record,
          defaultValue: {},
          placeholder: '{"last_contacted": "{{timestamp}}", "status": "{{outcome}}"}',
          helpText: 'Map conversation data to record fields'
        },
        {
          key: 'debug_mode',
          label: 'Debug Mode',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Log detailed AI evaluations and decisions'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.objective) {
      errors.objective = 'Conversation objective is required';
    }

    if (!config.success_criteria || config.success_criteria.length === 0) {
      errors.success_criteria = 'At least one success criterion is required';
    }

    if (!config.initial_message_template) {
      errors.initial_message_template = 'Initial message template is required';
    }

    if (!config.max_iterations || config.max_iterations < 1) {
      errors.max_iterations = 'Maximum iterations must be at least 1';
    }

    if (!config.timeout_minutes || config.timeout_minutes < 30) {
      errors.timeout_minutes = 'Timeout must be at least 30 minutes';
    }

    return errors;
  },

  defaults: {
    objective: '',
    success_criteria: [],
    initial_message_template: '',
    channels: {
      primary: 'email',
      fallback: []
    },
    follow_response_channel: true,
    max_iterations: 5,
    timeout_minutes: 1440,
    ai_config: {
      model: 'gpt-4',
      temperature: 0.7,
      system_prompt: 'You are a helpful and professional assistant focused on achieving the conversation objective while being respectful of the participants time.',
      tone: 'professional'
    },
    exit_conditions: {
      confidence_threshold: 80,
      opt_out_phrases: ['unsubscribe', 'stop', 'not interested', 'remove me'],
      human_handoff_triggers: ['speak to human', 'talk to someone', 'urgent', 'complaint'],
      on_timeout: 'end',
      on_max_iterations: 'handoff'
    },
    store_conversation: true,
    update_record: true,
    record_field_mapping: {},
    debug_mode: false
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: true
  }
};