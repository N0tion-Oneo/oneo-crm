import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { RotateCw, XCircle, Clock, CheckCircle } from 'lucide-react';

export const WorkflowLoopControllerConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.WORKFLOW_LOOP_CONTROLLER,
  label: 'Workflow Loop Controller',
  description: 'Control workflow iterations and loop back to earlier stages',
  icon: RotateCw,
  category: 'control',

  // Visual styling to indicate control flow node
  nodeStyle: {
    backgroundColor: '#f0f9ff',
    borderColor: '#0284c7',
    borderWidth: 2,
    borderStyle: 'dashed',
    shape: 'diamond', // Diamond shape for decision/control nodes
  },

  sections: [
    {
      id: 'loop_configuration',
      label: 'Loop Configuration',
      icon: RotateCw,
      fields: [
        {
          key: 'loop_key',
          label: 'Loop Identifier',
          type: 'text',
          required: true,
          defaultValue: 'main_loop',
          placeholder: 'unique_loop_id',
          helpText: 'Unique identifier for this loop (used to track state)'
        },
        {
          key: 'loop_type',
          label: 'Loop Type',
          type: 'select',
          required: true,
          defaultValue: 'conditional',
          options: [
            {
              label: 'Conditional',
              value: 'conditional',
              description: 'Loop based on conditions'
            },
            {
              label: 'Count Based',
              value: 'count_based',
              description: 'Loop a specific number of times'
            },
            {
              label: 'Time Based',
              value: 'time_based',
              description: 'Loop for a duration'
            }
          ],
          helpText: 'How the loop iteration is controlled'
        },
        {
          key: 'max_iterations',
          label: 'Maximum Iterations',
          type: 'number',
          required: true,
          defaultValue: 10,
          min: 1,
          max: 100,
          helpText: 'Safety limit to prevent infinite loops'
        },
        {
          key: 'target_count',
          label: 'Target Count',
          type: 'number',
          defaultValue: 5,
          min: 1,
          max: 100,
          helpText: 'Number of times to loop (for count-based loops)'
        },
        {
          key: 'max_duration_minutes',
          label: 'Maximum Duration (minutes)',
          type: 'number',
          defaultValue: 60,
          min: 1,
          max: 1440,
          helpText: 'Maximum time to keep looping (for time-based loops)'
        }
      ]
    },
    {
      id: 'exit_conditions',
      label: 'Exit Conditions',
      icon: XCircle,
      collapsed: false,
      fields: [
        {
          key: 'exit_conditions',
          label: 'When to Exit Loop',
          type: 'condition_builder',
          defaultValue: [],
          conditions: [
            {
              type: 'evaluation_result',
              label: 'AI Evaluation Result',
              fields: [
                {
                  key: 'action',
                  label: 'When action is',
                  type: 'select',
                  options: [
                    { label: 'Complete', value: 'complete' },
                    { label: 'Escalate', value: 'escalate' },
                    { label: 'Failed', value: 'failed' }
                  ]
                }
              ]
            },
            {
              type: 'context_value',
              label: 'Context Value Check',
              fields: [
                {
                  key: 'path',
                  label: 'Context Path',
                  type: 'text',
                  placeholder: 'evaluation_result.score'
                },
                {
                  key: 'operator',
                  label: 'Operator',
                  type: 'select',
                  options: [
                    { label: 'Equals', value: 'equals' },
                    { label: 'Not Equals', value: 'not_equals' },
                    { label: 'Greater Than', value: 'greater_than' },
                    { label: 'Less Than', value: 'less_than' },
                    { label: 'Contains', value: 'contains' },
                    { label: 'Is True', value: 'is_true' },
                    { label: 'Is False', value: 'is_false' }
                  ]
                },
                {
                  key: 'expected_value',
                  label: 'Expected Value',
                  type: 'text'
                }
              ]
            },
            {
              type: 'flag_set',
              label: 'Flag Check',
              fields: [
                {
                  key: 'flag_name',
                  label: 'Flag Name',
                  type: 'select',
                  options: [
                    { label: 'Opt Out Detected', value: 'opt_out_detected' },
                    { label: 'Conversation Complete', value: 'conversation_complete' },
                    { label: 'Needs Escalation', value: 'needs_escalation' },
                    { label: 'Error Occurred', value: 'error_occurred' }
                  ]
                }
              ]
            }
          ],
          helpText: 'Define conditions that will exit the loop'
        }
      ]
    },
    {
      id: 'workflow_paths',
      label: 'Workflow Paths',
      icon: CheckCircle,
      fields: [
        {
          key: 'loop_back_to',
          label: 'Loop Back To',
          type: 'node_selector',
          required: true,
          placeholder: 'Select node to loop back to',
          helpText: 'Which workflow node to return to when continuing the loop',
          nodeFilter: (node) => {
            // Only show nodes that come before this one in the workflow
            return true;
          }
        },
        {
          key: 'exit_to',
          label: 'Exit To',
          type: 'node_selector',
          required: true,
          placeholder: 'Select node to continue to after loop',
          helpText: 'Which workflow node to continue to when exiting the loop',
          nodeFilter: (node) => {
            // Only show nodes that come after this one
            return true;
          }
        }
      ]
    }
  ],

  // Visual connections to show loop flow
  connectionRules: {
    inputs: {
      min: 1,
      max: -1, // Unlimited inputs (can receive from multiple paths)
      types: ['data', 'control']
    },
    outputs: {
      min: 2,
      max: 2,
      labels: ['Continue Loop', 'Exit Loop'],
      types: ['control', 'control']
    }
  },

  // Runtime behavior
  executionMode: 'sync', // Executes immediately

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.loop_key) {
      errors.loop_key = 'Loop identifier is required';
    }

    if (!config.max_iterations || config.max_iterations < 1) {
      errors.max_iterations = 'Maximum iterations must be at least 1';
    }

    if (config.loop_type === 'count_based' && !config.target_count) {
      errors.target_count = 'Target count is required for count-based loops';
    }

    if (config.loop_type === 'time_based' && !config.max_duration_minutes) {
      errors.max_duration_minutes = 'Duration is required for time-based loops';
    }

    if (!config.loop_back_to) {
      errors.loop_back_to = 'Loop back target is required';
    }

    if (!config.exit_to) {
      errors.exit_to = 'Exit target is required';
    }

    return errors;
  },

  defaults: {
    loop_key: 'main_loop',
    loop_type: 'conditional',
    max_iterations: 10,
    exit_conditions: [],
    loop_back_to: '',
    exit_to: ''
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: false,
    supportsBreakpoints: true, // Can set breakpoints for debugging
    supportsMetrics: true // Track loop performance
  },

  // Help content
  helpContent: {
    overview: 'The Workflow Loop Controller manages iteration through workflow stages, allowing you to repeat sections of your workflow based on conditions.',
    examples: [
      {
        title: 'AI Conversation Loop',
        description: 'Loop through message generation and response evaluation until objective is met',
        config: {
          loop_type: 'conditional',
          max_iterations: 10,
          exit_conditions: [
            {
              type: 'evaluation_result',
              action: 'complete'
            }
          ]
        }
      },
      {
        title: 'Retry with Limit',
        description: 'Retry an operation up to 3 times',
        config: {
          loop_type: 'count_based',
          target_count: 3,
          max_iterations: 3
        }
      }
    ]
  }
};