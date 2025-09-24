/**
 * NodeInputStructure
 * Displays input data structure from previous nodes
 * Matches the exact UI of NodeOutputTabV2 with 3 sections
 */

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Code2,
  Database,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Copy,
  ChevronRight,
  ChevronDown,
  Loader2,
  User
} from 'lucide-react';
import { toast } from 'sonner';

interface InputField {
  key: string;
  type: string;
  value: any;
  description: string;
  depth: number;
  nodeId: string;
}

interface NodeInputStructureProps {
  sources: any[];
  testData?: any;
  isTriggerNode?: boolean;
  testDataList?: any[];
  testDataType?: string;
  selectedTestData?: any;
  onTestDataChange?: (data: any) => void;
  useRealData?: boolean;
  onUseRealDataChange?: (value: boolean) => void;
  loadingTestData?: boolean;
}

export function NodeInputStructure({
  sources,
  testData,
  isTriggerNode,
  testDataList = [],
  testDataType = '',
  selectedTestData,
  onTestDataChange,
  useRealData = false,
  onUseRealDataChange,
  loadingTestData = false
}: NodeInputStructureProps) {
  const [inputFields, setInputFields] = useState<InputField[]>([]);
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [sampleInput, setSampleInput] = useState<any>(null);

  // Extract fields from sources or test record
  useEffect(() => {
    setLoading(true);
    const fields: InputField[] = [];
    let inputData: any = null;

    if (isTriggerNode && testData) {
      // For trigger nodes, show test data
      const extracted = extractInputFields(testData, 'trigger', '', 0);
      fields.push(...extracted);
      inputData = testData;
      // Auto-expand first level
      setExpandedFields(new Set(extracted.filter(f => f.depth === 0 && f.type === 'object').map(f => f.key)));
    } else if (sources && sources.length > 0) {
      // For other nodes, show data from previous nodes
      const combinedData: any = {};
      sources.forEach(source => {
        if (source.data && typeof source.data === 'object') {
          // Handle data object format (preferred)
          const extracted = extractInputFields(source.data, source.nodeId, '', 0);
          fields.push(...extracted);
          combinedData[source.nodeId] = source.data;
        } else if (source.outputs && Array.isArray(source.outputs)) {
          // Handle outputs as array of field paths (fallback)
          source.outputs.forEach((outputPath: string) => {
            const pathParts = outputPath.split('.');
            const fieldName = pathParts[pathParts.length - 1];

            // Determine type based on field name
            let fieldType = 'string';
            if (fieldName === 'success' || fieldName === 'condition_met') {
              fieldType = 'boolean';
            } else if (fieldName === 'record' || fieldName === 'data') {
              fieldType = 'object';
            } else if (fieldName === 'id' || fieldName === 'tokens') {
              fieldType = 'number';
            } else if (fieldName === 'timestamp' || fieldName === 'sent_at') {
              fieldType = 'datetime';
            }

            fields.push({
              key: outputPath,
              type: fieldType,
              value: fieldType === 'object' ? {} : fieldType === 'boolean' ? true : null,
              description: getFieldDescription(outputPath, fieldType, null),
              depth: pathParts.length - 1,
              nodeId: source.nodeId
            });
          });

          // Create sample structure for display
          const nodeData: any = {};
          source.outputs.forEach((outputPath: string) => {
            const pathParts = outputPath.split('.');
            let current = nodeData;

            pathParts.forEach((part: string, index: number) => {
              if (index === pathParts.length - 1) {
                // Last part - set a sample value
                if (part === 'success' || part === 'condition_met') {
                  current[part] = true;
                } else if (part === 'id') {
                  current[part] = 123;
                } else if (part === 'timestamp' || part === 'sent_at') {
                  current[part] = new Date().toISOString();
                } else if (part === 'data' || part === 'record') {
                  current[part] = { /* sample data */ };
                } else {
                  current[part] = `sample_${part}`;
                }
              } else {
                // Intermediate part - create object if not exists
                if (!current[part]) {
                  current[part] = {};
                }
                current = current[part];
              }
            });
          });

          combinedData[source.nodeId] = nodeData;
        }
      });
      inputData = combinedData;
      // Auto-expand first level objects
      setExpandedFields(new Set(fields.filter(f => f.depth === 0 && f.type === 'object').map(f => f.key)));
    }

    setInputFields(fields);
    setSampleInput(inputData);
    setLoading(false);
  }, [sources, testData, isTriggerNode]);

  // Recursively extract fields from data
  const extractInputFields = (
    data: any,
    nodeId: string,
    prefix: string = '',
    depth: number = 0
  ): InputField[] => {
    const fields: InputField[] = [];

    if (!data || typeof data !== 'object' || depth > 3) {
      return fields;
    }

    Object.entries(data).forEach(([key, value]) => {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      const type = getDataType(value);

      fields.push({
        key: fullKey,
        type,
        value,
        description: getFieldDescription(fullKey, type, value),
        depth,
        nodeId
      });

      // Recursively add nested fields
      if (type === 'object' && value !== null && !isDate(value)) {
        fields.push(...extractInputFields(value, nodeId, fullKey, depth + 1));
      } else if (type === 'array' && Array.isArray(value) && value.length > 0) {
        if (typeof value[0] === 'object' && value[0] !== null) {
          fields.push(...extractInputFields(value[0], nodeId, `${fullKey}[0]`, depth + 1));
        }
      }
    });

    return fields;
  };

  // Helper to get test data display name based on type
  const getTestDataDisplayName = (data: any, dataType: string): string => {
    if (!data) return 'Test Data';

    // Handle different data types
    if (dataType === 'email' || dataType === 'email_message') {
      if (data.subject) return data.subject;
      if (data.from) return `Email from ${data.from}`;
      if (data.sender) return `Email from ${data.sender}`;
      return 'Email Message';
    }

    if (dataType === 'linkedin_message' || dataType === 'whatsapp_message') {
      const platform = dataType.includes('linkedin') ? 'LinkedIn' : 'WhatsApp';
      if (data.from) return `${platform} from ${data.from}`;
      if (data.sender) return `${platform} from ${data.sender}`;
      if (data.message) return data.message.substring(0, 50);
      return `${platform} Message`;
    }

    if (dataType === 'webhook') {
      if (data.method && data.path) return `${data.method} ${data.path}`;
      if (data.url) return data.url;
      return 'Webhook Data';
    }

    if (dataType === 'form_submission') {
      if (data.form_name) return `Form: ${data.form_name}`;
      if (data.title) return data.title;
      return 'Form Submission';
    }

    // Default to record handling
    if (dataType === 'record' || !dataType) {
      // Check top-level fields first
      const topLevelFields = ['title', 'display_name', 'name'];
      for (const field of topLevelFields) {
        if (data[field] && typeof data[field] === 'string' && data[field].trim() !== '') {
          return data[field];
        }
      }

      // Then check data object
      if (data.data) {
        for (const field of ['name', 'title', 'display_name', 'full_name', 'email', 'company']) {
          if (data.data[field] && typeof data.data[field] === 'string' && data.data[field].trim() !== '') {
            return data.data[field];
          }
        }
      }

      return `Record ${data.id || ''}`;
    }

    // Generic handling for unknown types
    if (data.title) return data.title;
    if (data.name) return data.name;
    if (data.id) return `${dataType} ${data.id}`;
    return dataType || 'Test Data';
  };

  // Helper to determine data type
  const getDataType = (value: any): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (Array.isArray(value)) return 'array';
    if (value instanceof Date || isDate(value)) return 'datetime';
    if (typeof value === 'object') return 'object';
    if (typeof value === 'boolean') return 'boolean';
    if (typeof value === 'number') return 'number';
    return 'string';
  };

  // Check if value is a date string
  const isDate = (value: any): boolean => {
    if (typeof value !== 'string') return false;
    return /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?)?$/.test(value);
  };

  // Generate field descriptions
  const getFieldDescription = (key: string, type: string, value: any): string => {
    if (type === 'array') {
      const length = Array.isArray(value) ? value.length : 0;
      return `${length} item${length !== 1 ? 's' : ''}`;
    }
    if (type === 'object') {
      const keys = Object.keys(value || {}).length;
      return `${keys} field${keys !== 1 ? 's' : ''}`;
    }
    return '';
  };

  // Format value for display
  const formatValue = (value: any, type: string): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';

    if (type === 'string') {
      const str = String(value);
      if (str.length > 50) {
        return `"${str.substring(0, 47)}..."`;
      }
      return `"${str}"`;
    }

    if (type === 'boolean') {
      return value ? '✓ true' : '✗ false';
    }

    if (type === 'number') {
      return Number(value).toLocaleString();
    }

    if (type === 'datetime') {
      const date = new Date(value);
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));

      if (days === 0) {
        return date.toLocaleTimeString();
      } else if (days === 1) {
        return 'Yesterday ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } else if (days < 7) {
        return `${days} days ago`;
      } else {
        return date.toLocaleDateString();
      }
    }

    if (type === 'array') {
      const count = Array.isArray(value) ? value.length : 0;
      return `[${count}]`;
    }

    if (type === 'object') {
      const count = Object.keys(value || {}).length;
      return `{${count}}`;
    }

    return String(value);
  };

  // Copy field path to clipboard
  const copyFieldPath = (field: InputField) => {
    const expression = `{{${field.nodeId}.${field.key}}}`;
    navigator.clipboard.writeText(expression);
    toast.success(`Copied: ${expression}`);
  };

  // Copy sample input
  const copySampleInput = () => {
    if (sampleInput) {
      navigator.clipboard.writeText(JSON.stringify(sampleInput, null, 2));
      toast.success('Sample input copied to clipboard');
    }
  };

  // Toggle field expansion
  const toggleFieldExpansion = (fieldKey: string) => {
    setExpandedFields(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fieldKey)) {
        newSet.delete(fieldKey);
        inputFields.forEach(field => {
          if (field.key.startsWith(fieldKey + '.')) {
            newSet.delete(field.key);
          }
        });
      } else {
        newSet.add(fieldKey);
      }
      return newSet;
    });
  };

  // Check if field is visible
  const isFieldVisible = (field: InputField) => {
    if (field.depth === 0) return true;

    const parts = field.key.split(/[\.\[\]]+/).filter(Boolean);
    for (let i = 1; i < parts.length; i++) {
      let parentKey = parts.slice(0, i).join('.');
      const parentField = inputFields.find(f => {
        return f.key === parentKey || f.key === `${parentKey}[0]`;
      });

      if (parentField && (parentField.type === 'object' || parentField.type === 'array')) {
        if (!expandedFields.has(parentField.key)) {
          return false;
        }
      }
    }
    return true;
  };

  // Get field type icon
  const getFieldTypeIcon = (type: string) => {
    switch (type) {
      case 'object':
        return <Database className="h-3.5 w-3.5 text-orange-500" />;
      case 'array':
        return <Database className="h-3.5 w-3.5 text-pink-500" />;
      case 'boolean':
        return <CheckCircle className="h-3.5 w-3.5 text-purple-500" />;
      case 'string':
        return <Code2 className="h-3.5 w-3.5 text-blue-500" />;
      case 'number':
        return <Code2 className="h-3.5 w-3.5 text-green-500" />;
      case 'datetime':
        return <Code2 className="h-3.5 w-3.5 text-indigo-500" />;
      case 'null':
      case 'undefined':
        return <Code2 className="h-3.5 w-3.5 text-gray-400" />;
      default:
        return <Code2 className="h-3.5 w-3.5 text-gray-500" />;
    }
  };

  // Get field type color
  const getFieldTypeColor = (type: string) => {
    switch (type) {
      case 'string':
        return 'text-blue-600 dark:text-blue-400';
      case 'number':
        return 'text-green-600 dark:text-green-400';
      case 'boolean':
        return 'text-purple-600 dark:text-purple-400';
      case 'object':
        return 'text-orange-600 dark:text-orange-400';
      case 'array':
        return 'text-pink-600 dark:text-pink-400';
      case 'datetime':
        return 'text-indigo-600 dark:text-indigo-400';
      case 'null':
      case 'undefined':
        return 'text-gray-500 dark:text-gray-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="space-y-4">
      {/* Section 1: Test Data Selection (for triggers) */}
      {isTriggerNode && (
        <>
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium">Test Data Selection</h4>
              {loadingTestData && (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              )}
            </div>

            <Card className="p-3">
              {testDataList.length > 0 ? (
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <Button
                      variant={useRealData ? "default" : "outline"}
                      size="sm"
                      onClick={() => onUseRealDataChange?.(true)}
                      disabled={testDataList.length === 0}
                      className="flex-1"
                    >
                      <Database className="h-3 w-3 mr-1" />
                      Use Real Data
                    </Button>
                    <Button
                      variant={!useRealData ? "default" : "outline"}
                      size="sm"
                      onClick={() => onUseRealDataChange?.(false)}
                      className="flex-1"
                    >
                      <Code2 className="h-3 w-3 mr-1" />
                      Use Mock Data
                    </Button>
                  </div>

                  {useRealData && (
                    <div className="space-y-2">
                      <Label className="text-xs">
                        Select test {testDataType || 'data'}:
                      </Label>
                      <Select
                        value={selectedTestData ? String(selectedTestData.id) : ''}
                        onValueChange={(value) => {
                          const data = testDataList.find((d: any) => String(d.id) === value);
                          onTestDataChange?.(data);
                        }}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder={`Select test ${testDataType || 'data'}`} />
                        </SelectTrigger>
                        <SelectContent>
                          {testDataList.map((item: any) => {
                            const displayName = getTestDataDisplayName(item, testDataType);

                            // Get additional preview info based on type (excluding form_submission)
                            let previewInfo = null;
                            if (testDataType === 'email' || testDataType === 'email_message') {
                              previewInfo = item.from || item.sender;
                            } else if (testDataType === 'linkedin_message' || testDataType === 'whatsapp_message') {
                              previewInfo = item.message?.substring(0, 50);
                            } else if (testDataType === 'record') {
                              previewInfo = item.data?.email || item.email;
                            }

                            return (
                              <SelectItem key={item.id} value={String(item.id)}>
                                <div className="flex items-center gap-2">
                                  <User className="h-3 w-3" />
                                  <span className="font-medium">
                                    {displayName}
                                  </span>
                                  {previewInfo && previewInfo !== displayName && (
                                    <span className="text-xs text-muted-foreground">
                                      ({previewInfo})
                                    </span>
                                  )}
                                </div>
                              </SelectItem>
                            );
                          })}
                        </SelectContent>
                      </Select>

                      {/* Show preview of selected form submission data */}
                      {selectedTestData && testDataType === 'form_submission' && selectedTestData.preview?.submitted_data && (
                        <div className="mt-2 p-2 bg-muted/50 rounded-md">
                          <div className="text-xs text-muted-foreground mb-1">Form Data Preview:</div>
                          <div className="space-y-1">
                            {Object.entries(selectedTestData.preview.submitted_data).slice(0, 3).map(([key, value]: [string, any]) => (
                              <div key={key} className="flex items-start gap-2 text-xs">
                                <span className="font-medium text-muted-foreground">{key}:</span>
                                <span className="text-foreground">
                                  {typeof value === 'object' ?
                                    (value?.number || JSON.stringify(value).substring(0, 50)) :
                                    String(value).substring(0, 50)}
                                </span>
                              </div>
                            ))}
                            {Object.keys(selectedTestData.preview.submitted_data).length > 3 && (
                              <div className="text-xs text-muted-foreground">
                                ...and {Object.keys(selectedTestData.preview.submitted_data).length - 3} more fields
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {!useRealData && (
                    <div className="text-xs text-muted-foreground">
                      Mock {testDataType || 'data'} will be generated for testing
                    </div>
                  )}
                </div>
              ) : loadingTestData ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Loading test data...
                </div>
              ) : (
                <div className="text-xs text-muted-foreground">
                  {testDataType === 'email' || testDataType === 'email_message' ?
                    'No email messages found. Send or receive emails to create test data.' :
                    testDataType === 'linkedin_message' ?
                    'No LinkedIn messages found. Send or receive messages to create test data.' :
                    testDataType === 'whatsapp_message' ?
                    'No WhatsApp messages found. Send or receive messages to create test data.' :
                    testDataType === 'webhook' ?
                    'No webhook data found. Configure webhook URL and send a test request.' :
                    testDataType === 'form_submission' ?
                    'No form submissions found. Submit a form to create test data.' :
                    'No test data available. Configure the trigger to load test data.'
                  }
                </div>
              )}
            </Card>
          </div>

          <Separator />
        </>
      )}

      {/* Section 2: Input Structure */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium">Input Structure</h4>
            {!loading && inputFields.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {inputFields.filter(f => f.depth === 0).length} root fields
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {!loading && inputFields.some(f => f.type === 'object' || f.type === 'array') && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs px-2"
                onClick={() => {
                  const allExpandable = inputFields
                    .filter(f => f.type === 'object' || f.type === 'array')
                    .map(f => f.key);

                  if (expandedFields.size === 0) {
                    setExpandedFields(new Set(allExpandable));
                  } else {
                    setExpandedFields(new Set());
                  }
                }}
              >
                {expandedFields.size > 0 ? 'Collapse All' : 'Expand All'}
              </Button>
            )}
            {loading && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
        </div>

        <Card className="p-3">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : inputFields.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No input data</p>
              <p className="text-xs mt-1">
                {isTriggerNode
                  ? 'This is a trigger node - it starts the workflow'
                  : 'Connect nodes to provide input data'}
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[300px]">
              <div className="space-y-0.5">
                {/* Group fields by node */}
                {Array.from(new Set(inputFields.map(f => f.nodeId))).map(nodeId => {
                  const nodeFields = inputFields.filter(f => f.nodeId === nodeId);
                  const source = sources.find(s => s.nodeId === nodeId);

                  return (
                    <div key={nodeId} className="mb-3">
                      <div className="px-2 py-1.5 bg-muted/30 rounded-md mb-1">
                        <div className="flex items-center gap-2">
                          <Code2 className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-xs font-medium">{source?.label || nodeId}</span>
                          <Badge variant="outline" className="text-xs ml-auto">
                            {nodeFields.length} fields
                          </Badge>
                        </div>
                      </div>

                      {nodeFields.filter(isFieldVisible).map((field, index) => {
                        const isExpandable = field.type === 'object' || field.type === 'array';
                        const isExpanded = expandedFields.has(field.key);

                        // Extract field name properly
                        let fieldName = field.key;
                        if (field.key.includes('.')) {
                          const parts = field.key.split('.');
                          fieldName = parts[parts.length - 1];
                        }
                        const isArrayIndex = fieldName.includes('[');

                        return (
                          <div key={`${nodeId}-${index}`} className="group relative">
                            {/* Tree connector lines */}
                            {field.depth > 0 && (
                              <div
                                className="absolute left-0 top-0 bottom-0 border-l border-gray-200 dark:border-gray-700"
                                style={{ left: `${(field.depth - 1) * 20 + 16}px` }}
                              />
                            )}

                      <div
                        className="relative hover:bg-muted/30 rounded-md transition-all duration-150 py-1.5 px-2"
                        style={{ paddingLeft: `${field.depth * 20 + 8}px` }}
                      >
                        {/* Main row */}
                        <div className="flex items-center gap-2">
                          {/* Expand/Collapse button */}
                          <Button
                            variant="ghost"
                            size="sm"
                            className={`h-5 w-5 p-0 hover:bg-muted ${!isExpandable ? 'invisible' : ''}`}
                            onClick={() => isExpandable && toggleFieldExpansion(field.key)}
                          >
                            {isExpandable && (
                              isExpanded ? (
                                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                              ) : (
                                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                              )
                            )}
                          </Button>

                          {/* Field icon */}
                          <div className="flex-shrink-0">
                            {getFieldTypeIcon(field.type)}
                          </div>

                          {/* Field name */}
                          <div className="flex-1 min-w-0 overflow-hidden">
                            <code className={`font-mono text-sm ${isArrayIndex ? 'text-muted-foreground' : 'font-medium'} break-all`}>
                              {fieldName}
                            </code>

                            {/* Type indicator - more subtle */}
                            <span className={`ml-2 text-xs ${getFieldTypeColor(field.type)} whitespace-nowrap`}>
                              {field.type}
                            </span>
                          </div>

                          {/* Value/Description for objects and arrays */}
                          {isExpandable && field.description && (
                            <span className="text-xs text-muted-foreground">
                              {field.description}
                            </span>
                          )}

                          {/* Copy button */}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                            onClick={() => copyFieldPath(field)}
                            title={`Copy: {{${field.nodeId}.${field.key}}}`}
                          >
                            <Copy className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                          </Button>
                        </div>

                        {/* Second row - Value for primitives */}
                        {!isExpandable && field.value !== undefined && (
                          <div className="flex items-center gap-2 mt-0.5 pl-7">
                            <span className="text-xs text-muted-foreground font-mono break-all">
                              = {formatValue(field.value, field.type)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </Card>
      </div>

      <Separator />

      {/* Section 3: Sample Input (JSON) */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium">Sample Input</h4>
            {sampleInput && (
              <Badge variant="secondary" className="text-xs">
                JSON
              </Badge>
            )}
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={copySampleInput}
              disabled={!sampleInput || loading}
              className="h-6 text-xs px-2"
            >
              <Copy className="h-3 w-3 mr-1" />
              Copy JSON
            </Button>
          </div>
        </div>

        <Card className="p-3 bg-muted/30">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/6" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : (
            <ScrollArea className="h-[200px]">
              <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                {sampleInput ? JSON.stringify(sampleInput, null, 2) : 'No input data available'}
              </pre>
            </ScrollArea>
          )}
        </Card>
      </div>

      {/* Usage hint */}
      <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-3">
        <div className="flex gap-2">
          <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-blue-700 dark:text-blue-300">
            <p className="font-medium mb-1">Using Input in Configuration</p>
            <p className="text-blue-600 dark:text-blue-400">
              Reference these fields in your configuration using expressions like:
              <code className="ml-1 font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded break-all">
                {isTriggerNode ? '{{trigger.record.id}}' : '{{nodeId.field}}'}
              </code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}