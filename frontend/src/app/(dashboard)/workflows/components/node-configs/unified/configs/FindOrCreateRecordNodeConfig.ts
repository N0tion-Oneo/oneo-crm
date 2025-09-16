import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { UserPlus, Search, Database, Settings, GitMerge } from 'lucide-react';

export const FindOrCreateRecordNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.RESOLVE_CONTACT,
  label: 'Find or Create Record',
  description: 'Find an existing record or create a new one if not found',
  icon: UserPlus,
  category: 'action',

  sections: [
    {
      id: 'identification',
      label: 'Record Identification',
      icon: Search,
      fields: [
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'pipeline_select',
          required: true,
          helpText: 'Pipeline to search in or create record'
        },
        {
          key: 'search_criteria',
          label: 'Search Criteria',
          type: 'object',
          required: true,
          helpText: 'Fields to use for finding existing records',
          fields: [
            {
              key: 'email',
              label: 'Email',
              type: 'text',
              allowExpressions: true,
              placeholder: '{{contact.email}}',
              helpText: 'Email address to search for'
            },
            {
              key: 'phone',
              label: 'Phone',
              type: 'text',
              allowExpressions: true,
              placeholder: '{{contact.phone}}',
              helpText: 'Phone number to search for'
            },
            {
              key: 'linkedin_url',
              label: 'LinkedIn URL',
              type: 'text',
              allowExpressions: true,
              placeholder: '{{contact.linkedin}}',
              helpText: 'LinkedIn profile URL'
            },
            {
              key: 'custom_identifier',
              label: 'Custom Identifier Field',
              type: 'text',
              placeholder: 'customer_id',
              helpText: 'Custom field name for unique identifier'
            },
            {
              key: 'custom_identifier_value',
              label: 'Custom Identifier Value',
              type: 'text',
              allowExpressions: true,
              showWhen: (config) => !!config.custom_identifier,
              placeholder: '{{data.customer_id}}',
              helpText: 'Value of the custom identifier'
            }
          ]
        },
        {
          key: 'search_mode',
          label: 'Search Mode',
          type: 'select',
          required: true,
          defaultValue: 'any',
          options: [
            { label: 'Match Any Criteria', value: 'any' },
            { label: 'Match All Criteria', value: 'all' },
            { label: 'Priority Order', value: 'priority' },
            { label: 'Custom Logic', value: 'custom' }
          ],
          helpText: 'How to match search criteria'
        },
        {
          key: 'priority_order',
          label: 'Search Priority Order',
          type: 'array',
          showWhen: (config) => config.search_mode === 'priority',
          defaultValue: ['email', 'phone', 'linkedin_url'],
          helpText: 'Order to check identifiers (first match wins)',
          arrayConfig: {
            addLabel: 'Add Field',
            itemLabel: 'Field',
            fields: [
              {
                key: 'field',
                label: 'Field',
                type: 'select',
                options: [
                  { label: 'Email', value: 'email' },
                  { label: 'Phone', value: 'phone' },
                  { label: 'LinkedIn URL', value: 'linkedin_url' },
                  { label: 'Custom', value: 'custom' }
                ]
              }
            ]
          }
        }
      ]
    },
    {
      id: 'creation',
      label: 'Record Creation',
      icon: Database,
      fields: [
        {
          key: 'create_if_not_found',
          label: 'Create If Not Found',
          type: 'boolean',
          required: true,
          defaultValue: true,
          helpText: 'Create a new record if no existing record is found'
        },
        {
          key: 'record_data',
          label: 'New Record Data',
          type: 'object',
          showWhen: (config) => config.create_if_not_found === true,
          helpText: 'Data for creating new record',
          fields: [
            {
              key: 'name',
              label: 'Name',
              type: 'text',
              allowExpressions: true,
              placeholder: '{{contact.first_name}} {{contact.last_name}}',
              helpText: 'Full name or company name'
            },
            {
              key: 'email',
              label: 'Email',
              type: 'text',
              allowExpressions: true,
              placeholder: '{{contact.email}}',
              helpText: 'Email address'
            },
            {
              key: 'phone',
              label: 'Phone',
              type: 'text',
              allowExpressions: true,
              placeholder: '{{contact.phone}}',
              helpText: 'Phone number'
            },
            {
              key: 'company',
              label: 'Company',
              type: 'text',
              allowExpressions: true,
              placeholder: '{{contact.company}}',
              helpText: 'Company name'
            },
            {
              key: 'title',
              label: 'Job Title',
              type: 'text',
              allowExpressions: true,
              placeholder: '{{contact.title}}',
              helpText: 'Job title or position'
            },
            {
              key: 'source',
              label: 'Source',
              type: 'select',
              defaultValue: 'workflow',
              options: [
                { label: 'Workflow', value: 'workflow' },
                { label: 'Import', value: 'import' },
                { label: 'API', value: 'api' },
                { label: 'Form', value: 'form' },
                { label: 'Manual', value: 'manual' },
                { label: 'Other', value: 'other' }
              ],
              helpText: 'Source of the record'
            }
          ]
        },
        {
          key: 'additional_fields',
          label: 'Additional Fields',
          type: 'json',
          showWhen: (config) => config.create_if_not_found === true,
          placeholder: '{"custom_field": "value", "tags": ["tag1", "tag2"]}',
          helpText: 'Additional fields for the new record'
        }
      ]
    },
    {
      id: 'update',
      label: 'Update Strategy',
      icon: GitMerge,
      fields: [
        {
          key: 'update_existing',
          label: 'Update Existing Record',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Update the record if it already exists'
        },
        {
          key: 'merge_strategy',
          label: 'Merge Strategy',
          type: 'select',
          required: true,
          defaultValue: 'update_empty',
          showWhen: (config) => config.update_existing === true,
          options: [
            { label: 'Update Empty Fields Only', value: 'update_empty' },
            { label: 'Override All Fields', value: 'override_all' },
            { label: 'Keep Existing (No Update)', value: 'keep_existing' },
            { label: 'Merge Arrays/Objects', value: 'deep_merge' },
            { label: 'Custom Merge Rules', value: 'custom' }
          ],
          helpText: 'How to handle existing data when updating'
        },
        {
          key: 'fields_to_update',
          label: 'Fields to Update',
          type: 'multiselect',
          showWhen: (config) => config.update_existing === true && config.merge_strategy === 'custom',
          placeholder: 'Select fields to update',
          options: [], // Will be populated with pipeline fields
          helpText: 'Specific fields to update on existing record'
        },
        {
          key: 'update_data',
          label: 'Update Data',
          type: 'json',
          showWhen: (config) => config.update_existing === true,
          placeholder: '{"last_contacted": "{{now}}", "status": "active"}',
          helpText: 'Data to update on existing record'
        },
        {
          key: 'conflict_resolution',
          label: 'Conflict Resolution',
          type: 'select',
          defaultValue: 'newer_wins',
          showWhen: (config) => config.update_existing === true && config.merge_strategy === 'deep_merge',
          options: [
            { label: 'Newer Value Wins', value: 'newer_wins' },
            { label: 'Existing Value Wins', value: 'existing_wins' },
            { label: 'Combine Values', value: 'combine' },
            { label: 'Create Array', value: 'array' }
          ],
          helpText: 'How to resolve conflicts in data'
        }
      ]
    },
    {
      id: 'output',
      label: 'Output Configuration',
      icon: Settings,
      fields: [
        {
          key: 'output_fields',
          label: 'Output Fields',
          type: 'multiselect',
          placeholder: 'Select fields to include in output',
          options: [], // Will be populated with pipeline fields
          helpText: 'Which fields to include in the output (leave empty for all)'
        },
        {
          key: 'include_metadata',
          label: 'Include Metadata',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include metadata about the operation'
        },
        {
          key: 'metadata_fields',
          label: 'Metadata to Include',
          type: 'multiselect',
          showWhen: (config) => config.include_metadata === true,
          defaultValue: ['created', 'updated', 'resolution_method'],
          options: [
            { label: 'Created Flag', value: 'created' },
            { label: 'Updated Flag', value: 'updated' },
            { label: 'Resolution Method', value: 'resolution_method' },
            { label: 'Match Score', value: 'match_score' },
            { label: 'Matched Fields', value: 'matched_fields' },
            { label: 'Timestamp', value: 'timestamp' }
          ],
          helpText: 'What metadata to include'
        },
        {
          key: 'on_multiple_matches',
          label: 'Multiple Matches Handling',
          type: 'select',
          defaultValue: 'first',
          options: [
            { label: 'Use First Match', value: 'first' },
            { label: 'Use Best Match', value: 'best' },
            { label: 'Fail Node', value: 'fail' },
            { label: 'Create New', value: 'create_new' },
            { label: 'Return All', value: 'all' }
          ],
          helpText: 'What to do if multiple records match'
        },
        {
          key: 'duplicate_detection',
          label: 'Enable Duplicate Detection',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Check for potential duplicates before creating'
        },
        {
          key: 'duplicate_threshold',
          label: 'Duplicate Match Threshold',
          type: 'number',
          showWhen: (config) => config.duplicate_detection === true,
          defaultValue: 0.8,
          min: 0,
          max: 1,
          step: 0.1,
          helpText: 'Similarity threshold for duplicate detection (0-1)'
        }
      ]
    }
  ]
};