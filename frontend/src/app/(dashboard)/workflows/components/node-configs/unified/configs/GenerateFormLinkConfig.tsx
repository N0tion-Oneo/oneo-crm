import React from 'react';
import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Link, FileText, Clock, Database, Share2 } from 'lucide-react';
import { generateFormUrl } from '@/lib/forms/form-url-generator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export const GenerateFormLinkConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.GENERATE_FORM_LINK,
  label: 'Generate Form Link',
  description: 'Generate a shareable link for a dynamic form',
  icon: Link,
  category: 'action',

  sections: [
    {
      id: 'form_config',
      label: 'Form Configuration',
      icon: FileText,
      fields: [
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'select',
          required: true,
          optionsSource: 'pipelines',
          placeholder: 'Select pipeline',
          helpText: 'Select the pipeline for the form',
          onChange: (value: string, config: any, { pipelines }: any) => {
            // Store pipeline slug when pipeline is selected
            // Convert both to strings for comparison since API might return numbers
            const pipeline = pipelines?.find((p: any) => String(p.id) === String(value));
            if (pipeline) {
              return {
                ...config,
                pipeline_id: value,
                pipeline_slug: pipeline.slug || pipeline.name?.toLowerCase().replace(/\s+/g, '-')
              };
            }
            return { ...config, pipeline_id: value };
          }
        },
        {
          key: 'form_mode',
          label: 'Form Type',
          type: 'select',
          required: true,
          defaultValue: 'public_filtered',
          options: [
            { label: 'All Fields (Internal)', value: 'internal_full' },
            { label: 'Public Fields Only', value: 'public_filtered' },
            { label: 'Stage-Specific (Internal)', value: 'stage_internal' },
            { label: 'Stage-Specific (Public)', value: 'stage_public' }
          ],
          helpText: 'Type of form to generate'
        },
        {
          key: 'stage_field',
          label: 'Stage Field',
          type: 'select',
          showWhen: (config) => {
            return config.form_mode?.includes('stage') && !!config.pipeline_id;
          },
          required: true,
          placeholder: 'Select the stage field',
          helpText: 'Select which field represents stages in this pipeline',
          optionsSource: 'pipelineFields',
          optionsFilter: (field: any) => field.field_type === 'select' || field.field_type === 'multiselect',
          optionsMap: (field: any) => ({
            value: field.slug || field.name,
            label: field.label || field.name
          })
        },
        {
          key: 'stage',
          label: 'Stage Value',
          type: 'select',
          showWhen: (config) => {
            return config.form_mode?.includes('stage') && !!config.stage_field && !!config.pipeline_id;
          },
          placeholder: 'Select stage value',
          helpText: 'Select the specific stage for this form',
          customRender: ({ config, onChange, pipelineFields }) => {
            if (!config.stage_field || !pipelineFields) {
              return <div className="text-muted-foreground text-sm">Select a stage field first</div>;
            }

            // Find the selected stage field
            const stageField = pipelineFields.find((f: any) =>
              (f.slug || f.name) === config.stage_field
            );

            if (!stageField || !stageField.field_config?.options) {
              return <div className="text-muted-foreground text-sm">No stages available in selected field</div>;
            }

            const options = stageField.field_config.options || [];

            return (
              <Select value={config.stage || ''} onValueChange={onChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select stage value" />
                </SelectTrigger>
                <SelectContent>
                  {options.map((option: any) => (
                    <SelectItem
                      key={option.value || option}
                      value={option.value || option}
                    >
                      {option.label || option.value || option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            );
          }
        }
      ]
    },
    {
      id: 'prefill_data',
      label: 'Prefill Data',
      icon: Database,
      collapsed: true,
      fields: [
        {
          key: 'include_prefill',
          label: 'Prefill Form Fields',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Include data from current record in form URL'
        },
        {
          key: 'prefill_fields',
          label: 'Fields to Prefill',
          type: 'multiselect',
          showWhen: (config) => config.include_prefill,
          optionsSource: 'pipelineFields',
          placeholder: 'Select fields to prefill',
          helpText: 'Select which fields to include in the form URL'
        },
        {
          key: 'prefill_source',
          label: 'Data Source',
          type: 'select',
          showWhen: (config) => config.include_prefill,
          defaultValue: 'current_record',
          options: [
            { label: 'Current Record', value: 'current_record' },
            { label: 'Previous Node Output', value: 'previous_node' },
            { label: 'Custom Data', value: 'custom' }
          ],
          helpText: 'Where to get the prefill data from'
        },
        {
          key: 'custom_prefill_data',
          label: 'Custom Prefill Data',
          type: 'json',
          showWhen: (config) => config.include_prefill && config.prefill_source === 'custom',
          placeholder: '{\n  "name": "John Doe",\n  "email": "john@example.com"\n}',
          rows: 6,
          helpText: 'JSON object with field values to prefill'
        }
      ]
    },
    {
      id: 'link_settings',
      label: 'Link Settings',
      icon: Clock,
      collapsed: true,
      fields: [
        {
          key: 'expiration_hours',
          label: 'Link Expiration (hours)',
          type: 'number',
          defaultValue: 0,
          min: 0,
          max: 8760, // 1 year
          helpText: 'Hours until link expires (0 = never expires)'
        },
        {
          key: 'single_use',
          label: 'Single Use Link',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Link becomes invalid after first submission'
        },
        {
          key: 'generate_short_link',
          label: 'Generate Short Link',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Create a shortened URL for easier sharing'
        }
      ]
    },
    {
      id: 'tracking',
      label: 'Tracking & Analytics',
      icon: Share2,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'include_tracking',
          label: 'Enable Tracking',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Track form views and submissions'
        },
        {
          key: 'utm_source',
          label: 'UTM Source',
          type: 'text',
          showWhen: (config) => config.include_tracking,
          placeholder: 'e.g., workflow',
          helpText: 'Traffic source for analytics'
        },
        {
          key: 'utm_medium',
          label: 'UTM Medium',
          type: 'text',
          showWhen: (config) => config.include_tracking,
          placeholder: 'e.g., email',
          helpText: 'Marketing medium'
        },
        {
          key: 'utm_campaign',
          label: 'UTM Campaign',
          type: 'text',
          showWhen: (config) => config.include_tracking,
          placeholder: 'e.g., spring-sale',
          helpText: 'Campaign name'
        },
        {
          key: 'utm_term',
          label: 'UTM Term',
          type: 'text',
          showWhen: (config) => config.include_tracking,
          placeholder: 'e.g., premium',
          helpText: 'Campaign term (optional)'
        },
        {
          key: 'utm_content',
          label: 'UTM Content',
          type: 'text',
          showWhen: (config) => config.include_tracking,
          placeholder: 'e.g., header-link',
          helpText: 'Content variant (optional)'
        }
      ]
    },
    {
      id: 'output',
      label: 'Output Configuration',
      collapsed: false,
      fields: [
        {
          key: 'output_variable',
          label: 'Output Variable Name',
          type: 'text',
          defaultValue: 'form_url',
          placeholder: 'form_url',
          helpText: 'Variable name to store the generated URL'
        },
        {
          key: 'include_qr_code',
          label: 'Generate QR Code',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Also generate a QR code for the form URL'
        },
        {
          key: 'url_preview',
          label: 'URL Preview',
          type: 'text',
          readonly: true,
          helpText: 'Preview of the generated form URL',
          customRender: ({ config }) => {
            if (!config.pipeline_id || !config.form_mode) {
              return <div className="text-muted-foreground text-sm">Configure form settings to see URL preview</div>;
            }

            try {
              const url = generateFormUrl({
                pipeline_id: config.pipeline_id,
                pipeline_slug: config.pipeline_slug,
                form_mode: config.form_mode,
                stage: config.stage
              }, {
                includeTracking: config.include_tracking,
                expirationHours: config.expiration_hours,
                utmParams: config.include_tracking ? {
                  source: config.utm_source,
                  medium: config.utm_medium,
                  campaign: config.utm_campaign,
                  term: config.utm_term,
                  content: config.utm_content
                } : undefined
              });

              return (
                <div className="space-y-2">
                  <div className="p-2 bg-muted rounded-md font-mono text-xs break-all">
                    {url}
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(url)}
                      className="text-xs text-primary hover:underline"
                    >
                      Copy URL
                    </button>
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline"
                    >
                      Open in new tab
                    </a>
                  </div>
                </div>
              );
            } catch (error) {
              return <div className="text-destructive text-sm">Error generating URL preview</div>;
            }
          }
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.pipeline_id) {
      errors.pipeline_id = 'Pipeline is required';
    }

    if (!config.form_mode) {
      errors.form_mode = 'Form type is required';
    }

    if (config.form_mode?.includes('stage')) {
      if (!config.stage_field) {
        errors.stage_field = 'Stage field is required for stage-specific forms';
      }
      if (config.stage_field && !config.stage) {
        errors.stage = 'Stage value is required for stage-specific forms';
      }
    }

    if (config.include_prefill && config.prefill_source === 'custom' && config.custom_prefill_data) {
      try {
        if (typeof config.custom_prefill_data === 'string') {
          JSON.parse(config.custom_prefill_data);
        }
      } catch {
        errors.custom_prefill_data = 'Custom prefill data must be valid JSON';
      }
    }

    if (!config.output_variable) {
      errors.output_variable = 'Output variable name is required';
    }

    return errors;
  },

  defaults: {
    form_mode: 'public_filtered',
    include_prefill: false,
    prefill_source: 'current_record',
    expiration_hours: 0,
    single_use: false,
    generate_short_link: false,
    include_tracking: true,
    output_variable: 'form_url',
    include_qr_code: false
  },

  dependencies: {
    pipelines: true,
    fields: true
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  },

  helpContent: {
    overview: 'Generate shareable form links that can be sent via email, SMS, or other communication channels.',
    examples: [
      {
        title: 'Lead Capture Form',
        description: 'Generate a public form link for lead capture',
        config: {
          form_mode: 'public_filtered',
          form_identifier: 'lead-capture',
          include_tracking: true,
          utm_source: 'email',
          utm_campaign: 'spring-campaign'
        }
      },
      {
        title: 'Stage-Specific Form with Prefill',
        description: 'Create a form for a specific stage with prefilled data',
        config: {
          form_mode: 'stage_public',
          stage: 'qualification',
          include_prefill: true,
          prefill_source: 'current_record',
          expiration_hours: 72
        }
      }
    ]
  }
};