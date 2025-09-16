import { UnifiedNodeConfig } from '../types';
import { WorkflowNodeType } from '../../../../types';
import { Brain, FileText, BarChart, Settings } from 'lucide-react';

export const AIAnalysisNodeConfig: UnifiedNodeConfig = {
  type: WorkflowNodeType.AI_ANALYSIS,
  label: 'AI Analysis',
  description: 'Analyze content and extract insights using AI',
  icon: Brain,
  category: 'action',

  sections: [
    {
      id: 'input',
      label: 'Input Configuration',
      icon: FileText,
      fields: [
        {
          key: 'input_source',
          label: 'Input Source',
          type: 'select',
          required: true,
          defaultValue: 'text',
          options: [
            { label: 'Text/Content', value: 'text' },
            { label: 'Record Data', value: 'record' },
            { label: 'File/Document', value: 'file' },
            { label: 'Image', value: 'image' },
            { label: 'Previous Node Output', value: 'previous' },
            { label: 'Multiple Sources', value: 'multiple' }
          ],
          helpText: 'What to analyze'
        },
        {
          key: 'input_text',
          label: 'Text to Analyze',
          type: 'textarea',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.input_source === 'text',
          placeholder: 'Enter text or use {{variables}}',
          helpText: 'The content to analyze',
          rows: 6
        },
        {
          key: 'record_fields',
          label: 'Record Fields',
          type: 'multiselect',
          required: true,
          showWhen: (config) => config.input_source === 'record',
          placeholder: 'Select fields to analyze',
          options: [], // Will be populated with pipeline fields
          helpText: 'Which record fields to include in analysis'
        },
        {
          key: 'file_path',
          label: 'File Path',
          type: 'text',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.input_source === 'file',
          placeholder: '{{file_url}} or path',
          helpText: 'Path or URL to the file'
        },
        {
          key: 'combine_sources',
          label: 'Combine Multiple Sources',
          type: 'boolean',
          showWhen: (config) => config.input_source === 'multiple',
          defaultValue: true,
          helpText: 'Combine all sources for analysis'
        }
      ]
    },
    {
      id: 'analysis',
      label: 'Analysis Configuration',
      icon: Brain,
      fields: [
        {
          key: 'analysis_type',
          label: 'Analysis Type',
          type: 'select',
          required: true,
          defaultValue: 'sentiment',
          options: [
            { label: 'Sentiment Analysis', value: 'sentiment' },
            { label: 'Entity Extraction', value: 'entities' },
            { label: 'Key Points Summary', value: 'summary' },
            { label: 'Classification', value: 'classification' },
            { label: 'Intent Detection', value: 'intent' },
            { label: 'Emotion Analysis', value: 'emotion' },
            { label: 'Topic Modeling', value: 'topics' },
            { label: 'Communication Analysis', value: 'communication' },
            { label: 'Lead Scoring', value: 'lead_scoring' },
            { label: 'Custom Analysis', value: 'custom' }
          ],
          helpText: 'Type of analysis to perform'
        },
        {
          key: 'custom_prompt',
          label: 'Analysis Instructions',
          type: 'textarea',
          required: true,
          allowExpressions: true,
          showWhen: (config) => config.analysis_type === 'custom',
          placeholder: 'Analyze the following content and extract...',
          helpText: 'Custom instructions for the AI',
          rows: 6
        },
        {
          key: 'classification_categories',
          label: 'Categories',
          type: 'array',
          required: true,
          showWhen: (config) => config.analysis_type === 'classification',
          placeholder: 'List of categories',
          helpText: 'Possible classification categories'
        },
        {
          key: 'entities_to_extract',
          label: 'Entity Types',
          type: 'multiselect',
          showWhen: (config) => config.analysis_type === 'entities',
          defaultValue: ['person', 'organization', 'location'],
          options: [
            { label: 'Person', value: 'person' },
            { label: 'Organization', value: 'organization' },
            { label: 'Location', value: 'location' },
            { label: 'Date', value: 'date' },
            { label: 'Money', value: 'money' },
            { label: 'Email', value: 'email' },
            { label: 'Phone', value: 'phone' },
            { label: 'URL', value: 'url' },
            { label: 'Product', value: 'product' },
            { label: 'Event', value: 'event' }
          ],
          helpText: 'Types of entities to extract'
        },
        {
          key: 'summary_length',
          label: 'Summary Length',
          type: 'select',
          showWhen: (config) => config.analysis_type === 'summary',
          defaultValue: 'medium',
          options: [
            { label: 'Brief (1-2 sentences)', value: 'brief' },
            { label: 'Short (3-5 sentences)', value: 'short' },
            { label: 'Medium (1-2 paragraphs)', value: 'medium' },
            { label: 'Detailed (3-5 paragraphs)', value: 'detailed' },
            { label: 'Custom length', value: 'custom' }
          ],
          helpText: 'Length of the summary'
        },
        {
          key: 'max_words',
          label: 'Maximum Words',
          type: 'number',
          showWhen: (config) => config.analysis_type === 'summary' && config.summary_length === 'custom',
          defaultValue: 150,
          min: 10,
          max: 1000,
          helpText: 'Maximum words in summary'
        },
        {
          key: 'communication_metrics',
          label: 'Communication Metrics',
          type: 'multiselect',
          showWhen: (config) => config.analysis_type === 'communication',
          defaultValue: ['engagement', 'tone', 'timing'],
          options: [
            { label: 'Engagement Level', value: 'engagement' },
            { label: 'Tone Analysis', value: 'tone' },
            { label: 'Response Timing', value: 'timing' },
            { label: 'Message Length', value: 'length' },
            { label: 'Call to Action', value: 'cta' },
            { label: 'Follow-up Needed', value: 'follow_up' },
            { label: 'Urgency', value: 'urgency' },
            { label: 'Professional Score', value: 'professional' }
          ],
          helpText: 'Metrics to analyze for communication'
        },
        {
          key: 'lead_scoring_factors',
          label: 'Lead Scoring Factors',
          type: 'multiselect',
          showWhen: (config) => config.analysis_type === 'lead_scoring',
          defaultValue: ['engagement', 'fit', 'interest'],
          options: [
            { label: 'Engagement Score', value: 'engagement' },
            { label: 'Company Fit', value: 'fit' },
            { label: 'Interest Level', value: 'interest' },
            { label: 'Budget Indicators', value: 'budget' },
            { label: 'Timeline', value: 'timeline' },
            { label: 'Authority', value: 'authority' },
            { label: 'Need', value: 'need' },
            { label: 'Pain Points', value: 'pain' }
          ],
          helpText: 'Factors to include in lead scoring'
        }
      ]
    },
    {
      id: 'output',
      label: 'Output Configuration',
      icon: BarChart,
      fields: [
        {
          key: 'output_format',
          label: 'Output Format',
          type: 'select',
          defaultValue: 'structured',
          options: [
            { label: 'Structured JSON', value: 'structured' },
            { label: 'Plain Text', value: 'text' },
            { label: 'Markdown', value: 'markdown' },
            { label: 'HTML', value: 'html' },
            { label: 'CSV', value: 'csv' }
          ],
          helpText: 'Format of the analysis output'
        },
        {
          key: 'include_confidence',
          label: 'Include Confidence Scores',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Include confidence levels in results'
        },
        {
          key: 'include_reasoning',
          label: 'Include Reasoning',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Include AI reasoning/explanation'
        },
        {
          key: 'save_to_record',
          label: 'Save to Record',
          type: 'boolean',
          defaultValue: false,
          helpText: 'Save analysis results to record'
        },
        {
          key: 'target_field',
          label: 'Target Field',
          type: 'field',
          showWhen: (config) => config.save_to_record,
          required: true,
          placeholder: 'Select field to store results',
          options: [], // Will be populated with pipeline fields
          helpText: 'Where to save the analysis'
        },
        {
          key: 'append_results',
          label: 'Append to Existing',
          type: 'boolean',
          showWhen: (config) => config.save_to_record,
          defaultValue: false,
          helpText: 'Append to existing field value'
        }
      ]
    },
    {
      id: 'ai_settings',
      label: 'AI Settings',
      icon: Settings,
      collapsed: true,
      fields: [
        {
          key: 'model',
          label: 'AI Model',
          type: 'select',
          defaultValue: 'gpt-4-turbo',
          options: [
            { label: 'GPT-4 Turbo', value: 'gpt-4-turbo', description: 'Most accurate' },
            { label: 'GPT-4', value: 'gpt-4', description: 'Powerful' },
            { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo', description: 'Fast & efficient' },
            { label: 'Claude 3 Opus', value: 'claude-3-opus', description: 'Best Claude' },
            { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet', description: 'Balanced' },
            { label: 'Claude 3 Haiku', value: 'claude-3-haiku', description: 'Fast' }
          ],
          helpText: 'Which AI model to use'
        },
        {
          key: 'temperature',
          label: 'Temperature',
          type: 'slider',
          defaultValue: 0.3,
          min: 0,
          max: 1,
          step: 0.1,
          helpText: 'Lower = more focused, Higher = more creative'
        },
        {
          key: 'max_tokens',
          label: 'Max Tokens',
          type: 'number',
          defaultValue: 1000,
          min: 100,
          max: 4000,
          helpText: 'Maximum response length'
        },
        {
          key: 'language',
          label: 'Output Language',
          type: 'select',
          defaultValue: 'auto',
          options: [
            { label: 'Auto-detect', value: 'auto' },
            { label: 'English', value: 'en' },
            { label: 'Spanish', value: 'es' },
            { label: 'French', value: 'fr' },
            { label: 'German', value: 'de' },
            { label: 'Italian', value: 'it' },
            { label: 'Portuguese', value: 'pt' },
            { label: 'Chinese', value: 'zh' },
            { label: 'Japanese', value: 'ja' },
            { label: 'Korean', value: 'ko' }
          ],
          helpText: 'Language for the analysis output'
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
          key: 'preprocessing',
          label: 'Text Preprocessing',
          type: 'multiselect',
          defaultValue: ['clean'],
          options: [
            { label: 'Clean HTML/Markdown', value: 'clean' },
            { label: 'Remove URLs', value: 'remove_urls' },
            { label: 'Remove Emails', value: 'remove_emails' },
            { label: 'Remove Numbers', value: 'remove_numbers' },
            { label: 'Remove Punctuation', value: 'remove_punctuation' },
            { label: 'Lowercase', value: 'lowercase' },
            { label: 'Remove Stop Words', value: 'remove_stopwords' }
          ],
          helpText: 'Preprocessing steps before analysis'
        },
        {
          key: 'chunk_size',
          label: 'Chunk Size',
          type: 'number',
          defaultValue: 0,
          min: 0,
          max: 10000,
          helpText: 'Split large text into chunks (0 = no chunking)'
        },
        {
          key: 'cache_results',
          label: 'Cache Results',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Cache analysis for repeated content'
        },
        {
          key: 'cache_duration',
          label: 'Cache Duration (hours)',
          type: 'number',
          showWhen: (config) => config.cache_results,
          defaultValue: 24,
          min: 1,
          max: 168,
          helpText: 'How long to cache results'
        },
        {
          key: 'fallback_on_error',
          label: 'Fallback on Error',
          type: 'boolean',
          defaultValue: true,
          helpText: 'Use simpler analysis if main fails'
        }
      ]
    }
  ],

  validate: (config) => {
    const errors: Record<string, string> = {};

    if (!config.input_source) {
      errors.input_source = 'Input source is required';
    }

    if (config.input_source === 'text' && !config.input_text) {
      errors.input_text = 'Text input is required';
    }

    if (config.input_source === 'record' && (!config.record_fields || config.record_fields.length === 0)) {
      errors.record_fields = 'Select at least one field to analyze';
    }

    if (config.input_source === 'file' && !config.file_path) {
      errors.file_path = 'File path is required';
    }

    if (!config.analysis_type) {
      errors.analysis_type = 'Analysis type is required';
    }

    if (config.analysis_type === 'custom' && !config.custom_prompt) {
      errors.custom_prompt = 'Analysis instructions are required';
    }

    if (config.analysis_type === 'classification' &&
        (!config.classification_categories || config.classification_categories.length < 2)) {
      errors.classification_categories = 'At least 2 categories are required';
    }

    if (config.save_to_record && !config.target_field) {
      errors.target_field = 'Target field is required';
    }

    return errors;
  },

  defaults: {
    input_source: 'text',
    analysis_type: 'sentiment',
    entities_to_extract: ['person', 'organization', 'location'],
    summary_length: 'medium',
    output_format: 'structured',
    include_confidence: true,
    include_reasoning: false,
    save_to_record: false,
    append_results: false,
    model: 'gpt-4-turbo',
    temperature: 0.3,
    max_tokens: 1000,
    language: 'auto',
    preprocessing: ['clean'],
    chunk_size: 0,
    cache_results: true,
    cache_duration: 24,
    fallback_on_error: true,
    combine_sources: true
  },

  dependencies: {
    pipelines: true,
    fields: true
  },

  features: {
    supportsExpressions: true,
    supportsVariables: true,
    supportsTesting: true,
    supportsTemplates: true
  }
};