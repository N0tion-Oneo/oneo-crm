import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Globe, Shield, Settings, Zap } from 'lucide-react';

export const TriggerAPIEndpointConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_API_ENDPOINT,
  category: 'trigger',
  label: 'API Endpoint',
  description: 'Trigger workflow via custom API endpoint',
  icon: Globe,

  sections: [
    {
      id: 'basic',
      label: 'Basic Configuration',
      icon: Globe,
      fields: [
    {
      key: 'name',
      label: 'Endpoint Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., Customer Webhook',
      validation: {
        minLength: 3,
        maxLength: 100
      }
    },
    {
      key: 'description',
      label: 'Description',
      type: 'textarea',
      placeholder: 'Describe what this endpoint does',
      rows: 3
        }
      ]
    },
    {
      id: 'endpoint',
      label: 'Endpoint Configuration',
      icon: Zap,
      fields: [
        {
          key: 'endpoint_path',
      label: 'Endpoint Path',
      type: 'text',
      required: true,
      placeholder: '/api/workflows/trigger/my-endpoint',
      helperText: 'URL path for this endpoint (must be unique)',
      validation: {
        pattern: '^/[a-z0-9-/]+$',
        message: 'Must start with / and contain only lowercase letters, numbers, hyphens, and slashes'
      }
    },
    {
      key: 'method',
      label: 'HTTP Method',
      type: 'select',
      required: true,
      defaultValue: 'POST',
      options: [
        { value: 'GET', label: 'GET' },
        { value: 'POST', label: 'POST' },
        { value: 'PUT', label: 'PUT' },
        { value: 'PATCH', label: 'PATCH' }
      ]
        },
        {
          key: 'authentication',
      label: 'Authentication',
      type: 'select',
      required: true,
      defaultValue: 'api_key',
      options: [
        { value: 'none', label: 'None (Public)' },
        { value: 'api_key', label: 'API Key' },
        { value: 'bearer_token', label: 'Bearer Token' },
        { value: 'basic_auth', label: 'Basic Auth' },
        { value: 'custom_header', label: 'Custom Header' }
      ]
        }
      ]
    },
    {
      id: 'security',
      label: 'Security Settings',
      icon: Shield,
      collapsed: true,
      fields: [
        {
          key: 'api_key_header',
      label: 'API Key Header Name',
      type: 'text',
      showWhen: (config) => config.authentication === 'api_key',
      defaultValue: 'X-API-Key',
      placeholder: 'X-API-Key'
    },
    {
      key: 'custom_header_name',
      label: 'Custom Header Name',
      type: 'text',
      showWhen: (config) => config.authentication === 'custom_header',
      placeholder: 'X-Custom-Auth'
        },
        {
          key: 'expected_headers',
      label: 'Expected Headers',
      type: 'json',
      placeholder: '{\n  "Content-Type": "application/json"\n}',
      helperText: 'Headers that must be present in the request'
    },
    {
      key: 'payload_schema',
      label: 'Expected Payload Schema',
      type: 'json',
      placeholder: '{\n  "type": "object",\n  "properties": {\n    "id": { "type": "string" },\n    "data": { "type": "object" }\n  }\n}',
      helperText: 'JSON Schema for request validation'
        },
        {
          key: 'rate_limit',
      label: 'Rate Limit',
      type: 'number',
      defaultValue: 100,
      min: 1,
      max: 10000,
      helperText: 'Maximum requests per minute'
        },
        {
          key: 'enable_cors',
      label: 'Enable CORS',
      type: 'boolean',
      defaultValue: false,
      helperText: 'Allow cross-origin requests'
    },
    {
      key: 'allowed_origins',
      label: 'Allowed Origins',
      type: 'multiselect',
      showWhen: (config) => config.enable_cors === true,
      placeholder: 'Add allowed origins',
      options: [] // Dynamic input
        }
      ]
    },
    {
      id: 'response',
      label: 'Response Configuration',
      icon: Settings,
      collapsed: true,
      fields: [
        {
          key: 'response_type',
      label: 'Response Type',
      type: 'select',
      defaultValue: 'json',
      options: [
        { value: 'json', label: 'JSON' },
        { value: 'text', label: 'Plain Text' },
        { value: 'html', label: 'HTML' },
        { value: 'empty', label: 'Empty (204)' }
      ]
    },
    {
      key: 'success_response',
      label: 'Success Response',
      type: 'json',
      showWhen: (config) => config.response_type === 'json',
      defaultValue: '{"success": true, "message": "Workflow triggered"}',
      placeholder: '{"success": true}'
        },
        {
          key: 'active',
      label: 'Active',
      type: 'boolean',
      defaultValue: true
        }
      ]
    }
  ],
  outputs: [
    { key: 'request_body', type: 'json', label: 'Request Body' },
    { key: 'request_headers', type: 'json', label: 'Request Headers' },
    { key: 'request_params', type: 'json', label: 'Query Parameters' },
    { key: 'request_method', type: 'string', label: 'HTTP Method' },
    { key: 'request_path', type: 'string', label: 'Request Path' },
    { key: 'client_ip', type: 'string', label: 'Client IP' }
  ]
};