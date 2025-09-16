import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Workflow, Settings, ArrowUpDown, Shield, RefreshCw } from 'lucide-react';

export const SubWorkflowNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.SUB_WORKFLOW,
  category: 'logic',
  label: 'Sub-workflow',
  description: 'Execute another workflow as a sub-process',
  icon: Workflow,

  sections: [
    {
      id: 'basic',
      label: 'Basic Configuration',
      icon: Workflow,
      fields: [
    {
      key: 'name',
      label: 'Sub-workflow Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., Process Customer Onboarding',
      validation: {
        minLength: 3,
        maxLength: 100
      }
    },
    {
      key: 'description',
      label: 'Description',
      type: 'textarea',
      placeholder: 'Describe what this sub-workflow does',
      rows: 2
        },
        {
          key: 'workflow_selection',
      label: 'Workflow Selection',
      type: 'select',
      required: true,
      defaultValue: 'specific',
      options: [
        { value: 'specific', label: 'Specific Workflow' },
        { value: 'reusable', label: 'Reusable Workflow' },
        { value: 'dynamic', label: 'Dynamic (Based on Condition)' },
        { value: 'template', label: 'From Template' }
      ]
    },
    {
      key: 'workflow_id',
      label: 'Target Workflow',
      type: 'select',
      required: true,
      showWhen: (config) => config.workflow_selection === 'specific',
      placeholder: 'Select workflow to execute',
      options: [], // Will be populated dynamically
      optionsSource: 'workflows',
      optionsFilter: (workflow) => workflow.is_active !== false,
      optionsMap: (workflow) => ({
        value: workflow.id,
        label: workflow.name
      })
    },
    {
      key: 'reusable_workflow_id',
      label: 'Reusable Workflow',
      type: 'select',
      required: true,
      showWhen: (config) => config.workflow_selection === 'reusable',
      placeholder: 'Select reusable workflow component',
      helpText: 'Select a workflow marked as reusable',
      options: [], // Will be populated with reusable workflows
      optionsSource: 'workflows',
      optionsFilter: (workflow) => workflow.is_reusable === true,
      optionsMap: (workflow) => ({
        value: workflow.id,
        label: workflow.name,
        description: workflow.description
      })
    },
    {
      key: 'workflow_condition',
      label: 'Workflow Selection Logic',
      type: 'json',
      required: true,
      showWhen: (config) => config.workflow_selection === 'dynamic',
      placeholder: '{\n  "conditions": [\n    {"if": "{{record.type}} == \'lead\'", "workflow": "lead_processing"},\n    {"if": "{{record.type}} == \'customer\'", "workflow": "customer_processing"}\n  ]\n}',
      helperText: 'Define conditions to select workflow dynamically'
    },
    {
      key: 'template_id',
      label: 'Workflow Template',
      type: 'select',
      required: true,
      showWhen: (config) => config.workflow_selection === 'template',
      placeholder: 'Select workflow template',
      options: [] // Will be populated with templates
        }
      ]
    },
    {
      id: 'execution',
      label: 'Execution Settings',
      icon: Settings,
      fields: [
        {
          key: 'execution_mode',
      label: 'Execution Mode',
      type: 'select',
      required: true,
      defaultValue: 'sync',
      options: [
        { value: 'sync', label: 'Synchronous (Wait for Completion)' },
        { value: 'async', label: 'Asynchronous (Fire and Forget)' },
        { value: 'parallel', label: 'Parallel (Multiple Instances)' }
      ]
    },
    {
      key: 'wait_for_completion',
      label: 'Wait for Completion',
      type: 'boolean',
      defaultValue: true,
      showWhen: (config) => config.execution_mode === 'sync',
      helperText: 'Pause parent workflow until sub-workflow completes'
    },
    {
      key: 'timeout_minutes',
      label: 'Timeout (Minutes)',
      type: 'number',
      showWhen: (config) => config.wait_for_completion === true,
      defaultValue: 60,
      min: 1,
      max: 1440,
      helperText: 'Maximum time to wait for sub-workflow'
        },
        {
          key: 'reusable_parameters',
      label: 'Reusable Workflow Parameters',
      type: 'json',
      showWhen: (config) => config.workflow_selection === 'reusable',
      placeholder: '{\n  "process_type": "standard",\n  "notification_enabled": true,\n  "priority_level": "medium"\n}',
      helpText: 'Configuration parameters for the reusable workflow'
    },
        {
          key: 'input_mapping',
      label: 'Input Parameters',
      type: 'json',
      placeholder: '{\n  "customer_id": "{{record.id}}",\n  "order_amount": "{{previous_node.total}}",\n  "priority": "high"\n}',
      helperText: 'Map data from parent to sub-workflow'
    },
    {
      key: 'output_mapping',
      label: 'Output Mapping',
      type: 'json',
      showWhen: (config) => config.execution_mode === 'sync',
      placeholder: '{\n  "approval_status": "status",\n  "processed_data": "result"\n}',
      helperText: 'Map sub-workflow outputs to parent variables'
        }
      ]
    },
    {
      id: 'iteration',
      label: 'Iteration & Parallelization',
      icon: RefreshCw,
      collapsed: true,
      fields: [
        {
          key: 'iteration_mode',
      label: 'Iteration Mode',
      type: 'select',
      showWhen: (config) => config.execution_mode === 'parallel',
      defaultValue: 'none',
      options: [
        { value: 'none', label: 'Single Instance' },
        { value: 'for_each', label: 'For Each Item' },
        { value: 'batch', label: 'Batch Processing' }
      ]
    },
    {
      key: 'iteration_source',
      label: 'Iteration Source',
      type: 'expression',
      showWhen: (config) => config.iteration_mode !== 'none',
      placeholder: '{{previous_node.items}} or {{record.line_items}}',
      helperText: 'Array to iterate over'
    },
    {
      key: 'batch_size',
      label: 'Batch Size',
      type: 'number',
      showWhen: (config) => config.iteration_mode === 'batch',
      defaultValue: 10,
      min: 1,
      max: 100
        }
      ]
    },
    {
      id: 'error_handling',
      label: 'Error Handling',
      icon: Shield,
      collapsed: true,
      fields: [
        {
          key: 'error_handling',
      label: 'Error Handling',
      type: 'select',
      defaultValue: 'fail',
      options: [
        { value: 'fail', label: 'Fail Parent Workflow' },
        { value: 'continue', label: 'Continue on Error' },
        { value: 'retry', label: 'Retry Failed Instances' },
        { value: 'fallback', label: 'Use Fallback Workflow' }
      ]
    },
    {
      key: 'retry_count',
      label: 'Retry Count',
      type: 'number',
      showWhen: (config) => config.error_handling === 'retry',
      defaultValue: 3,
      min: 1,
      max: 10
    },
    {
      key: 'fallback_workflow',
      label: 'Fallback Workflow',
      type: 'select',
      showWhen: (config) => config.error_handling === 'fallback',
      placeholder: 'Select fallback workflow',
      options: [], // Will be populated dynamically
      optionsSource: 'workflows',
      optionsFilter: (workflow) => workflow.is_active !== false,
      optionsMap: (workflow) => ({
        value: workflow.id,
        label: workflow.name
      })
        },
        {
          key: 'inherit_context',
      label: 'Inherit Parent Context',
      type: 'boolean',
      defaultValue: true,
      helperText: 'Pass parent workflow context to sub-workflow'
    },
    {
      key: 'isolated_execution',
      label: 'Isolated Execution',
      type: 'boolean',
      defaultValue: false,
      helperText: 'Run in isolated environment (no parent access)'
        }
      ]
    }
  ],
  outputs: [
    { key: 'execution_id', type: 'string', label: 'Execution ID' },
    { key: 'status', type: 'string', label: 'Execution Status' },
    { key: 'output_data', type: 'object', label: 'Output Data' },
    { key: 'execution_time', type: 'number', label: 'Execution Time (ms)' },
    { key: 'error_message', type: 'string', label: 'Error Message' },
    { key: 'iteration_results', type: 'array', label: 'Iteration Results' }
  ]
};