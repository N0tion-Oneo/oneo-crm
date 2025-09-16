import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Webhook, Shield, Key } from 'lucide-react';

export const TriggerWebhookConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_WEBHOOK,
  label: 'Webhook Trigger',
  description: 'Triggers when a webhook is received',
  icon: Webhook,
  category: 'trigger',

  sections: [
    {
      id: 'webhook',
      label: 'Webhook Configuration',
      icon: Webhook,
      fields: [
        {
          key: 'webhook_url',
          label: 'Webhook URL',
          type: 'text',
          readonly: true,
          placeholder: 'Generated after save',
          helpText: 'The URL to send webhooks to (generated automatically)'
        },
        {
          key: 'webhook_method',
          label: 'Accepted Methods',
          type: 'multiselect',
          defaultValue: ['POST'],
          options: [
            { label: 'GET', value: 'GET' },
            { label: 'POST', value: 'POST' },
            { label: 'PUT', value: 'PUT' },
            { label: 'PATCH', value: 'PATCH' },
            { label: 'DELETE', value: 'DELETE' }
          ],
          helpText: 'HTTP methods to accept'
        },
        {
          key: 'content_type',
          label: 'Expected Content Type',
          type: 'select',
          defaultValue: 'application/json',
          options: [
            { label: 'JSON', value: 'application/json' },
            { label: 'Form Data', value: 'application/x-www-form-urlencoded' },
            { label: 'Multipart', value: 'multipart/form-data' },
            { label: 'XML', value: 'application/xml' },
            { label: 'Plain Text', value: 'text/plain' },
            { label: 'Any', value: '*/*' }
          ],
          helpText: 'Expected content type of webhook payload'
        }
      ]
    },
    {
      id: 'security',
      label: 'Security',
      icon: Shield,
      fields: [
        {
          key: 'require_authentication',
          label: 'Require Authentication',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Require authentication for webhook requests'
        },
        {
          key: 'auth_type',
          label: 'Authentication Type',
          type: 'select',
          showWhen: (c) => c.require_authentication,
          defaultValue: 'token',
          options: [
            { label: 'Bearer Token', value: 'token' },
            { label: 'API Key', value: 'api_key' },
            { label: 'HMAC Signature', value: 'hmac' },
            { label: 'Basic Auth', value: 'basic' }
          ]
        },
        {
          key: 'auth_token',
          label: 'Token/Key',
          type: 'text',
          showWhen: (c) => c.require_authentication && ['token', 'api_key'].includes(c.auth_type),
          placeholder: 'Enter secret token or API key',
          helpText: 'Secret token or API key for authentication'
        },
        {
          key: 'hmac_secret',
          label: 'HMAC Secret',
          type: 'text',
          showWhen: (c) => c.require_authentication && c.auth_type === 'hmac',
          placeholder: 'Enter HMAC secret',
          helpText: 'Secret for HMAC signature verification'
        },
        {
          key: 'allowed_ips',
          label: 'Allowed IP Addresses',
          type: 'textarea',
          placeholder: '192.168.1.1\n10.0.0.0/24',
          helpText: 'Whitelist IP addresses (one per line, supports CIDR)',
          rows: 3
        }
      ]
    },
    {
      id: 'validation',
      label: 'Payload Validation',
      collapsed: true,
      fields: [
        {
          key: 'validate_payload',
          label: 'Validate Payload',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Validate incoming payload structure'
        },
        {
          key: 'payload_schema',
          label: 'Payload Schema (JSON Schema)',
          type: 'json',
          showWhen: (c) => c.validate_payload,
          placeholder: '{\n  "type": "object",\n  "required": ["event", "data"],\n  "properties": {\n    "event": {"type": "string"},\n    "data": {"type": "object"}\n  }\n}',
          helpText: 'JSON Schema for payload validation',
          rows: 8
        },
        {
          key: 'reject_invalid',
          label: 'Reject Invalid Payloads',
          type: 'boolean',
          defaultValue: true,
          showWhen: (c) => c.validate_payload,
          helpText: 'Return error for invalid payloads'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Settings',
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'rate_limit',
          label: 'Rate Limit (per minute)',
          type: 'number',
          defaultValue: 60,
          min: 0,
          max: 1000,
          helpText: 'Maximum requests per minute (0 = unlimited)'
        },
        {
          key: 'timeout_seconds',
          label: 'Request Timeout (seconds)',
          type: 'number',
          defaultValue: 30,
          min: 1,
          max: 300,
          helpText: 'Maximum time to process webhook'
        },
        {
          key: 'store_raw_payload',
          label: 'Store Raw Payload',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Store the raw webhook payload for debugging'
        },
        {
          key: 'retry_on_failure',
          label: 'Allow Retries',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Allow webhook sender to retry on failure'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.webhook_method || config.webhook_method.length === 0) {
      errors.webhook_method = 'At least one HTTP method must be selected';
    }
    
    if (config.validate_payload && config.payload_schema) {
      try {
        if (typeof config.payload_schema === 'string') {
          JSON.parse(config.payload_schema);
        }
      } catch {
        errors.payload_schema = 'Schema must be valid JSON';
      }
    }
    
    return errors;
  },

  defaults: {
    webhook_method: ['POST'],
    content_type: 'application/json',
    require_authentication: false,
    auth_type: 'token',
    validate_payload: false,
    reject_invalid: true,
    rate_limit: 60,
    timeout_seconds: 30,
    store_raw_payload: true,
    retry_on_failure: true
  },

  features: {
    supportsExpressions: false,
    supportsVariables: false,
    supportsTesting: true,
    supportsTemplates: false
  }
};