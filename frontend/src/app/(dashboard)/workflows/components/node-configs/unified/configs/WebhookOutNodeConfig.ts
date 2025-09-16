import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Send, Shield, Settings } from 'lucide-react';

export const WebhookOutNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.WEBHOOK_OUT,
  label: 'Send Webhook',
  description: 'Send data to an external webhook URL',
  icon: Send,
  category: 'action',

  sections: [
    {
      id: 'webhook_config',
      label: 'Webhook Configuration',
      icon: Send,
      fields: [
        {
          key: 'url',
          label: 'Webhook URL',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: 'https://api.example.com/webhook or {{webhook_url}}',
          helpText: 'The URL to send the webhook to'
        },
        {
          key: 'method',
          label: 'HTTP Method',
          type: 'select',
          required: true,
          defaultValue: 'POST',
          options: [
            { label: 'POST', value: 'POST' },
            { label: 'PUT', value: 'PUT' },
            { label: 'PATCH', value: 'PATCH' },
            { label: 'GET', value: 'GET' },
            { label: 'DELETE', value: 'DELETE' }
          ],
          helpText: 'HTTP method for the request'
        },
        {
          key: 'payload',
          label: 'Payload',
          type: 'json',
          required: true,
          allowExpressions: true,
          placeholder: '{\n  "event": "workflow_completed",\n  "data": {{record}},\n  "timestamp": "{{now}}"\n}',
          helpText: 'Data to send in the webhook',
          rows: 8
        },
        {
          key: 'headers',
          label: 'Headers',
          type: 'json',
          allowExpressions: true,
          placeholder: '{\n  "Content-Type": "application/json",\n  "X-API-Key": "{{api_key}}"\n}',
          helpText: 'Custom headers for the request',
          rows: 4
        }
      ]
    },
    {
      id: 'authentication',
      label: 'Authentication',
      icon: Shield,
      collapsed: true,
      fields: [
        {
          key: 'auth_type',
          label: 'Authentication Type',
          type: 'select',
          defaultValue: 'none',
          options: [
            { label: 'None', value: 'none' },
            { label: 'Bearer Token', value: 'bearer' },
            { label: 'API Key', value: 'api_key' },
            { label: 'Basic Auth', value: 'basic' },
            { label: 'OAuth 2.0', value: 'oauth2' }
          ],
          helpText: 'Authentication method for the webhook'
        },
        {
          key: 'bearer_token',
          label: 'Bearer Token',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.auth_type === 'bearer',
          placeholder: '{{auth_token}}',
          helpText: 'Bearer token for authentication'
        },
        {
          key: 'api_key',
          label: 'API Key',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.auth_type === 'api_key',
          placeholder: '{{api_key}}',
          helpText: 'API key for authentication'
        },
        {
          key: 'api_key_header',
          label: 'API Key Header Name',
          type: 'text',
          showWhen: (c) => c.auth_type === 'api_key',
          defaultValue: 'X-API-Key',
          helpText: 'Header name for the API key'
        }
      ]
    },
    {
      id: 'response',
      label: 'Response Handling',
      collapsed: true,
      fields: [
        {
          key: 'wait_for_response',
          label: 'Wait for Response',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Wait for webhook response before continuing'
        },
        {
          key: 'timeout_seconds',
          label: 'Timeout (seconds)',
          type: 'number',
          showWhen: (c) => c.wait_for_response,
          defaultValue: 30,
          min: 1,
          max: 300,
          helpText: 'Maximum time to wait for response'
        },
        {
          key: 'store_response',
          label: 'Store Response',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Store the webhook response for later use'
        },
        {
          key: 'response_variable',
          label: 'Response Variable Name',
          type: 'text',
          showWhen: (c) => c.store_response,
          defaultValue: 'webhook_response',
          placeholder: 'webhook_response',
          helpText: 'Variable name to store the response'
        },
        {
          key: 'fail_on_error',
          label: 'Fail on Error',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Fail workflow if webhook returns an error'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Options',
      icon: Settings,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'retry_on_failure',
          label: 'Retry on Failure',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Retry if webhook fails'
        },
        {
          key: 'retry_count',
          label: 'Retry Count',
          type: 'number',
          showWhen: (c) => c.retry_on_failure,
          defaultValue: 3,
          min: 1,
          max: 10,
          helpText: 'Number of retry attempts'
        },
        {
          key: 'retry_delay',
          label: 'Retry Delay (seconds)',
          type: 'number',
          showWhen: (c) => c.retry_on_failure,
          defaultValue: 5,
          min: 1,
          max: 60,
          helpText: 'Delay between retry attempts'
        },
        {
          key: 'follow_redirects',
          label: 'Follow Redirects',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Follow HTTP redirects'
        },
        {
          key: 'validate_ssl',
          label: 'Validate SSL Certificate',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Validate SSL certificates'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.url) {
      errors.url = 'Webhook URL is required';
    } else if (!config.url.includes('{{') && !config.url.match(/^https?:\/\//)) {
      errors.url = 'URL must start with http:// or https://';
    }
    
    if (!config.method) {
      errors.method = 'HTTP method is required';
    }
    
    if (!config.payload && ['POST', 'PUT', 'PATCH'].includes(config.method)) {
      errors.payload = 'Payload is required for this method';
    }
    
    return errors;
  },

  defaults: {
    method: 'POST',
    auth_type: 'none',
    api_key_header: 'X-API-Key',
    wait_for_response: true,
    timeout_seconds: 30,
    store_response: true,
    response_variable: 'webhook_response',
    fail_on_error: true,
    retry_on_failure: true,
    retry_count: 3,
    retry_delay: 5,
    follow_redirects: true,
    validate_ssl: true
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};