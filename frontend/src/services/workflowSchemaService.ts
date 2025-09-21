/**
 * Service to fetch workflow node schemas from backend and transform them
 * to work with the existing UnifiedConfigRenderer
 */

import React from 'react';
import { WorkflowNodeType } from '@/app/(dashboard)/workflows/types';
import { UnifiedNodeConfig, ConfigSection, ConfigField, FieldType } from '@/app/(dashboard)/workflows/components/node-configs/unified/types';
import { api } from '@/lib/api';

interface BackendSchema {
  node_type: string;
  display_name: string;
  description: string;
  supports_replay: boolean;
  supports_checkpoints: boolean;
  config_schema: {
    type: string;
    required?: string[];
    properties: Record<string, any>;
  } | null;
}

interface BackendSchemas {
  [key: string]: BackendSchema;
}

class WorkflowSchemaService {
  private schemas: BackendSchemas | null = null;
  private schemaPromise: Promise<BackendSchemas> | null = null;
  private transformedConfigs: Map<WorkflowNodeType, UnifiedNodeConfig> = new Map();

  /**
   * Fetch all schemas from backend
   */
  async fetchSchemas(): Promise<BackendSchemas> {
    if (this.schemas) {
      return this.schemas;
    }

    if (this.schemaPromise) {
      return this.schemaPromise;
    }

    this.schemaPromise = api.get('/api/v1/workflows/node_schemas/')
      .then(response => {
        const data = response.data;
        this.schemas = data;
        this.schemaPromise = null;
        return data;
      })
      .catch(err => {
        this.schemaPromise = null;
        console.error('Failed to fetch workflow schemas:', err);
        throw new Error(err.response?.data?.detail || err.message || 'Failed to fetch schemas');
      });

    return this.schemaPromise;
  }

  /**
   * Get UnifiedNodeConfig for a specific node type
   */
  async getNodeConfig(nodeType: WorkflowNodeType): Promise<UnifiedNodeConfig | null> {
    // Check cache first
    if (this.transformedConfigs.has(nodeType)) {
      return this.transformedConfigs.get(nodeType)!;
    }

    const schemas = await this.fetchSchemas();

    // Map frontend node type to backend node type
    const backendNodeType = this.mapNodeType(nodeType);
    const schema = schemas[backendNodeType];

    if (!schema || !schema.config_schema) {
      console.warn(`No schema found for node type: ${nodeType} (backend: ${backendNodeType})`);
      return null;
    }

    // Transform backend schema to UnifiedNodeConfig
    const config = this.transformSchema(nodeType, schema);
    this.transformedConfigs.set(nodeType, config);

    return config;
  }

  /**
   * Transform backend schema directly (public method for external use)
   */
  transformBackendSchema(schema: BackendSchema, nodeType: string): UnifiedNodeConfig | null {
    if (!schema.config_schema) {
      return null;
    }
    return this.transformSchema(nodeType as WorkflowNodeType, schema);
  }

  /**
   * Map frontend WorkflowNodeType to backend node type string
   * Backend now uses all lowercase with underscores
   */
  private mapNodeType(nodeType: WorkflowNodeType): string {
    // Since both frontend and backend now use the same lowercase convention,
    // we can just return the nodeType directly in most cases
    return nodeType;
  }

  /**
   * Transform backend schema to UnifiedNodeConfig format
   */
  private transformSchema(nodeType: WorkflowNodeType, schema: BackendSchema): UnifiedNodeConfig {
    const configSchema = schema.config_schema!;
    const properties = configSchema.properties || {};
    const required = configSchema.required || [];

    // Group fields by section based on ui_hints
    const sections: ConfigSection[] = [];
    const mainFields: ConfigField[] = [];
    const advancedFields: ConfigField[] = [];

    // Transform each property to a ConfigField
    Object.entries(properties).forEach(([key, prop]) => {
      const field = this.transformField(key, prop, required.includes(key));

      // Sort into sections based on ui_hints
      if (prop.ui_hints?.section === 'advanced') {
        advancedFields.push(field);
      } else {
        mainFields.push(field);
      }
    });

    // Create main section if there are fields
    if (mainFields.length > 0) {
      sections.push({
        id: 'main',
        label: 'Configuration',
        fields: mainFields
      });
    }

    // Create advanced section if there are fields
    if (advancedFields.length > 0) {
      sections.push({
        id: 'advanced',
        label: 'Advanced Settings',
        collapsed: true,
        advanced: true,
        fields: advancedFields
      });
    }

    // If no sections were created, create a default one
    if (sections.length === 0) {
      sections.push({
        id: 'main',
        label: 'Configuration',
        fields: []
      });
    }

    // Add custom component for specific node types
    let customComponent = undefined;
    if (nodeType === 'trigger_date_reached' || nodeType === WorkflowNodeType.TRIGGER_DATE_REACHED) {
      // Lazy load the custom component to avoid circular dependencies
      customComponent = React.lazy(() =>
        import('@/app/(dashboard)/workflows/components/node-configs/triggers/DateReachedConfig')
          .then(module => ({ default: module.DateReachedConfig }))
      );
    }
    // RecordUpdatedConfig custom component removed - backend fields handle everything

    // Use defaults from backend - backend is single source of truth
    // First, get any defaults from the backend default_config
    let defaults: Record<string, any> = schema.default_config || {};

    // Then merge in any field-level defaults from the schema
    Object.entries(properties).forEach(([key, prop]) => {
      if (prop.default !== undefined && !(key in defaults)) {
        defaults[key] = prop.default;
      }
    });

    return {
      type: nodeType,
      label: schema.display_name,
      description: schema.description,
      category: this.getNodeCategory(nodeType),
      sections,
      customComponent,
      defaults,
      features: {
        supportsExpressions: true,
        supportsVariables: true,
        supportsTesting: true,
        supportsTemplates: true
      },
      validate: (config: any) => {
        // Basic required field validation
        const errors: Record<string, string> = {};

        // Special validation for date_reached trigger
        if (nodeType === 'trigger_date_reached' || nodeType === WorkflowNodeType.TRIGGER_DATE_REACHED) {
          // Must have either date_field OR target_date
          if (!config.date_field && !config.target_date) {
            errors.date_field = 'Either date field or target date is required';
            errors.target_date = 'Either target date or date field is required';
          }
          // If using dynamic mode, pipeline is required
          if (config.date_field && !config.pipeline_id) {
            errors.pipeline_id = 'Pipeline is required when using date field';
          }
        } else {
          // Standard required field validation
          required.forEach(field => {
            if (!config[field]) {
              errors[field] = `${properties[field]?.description || field} is required`;
            }
          });
        }

        return errors;
      }
    };
  }

  /**
   * Transform a backend property to a ConfigField
   */
  private transformField(key: string, prop: any, required: boolean): ConfigField {
    const uiHints = prop.ui_hints || {};

    // Map backend widget to frontend field type
    const fieldType = this.mapFieldType(prop.type, prop.format, uiHints.widget);

    const field: ConfigField = {
      key,
      label: prop.description || key,
      type: fieldType,
      required,
      placeholder: uiHints.placeholder,
      helpText: uiHints.help_text,
      rows: uiHints.rows,
      allowExpressions: true, // Always allow expressions for workflow fields
      uiHints: uiHints, // Pass through all UI hints
      widget: uiHints.widget, // Explicit widget type
    };

    // Handle conditional visibility
    if (uiHints.show_when) {
      field.showWhen = (config: any) => {
        // Simple implementation - can be enhanced
        for (const [k, v] of Object.entries(uiHints.show_when)) {
          if (config[k] !== v) return false;
        }
        return true;
      };
    }

    // Handle select/multiselect options
    if (prop.enum) {
      field.options = prop.enum.map((value: any) => ({
        label: String(value),
        value
      }));
      // Also add to uiHints so SelectWidget can access them
      field.uiHints.options = field.options;
    } else if (uiHints.options) {
      // Handle options provided through ui_hints
      field.options = uiHints.options;
      // Ensure uiHints has the options for the widget
      field.uiHints.options = uiHints.options;
    }

    // Handle special widgets
    if (uiHints.widget === 'pipeline_select' || uiHints.widget === 'pipeline_multiselect') {
      field.type = 'pipeline';
      field.optionsSource = 'pipelines';
      field.multiple = uiHints.widget === 'pipeline_multiselect';
    } else if (uiHints.widget === 'user_select' || uiHints.widget === 'user_multiselect') {
      field.type = 'user';
      field.optionsSource = 'users';
      field.multiple = uiHints.widget === 'user_multiselect';
    } else if (uiHints.widget === 'field_select' || uiHints.widget === 'field_multiselect') {
      field.type = 'field';
      field.optionsSource = 'pipelineFields';
      field.multiple = uiHints.widget === 'field_multiselect';
    } else if (uiHints.widget === 'workflow_select') {
      field.type = 'workflow';
      field.optionsSource = 'workflows';
    } else if (uiHints.widget === 'dynamic_select') {
      // Dynamic select that fetches options from an API endpoint
      field.type = 'select';
      field.fetchEndpoint = uiHints.fetch_endpoint;
      field.dependsOn = uiHints.depends_on;
      field.valueField = uiHints.value_field;
      field.labelField = uiHints.label_field;
      field.showFieldCount = uiHints.show_field_count;
      field.groupBy = uiHints.group_by;
    } else if (uiHints.widget === 'readonly_text') {
      field.type = 'text';
      field.readonly = true;
      field.computedFrom = uiHints.computed_from;
    } else if (uiHints.widget === 'json_editor') {
      field.type = 'json';
    } else if (uiHints.widget === 'code_editor') {
      field.type = 'code';
      field.richField = {
        type: 'code',
        language: uiHints.language || 'javascript'
      };
    }

    // Handle number constraints
    if (prop.type === 'number' || prop.type === 'integer') {
      field.min = prop.minimum;
      field.max = prop.maximum;
      field.step = prop.type === 'integer' ? 1 : undefined;
    }

    // Handle string constraints
    if (prop.type === 'string') {
      if (prop.minLength || prop.maxLength) {
        field.validation = (value: any) => {
          if (prop.minLength && value.length < prop.minLength) {
            return `Minimum length is ${prop.minLength}`;
          }
          if (prop.maxLength && value.length > prop.maxLength) {
            return `Maximum length is ${prop.maxLength}`;
          }
          return null;
        };
      }
    }

    // Set default value
    if (prop.default !== undefined) {
      field.defaultValue = prop.default;
    }

    return field;
  }

  /**
   * Map backend type/format/widget to frontend FieldType
   */
  private mapFieldType(type: string, format?: string, widget?: string): FieldType {
    // Check widget first (most specific)
    if (widget) {
      const widgetMap: Record<string, FieldType> = {
        'textarea': 'textarea',
        'select': 'select',
        'multiselect': 'multiselect',
        'radio': 'radio',
        'checkbox': 'checkbox',
        'json_editor': 'json',
        'json_builder': 'json', // User-friendly JSON builder
        'code_editor': 'code',
        'html_editor': 'html',
        'markdown_editor': 'markdown',
        'pipeline_select': 'pipeline',
        'user_select': 'user',
        'user_multiselect': 'user',
        'workflow_select': 'workflow',
        'field_select': 'field',
        'date_picker': 'date',
        'datetime_picker': 'datetime',
        'time_picker': 'time',
        'color_picker': 'color',
        'slider': 'slider',
        'tag_input': 'tags', // Enhanced tag input
        'schedule_builder': 'text', // Schedule builder returns cron string
        'condition_builder': 'conditions', // Condition builder for complex logic
        'file_upload': 'file',
        'stage_options_multiselect': 'stage_options_multiselect',
        'stage_tracking_toggle': 'stage_tracking_toggle',
      };
      if (widgetMap[widget]) {
        return widgetMap[widget];
      }
    }

    // Check format (medium specific)
    if (format) {
      const formatMap: Record<string, FieldType> = {
        'email': 'text',
        'uri': 'text',
        'date': 'date',
        'date-time': 'datetime',
        'time': 'time',
      };
      if (formatMap[format]) {
        return formatMap[format];
      }
    }

    // Map by type (least specific)
    const typeMap: Record<string, FieldType> = {
      'string': 'text',
      'number': 'number',
      'integer': 'number',
      'boolean': 'boolean',
      'array': 'array',
      'object': 'json',
    };

    return typeMap[type] || 'text';
  }

  /**
   * Get node category based on node type
   */
  private getNodeCategory(nodeType: WorkflowNodeType): UnifiedNodeConfig['category'] {
    if (nodeType.startsWith('TRIGGER_')) return 'trigger';
    if (nodeType.includes('AI_')) return 'integration';
    if (nodeType.includes('RECORD_') || nodeType.includes('MERGE_')) return 'data';
    if (nodeType.includes('SEND_') || nodeType.includes('EMAIL') || nodeType.includes('SMS')) return 'communication';
    if (['CONDITION', 'FOR_EACH', 'WAIT_', 'WORKFLOW_LOOP'].some(t => nodeType.includes(t))) return 'control';
    return 'action';
  }

  /**
   * Clear cached schemas and configs
   */
  clearCache(): void {
    this.schemas = null;
    this.schemaPromise = null;
    this.transformedConfigs.clear();
  }
}

// Export singleton instance
export const workflowSchemaService = new WorkflowSchemaService();