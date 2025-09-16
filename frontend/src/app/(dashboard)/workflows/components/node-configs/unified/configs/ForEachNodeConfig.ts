import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Repeat, Settings } from 'lucide-react';

export const ForEachNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.FOR_EACH,
  label: 'For Each Loop',
  description: 'Iterate over a list of items',
  icon: Repeat,
  category: 'control',

  sections: [
    {
      id: 'loop_config',
      label: 'Loop Configuration',
      icon: Repeat,
      fields: [
        {
          key: 'items_source',
          label: 'Items Source',
          type: 'select',
          required: true,
          defaultValue: 'variable',
          options: [
            { label: 'From Variable', value: 'variable' },
            { label: 'From Previous Node', value: 'previous' },
            { label: 'From Record Field', value: 'field' },
            { label: 'Fixed List', value: 'fixed' },
            { label: 'Range of Numbers', value: 'range' }
          ],
          helpText: 'Source of items to iterate over'
        },
        {
          key: 'items_variable',
          label: 'Items Variable',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.items_source === 'variable',
          placeholder: '{{items}} or {{records}}',
          helpText: 'Variable containing the array to iterate'
        },
        {
          key: 'field_path',
          label: 'Field Path',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (c) => c.items_source === 'field',
          placeholder: '{{record.items}} or items.data',
          helpText: 'Path to the array field'
        },
        {
          key: 'fixed_items',
          label: 'Fixed Items',
          type: 'json',
          required: true,
          showWhen: (c) => c.items_source === 'fixed',
          placeholder: '[\n  "item1",\n  "item2",\n  "item3"\n]',
          helpText: 'Array of items to iterate over',
          rows: 6
        },
        {
          key: 'range_start',
          label: 'Range Start',
          type: 'number',
          required: true,
          showWhen: (c) => c.items_source === 'range',
          defaultValue: 1,
          helpText: 'Starting number for range'
        },
        {
          key: 'range_end',
          label: 'Range End',
          type: 'number',
          required: true,
          showWhen: (c) => c.items_source === 'range',
          defaultValue: 10,
          helpText: 'Ending number for range (inclusive)'
        },
        {
          key: 'range_step',
          label: 'Range Step',
          type: 'number',
          showWhen: (c) => c.items_source === 'range',
          defaultValue: 1,
          helpText: 'Step increment for range'
        },
        {
          key: 'item_variable_name',
          label: 'Item Variable Name',
          type: 'text',
          defaultValue: 'item',
          placeholder: 'item',
          helpText: 'Variable name for current item in loop'
        },
        {
          key: 'index_variable_name',
          label: 'Index Variable Name',
          type: 'text',
          defaultValue: 'index',
          placeholder: 'index',
          helpText: 'Variable name for current index in loop'
        }
      ]
    },
    {
      id: 'execution',
      label: 'Execution Settings',
      fields: [
        {
          key: 'batch_size',
          label: 'Batch Size',
          type: 'number',
          defaultValue: 1,
          min: 1,
          max: 100,
          helpText: 'Number of items to process in parallel'
        },
        {
          key: 'max_iterations',
          label: 'Max Iterations',
          type: 'number',
          defaultValue: 1000,
          min: 1,
          max: 10000,
          helpText: 'Maximum number of iterations (safety limit)'
        },
        {
          key: 'continue_on_error',
          label: 'Continue on Error',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Continue loop if an iteration fails'
        },
        {
          key: 'collect_results',
          label: 'Collect Results',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Collect results from each iteration'
        },
        {
          key: 'results_variable_name',
          label: 'Results Variable Name',
          type: 'text',
          showWhen: (c) => c.collect_results,
          defaultValue: 'loop_results',
          placeholder: 'loop_results',
          helpText: 'Variable to store collected results'
        }
      ]
    },
    {
      id: 'filtering',
      label: 'Filtering',
      collapsed: true,
      fields: [
        {
          key: 'enable_filter',
          label: 'Enable Filtering',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Filter items before processing'
        },
        {
          key: 'filter_condition',
          label: 'Filter Condition',
          type: 'text',
          allowExpressions: true,
          showWhen: (c) => c.enable_filter,
          placeholder: '{{item.status}} === "active"',
          helpText: 'Condition to filter items'
        },
        {
          key: 'skip_empty',
          label: 'Skip Empty Items',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Skip null, undefined, or empty items'
        }
      ]
    },
    {
      id: 'advanced',
      label: 'Advanced Options',
      icon: Settings,
      collapsed: true,
      advanced: true,
      fields: [
        {
          key: 'delay_between',
          label: 'Delay Between Items (ms)',
          type: 'number',
          defaultValue: 0,
          min: 0,
          max: 10000,
          helpText: 'Delay between processing items'
        },
        {
          key: 'reverse_order',
          label: 'Reverse Order',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Process items in reverse order'
        },
        {
          key: 'unique_items',
          label: 'Unique Items Only',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Remove duplicate items before processing'
        },
        {
          key: 'break_on_condition',
          label: 'Break Condition',
          type: 'text',
          allowExpressions: true,
          placeholder: '{{total}} > 100',
          helpText: 'Condition to break out of loop early'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};
    
    if (!config.items_source) {
      errors.items_source = 'Items source is required';
    }
    
    if (config.items_source === 'variable' && !config.items_variable) {
      errors.items_variable = 'Items variable is required';
    }
    
    if (config.items_source === 'field' && !config.field_path) {
      errors.field_path = 'Field path is required';
    }
    
    if (config.items_source === 'range') {
      if (!config.range_start) errors.range_start = 'Range start is required';
      if (!config.range_end) errors.range_end = 'Range end is required';
    }
    
    return errors;
  },

  defaults: {
    items_source: 'variable',
    item_variable_name: 'item',
    index_variable_name: 'index',
    batch_size: 1,
    max_iterations: 1000,
    continue_on_error: false,
    collect_results: true,
    results_variable_name: 'loop_results',
    enable_filter: false,
    skip_empty: true,
    delay_between: 0,
    reverse_order: false,
    unique_items: false,
    range_start: 1,
    range_end: 10,
    range_step: 1
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false
  }
};