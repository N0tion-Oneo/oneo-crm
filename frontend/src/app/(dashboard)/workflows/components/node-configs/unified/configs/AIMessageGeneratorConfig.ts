import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { MessageSquare, Sparkles, Settings } from 'lucide-react';

export const AIMessageGeneratorConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.AI_MESSAGE_GENERATOR,
  label: 'AI Message Generator',
  description: 'Generate contextual messages using AI',
  icon: MessageSquare,
  category: 'action',

  sections: [
    {
      id: 'message_config',
      label: 'Message Configuration',
      icon: MessageSquare,
      fields: [
        {
          key: 'channel',
          label: 'Communication Channel',
          type: 'select',
          required: true,
          defaultValue: 'email',
          options: [
            { label: 'Email', value: 'email', description: 'Generate email messages' },
            { label: 'WhatsApp', value: 'whatsapp', description: 'Generate WhatsApp messages' },
            { label: 'LinkedIn', value: 'linkedin', description: 'Generate LinkedIn messages' },
            { label: 'SMS', value: 'sms', description: 'Generate SMS messages' },
            { label: 'Generic', value: 'generic', description: 'General purpose message' }
          ],
          helpText: 'The communication channel for the message'
        },
        {
          key: 'message_type',
          label: 'Message Type',
          type: 'select',
          required: true,
          defaultValue: 'initial',
          options: [
            { label: 'Initial Outreach', value: 'initial', description: 'First contact message' },
            { label: 'Follow Up', value: 'follow_up', description: 'Follow up on previous message' },
            { label: 'Response', value: 'response', description: 'Reply to received message' },
            { label: 'Reminder', value: 'reminder', description: 'Reminder message' },
            { label: 'Thank You', value: 'thank_you', description: 'Thank you message' },
            { label: 'Apology', value: 'apology', description: 'Apology message' }
          ],
          helpText: 'The type of message to generate'
        },
        {
          key: 'tone',
          label: 'Message Tone',
          type: 'select',
          required: true,
          defaultValue: 'professional',
          options: [
            { label: 'Professional', value: 'professional' },
            { label: 'Friendly', value: 'friendly' },
            { label: 'Formal', value: 'formal' },
            { label: 'Casual', value: 'casual' },
            { label: 'Enthusiastic', value: 'enthusiastic' },
            { label: 'Empathetic', value: 'empathetic' }
          ],
          helpText: 'The tone of voice for the message'
        }
      ]
    },
    {
      id: 'content',
      label: 'Content Settings',
      icon: Settings,
      fields: [
        {
          key: 'context',
          label: 'Message Context',
          type: 'textarea',
          required: true,
          allowExpressions: true,
          placeholder: 'Customer: {{customer_name}}\nProduct: {{product}}\nPrevious interaction: {{last_message}}\n\nProvide context for the AI to generate relevant messages.',
          helpText: 'Context and information for message generation',
          rows: 6
        },
        {
          key: 'key_points',
          label: 'Key Points to Include',
          type: 'textarea',
          allowExpressions: true,
          placeholder: '- Mention {{offer_details}}\n- Include deadline: {{deadline}}\n- Reference previous conversation\n\nList important points to cover.',
          helpText: 'Bullet points of what must be included',
          rows: 4
        },
        {
          key: 'max_length',
          label: 'Maximum Length',
          type: 'number',
          defaultValue: 500,
          min: 50,
          max: 5000,
          helpText: 'Maximum character count for the message'
        },
        {
          key: 'language',
          label: 'Language',
          type: 'select',
          defaultValue: 'en',
          options: [
            { label: 'English', value: 'en' },
            { label: 'Spanish', value: 'es' },
            { label: 'French', value: 'fr' },
            { label: 'German', value: 'de' },
            { label: 'Italian', value: 'it' },
            { label: 'Portuguese', value: 'pt' },
            { label: 'Dutch', value: 'nl' },
            { label: 'Japanese', value: 'ja' },
            { label: 'Chinese', value: 'zh' },
            { label: 'Auto-detect', value: 'auto' }
          ],
          helpText: 'Language for the generated message'
        }
      ]
    },
    {
      id: 'ai_settings',
      label: 'AI Settings',
      icon: Sparkles,
      collapsed: true,
      fields: [
        {
          key: 'model',
          label: 'AI Model',
          type: 'select',
          defaultValue: 'gpt-4-turbo',
          options: [
            { label: 'GPT-4 Turbo', value: 'gpt-4-turbo', description: 'Best for complex messages' },
            { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo', description: 'Fast and efficient' },
            { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet', description: 'Balanced performance' }
          ],
          helpText: 'AI model for message generation'
        },
        {
          key: 'temperature',
          label: 'Creativity Level',
          type: 'slider',
          defaultValue: 0.7,
          min: 0,
          max: 1,
          step: 0.1,
          helpText: 'Higher values make output more creative, lower values more focused'
        },
        {
          key: 'include_subject',
          label: 'Generate Subject Line',
          type: 'switch',
          defaultValue: true,
          helpText: 'Also generate a subject line (for email)'
        },
        {
          key: 'personalization_level',
          label: 'Personalization Level',
          type: 'select',
          defaultValue: 'medium',
          options: [
            { label: 'Low', value: 'low', description: 'Generic message' },
            { label: 'Medium', value: 'medium', description: 'Some personalization' },
            { label: 'High', value: 'high', description: 'Highly personalized' }
          ],
          helpText: 'How personalized the message should be'
        }
      ]
    }
  ],

  outputs: [
    {
      key: 'message',
      label: 'Generated Message',
      type: 'string',
      description: 'The generated message content'
    },
    {
      key: 'subject',
      label: 'Subject Line',
      type: 'string',
      description: 'Generated subject line (for email)'
    },
    {
      key: 'metadata',
      label: 'Message Metadata',
      type: 'object',
      description: 'Additional message information'
    }
  ],

  validationRules: [
    {
      fields: ['context'],
      validator: (values) => {
        if (!values.context || values.context.trim().length < 10) {
          return 'Context must be at least 10 characters';
        }
        return null;
      }
    }
  ]
};