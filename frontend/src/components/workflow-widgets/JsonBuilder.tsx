'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Plus, Trash2, Code, Eye, AlertCircle, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface JsonBuilderProps {
  value: any;
  onChange: (value: any) => void;
  placeholder?: string;
  schema?: any; // JSON Schema for validation
  disabled?: boolean;
  rows?: number;
  templates?: Array<{
    label: string;
    value: any;
    description?: string;
  }>;
}

interface JsonField {
  key: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  value: any;
  required?: boolean;
}

type ViewMode = 'visual' | 'code' | 'preview';

export function JsonBuilder({
  value,
  onChange,
  placeholder = '{}',
  schema,
  disabled = false,
  rows = 10,
  templates = []
}: JsonBuilderProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('visual');
  const [fields, setFields] = useState<JsonField[]>([]);
  const [jsonString, setJsonString] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Common webhook payload templates
  const defaultTemplates = templates.length > 0 ? templates : [
    {
      label: 'Simple Notification',
      value: { message: 'Workflow triggered', status: 'success' },
      description: 'Basic success response'
    },
    {
      label: 'Webhook Response',
      value: { success: true, message: 'Webhook received', timestamp: '{{now}}' },
      description: 'Standard webhook acknowledgment'
    },
    {
      label: 'Form Validation',
      value: {
        type: 'object',
        required: ['email', 'name'],
        properties: {
          email: { type: 'string', format: 'email' },
          name: { type: 'string', minLength: 2 }
        }
      },
      description: 'Email and name validation schema'
    },
    {
      label: 'Order Validation',
      value: {
        type: 'object',
        required: ['orderId', 'amount'],
        properties: {
          orderId: { type: 'string' },
          amount: { type: 'number', minimum: 0 },
          items: { type: 'array', minItems: 1 }
        }
      },
      description: 'E-commerce order validation'
    }
  ];

  // Parse value to fields on mount and when value changes
  useEffect(() => {
    if (value && typeof value === 'object') {
      const parsedFields = parseObjectToFields(value);
      setFields(parsedFields);
      setJsonString(JSON.stringify(value, null, 2));
    } else if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);
        const parsedFields = parseObjectToFields(parsed);
        setFields(parsedFields);
        setJsonString(value);
      } catch {
        setJsonString(value || placeholder);
      }
    }
  }, [value]);

  const parseObjectToFields = (obj: any): JsonField[] => {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return [];

    return Object.entries(obj).map(([key, val]) => ({
      key,
      type: getValueType(val),
      value: val,
      required: schema?.required?.includes(key)
    }));
  };

  const getValueType = (val: any): JsonField['type'] => {
    if (val === null || val === undefined) return 'string';
    if (typeof val === 'boolean') return 'boolean';
    if (typeof val === 'number') return 'number';
    if (Array.isArray(val)) return 'array';
    if (typeof val === 'object') return 'object';
    return 'string';
  };

  const fieldsToObject = (): any => {
    const obj: any = {};
    fields.forEach(field => {
      if (field.key) {
        obj[field.key] = convertValue(field.value, field.type);
      }
    });
    return obj;
  };

  const convertValue = (value: any, type: JsonField['type']): any => {
    switch (type) {
      case 'number':
        return Number(value) || 0;
      case 'boolean':
        return Boolean(value);
      case 'array':
        return Array.isArray(value) ? value : [];
      case 'object':
        return typeof value === 'object' ? value : {};
      default:
        return String(value || '');
    }
  };

  const addField = () => {
    setFields([...fields, { key: '', type: 'string', value: '' }]);
  };

  const removeField = (index: number) => {
    const newFields = fields.filter((_, i) => i !== index);
    setFields(newFields);
    updateJson(newFields);
  };

  const updateField = (index: number, updates: Partial<JsonField>) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], ...updates };
    setFields(newFields);
    updateJson(newFields);
  };

  const updateJson = (updatedFields: JsonField[]) => {
    const obj = {};
    updatedFields.forEach(field => {
      if (field.key) {
        obj[field.key] = convertValue(field.value, field.type);
      }
    });
    onChange(obj);
    setJsonString(JSON.stringify(obj, null, 2));
    setError(null);
  };

  const handleJsonStringChange = (str: string) => {
    setJsonString(str);
    try {
      const parsed = JSON.parse(str);
      onChange(parsed);
      setFields(parseObjectToFields(parsed));
      setError(null);
    } catch (e) {
      setError('Invalid JSON format');
    }
  };

  const applyTemplate = (template: any) => {
    onChange(template.value);
    setFields(parseObjectToFields(template.value));
    setJsonString(JSON.stringify(template.value, null, 2));
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderFieldInput = (field: JsonField, index: number) => {
    switch (field.type) {
      case 'boolean':
        return (
          <Switch
            checked={field.value}
            onCheckedChange={(checked) => updateField(index, { value: checked })}
            disabled={disabled}
          />
        );
      case 'number':
        return (
          <Input
            type="number"
            value={field.value}
            onChange={(e) => updateField(index, { value: e.target.valueAsNumber })}
            disabled={disabled}
            className="flex-1"
          />
        );
      case 'array':
      case 'object':
        return (
          <Textarea
            value={JSON.stringify(field.value, null, 2)}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                updateField(index, { value: parsed });
              } catch {
                // Keep as string if invalid
              }
            }}
            disabled={disabled}
            rows={3}
            className="flex-1 font-mono text-xs"
          />
        );
      default:
        return (
          <Input
            value={field.value}
            onChange={(e) => updateField(index, { value: e.target.value })}
            disabled={disabled}
            className="flex-1"
          />
        );
    }
  };

  return (
    <div className="space-y-4">
      <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as ViewMode)}>
        <div className="flex items-center justify-between mb-2">
          <TabsList>
            <TabsTrigger value="visual">
              <Eye className="h-4 w-4 mr-2" />
              Visual
            </TabsTrigger>
            <TabsTrigger value="code">
              <Code className="h-4 w-4 mr-2" />
              Code
            </TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>

          {viewMode === 'code' && (
            <Button
              size="sm"
              variant="outline"
              onClick={copyToClipboard}
            >
              {copied ? (
                <Check className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>

        <TabsContent value="visual" className="space-y-4">
          {/* Templates */}
          {defaultTemplates.length > 0 && (
            <div className="space-y-2">
              <Label>Quick Templates</Label>
              <div className="grid grid-cols-2 gap-2">
                {defaultTemplates.map((template, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    className="justify-start h-auto py-2"
                    onClick={() => applyTemplate(template)}
                    disabled={disabled}
                  >
                    <div className="text-left">
                      <div className="font-medium text-xs">{template.label}</div>
                      {template.description && (
                        <div className="text-xs text-muted-foreground">{template.description}</div>
                      )}
                    </div>
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Fields */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Fields</Label>
              <Button
                size="sm"
                variant="outline"
                onClick={addField}
                disabled={disabled}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Field
              </Button>
            </div>

            {fields.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-4 border-2 border-dashed rounded-lg">
                No fields yet. Click "Add Field" to start building your JSON.
              </div>
            ) : (
              <div className="space-y-2">
                {fields.map((field, index) => (
                  <div key={index} className="flex items-start gap-2 p-3 bg-muted rounded-lg">
                    <div className="flex-1 space-y-2">
                      <div className="flex gap-2">
                        <Input
                          placeholder="Field name"
                          value={field.key}
                          onChange={(e) => updateField(index, { key: e.target.value })}
                          disabled={disabled}
                          className="flex-1"
                        />
                        <Select
                          value={field.type}
                          onValueChange={(v) => updateField(index, { type: v as JsonField['type'] })}
                          disabled={disabled}
                        >
                          <SelectTrigger className="w-32">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="string">Text</SelectItem>
                            <SelectItem value="number">Number</SelectItem>
                            <SelectItem value="boolean">Yes/No</SelectItem>
                            <SelectItem value="array">List</SelectItem>
                            <SelectItem value="object">Object</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      {renderFieldInput(field, index)}
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeField(index)}
                      disabled={disabled}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="code" className="space-y-2">
          <Textarea
            value={jsonString}
            onChange={(e) => handleJsonStringChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            rows={rows}
            className={cn(
              "font-mono text-sm",
              error && "border-destructive focus:ring-destructive"
            )}
          />
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </TabsContent>

        <TabsContent value="preview">
          <div className="p-4 bg-muted rounded-lg">
            <pre className="text-sm overflow-x-auto">
              {JSON.stringify(fieldsToObject(), null, 2)}
            </pre>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}