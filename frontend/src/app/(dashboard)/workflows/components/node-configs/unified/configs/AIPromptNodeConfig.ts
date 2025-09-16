import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Sparkles, Settings, DollarSign } from 'lucide-react';

export const AIPromptNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.AI_PROMPT,
  label: 'AI Prompt',
  description: 'Generate content using AI with custom prompts',
  icon: Sparkles,
  category: 'action',

  sections: [
    {
      id: 'ai_config',
      label: 'AI Configuration',
      icon: Sparkles,
      fields: [
        {
          key: 'model',
          label: 'AI Model',
          type: 'select',
          required: true,
          defaultValue: 'gpt-4-turbo',
          options: [
            { label: 'GPT-4 Turbo', value: 'gpt-4-turbo', description: 'Most capable, latest GPT-4' },
            { label: 'GPT-4', value: 'gpt-4', description: 'Powerful reasoning' },
            { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo', description: 'Fast and efficient' },
            { label: 'Claude 3 Opus', value: 'claude-3-opus', description: 'Best Claude model' },
            { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet', description: 'Balanced Claude' },
            { label: 'Claude 3 Haiku', value: 'claude-3-haiku', description: 'Fast Claude' }
          ],
          helpText: 'Select the AI model to use'
        },
        {
          key: 'prompt',
          label: 'Prompt',
          type: 'textarea',
          required: true,
          allowExpressions: true,
          placeholder: 'Write a professional email to {{customer_name}} about {{topic}}...\n\nUse {{variable}} to insert data.',
          helpText: 'The prompt to send to the AI model',
          rows: 8
        },
        {
          key: 'system_prompt',
          label: 'System Prompt',
          type: 'textarea',
          allowExpressions: true,
          placeholder: 'You are a helpful assistant that...\n\nSet the AI\'s behavior and context.',
          helpText: 'Sets the behavior and context for the AI',
          rows: 4
        },
        {
          key: 'response_format',
          label: 'Response Format',
          type: 'select',
          defaultValue: 'text',
          options: [
            { label: 'Plain Text', value: 'text' },
            { label: 'JSON', value: 'json' },
            { label: 'Markdown', value: 'markdown' },
            { label: 'HTML', value: 'html' },
            { label: 'Code', value: 'code' }
          ],
          helpText: 'Expected format of the AI response'
        },
        {
          key: 'json_schema',
          label: 'JSON Schema',
          type: 'json',
          showWhen: (c) => c.response_format === 'json',
          placeholder: '{\n  "name": "string",\n  "email": "string",\n  "score": "number"\n}',
          helpText: 'Schema for structured JSON output',
          rows: 6
        }
      ]
    },
    {
      id: 'parameters',
      label: 'Model Parameters',
      icon: Settings,
      collapsed: true,
      fields: [
        {
          key: 'temperature',
          label: 'Temperature',
          type: 'slider',
          defaultValue: 0.7,
          min: 0,
          max: 2,
          step: 0.1,
          helpText: 'Controls randomness (0 = deterministic, 2 = very creative)'
        },
        {
          key: 'max_tokens',
          label: 'Max Tokens',
          type: 'number',
          defaultValue: 1000,
          min: 1,
          max: 4000,
          placeholder: '1000',
          helpText: 'Maximum length of the response'
        },
        {
          key: 'top_p',
          label: 'Top P',
          type: 'slider',
          defaultValue: 1,
          min: 0,
          max: 1,
          step: 0.01,
          helpText: 'Nucleus sampling (alternative to temperature)'
        },
        {
          key: 'frequency_penalty',
          label: 'Frequency Penalty',
          type: 'slider',
          defaultValue: 0,
          min: -2,
          max: 2,
          step: 0.1,
          helpText: 'Reduce repetition of tokens'
        },
        {
          key: 'presence_penalty',
          label: 'Presence Penalty',
          type: 'slider',
          defaultValue: 0,
          min: -2,
          max: 2,
          step: 0.1,
          helpText: 'Encourage talking about new topics'
        },
        {
          key: 'stop_sequences',
          label: 'Stop Sequences',
          type: 'textarea',
          placeholder: 'END\n---\nSTOP',
          helpText: 'Sequences where the AI should stop (one per line)',
          rows: 2
        }
      ]
    },
    {
      id: 'tools',
      label: 'AI Tools & Functions',
      collapsed: true,
      fields: [
        {
          key: 'enable_tools',
          label: 'Enable Tools',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Allow AI to use tools and functions'
        },
        {
          key: 'available_tools',
          label: 'Available Tools',
          type: 'multiselect',
          showWhen: (c) => c.enable_tools,
          options: [
            { label: 'Web Search', value: 'web_search' },
            { label: 'Code Interpreter', value: 'code_interpreter' },
            { label: 'Image Generation', value: 'dalle' },
            { label: 'Calculator', value: 'calculator' },
            { label: 'Knowledge Base', value: 'knowledge_base' }
          ],
          helpText: 'Select which tools the AI can use'
        },
        {
          key: 'function_calling',
          label: 'Function Calling',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Allow AI to call custom functions'
        },
        {
          key: 'functions',
          label: 'Custom Functions',
          type: 'json',
          showWhen: (c) => c.function_calling,
          placeholder: '[\n  {\n    "name": "get_weather",\n    "description": "Get weather for a location",\n    "parameters": {...}\n  }\n]',
          helpText: 'Define custom functions the AI can call',
          rows: 8
        }
      ]
    },
    {
      id: 'cost_control',
      label: 'Cost Control',
      icon: DollarSign,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'max_cost',
          label: 'Max Cost per Request ($)',
          type: 'number',
          defaultValue: 1,
          min: 0.01,
          max: 100,
          step: 0.01,
          helpText: 'Maximum cost allowed per request'
        },
        {
          key: 'cache_responses',
          label: 'Cache Responses',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Cache AI responses for identical prompts'
        },
        {
          key: 'cache_duration',
          label: 'Cache Duration (hours)',
          type: 'number',
          showWhen: (c) => c.cache_responses,
          defaultValue: 24,
          min: 1,
          max: 168,
          helpText: 'How long to cache responses'
        },
        {
          key: 'fallback_model',
          label: 'Fallback Model',
          type: 'select',
          options: [
            { label: 'None', value: 'none' },
            { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
            { label: 'Claude Haiku', value: 'claude-3-haiku' }
          ],
          helpText: 'Cheaper model to use if cost limit exceeded'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.model) {
      errors.model = 'AI model selection is required';
    }
    if (!config.prompt) {
      errors.prompt = 'Prompt is required';
    }
    if (config.temperature < 0 || config.temperature > 2) {
      errors.temperature = 'Temperature must be between 0 and 2';
    }
    if (config.max_tokens < 1) {
      errors.max_tokens = 'Max tokens must be at least 1';
    }
    
    return errors;
  },

  defaults: {
    model: 'gpt-4-turbo',
    response_format: 'text',
    temperature: 0.7,
    max_tokens: 1000,
    top_p: 1,
    frequency_penalty: 0,
    presence_penalty: 0,
    enable_tools: false,
    function_calling: false,
    max_cost: 1,
    cache_responses: false,
    cache_duration: 24,
    fallback_model: 'none'
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: true
  }
};