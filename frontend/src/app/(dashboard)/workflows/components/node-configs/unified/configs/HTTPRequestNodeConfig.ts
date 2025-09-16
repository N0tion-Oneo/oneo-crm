import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Globe, Key, Clock, FileJson } from 'lucide-react';

export const HTTPRequestNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.HTTP_REQUEST,
  label: 'HTTP Request',
  description: 'Make HTTP requests to external APIs',
  icon: Globe,
  category: 'integration',

  sections: [
    {
      id: 'request',
      label: 'Request Configuration',
      icon: Globe,
      fields: [
        {
          key: 'method',
          label: 'Method',
          type: 'select',
          required: true,
          defaultValue: 'GET',
          options: [
            { label: 'GET', value: 'GET' },
            { label: 'POST', value: 'POST' },
            { label: 'PUT', value: 'PUT' },
            { label: 'PATCH', value: 'PATCH' },
            { label: 'DELETE', value: 'DELETE' },
            { label: 'HEAD', value: 'HEAD' },
            { label: 'OPTIONS', value: 'OPTIONS' }
          ]
        },
        {
          key: 'url',
          label: 'URL',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: 'https://api.example.com/{{endpoint}}',
          helpText: 'The URL to make the request to',
          validation: (value) => {
            if (!value) return 'URL is required';
            if (!value.includes('{{') && !value.startsWith('http')) {
              return 'URL must start with http:// or https://';
            }
            return null;
          }
        },
        {
          key: 'headers',
          label: 'Headers',
          type: 'json',
          allowExpressions: true,
          placeholder: '{\n  "Content-Type": "application/json",\n  "Authorization": "Bearer {{token}}"\n}',
          helpText: 'Request headers in JSON format',
          rows: 5
        },
        {
          key: 'body',
          label: 'Body',
          type: 'json',
          allowExpressions: true,
          placeholder: '{\n  "key": "{{value}}"\n}',
          helpText: 'Request body (for POST, PUT, PATCH)',
          showWhen: (c) => ['POST', 'PUT', 'PATCH'].includes(c.method),
          rows: 8
        },
        {
          key: 'query_params',
          label: 'Query Parameters',
          type: 'json',
          allowExpressions: true,
          placeholder: '{\n  "page": "{{page}}",\n  "limit": 10\n}',
          helpText: 'Query parameters to append to URL',
          rows: 4
        }
      ]
    },
    {
      id: 'authentication',
      label: 'Authentication',
      icon: Key,
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
            { label: 'Basic Auth', value: 'basic' },
            { label: 'API Key', value: 'api_key' },
            { label: 'OAuth 2.0', value: 'oauth2' }
          ]
        },
        {
          key: 'bearer_token',
          label: 'Bearer Token',
          type: 'text',
          allowExpressions: true,
          placeholder: '{{api_token}}',
          showWhen: (c) => c.auth_type === 'bearer'
        },
        {
          key: 'username',
          label: 'Username',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.auth_type === 'basic'
        },
        {
          key: 'password',
          label: 'Password',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.auth_type === 'basic'
        },
        {
          key: 'api_key',
          label: 'API Key',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.auth_type === 'api_key'
        },
        {
          key: 'api_key_header',
          label: 'API Key Header Name',
          type: 'text',
          defaultValue: 'X-API-Key',
          placeholder: 'X-API-Key',
          showWhen: (c) => c.auth_type === 'api_key'
        }
      ]
    },
    {
      id: 'response',
      label: 'Response Handling',
      icon: FileJson,
      collapsed: true,
      fields: [
        {
          key: 'response_type',
          label: 'Expected Response Type',
          type: 'select',
          defaultValue: 'json',
          options: [
            { label: 'JSON', value: 'json' },
            { label: 'Text', value: 'text' },
            { label: 'Binary', value: 'binary' },
            { label: 'XML', value: 'xml' }
          ]
        },
        {
          key: 'extract_path',
          label: 'JSON Path',
          type: 'text',
          allowExpressions: true,
          placeholder: '$.data.items',
          helpText: 'JSONPath to extract specific data',
          showWhen: (c) => c.response_type === 'json'
        },
        {
          key: 'store_response',
          label: 'Store Full Response',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Store the complete response for later use'
        },
        {
          key: 'error_handling',
          label: 'Error Handling',
          type: 'select',
          defaultValue: 'fail',
          options: [
            { label: 'Fail Workflow', value: 'fail' },
            { label: 'Continue with Error', value: 'continue' },
            { label: 'Retry', value: 'retry' },
            { label: 'Use Fallback', value: 'fallback' }
          ]
        },
        {
          key: 'fallback_value',
          label: 'Fallback Value',
          type: 'json',
          allowExpressions: true,
          showWhen: (c) => c.error_handling === 'fallback',
          placeholder: '{"error": true}'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Settings',
      icon: Clock,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'timeout',
          label: 'Timeout (seconds)',
          type: 'number',
          defaultValue: 30,
          min: 1,
          max: 300,
          placeholder: '30',
          helpText: 'Request timeout in seconds'
        },
        {
          key: 'retry_count',
          label: 'Retry Count',
          type: 'number',
          defaultValue: 3,
          min: 0,
          max: 10,
          placeholder: '3',
          showWhen: (c) => c.error_handling === 'retry'
        },
        {
          key: 'retry_delay',
          label: 'Retry Delay (seconds)',
          type: 'number',
          defaultValue: 5,
          min: 1,
          max: 60,
          placeholder: '5',
          showWhen: (c) => c.error_handling === 'retry'
        },
        {
          key: 'follow_redirects',
          label: 'Follow Redirects',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Automatically follow HTTP redirects'
        },
        {
          key: 'ssl_verify',
          label: 'Verify SSL Certificate',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Verify SSL certificates (disable for self-signed certs)'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.url) {
      errors.url = 'URL is required';
    }
    if (!config.method) {
      errors.method = 'Method is required';
    }

    // Validate JSON fields
    if (config.headers) {
      try {
        if (typeof config.headers === 'string') {
          JSON.parse(config.headers);
        }
      } catch {
        errors.headers = 'Headers must be valid JSON';
      }
    }

    if (config.body && ['POST', 'PUT', 'PATCH'].includes(config.method)) {
      try {
        if (typeof config.body === 'string') {
          JSON.parse(config.body);
        }
      } catch {
        errors.body = 'Body must be valid JSON';
      }
    }

    return errors;
  },

  defaults: {
    method: 'GET',
    auth_type: 'none',
    response_type: 'json',
    store_response: true,
    error_handling: 'fail',
    timeout: 30,
    retry_count: 3,
    retry_delay: 5,
    follow_redirects: true,
    ssl_verify: true
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};