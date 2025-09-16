import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Search, Database, Filter } from 'lucide-react';

export const RecordFindNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.RECORD_FIND,
  label: 'Find Records',
  description: 'Search for records in a pipeline',
  icon: Search,
  category: 'data',

  sections: [
    {
      id: 'search_config',
      label: 'Search Configuration',
      icon: Search,
      fields: [
        {
          key: 'pipeline_id',
          label: 'Pipeline',
          type: 'pipeline',
          required: true,
          placeholder: 'Select pipeline to search',
          helpText: 'The pipeline to search for records'
        },
        {
          key: 'search_type',
          label: 'Search Type',
          type: 'select',
          required: true,
          defaultValue: 'filter',
          options: [
            { label: 'Filter Criteria', value: 'filter' },
            { label: 'Record ID', value: 'id' },
            { label: 'Full Text Search', value: 'text' },
            { label: 'Related Records', value: 'related' },
            { label: 'Custom Query', value: 'custom' }
          ],
          helpText: 'How to search for records'
        },
        {
          key: 'record_id',
          label: 'Record ID',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.search_type === 'id',
          placeholder: '{{record_id}}',
          helpText: 'ID of the record to find'
        },
        {
          key: 'search_text',
          label: 'Search Text',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.search_type === 'text',
          placeholder: '{{search_query}}',
          helpText: 'Text to search for across all fields'
        },
        {
          key: 'filter_criteria',
          label: 'Filter Criteria',
          type: 'json',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.search_type === 'filter',
          placeholder: '{\n  "status": "active",\n  "created_at": {\n    "$gte": "{{start_date}}"\n  }\n}',
          helpText: 'MongoDB-style filter conditions',
          rows: 8
        },
        {
          key: 'related_record',
          label: 'Related to Record',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.search_type === 'related',
          placeholder: '{{record_id}}',
          helpText: 'Find records related to this record'
        },
        {
          key: 'relationship_type',
          label: 'Relationship Type',
          type: 'select',
          showWhen: (c) => c.search_type === 'related',
          options: [
            { label: 'Any Relationship', value: 'any' },
            { label: 'Parent Of', value: 'parent_of' },
            { label: 'Child Of', value: 'child_of' },
            { label: 'Related To', value: 'related_to' }
          ],
          helpText: 'Type of relationship to search'
        }
      ]
    },
    {
      id: 'results',
      label: 'Result Options',
      icon: Filter,
      fields: [
        {
          key: 'limit',
          label: 'Maximum Results',
          type: 'number',
          defaultValue: 100,
          min: 1,
          max: 1000,
          helpText: 'Maximum number of records to return'
        },
        {
          key: 'sort_by',
          label: 'Sort By Field',
          type: 'text',
          placeholder: 'created_at',
          helpText: 'Field to sort results by'
        },
        {
          key: 'sort_order',
          label: 'Sort Order',
          type: 'select',
          defaultValue: 'desc',
          options: [
            { label: 'Ascending', value: 'asc' },
            { label: 'Descending', value: 'desc' }
          ],
          helpText: 'Sort direction for results'
        },
        {
          key: 'skip',
          label: 'Skip Records',
          type: 'number',
          defaultValue: 0,
          min: 0,
          helpText: 'Number of records to skip (for pagination)'
        },
        {
          key: 'return_single',
          label: 'Return Single Record',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Return only the first matching record'
        }
      ]
    },
    {
      id: 'fields',
      label: 'Field Selection',
      collapsed: true,
      fields: [
        {
          key: 'select_fields',
          label: 'Select Specific Fields',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Return only specific fields'
        },
        {
          key: 'included_fields',
          label: 'Fields to Include',
          type: 'multiselect',
          showWhen: (c) => c.select_fields,
          options: [], // Will be populated based on pipeline
          helpText: 'Fields to include in results'
        },
        {
          key: 'excluded_fields',
          label: 'Fields to Exclude',
          type: 'multiselect',
          showWhen: (c) => !c.select_fields,
          options: [], // Will be populated based on pipeline
          helpText: 'Fields to exclude from results'
        },
        {
          key: 'include_relationships',
          label: 'Include Relationships',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Include related records in results'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Options',
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'fail_if_not_found',
          label: 'Fail if No Results',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Throw error if no records found'
        },
        {
          key: 'cache_results',
          label: 'Cache Results',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Cache search results for performance'
        },
        {
          key: 'cache_duration',
          label: 'Cache Duration (seconds)',
          type: 'number',
          showWhen: (c) => c.cache_results,
          defaultValue: 300,
          min: 1,
          max: 3600,
          helpText: 'How long to cache results'
        },
        {
          key: 'timeout_seconds',
          label: 'Timeout (seconds)',
          type: 'number',
          defaultValue: 30,
          min: 1,
          max: 300,
          helpText: 'Maximum time for search operation'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.pipeline_id) {
      errors.pipeline_id = 'Pipeline selection is required';
    }
    
    if (!config.search_type) {
      errors.search_type = 'Search type is required';
    }
    
    if (config.search_type === 'filter' && !config.filter_criteria) {
      errors.filter_criteria = 'Filter criteria is required';
    }
    
    if (config.search_type === 'id' && !config.record_id) {
      errors.record_id = 'Record ID is required';
    }
    
    if (config.search_type === 'text' && !config.search_text) {
      errors.search_text = 'Search text is required';
    }
    
    return errors;
  },

  defaults: {
    search_type: 'filter',
    limit: 100,
    sort_order: 'desc',
    skip: 0,
    return_single: false,
    select_fields: false,
    include_relationships: false,
    fail_if_not_found: false,
    cache_results: false,
    cache_duration: 300,
    timeout_seconds: 30
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
  }
};