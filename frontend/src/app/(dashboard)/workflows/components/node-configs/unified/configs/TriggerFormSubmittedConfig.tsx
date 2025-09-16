import React from 'react';
import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { FileText } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export const TriggerFormSubmittedConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.TRIGGER_FORM_SUBMITTED,
  label: 'Form Submitted Trigger',
  description: 'Triggers when a form is submitted',
  icon: FileText,
  category: 'trigger',

  sections: [
    {
      id: 'form_selection',
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
        },
        {
          key: 'form_url_preview',
          label: 'Form URL Preview',
          type: 'text',
          readonly: true,
          helpText: 'This is the URL that will be generated for your form',
          customRender: ({ config }) => {
            if (!config.pipeline_id) return <div className="text-muted-foreground text-sm">Select a pipeline to see form URL</div>;

            let url = '/forms';
            const pipelineSlug = config.pipeline_slug || config.pipeline_id;

            if (config.form_mode === 'internal_full') {
              url = `/forms/internal/${config.pipeline_id}`;
            } else if (config.form_mode === 'public_filtered') {
              url = `/forms/${pipelineSlug}`;
            } else if (config.form_mode === 'stage_internal' && config.stage) {
              // Internal stage forms use query parameter
              url = `/forms/internal/${config.pipeline_id}?stage=${config.stage}`;
            } else if (config.form_mode === 'stage_public' && config.stage) {
              url = `/forms/${pipelineSlug}/stage/${config.stage}`;
            }

            return (
              <div className="p-2 bg-muted rounded-md font-mono text-xs">
                {window.location.origin}{url}
              </div>
            );
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

    return errors;
  },

  defaults: {
    form_mode: 'public_filtered'
  },

  dependencies: {
    pipelines: true,
    fields: true
  },

  features: {
    supportsExpressions: false,
    supportsVariables: false,
    supportsTesting: true,
    supportsTemplates: true
  }
};