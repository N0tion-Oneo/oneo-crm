import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { MessageSquare, Phone, Image, Clock } from 'lucide-react';

export const WhatsAppNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.UNIPILE_SEND_WHATSAPP,
  label: 'Send WhatsApp',
  description: 'Send WhatsApp messages via UniPile',
  icon: MessageSquare,
  category: 'communication',

  sections: [
    {
      id: 'recipient',
      label: 'Recipient',
      icon: Phone,
      fields: [
        {
          key: 'to',
          label: 'Phone Number',
          type: 'text',
          required: true,
          allowExpressions: true,
          placeholder: '{{phone}} or +1234567890',
          helpText: 'Recipient phone number with country code',
          validation: (value) => {
            if (!value) return 'Phone number is required';
            if (!value.includes('{{') && !value.match(/^\+?[1-9]\d{1,14}$/)) {
              return 'Invalid phone number format';
            }
            return null;
          }
        },
        {
          key: 'recipient_name',
          label: 'Recipient Name',
          type: 'text',
          allowExpressions: true,
          placeholder: '{{name}}',
          helpText: 'Optional recipient name for personalization'
        }
      ]
    },
    {
      id: 'message',
      label: 'Message Content',
      icon: MessageSquare,
      fields: [
        {
          key: 'message_type',
          label: 'Message Type',
          type: 'select',
          required: true,
          defaultValue: 'text',
          options: [
            { label: 'Text Message', value: 'text' },
            { label: 'Template Message', value: 'template' },
            { label: 'Media Message', value: 'media' },
            { label: 'Interactive Message', value: 'interactive' },
            { label: 'Location', value: 'location' },
            { label: 'Contact Card', value: 'contact' }
          ],
          helpText: 'Type of WhatsApp message to send'
        },
        {
          key: 'text',
          label: 'Message Text',
          type: 'textarea',
          required: true,
          allowExpressions: true,
          placeholder: 'Hello {{name}}, your order #{{order_id}} is ready!',
          showWhen: (c) => c.message_type === 'text',
          helpText: 'Message content (max 4096 characters)',
          rows: 5,
          validation: (value) => {
            if (value && value.length > 4096) {
              return 'Message exceeds 4096 character limit';
            }
            return null;
          }
        },
        {
          key: 'template_name',
          label: 'Template Name',
          type: 'select',
          required: true,
          showWhen: (c) => c.message_type === 'template',
          options: [], // Will be populated with approved WhatsApp templates
          helpText: 'Pre-approved WhatsApp template'
        },
        {
          key: 'template_params',
          label: 'Template Parameters',
          type: 'json',
          allowExpressions: true,
          showWhen: (c) => c.message_type === 'template',
          placeholder: '{\n  "1": "{{customer_name}}",\n  "2": "{{order_number}}",\n  "3": "{{delivery_date}}"\n}',
          helpText: 'Parameters for the template',
          rows: 6
        },
        {
          key: 'media_type',
          label: 'Media Type',
          type: 'select',
          showWhen: (c) => c.message_type === 'media',
          required: true,
          options: [
            { label: 'Image', value: 'image' },
            { label: 'Video', value: 'video' },
            { label: 'Audio', value: 'audio' },
            { label: 'Document', value: 'document' },
            { label: 'Sticker', value: 'sticker' }
          ],
          helpText: 'Type of media to send'
        },
        {
          key: 'media_url',
          label: 'Media URL',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.message_type === 'media',
          placeholder: 'https://example.com/image.jpg or {{media_url}}',
          helpText: 'URL of the media file'
        },
        {
          key: 'media_caption',
          label: 'Caption',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.message_type === 'media',
          placeholder: 'Check out this image!',
          helpText: 'Optional caption for media (max 1024 chars)'
        }
      ]
    },
    {
      id: 'interactive',
      label: 'Interactive Elements',
      collapsed: true,
      showWhen: (c) => c.message_type === 'interactive',
      fields: [
        {
          key: 'interactive_type',
          label: 'Interactive Type',
          type: 'select',
          required: true,
          options: [
            { label: 'Reply Buttons', value: 'button' },
            { label: 'List Menu', value: 'list' },
            { label: 'Single Product', value: 'product' },
            { label: 'Product List', value: 'product_list' }
          ],
          helpText: 'Type of interactive element'
        },
        {
          key: 'header_text',
          label: 'Header',
          type: 'text',
          allowExpressions: true,
          placeholder: 'Choose an option',
          helpText: 'Header text for interactive message'
        },
        {
          key: 'body_text',
          label: 'Body',
          type: 'textarea',
          required: true,
          allowExpressions: true,
          placeholder: 'Please select from the options below',
          helpText: 'Main message text',
          rows: 3
        },
        {
          key: 'footer_text',
          label: 'Footer',
          type: 'text',
          allowExpressions: true,
          placeholder: 'Reply within 24 hours',
          helpText: 'Optional footer text'
        },
        {
          key: 'buttons',
          label: 'Buttons',
          type: 'json',
          required: true,
          showWhen: (c) => c.interactive_type === 'button',
          placeholder: '[\n  {"id": "yes", "title": "Yes"},\n  {"id": "no", "title": "No"},\n  {"id": "maybe", "title": "Maybe"}\n]',
          helpText: 'Button configuration (max 3 buttons)',
          rows: 6
        },
        {
          key: 'list_sections',
          label: 'List Sections',
          type: 'json',
          required: true,
          showWhen: (c) => c.interactive_type === 'list',
          placeholder: '[\n  {\n    "title": "Section 1",\n    "rows": [\n      {"id": "1", "title": "Option 1", "description": "Description"}\n    ]\n  }\n]',
          helpText: 'List menu configuration',
          rows: 8
        }
      ]
    },
    {
      id: 'delivery',
      label: 'Delivery Options',
      icon: Clock,
      collapsed: true,
      advanced: true,
      fields: [
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
          helpText: 'When to send the message'
        },
        {
          key: 'scheduled_time',
          label: 'Scheduled Time',
          type: 'datetime',
          allowExpressions: true,
          showWhen: (c) => c.send_time === 'scheduled',
          helpText: 'Time to send the message'
        },
        {
          key: 'priority',
          label: 'Priority',
          type: 'select',
          defaultValue: 'normal',
          options: [
            { label: 'High', value: 'high' },
            { label: 'Normal', value: 'normal' },
            { label: 'Low', value: 'low' }
          ],
          helpText: 'Message priority'
        },
        {
          key: 'track_delivery',
          label: 'Track Delivery',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Track message delivery status'
        },
        {
          key: 'track_read',
          label: 'Track Read Receipt',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Track when message is read'
        },
        {
          key: 'retry_on_failure',
          label: 'Retry on Failure',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Retry if message fails to send'
        },
        {
          key: 'retry_count',
          label: 'Retry Count',
          type: 'number',
          defaultValue: 3,
          min: 1,
          max: 5,
          showWhen: (c) => c.retry_on_failure,
          helpText: 'Number of retry attempts'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.to) {
      errors.to = 'Phone number is required';
    }
    
    if (config.message_type === 'text' && !config.text) {
      errors.text = 'Message text is required';
    }
    
    if (config.message_type === 'template' && !config.template_name) {
      errors.template_name = 'Template selection is required';
    }
    
    if (config.message_type === 'media' && !config.media_url) {
      errors.media_url = 'Media URL is required';
    }
    
    return errors;
  },

  defaults: {
    message_type: 'text',
    send_time: 'immediate',
    priority: 'normal',
    track_delivery: true,
    track_read: true,
    retry_on_failure: true,
    retry_count: 3
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: true
  }
};