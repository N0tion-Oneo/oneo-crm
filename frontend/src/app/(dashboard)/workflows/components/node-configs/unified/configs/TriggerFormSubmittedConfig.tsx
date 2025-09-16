import React from 'react';
import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { FileText, Filter, MapPin, Shield } from 'lucide-react';
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
        },
        {
          key: 'create_record',
          label: 'Create Record',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Automatically create a record from form data'
        }
      ]
    },
    {
      id: 'field_mapping',
      label: 'Field Mapping',
      showWhen: (config) => config.create_record,
      fields: [
        {
          key: 'mapping_mode',
          label: 'Mapping Mode',
          type: 'select',
          defaultValue: 'auto',
          options: [
            { label: 'Auto-map by field names', value: 'auto' },
            { label: 'Custom mapping', value: 'custom' },
            { label: 'Use form defaults', value: 'defaults' }
          ],
          helpText: 'How to map form fields to pipeline fields'
        },
        {
          key: 'field_mappings',
          label: 'Field Mappings',
          type: 'keyvalue',
          showWhen: (config) => config.mapping_mode === 'custom',
          placeholder: 'Map form fields to pipeline fields',
          helpText: 'Custom field mapping configuration'
        },
        {
          key: 'unmapped_fields',
          label: 'Unmapped Fields',
          type: 'select',
          defaultValue: 'ignore',
          options: [
            { label: 'Ignore unmapped fields', value: 'ignore' },
            { label: 'Store in metadata', value: 'metadata' },
            { label: 'Reject submission', value: 'reject' }
          ],
          helpText: 'How to handle fields without mapping'
        }
      ]
    },
    {
      id: 'validation',
      label: 'Submission Validation',
      icon: Shield,
      collapsed: true,
      fields: [
        {
          key: 'require_validation',
          label: 'Require Validation',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Validate submissions before triggering'
        },
        {
          key: 'validation_rules',
          label: 'Validation Rules',
          type: 'json',
          showWhen: (config) => config.require_validation,
          placeholder: '{\n  "email": "required|email",\n  "age": "required|min:18"\n}',
          rows: 6,
          helpText: 'Validation rules for form fields'
        },
        {
          key: 'duplicate_check',
          label: 'Check for Duplicates',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Check if record already exists'
        },
        {
          key: 'duplicate_fields',
          label: 'Duplicate Check Fields',
          type: 'multiselect',
          showWhen: (config) => config.duplicate_check,
          placeholder: 'Select fields for duplicate check',
          options: [], // Will be populated with pipeline fields
          helpText: 'Fields to use for duplicate detection'
        },
        {
          key: 'duplicate_action',
          label: 'Duplicate Action',
          type: 'select',
          showWhen: (config) => config.duplicate_check,
          defaultValue: 'skip',
          options: [
            { label: 'Skip duplicate', value: 'skip' },
            { label: 'Update existing', value: 'update' },
            { label: 'Create anyway', value: 'create' },
            { label: 'Merge data', value: 'merge' }
          ],
          helpText: 'What to do when duplicate is found'
        }
      ]
    },
    {
      id: 'filtering',
      label: 'Submission Filtering',
      icon: Filter,
      collapsed: true,
      fields: [
        {
          key: 'filter_submissions',
          label: 'Filter Submissions',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Only trigger for certain submissions'
        },
        {
          key: 'filter_conditions',
          label: 'Filter Conditions',
          type: 'json',
          showWhen: (config) => config.filter_submissions,
          placeholder: '{\n  "country": "US",\n  "score": { "$gte": 50 }\n}',
          rows: 6,
          helpText: 'Conditions that submissions must meet'
        },
        {
          key: 'source_filter',
          label: 'Source Filter',
          type: 'select',
          defaultValue: 'any',
          options: [
            { label: 'Any source', value: 'any' },
            { label: 'Direct submission only', value: 'direct' },
            { label: 'API submission only', value: 'api' },
            { label: 'Embedded forms only', value: 'embedded' }
          ],
          helpText: 'Filter by submission source'
        }
      ]
    },
    {
      id: 'location',
      label: 'Location & Device',
      icon: MapPin,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'capture_location',
          label: 'Capture Location',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Capture submitter location data'
        },
        {
          key: 'location_required',
          label: 'Location Required',
          type: 'boolean',
          showWhen: (config) => config.capture_location,
          defaultValue: false,
          helpText: 'Require location for submission'
        },
        {
          key: 'capture_device',
          label: 'Capture Device Info',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Capture device and browser information'
        },
        {
          key: 'device_filter',
          label: 'Device Filter',
          type: 'multiselect',
          showWhen: (config) => config.capture_device,
          defaultValue: [],
          options: [
            { label: 'Desktop', value: 'desktop' },
            { label: 'Mobile', value: 'mobile' },
            { label: 'Tablet', value: 'tablet' }
          ],
          helpText: 'Only accept from specific devices'
        }
      ]
    },
    {
      id: 'notifications',
      label: 'Notifications',
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'send_confirmation',
          label: 'Send Confirmation',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Send confirmation to submitter'
        },
        {
          key: 'confirmation_template',
          label: 'Confirmation Template',
          type: 'select',
          showWhen: (config) => config.send_confirmation,
          placeholder: 'Select template',
          options: [], // Will be populated with email templates
          helpText: 'Email template for confirmation'
        },
        {
          key: 'notify_team',
          label: 'Notify Team',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Notify team members of submission'
        },
        {
          key: 'team_members',
          label: 'Team Members',
          type: 'multiselect',
          showWhen: (config) => config.notify_team,
          placeholder: 'Select team members',
          options: [], // Will be populated with users
          helpText: 'Team members to notify'
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

    if (config.require_validation && config.validation_rules) {
      try {
        if (typeof config.validation_rules === 'string') {
          JSON.parse(config.validation_rules);
        }
      } catch {
        errors.validation_rules = 'Validation rules must be valid JSON';
      }
    }

    if (config.filter_submissions && config.filter_conditions) {
      try {
        if (typeof config.filter_conditions === 'string') {
          JSON.parse(config.filter_conditions);
        }
      } catch {
        errors.filter_conditions = 'Filter conditions must be valid JSON';
      }
    }

    return errors;
  },

  defaults: {
    form_mode: 'public_filtered',
    create_record: true,
    mapping_mode: 'auto',
    unmapped_fields: 'ignore',
    require_validation: false,
    duplicate_check: false,
    duplicate_action: 'skip',
    filter_submissions: false,
    source_filter: 'any',
    capture_location: false,
    capture_device: true,
    send_confirmation: false,
    notify_team: false
  },

  dependencies: {
    pipelines: true,
    fields: true,
    users: true
  },

  features: {
    supportsExpressions: false,
    supportsVariables: false,
    supportsTesting: true,
    supportsTemplates: true
  }
};