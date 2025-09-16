import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Mail, MessageSquare, Paperclip, Settings } from 'lucide-react';

export const EmailNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.UNIPILE_SEND_EMAIL,
  label: 'Send Email',
  description: 'Send an email via UniPile integration',
  icon: Mail,
  category: 'communication',

  sections: [
    {
      id: 'recipient',
      label: 'Recipients',
      icon: Mail,
      fields: [
        {
          key: 'to',
          label: 'To',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: '{{email}} or email@example.com',
          helpText: 'Email recipient(s) - comma separated for multiple',
          validation: (value) => {
            if (!value) return 'At least one recipient is required';
            // Basic email validation
            const emails = value.split(',').map((e: string) => e.trim());
            for (const email of emails) {
              if (!email.includes('{{') && !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
                return `Invalid email: ${email}`;
              }
            }
            return null;
          }
        },
        {
          key: 'cc',
          label: 'CC',
          type: 'text',
          allowExpressions: true,
          placeholder: 'Optional CC recipients',
          helpText: 'Carbon copy recipients - comma separated'
        },
        {
          key: 'bcc',
          label: 'BCC',
          type: 'text',
          allowExpressions: true,
          placeholder: 'Optional BCC recipients',
          helpText: 'Blind carbon copy recipients - comma separated'
        },
        {
          key: 'from',
          label: 'From',
          type: 'select',
          placeholder: 'Select sender account',
          helpText: 'Email account to send from',
          options: [] // Will be populated dynamically
        },
        {
          key: 'reply_to',
          label: 'Reply To',
          type: 'text',
          allowExpressions: true,
          placeholder: 'Optional reply-to address',
          helpText: 'Override the reply-to address'
        }
      ]
    },
    {
      id: 'content',
      label: 'Email Content',
      icon: MessageSquare,
      fields: [
        {
          key: 'subject',
          label: 'Subject',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: 'Email subject line',
          validation: (value) => {
            if (!value || value.trim().length === 0) {
              return 'Subject is required';
            }
            if (value.length > 200) {
              return 'Subject is too long (max 200 characters)';
            }
            return null;
          }
        },
        {
          key: 'content_type',
          label: 'Content Type',
          type: 'select',
          defaultValue: 'html',
          options: [
            { label: 'HTML', value: 'html', description: 'Rich HTML content' },
            { label: 'Plain Text', value: 'text', description: 'Simple text only' },
            { label: 'Template', value: 'template', description: 'Use email template' }
          ],
          helpText: 'Type of email content'
        },
        {
          key: 'body',
          label: 'Body',
          type: 'textarea',
          required: true,
          allowExpressions: true,
          placeholder: 'Email body content...',
          rows: 10,
          helpText: 'Email body - supports variables and HTML',
          showWhen: (config) => config.content_type !== 'template',
          richField: {
            type: config => config.content_type === 'html' ? 'html' : 'markdown',
            height: '300px'
          }
        },
        {
          key: 'template_id',
          label: 'Email Template',
          type: 'select',
          required: true,
          showWhen: (config) => config.content_type === 'template',
          placeholder: 'Select template',
          options: [] // Will be populated with available templates
        },
        {
          key: 'template_variables',
          label: 'Template Variables',
          type: 'json',
          showWhen: (config) => config.content_type === 'template',
          placeholder: '{\n  "name": "{{customer_name}}",\n  "order_id": "{{order.id}}"\n}',
          helpText: 'Variables to pass to the template',
          allowExpressions: true
        }
      ]
    },
    {
      id: 'attachments',
      label: 'Attachments',
      icon: Paperclip,
      collapsed: true,
      fields: [
        {
          key: 'attachments',
          label: 'File Attachments',
          type: 'array',
          helpText: 'Add file attachments to the email',
          // This would need a custom component for file management
          // For now, using a simple JSON field
          defaultValue: []
        },
        {
          key: 'attachment_sources',
          label: 'Attachment Sources',
          type: 'multiselect',
          options: [
            { label: 'From Previous Node', value: 'node_output' },
            { label: 'From URL', value: 'url' },
            { label: 'From Pipeline Record', value: 'record' },
            { label: 'Generated PDF', value: 'pdf' }
          ],
          helpText: 'Sources for attachments'
        },
        {
          key: 'generate_pdf',
          label: 'Generate PDF from Body',
          type: 'boolean',
          helpText: 'Convert email body to PDF and attach',
          showWhen: (config) => config.attachment_sources?.includes('pdf')
        }
      ]
    },
    {
      id: 'tracking',
      label: 'Tracking & Analytics',
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'track_opens',
          label: 'Track Opens',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Track when emails are opened'
        },
        {
          key: 'track_clicks',
          label: 'Track Clicks',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Track link clicks in emails'
        },
        {
          key: 'require_read_receipt',
          label: 'Request Read Receipt',
          type: 'boolean',
          helpText: 'Request read receipt from recipient'
        },
        {
          key: 'importance',
          label: 'Importance',
          type: 'select',
          defaultValue: 'normal',
          options: [
            { label: 'Low', value: 'low' },
            { label: 'Normal', value: 'normal' },
            { label: 'High', value: 'high' }
          ],
          helpText: 'Email importance/priority level'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Settings',
      icon: Settings,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'headers',
          label: 'Custom Headers',
          type: 'keyvalue',
          helpText: 'Add custom email headers',
          placeholder: 'Header name: value'
        },
        {
          key: 'send_time',
          label: 'Send Time',
          type: 'select',
          defaultValue: 'immediate',
          options: [
            { label: 'Immediately', value: 'immediate' },
            { label: 'Scheduled', value: 'scheduled' },
            { label: 'Optimal Time', value: 'optimal' }
          ],
          helpText: 'When to send the email'
        },
        {
          key: 'scheduled_datetime',
          label: 'Scheduled Date/Time',
          type: 'datetime',
          showWhen: (config) => config.send_time === 'scheduled',
          helpText: 'When to send the email',
          allowExpressions: true
        },
        {
          key: 'retry_on_failure',
          label: 'Retry on Failure',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Retry sending if initial attempt fails'
        },
        {
          key: 'retry_count',
          label: 'Retry Count',
          type: 'number',
          defaultValue: 3,
          min: 1,
          max: 5,
          showWhen: (config) => config.retry_on_failure,
          helpText: 'Number of retry attempts'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    // Required fields
    if (!config.to) {
      errors.to = 'At least one recipient is required';
    }
    if (!config.subject) {
      errors.subject = 'Subject is required';
    }
    if (config.content_type !== 'template' && !config.body) {
      errors.body = 'Email body is required';
    }
    if (config.content_type === 'template' && !config.template_id) {
      errors.template_id = 'Template selection is required';
    }

    return errors;
  },

  defaults: {
    content_type: 'html',
    track_opens: true,
    track_clicks: true,
    importance: 'normal',
    send_time: 'immediate',
    retry_on_failure: true,
    retry_count: 3,
    attachments: []
  },

  dependencies: {
    pipelines: false,
    workflows: false,
    users: false,
    fields: false
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: true
  }

  // Note: For complex attachment management, we could add a customComponent
  // customComponent: EmailAttachmentManager
};