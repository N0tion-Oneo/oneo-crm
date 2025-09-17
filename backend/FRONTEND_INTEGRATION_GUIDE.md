# Frontend Integration Guide for Workflow Node Schemas

## Quick Start

This guide explains how to integrate the backend workflow node schemas API into the frontend application.

## Step 1: Remove Old Frontend Configs

The frontend currently has 42 config files that should be replaced:

```bash
# Old structure (TO BE REMOVED)
frontend/src/app/(dashboard)/workflows/components/node-configs/
├── ai/
│   ├── AIAnalysisNodeConfig.ts
│   ├── AIPromptNodeConfig.ts
│   └── ...
├── communication/
│   ├── EmailNodeConfig.ts
│   ├── WhatsAppNodeConfig.ts
│   └── ...
└── ...
```

## Step 2: Create Schema Service

Create a new service to fetch and cache schemas:

```typescript
// frontend/src/services/workflowSchemas.ts

interface NodeSchema {
  node_type: string;
  display_name: string;
  description: string;
  supports_replay: boolean;
  supports_checkpoints: boolean;
  config_schema: JSONSchema;
}

interface JSONSchema {
  type: string;
  required?: string[];
  properties: Record<string, any>;
}

class WorkflowSchemaService {
  private schemas: Record<string, NodeSchema> | null = null;
  private schemaPromise: Promise<Record<string, NodeSchema>> | null = null;

  async getSchemas(): Promise<Record<string, NodeSchema>> {
    // Return cached schemas if available
    if (this.schemas) {
      return this.schemas;
    }

    // Return existing promise if fetch is in progress
    if (this.schemaPromise) {
      return this.schemaPromise;
    }

    // Fetch schemas from API
    this.schemaPromise = this.fetchSchemas();
    this.schemas = await this.schemaPromise;
    this.schemaPromise = null;

    return this.schemas;
  }

  async getSchema(nodeType: string): Promise<NodeSchema | null> {
    const schemas = await this.getSchemas();
    return schemas[nodeType] || null;
  }

  private async fetchSchemas(): Promise<Record<string, NodeSchema>> {
    const response = await fetch('/api/v1/workflows/node-schemas/', {
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch schemas: ${response.statusText}`);
    }

    return response.json();
  }

  clearCache(): void {
    this.schemas = null;
    this.schemaPromise = null;
  }
}

export const workflowSchemaService = new WorkflowSchemaService();
```

## Step 3: Create Dynamic Form Generator

Replace static config components with a dynamic form generator:

```tsx
// frontend/src/components/workflow/DynamicNodeConfig.tsx

import React, { useEffect, useState } from 'react';
import { workflowSchemaService } from '@/services/workflowSchemas';
import { FormField } from './FormField';

interface DynamicNodeConfigProps {
  nodeType: string;
  initialConfig?: Record<string, any>;
  onChange: (config: Record<string, any>) => void;
}

export function DynamicNodeConfig({
  nodeType,
  initialConfig = {},
  onChange
}: DynamicNodeConfigProps) {
  const [schema, setSchema] = useState<NodeSchema | null>(null);
  const [config, setConfig] = useState(initialConfig);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSchema();
  }, [nodeType]);

  const loadSchema = async () => {
    try {
      setLoading(true);
      const nodeSchema = await workflowSchemaService.getSchema(nodeType);
      setSchema(nodeSchema);
    } catch (error) {
      console.error('Failed to load schema:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldName: string, value: any) => {
    const newConfig = { ...config, [fieldName]: value };
    setConfig(newConfig);

    // Validate field
    if (schema) {
      const fieldSchema = schema.config_schema.properties[fieldName];
      const error = validateField(fieldName, value, fieldSchema);
      setErrors({ ...errors, [fieldName]: error });
    }

    onChange(newConfig);
  };

  const validateField = (name: string, value: any, fieldSchema: any): string => {
    // Required field validation
    if (schema?.config_schema.required?.includes(name) && !value) {
      return 'This field is required';
    }

    // Type-specific validation
    switch (fieldSchema.type) {
      case 'string':
        if (fieldSchema.minLength && value.length < fieldSchema.minLength) {
          return `Minimum length is ${fieldSchema.minLength}`;
        }
        if (fieldSchema.maxLength && value.length > fieldSchema.maxLength) {
          return `Maximum length is ${fieldSchema.maxLength}`;
        }
        if (fieldSchema.pattern && !new RegExp(fieldSchema.pattern).test(value)) {
          return 'Invalid format';
        }
        break;

      case 'number':
      case 'integer':
        if (fieldSchema.minimum !== undefined && value < fieldSchema.minimum) {
          return `Minimum value is ${fieldSchema.minimum}`;
        }
        if (fieldSchema.maximum !== undefined && value > fieldSchema.maximum) {
          return `Maximum value is ${fieldSchema.maximum}`;
        }
        break;
    }

    return '';
  };

  if (loading) {
    return <div>Loading configuration...</div>;
  }

  if (!schema) {
    return <div>No configuration available for {nodeType}</div>;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{schema.display_name}</h3>
      <p className="text-sm text-gray-600">{schema.description}</p>

      {Object.entries(schema.config_schema.properties).map(([key, fieldSchema]) => {
        const isVisible = shouldShowField(fieldSchema, config);
        if (!isVisible) return null;

        return (
          <FormField
            key={key}
            name={key}
            schema={fieldSchema}
            value={config[key]}
            error={errors[key]}
            required={schema.config_schema.required?.includes(key)}
            onChange={(value) => handleFieldChange(key, value)}
          />
        );
      })}
    </div>
  );
}

function shouldShowField(fieldSchema: any, config: Record<string, any>): boolean {
  const showWhen = fieldSchema.ui_hints?.show_when;
  if (!showWhen) return true;

  for (const [key, value] of Object.entries(showWhen)) {
    if (config[key] !== value) {
      return false;
    }
  }

  return true;
}
```

## Step 4: Create Field Components

Map schema types to React components:

```tsx
// frontend/src/components/workflow/FormField.tsx

import React from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { JsonEditor } from '@/components/ui/json-editor';
import { PipelineSelect } from '@/components/selects/PipelineSelect';
import { UserSelect } from '@/components/selects/UserSelect';

interface FormFieldProps {
  name: string;
  schema: any;
  value: any;
  error?: string;
  required?: boolean;
  onChange: (value: any) => void;
}

export function FormField({
  name,
  schema,
  value,
  error,
  required,
  onChange
}: FormFieldProps) {
  const widget = schema.ui_hints?.widget || getDefaultWidget(schema.type);
  const label = schema.description || name;
  const placeholder = schema.ui_hints?.placeholder;
  const helpText = schema.ui_hints?.help_text;

  const renderField = () => {
    switch (widget) {
      case 'textarea':
        return (
          <Textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            rows={schema.ui_hints?.rows || 4}
          />
        );

      case 'select':
        return (
          <Select
            value={value}
            onChange={onChange}
            options={schema.enum?.map(v => ({ label: v, value: v }))}
          />
        );

      case 'checkbox':
        return (
          <Checkbox
            checked={value || false}
            onChange={onChange}
          />
        );

      case 'json_editor':
        return (
          <JsonEditor
            value={value || {}}
            onChange={onChange}
            rows={schema.ui_hints?.rows || 6}
          />
        );

      case 'pipeline_select':
        return (
          <PipelineSelect
            value={value}
            onChange={onChange}
          />
        );

      case 'user_select':
        return (
          <UserSelect
            value={value}
            onChange={onChange}
            multiple={schema.type === 'array'}
          />
        );

      case 'number_input':
        return (
          <Input
            type="number"
            value={value || ''}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            placeholder={placeholder}
            min={schema.minimum}
            max={schema.maximum}
          />
        );

      default:
        return (
          <Input
            type={getInputType(schema)}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
          />
        );
    }
  };

  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>

      {renderField()}

      {helpText && (
        <p className="text-xs text-gray-500">{helpText}</p>
      )}

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}
    </div>
  );
}

function getDefaultWidget(type: string): string {
  switch (type) {
    case 'boolean': return 'checkbox';
    case 'integer':
    case 'number': return 'number_input';
    case 'object': return 'json_editor';
    case 'array': return 'multiselect';
    default: return 'text';
  }
}

function getInputType(schema: any): string {
  if (schema.format === 'email') return 'email';
  if (schema.format === 'uri') return 'url';
  if (schema.format === 'date') return 'date';
  if (schema.format === 'datetime-local') return 'datetime-local';
  if (schema.type === 'integer' || schema.type === 'number') return 'number';
  return 'text';
}
```

## Step 5: Update Node Configuration Panel

Replace the old NodeConfigurationPanel:

```tsx
// frontend/src/app/(dashboard)/workflows/components/NodeConfigurationPanel.tsx

import React from 'react';
import { DynamicNodeConfig } from '@/components/workflow/DynamicNodeConfig';

export function NodeConfigurationPanel({ node, onChange }) {
  if (!node) {
    return <div>Select a node to configure</div>;
  }

  const handleConfigChange = (config: Record<string, any>) => {
    onChange({
      ...node,
      data: {
        ...node.data,
        config
      }
    });
  };

  return (
    <div className="p-4">
      <DynamicNodeConfig
        nodeType={node.type}
        initialConfig={node.data?.config || {}}
        onChange={handleConfigChange}
      />
    </div>
  );
}
```

## Step 6: Add Schema Validation

Use ajv for client-side validation:

```bash
npm install ajv ajv-formats
```

```typescript
// frontend/src/utils/schemaValidator.ts

import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);

export function validateNodeConfig(
  schema: JSONSchema,
  config: any
): { valid: boolean; errors: any[] } {
  const validate = ajv.compile(schema);
  const valid = validate(config);

  return {
    valid: !!valid,
    errors: validate.errors || []
  };
}

export function getErrorMessages(errors: any[]): Record<string, string> {
  const messages: Record<string, string> = {};

  errors.forEach(error => {
    const field = error.instancePath.replace('/', '');

    switch (error.keyword) {
      case 'required':
        messages[error.params.missingProperty] = 'This field is required';
        break;
      case 'minLength':
        messages[field] = `Minimum length is ${error.params.limit}`;
        break;
      case 'maxLength':
        messages[field] = `Maximum length is ${error.params.limit}`;
        break;
      case 'minimum':
        messages[field] = `Minimum value is ${error.params.limit}`;
        break;
      case 'maximum':
        messages[field] = `Maximum value is ${error.params.limit}`;
        break;
      case 'pattern':
        messages[field] = 'Invalid format';
        break;
      case 'format':
        messages[field] = `Invalid ${error.params.format}`;
        break;
      default:
        messages[field] = error.message || 'Invalid value';
    }
  });

  return messages;
}
```

## Step 7: Handle Special Widget Types

Create specialized components for complex widgets:

```tsx
// frontend/src/components/workflow/widgets/ConditionalFields.tsx

export function ConditionalFields({ schema, config, onChange }) {
  const conditions = config.conditions || [];

  const addCondition = () => {
    onChange({
      ...config,
      conditions: [...conditions, { left: '', operator: '==', right: '' }]
    });
  };

  const updateCondition = (index: number, field: string, value: any) => {
    const newConditions = [...conditions];
    newConditions[index] = { ...newConditions[index], [field]: value };
    onChange({ ...config, conditions: newConditions });
  };

  const removeCondition = (index: number) => {
    onChange({
      ...config,
      conditions: conditions.filter((_, i) => i !== index)
    });
  };

  return (
    <div>
      {conditions.map((condition, index) => (
        <div key={index} className="flex gap-2 mb-2">
          <Input
            placeholder="Field path"
            value={condition.left}
            onChange={(e) => updateCondition(index, 'left', e.target.value)}
          />
          <Select
            value={condition.operator}
            onChange={(v) => updateCondition(index, 'operator', v)}
            options={[
              { label: 'Equals', value: '==' },
              { label: 'Not Equals', value: '!=' },
              { label: 'Greater Than', value: '>' },
              { label: 'Less Than', value: '<' },
              { label: 'Contains', value: 'contains' },
            ]}
          />
          <Input
            placeholder="Value"
            value={condition.right}
            onChange={(e) => updateCondition(index, 'right', e.target.value)}
          />
          <Button
            onClick={() => removeCondition(index)}
            variant="ghost"
            size="sm"
          >
            Remove
          </Button>
        </div>
      ))}
      <Button onClick={addCondition} variant="outline" size="sm">
        Add Condition
      </Button>
    </div>
  );
}
```

## Step 8: Migration Checklist

1. **Install Dependencies**
   ```bash
   npm install ajv ajv-formats
   ```

2. **Create Service Layer**
   - [ ] Create `workflowSchemas.ts` service
   - [ ] Add schema caching logic
   - [ ] Add error handling

3. **Build Form Components**
   - [ ] Create `DynamicNodeConfig.tsx`
   - [ ] Create `FormField.tsx`
   - [ ] Map all widget types

4. **Update Existing Code**
   - [ ] Replace `NodeConfigurationPanel.tsx`
   - [ ] Remove old config imports
   - [ ] Update node creation logic

5. **Add Validation**
   - [ ] Create validation utilities
   - [ ] Add real-time validation
   - [ ] Handle validation errors

6. **Test Integration**
   - [ ] Test all node types
   - [ ] Verify conditional fields
   - [ ] Check validation rules

7. **Clean Up**
   - [ ] Remove old config files
   - [ ] Remove unused imports
   - [ ] Update documentation

## Common Issues & Solutions

### Issue: Schema not loading

**Solution**: Check network tab for API errors, verify authentication token.

### Issue: Widget not rendering

**Solution**: Ensure widget type is mapped in `FormField.tsx`.

### Issue: Validation not working

**Solution**: Check schema format, ensure ajv is properly configured.

### Issue: Conditional fields not showing

**Solution**: Verify `show_when` logic in `shouldShowField()`.

## Benefits of Migration

1. **Single Source of Truth** - Backend controls all configurations
2. **Reduced Code** - Remove 42+ config files from frontend
3. **Dynamic Updates** - Schema changes reflect immediately
4. **Better Validation** - JSON Schema provides robust validation
5. **Type Safety** - TypeScript types generated from schemas
6. **Maintainability** - Easier to add new node types

## Example: Before and After

### Before (Static Config)

```typescript
// 42 separate config files like this:
export const emailNodeConfig = {
  fields: [
    {
      name: 'recipient_email',
      label: 'Recipient Email',
      type: 'email',
      required: true,
      placeholder: 'Enter email...'
    },
    // ... more fields
  ]
};
```

### After (Dynamic Schema)

```typescript
// Single dynamic component handles all node types:
<DynamicNodeConfig
  nodeType="EMAIL"
  initialConfig={node.config}
  onChange={handleChange}
/>
// Schema fetched from API, forms generated dynamically
```

## Next Steps

1. Start with a single node type (e.g., EMAIL)
2. Test the integration thoroughly
3. Gradually migrate other node types
4. Remove old config files once verified
5. Update tests to use new system

## Support

- API Documentation: `/backend/WORKFLOW_SCHEMAS_API.md`
- Backend Changes: `/backend/workflow_schema_migration_plan.md`
- Schema Definitions: `/backend/workflows/nodes/*/`