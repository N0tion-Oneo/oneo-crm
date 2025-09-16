import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { CheckCircle, Sparkles, GitBranch } from 'lucide-react';

export const AIResponseEvaluatorConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.AI_RESPONSE_EVALUATOR,
  label: 'AI Response Evaluator',
  description: 'Evaluate responses and determine next actions using AI',
  icon: CheckCircle,
  category: 'logic',

  sections: [
    {
      id: 'evaluation_config',
      label: 'Evaluation Settings',
      icon: CheckCircle,
      fields: [
        {
          key: 'response_input',
          label: 'Response to Evaluate',
          type: 'expression',
          required: true,
          placeholder: '{{previous_node.response}} or {{customer_message}}',
          helpText: 'The response or message to evaluate'
        },
        {
          key: 'evaluation_type',
          label: 'Evaluation Type',
          type: 'multiselect',
          required: true,
          defaultValue: ['sentiment', 'intent'],
          options: [
            { label: 'Sentiment Analysis', value: 'sentiment', description: 'Positive, negative, neutral' },
            { label: 'Intent Detection', value: 'intent', description: 'What the person wants' },
            { label: 'Urgency Level', value: 'urgency', description: 'How urgent is the response' },
            { label: 'Topic Classification', value: 'topic', description: 'Categorize the topic' },
            { label: 'Action Required', value: 'action', description: 'What action to take' },
            { label: 'Quality Score', value: 'quality', description: 'Rate response quality' },
            { label: 'Compliance Check', value: 'compliance', description: 'Check for compliance issues' },
            { label: 'Language Detection', value: 'language', description: 'Detect language used' }
          ],
          helpText: 'What aspects to evaluate'
        },
        {
          key: 'context',
          label: 'Evaluation Context',
          type: 'textarea',
          allowExpressions: true,
          placeholder: 'Conversation history: {{conversation_history}}\nCustomer profile: {{customer_data}}\nProduct: {{product_name}}\n\nProvide context for better evaluation.',
          helpText: 'Additional context for accurate evaluation',
          rows: 5
        }
      ]
    },
    {
      id: 'decision_rules',
      label: 'Decision Rules',
      icon: GitBranch,
      fields: [
        {
          key: 'decision_mode',
          label: 'Decision Mode',
          type: 'select',
          required: true,
          defaultValue: 'ai_guided',
          options: [
            { label: 'AI Guided', value: 'ai_guided', description: 'AI determines the path' },
            { label: 'Rule Based', value: 'rule_based', description: 'Use defined rules' },
            { label: 'Hybrid', value: 'hybrid', description: 'Combine AI and rules' }
          ],
          helpText: 'How decisions are made'
        },
        {
          key: 'sentiment_routing',
          label: 'Route by Sentiment',
          type: 'fieldGroup',
          fields: [
            {
              key: 'positive_action',
              label: 'Positive Response Action',
              type: 'select',
              options: [
                { label: 'Continue Flow', value: 'continue' },
                { label: 'Send Thank You', value: 'thank_you' },
                { label: 'Upsell Opportunity', value: 'upsell' },
                { label: 'Request Review', value: 'review' },
                { label: 'Custom Action', value: 'custom' }
              ]
            },
            {
              key: 'negative_action',
              label: 'Negative Response Action',
              type: 'select',
              options: [
                { label: 'Escalate to Human', value: 'escalate' },
                { label: 'Send Apology', value: 'apology' },
                { label: 'Offer Solution', value: 'solution' },
                { label: 'Create Ticket', value: 'ticket' },
                { label: 'Custom Action', value: 'custom' }
              ]
            },
            {
              key: 'neutral_action',
              label: 'Neutral Response Action',
              type: 'select',
              options: [
                { label: 'Continue Flow', value: 'continue' },
                { label: 'Request Clarification', value: 'clarify' },
                { label: 'Provide Information', value: 'inform' },
                { label: 'Custom Action', value: 'custom' }
              ]
            }
          ]
        },
        {
          key: 'intent_categories',
          label: 'Intent Categories',
          type: 'textarea',
          placeholder: 'Purchase Intent\nSupport Request\nComplaint\nInformation Query\nCancellation Request\n\nDefine intent categories to detect.',
          helpText: 'List possible intents (one per line)',
          rows: 6
        },
        {
          key: 'urgency_threshold',
          label: 'Urgency Threshold',
          type: 'slider',
          defaultValue: 7,
          min: 1,
          max: 10,
          helpText: 'Threshold for high urgency (1-10)'
        },
        {
          key: 'quality_threshold',
          label: 'Quality Threshold',
          type: 'slider',
          defaultValue: 6,
          min: 1,
          max: 10,
          helpText: 'Minimum acceptable quality score'
        }
      ]
    },
    {
      id: 'ai_settings',
      label: 'AI Configuration',
      icon: Sparkles,
      collapsed: true,
      fields: [
        {
          key: 'model',
          label: 'AI Model',
          type: 'select',
          defaultValue: 'gpt-4-turbo',
          options: [
            { label: 'GPT-4 Turbo', value: 'gpt-4-turbo', description: 'Most accurate analysis' },
            { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo', description: 'Fast evaluation' },
            { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet', description: 'Nuanced understanding' }
          ],
          helpText: 'AI model for evaluation'
        },
        {
          key: 'custom_instructions',
          label: 'Custom Evaluation Instructions',
          type: 'textarea',
          placeholder: 'Additional instructions for the AI evaluator...\n\nExample: Pay special attention to customer satisfaction indicators.',
          helpText: 'Custom instructions for evaluation',
          rows: 4
        },
        {
          key: 'confidence_threshold',
          label: 'Confidence Threshold',
          type: 'slider',
          defaultValue: 0.7,
          min: 0,
          max: 1,
          step: 0.1,
          helpText: 'Minimum confidence for decisions'
        },
        {
          key: 'include_reasoning',
          label: 'Include AI Reasoning',
          type: 'switch',
          defaultValue: true,
          helpText: 'Include explanation for evaluations'
        }
      ]
    }
  ],

  outputs: [
    {
      key: 'evaluation',
      label: 'Evaluation Result',
      type: 'object',
      description: 'Complete evaluation results'
    },
    {
      key: 'sentiment',
      label: 'Sentiment',
      type: 'string',
      description: 'Detected sentiment (positive/negative/neutral)'
    },
    {
      key: 'intent',
      label: 'Intent',
      type: 'string',
      description: 'Detected intent category'
    },
    {
      key: 'urgency',
      label: 'Urgency Score',
      type: 'number',
      description: 'Urgency level (1-10)'
    },
    {
      key: 'quality',
      label: 'Quality Score',
      type: 'number',
      description: 'Response quality (1-10)'
    },
    {
      key: 'next_action',
      label: 'Recommended Action',
      type: 'string',
      description: 'AI recommended next action'
    },
    {
      key: 'confidence',
      label: 'Confidence Score',
      type: 'number',
      description: 'AI confidence in evaluation'
    },
    {
      key: 'reasoning',
      label: 'AI Reasoning',
      type: 'string',
      description: 'Explanation of evaluation'
    }
  ],

  connectionPoints: {
    outputs: [
      { id: 'positive', label: 'Positive', type: 'conditional' },
      { id: 'negative', label: 'Negative', type: 'conditional' },
      { id: 'neutral', label: 'Neutral', type: 'conditional' },
      { id: 'high_urgency', label: 'High Urgency', type: 'conditional' },
      { id: 'low_quality', label: 'Low Quality', type: 'conditional' },
      { id: 'default', label: 'Default', type: 'default' }
    ]
  },

  validationRules: [
    {
      fields: ['response_input'],
      validator: (values) => {
        if (!values.response_input || values.response_input.trim().length === 0) {
          return 'Response input is required';
        }
        return null;
      }
    },
    {
      fields: ['evaluation_type'],
      validator: (values) => {
        if (!values.evaluation_type || values.evaluation_type.length === 0) {
          return 'At least one evaluation type must be selected';
        }
        return null;
      }
    }
  ]
};