import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Combine, Database, Settings, GitMerge } from 'lucide-react';

export const MergeDataNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.MERGE_DATA,
  label: 'Merge Data',
  description: 'Combine data from multiple sources into a single output',
  icon: GitMerge,
  category: 'action',

  sections: [
    {
      id: 'sources',
      label: 'Data Sources',
      icon: Database,
      fields: [
        {
          key: 'merge_sources',
          label: 'Data Sources',
          type: 'array',
          required: true,
          helpText: 'Add data sources to merge. Use {{variables}} to reference previous outputs',
          placeholder: 'e.g., {{previous_node.output}}, {{record.data}}',
          defaultValue: [],
          arrayConfig: {
            addLabel: 'Add Source',
            itemLabel: 'Source',
            fields: [
              {
                key: 'source_path',
                label: 'Source Path',
                type: 'text',
                required: true,
                allowExpressions: true,
                placeholder: '{{node_id.output}} or literal value',
                helpText: 'Path to data or literal value'
              },
              {
                key: 'source_type',
                label: 'Source Type',
                type: 'select',
                required: true,
                defaultValue: 'context_path',
                options: [
                  { label: 'Context Path', value: 'context_path' },
                  { label: 'Literal Value', value: 'literal' },
                  { label: 'Template', value: 'template' }
                ],
                helpText: 'How to interpret the source'
              },
              {
                key: 'transformations',
                label: 'Transformations',
                type: 'array',
                showWhen: (config) => config.source_type === 'context_path',
                helpText: 'Optional transformations to apply',
                arrayConfig: {
                  addLabel: 'Add Transformation',
                  fields: [
                    {
                      key: 'type',
                      label: 'Transformation Type',
                      type: 'select',
                      options: [
                        { label: 'Rename Keys', value: 'rename' },
                        { label: 'Filter Keys', value: 'filter' },
                        { label: 'Map Values', value: 'map' },
                        { label: 'Flatten', value: 'flatten' }
                      ]
                    },
                    {
                      key: 'config',
                      label: 'Configuration',
                      type: 'json',
                      placeholder: '{"oldKey": "newKey"}'
                    }
                  ]
                }
              }
            ]
          }
        }
      ]
    },
    {
      id: 'merge_config',
      label: 'Merge Configuration',
      icon: Combine,
      fields: [
        {
          key: 'merge_strategy',
          label: 'Merge Strategy',
          type: 'select',
          required: true,
          defaultValue: 'combine',
          options: [
            { label: 'Combine (merge all keys)', value: 'combine' },
            { label: 'Override (last wins)', value: 'override' },
            { label: 'Append (create array)', value: 'append' },
            { label: 'Deep Merge (nested objects)', value: 'deep_merge' },
            { label: 'Union (unique values)', value: 'union' },
            { label: 'Custom', value: 'custom' }
          ],
          helpText: 'How to merge data from multiple sources'
        },
        {
          key: 'conflict_resolution',
          label: 'Conflict Resolution',
          type: 'select',
          required: true,
          defaultValue: 'last_wins',
          showWhen: (config) => ['combine', 'deep_merge'].includes(config.merge_strategy),
          options: [
            { label: 'Last Wins', value: 'last_wins' },
            { label: 'First Wins', value: 'first_wins' },
            { label: 'Combine as Array', value: 'array' },
            { label: 'Concatenate Strings', value: 'concat' },
            { label: 'Sum Numbers', value: 'sum' },
            { label: 'Skip Conflicts', value: 'skip' }
          ],
          helpText: 'How to handle conflicting keys'
        },
        {
          key: 'custom_merge_function',
          label: 'Custom Merge Function',
          type: 'textarea',
          showWhen: (config) => config.merge_strategy === 'custom',
          placeholder: '// JavaScript function to merge data\n// (data1, data2) => { return {...data1, ...data2}; }',
          helpText: 'Custom JavaScript function for merging',
          rows: 8
        },
        {
          key: 'preserve_arrays',
          label: 'Preserve Arrays',
          type: 'boolean',
          defaultValue: true,
          showWhen: (config) => config.merge_strategy === 'deep_merge',
          helpText: 'Keep arrays as arrays instead of merging them'
        },
        {
          key: 'null_handling',
          label: 'Null Value Handling',
          type: 'select',
          defaultValue: 'ignore',
          options: [
            { label: 'Ignore Nulls', value: 'ignore' },
            { label: 'Keep Nulls', value: 'keep' },
            { label: 'Remove Null Keys', value: 'remove' }
          ],
          helpText: 'How to handle null/undefined values'
        }
      ]
    },
    {
      id: 'output',
      label: 'Output Configuration',
      icon: Settings,
      fields: [
        {
          key: 'output_key',
          label: 'Output Key',
          type: 'text',
          required: true,
          defaultValue: 'merged_data',
          placeholder: 'merged_data',
          helpText: 'Key name for the merged output'
        },
        {
          key: 'output_format',
          label: 'Output Format',
          type: 'select',
          defaultValue: 'object',
          options: [
            { label: 'Object', value: 'object' },
            { label: 'Array', value: 'array' },
            { label: 'JSON String', value: 'json_string' },
            { label: 'Flattened Object', value: 'flattened' }
          ],
          helpText: 'Format of the merged output'
        },
        {
          key: 'include_metadata',
          label: 'Include Merge Metadata',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Include information about the merge process'
        },
        {
          key: 'validation_schema',
          label: 'Output Validation Schema',
          type: 'json',
          placeholder: '{"type": "object", "properties": {...}}',
          helpText: 'Optional JSON schema to validate output'
        },
        {
          key: 'on_validation_error',
          label: 'On Validation Error',
          type: 'select',
          defaultValue: 'warn',
          showWhen: (config) => config.validation_schema,
          options: [
            { label: 'Warning Only', value: 'warn' },
            { label: 'Fail Node', value: 'fail' },
            { label: 'Use Default', value: 'default' }
          ],
          helpText: 'Action when validation fails'
        }
      ]
    }
  ]
};