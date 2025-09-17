# Workflow Node Schemas API Documentation

## Overview

The Workflow Node Schemas API provides configuration schemas for all workflow node types. This enables the frontend to dynamically generate configuration forms based on backend-defined schemas, establishing a single source of truth for node configurations.

## API Endpoint

### Get All Node Schemas

```http
GET /api/v1/workflows/node-schemas/
```

**Authentication**: Required (JWT token)

**Response**: JSON object with all node type schemas

### Response Structure

```json
{
  "RECORD_CREATE": {
    "node_type": "RECORD_CREATE",
    "display_name": "Create Record",
    "description": "Process record creation nodes",
    "supports_replay": true,
    "supports_checkpoints": true,
    "config_schema": {
      "type": "object",
      "required": ["pipeline_id"],
      "properties": {
        "pipeline_id": {
          "type": "string",
          "description": "Target pipeline for record creation",
          "ui_hints": {
            "widget": "pipeline_select"
          }
        },
        "field_mapping": {
          "type": "object",
          "description": "Field values for the new record",
          "ui_hints": {
            "widget": "json_editor",
            "rows": 6
          }
        }
      }
    }
  },
  // ... more node types
}
```

## Schema Properties

### Core Fields

Each node schema contains:

- `node_type` - Unique identifier for the node type
- `display_name` - Human-readable name for UI display
- `description` - Brief description of the node's purpose
- `supports_replay` - Whether the node supports workflow replay
- `supports_checkpoints` - Whether the node supports checkpointing
- `config_schema` - JSON Schema defining configuration structure

### JSON Schema Format

All schemas follow JSON Schema Draft-07 specification with additional UI hints.

#### Basic Types

- `string` - Text input
- `number` - Decimal number
- `integer` - Whole number
- `boolean` - True/false
- `array` - List of items
- `object` - Complex nested object

#### Validation Rules

```json
{
  "type": "string",
  "minLength": 1,
  "maxLength": 255,
  "pattern": "^[a-z][a-z0-9_]*$",
  "format": "email"
}
```

#### UI Hints

```json
{
  "ui_hints": {
    "widget": "textarea",        // Widget type
    "rows": 4,                   // Widget-specific options
    "placeholder": "Enter...",   // Placeholder text
    "help_text": "Help text",    // Additional help
    "section": "advanced",       // UI section grouping
    "order": 1,                  // Display order
    "show_when": {               // Conditional visibility
      "other_field": true
    }
  }
}
```

## Available Widget Types

### Text Inputs
- `text` - Single line text input
- `textarea` - Multi-line text input
- `email` - Email input with validation
- `url` - URL input with validation
- `password` - Password input (masked)

### Selection
- `select` - Single selection dropdown
- `multiselect` - Multiple selection
- `radio` - Radio button group
- `checkbox` - Single checkbox

### Specialized
- `pipeline_select` - Pipeline selection dropdown
- `user_select` - User selection dropdown
- `json_editor` - JSON code editor
- `code_editor` - Code editor with syntax highlighting
- `file_upload` - File upload widget
- `date_picker` - Date selection
- `datetime_picker` - Date and time selection
- `number_input` - Number with increment/decrement
- `slider` - Range slider
- `tag_input` - Tag/chip input
- `color_picker` - Color selection

## Node Types Reference

### Data Operations

#### RECORD_CREATE
Create new records in a pipeline.

**Required Fields**:
- `pipeline_id` - Target pipeline

**Optional Fields**:
- `field_mapping` - Record field values
- `skip_validation` - Bypass validation

#### RECORD_UPDATE
Update existing records.

**Required Fields**:
- `pipeline_id` - Target pipeline
- `record_id` - Record to update

**Optional Fields**:
- `field_mapping` - Fields to update
- `update_mode` - merge/replace

#### RECORD_FIND
Find records by criteria.

**Required Fields**:
- `pipeline_id` - Target pipeline

**Optional Fields**:
- `conditions` - Search conditions
- `limit` - Maximum results
- `create_if_not_found` - Auto-create if missing

#### RECORD_DELETE
Delete records.

**Required Fields**:
- `pipeline_id` - Target pipeline
- `record_id` - Record to delete

**Optional Fields**:
- `soft_delete` - Mark as deleted vs permanent

### AI Processors

#### AI_PROMPT
Execute AI prompts with context.

**Required Fields**:
- `prompt` - AI prompt template

**Optional Fields**:
- `model` - AI model (gpt-4/gpt-3.5-turbo/claude)
- `temperature` - Creativity (0-1)
- `max_tokens` - Response length limit
- `tools` - Available AI tools
- `system_prompt` - System instructions

#### AI_ANALYSIS
Analyze content with AI.

**Required Fields**:
- `analysis_type` - Type of analysis
- `data_source` - Data to analyze

**Optional Fields**:
- `output_format` - Response format
- `extraction_fields` - Fields to extract

### Communication

#### EMAIL
Send email messages.

**Required Fields**:
- `recipient_email` - Recipient address
- `subject` - Email subject
- `content` - Email body

**Optional Fields**:
- `cc_emails` - CC recipients
- `bcc_emails` - BCC recipients
- `attachments` - File attachments
- `tracking_enabled` - Email tracking
- `is_reply` - Reply to existing thread
- `reply_to_message_id` - Thread message ID

#### WHATSAPP
Send WhatsApp messages.

**Required Fields**:
- `recipient_phone` - Phone number
- `message` - Message text

**Optional Fields**:
- `media_url` - Media attachment
- `template_name` - Message template

#### SMS
Send SMS messages.

**Required Fields**:
- `recipient_phone` - Phone number
- `message` - Message text (max 160 chars)

### Control Flow

#### CONDITION
Conditional branching.

**Required Fields**:
- `conditions` - Array of conditions

**Optional Fields**:
- `operator` - AND/OR for multiple conditions
- `default_output` - Default branch

#### FOR_EACH
Iterate over collections.

**Required Fields**:
- `items_source` - Source collection

**Optional Fields**:
- `max_iterations` - Iteration limit
- `parallel` - Process in parallel

#### WAIT_DELAY
Add delays to workflows.

**Required Fields**:
- `wait_type` - immediate/scheduled/business_hours

**Optional Fields**:
- `delay_seconds` - Delay duration
- `scheduled_time` - Specific time
- `business_hours_config` - Business hours settings

### External Integration

#### HTTP_REQUEST
Make HTTP API calls.

**Required Fields**:
- `url` - Request URL
- `method` - HTTP method

**Optional Fields**:
- `headers` - Request headers
- `body` - Request body
- `auth` - Authentication config
- `timeout` - Request timeout
- `retry` - Retry configuration

#### WEBHOOK_OUT
Send webhook notifications.

**Required Fields**:
- `webhook_url` - Webhook endpoint

**Optional Fields**:
- `payload` - Webhook payload
- `headers` - Custom headers
- `include_context` - Include workflow context
- `include_execution_metadata` - Include metadata

## Frontend Integration Guide

### 1. Fetch Schemas

```typescript
// Fetch all node schemas
const response = await fetch('/api/v1/workflows/node-schemas/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

const schemas = await response.json();
```

### 2. Generate Form from Schema

```typescript
function generateFormFields(schema: ConfigSchema) {
  const fields = [];

  for (const [key, fieldSchema] of Object.entries(schema.properties)) {
    const field = {
      name: key,
      label: fieldSchema.description,
      required: schema.required?.includes(key),
      type: fieldSchema.type,
      widget: fieldSchema.ui_hints?.widget || 'text',
      placeholder: fieldSchema.ui_hints?.placeholder,
      helpText: fieldSchema.ui_hints?.help_text,
      validation: {
        minLength: fieldSchema.minLength,
        maxLength: fieldSchema.maxLength,
        pattern: fieldSchema.pattern,
        min: fieldSchema.minimum,
        max: fieldSchema.maximum
      }
    };

    fields.push(field);
  }

  return fields;
}
```

### 3. Handle Conditional Visibility

```typescript
function shouldShowField(field: Field, formValues: any): boolean {
  const showWhen = field.ui_hints?.show_when;

  if (!showWhen) return true;

  for (const [key, value] of Object.entries(showWhen)) {
    if (formValues[key] !== value) {
      return false;
    }
  }

  return true;
}
```

### 4. Validate Against Schema

```typescript
import Ajv from 'ajv';

const ajv = new Ajv();

function validateConfig(nodeType: string, config: any): boolean {
  const schema = schemas[nodeType].config_schema;
  const validate = ajv.compile(schema);

  const valid = validate(config);

  if (!valid) {
    console.error('Validation errors:', validate.errors);
  }

  return valid;
}
```

## Example Usage

### Creating a Node Configuration

```javascript
// Get schema for EMAIL node
const emailSchema = schemas.EMAIL.config_schema;

// Create configuration based on schema
const emailConfig = {
  recipient_email: "{{contact.email}}",
  subject: "Welcome to our platform",
  content: "Hello {{contact.first_name}}, welcome!",
  tracking_enabled: true,
  attachments: []
};

// Validate configuration
if (validateConfig('EMAIL', emailConfig)) {
  // Save node configuration
  saveNodeConfig(emailConfig);
}
```

### Dynamic Form Generation

```tsx
function NodeConfigForm({ nodeType, onSave }) {
  const [config, setConfig] = useState({});
  const schema = schemas[nodeType].config_schema;

  const handleSubmit = (values) => {
    if (validateConfig(nodeType, values)) {
      onSave(values);
    }
  };

  return (
    <Form schema={schema} onSubmit={handleSubmit}>
      {Object.entries(schema.properties).map(([key, field]) => (
        <FormField
          key={key}
          name={key}
          schema={field}
          required={schema.required?.includes(key)}
          onChange={(value) => setConfig({...config, [key]: value})}
        />
      ))}
    </Form>
  );
}
```

## Migration from Frontend Configs

### Before (Frontend Config)

```typescript
// frontend/workflow-configs/email.config.ts
export const emailConfig = {
  fields: [
    {
      name: 'recipient_email',
      type: 'email',
      required: true,
      validation: {...}
    }
  ]
};
```

### After (Backend Schema)

```python
# backend/workflows/nodes/communication/email.py
class EmailProcessor(AsyncNodeProcessor):
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["recipient_email"],
        "properties": {
            "recipient_email": {
                "type": "string",
                "format": "email",
                "description": "Recipient email address"
            }
        }
    }
```

Frontend now fetches schema from API instead of maintaining local configs.

## Benefits

1. **Single Source of Truth** - Backend defines all configuration contracts
2. **Type Safety** - JSON Schema provides strong typing
3. **Auto-validation** - Built-in validation rules
4. **Dynamic UI** - Forms generated from schemas
5. **Multi-client Support** - Mobile, CLI can use same schemas
6. **Version Control** - Schema changes tracked in backend
7. **Documentation** - Self-documenting configurations

## Troubleshooting

### Schema Not Found

If a node type doesn't return a schema:
1. Check that the processor has `CONFIG_SCHEMA` defined
2. Verify the processor is registered in `get_all_node_processors()`
3. Check for import errors in the processor module

### Validation Errors

If validation fails:
1. Check required fields are provided
2. Verify field types match schema
3. Check field formats (email, URL, etc.)
4. Ensure conditional requirements are met

### UI Rendering Issues

If UI widgets don't render correctly:
1. Check `ui_hints.widget` is a supported type
2. Verify widget-specific options are provided
3. Check conditional visibility logic
4. Ensure placeholder and help text are escaped

## Support

For issues or questions:
- Check the migration plan: `/backend/workflow_schema_migration_plan.md`
- Review processor implementations in `/backend/workflows/nodes/`
- Contact the backend team for schema updates