'use client';

/**
 * NodeOutputTabV2
 * Displays expected output structure for workflow nodes
 * Now uses actual backend processors for authentic output
 */

import React, { useEffect, useState, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Code2,
  Database,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Copy,
  Loader2,
  ChevronRight,
  ChevronDown
} from 'lucide-react';
import { WorkflowNodeType } from '../../types';
import { useTestData } from './TestDataContext';
import { toast } from 'sonner';
import { workflowsApi } from '@/lib/api';

interface NodeOutputTabV2Props {
  nodeId: string;
  nodeType: WorkflowNodeType;
  config: any;
  inputData?: any;
  testRecord?: any;  // Test record selected in input panel
  testDataType?: string;  // Type of test data (record, email, linkedin_message, etc.)
  onNodeTest?: (nodeId: string, output: any) => void;
  nodeOutputs?: Record<string, any>;
}

export function NodeOutputTabV2({
  nodeId,
  nodeType,
  config,
  inputData,
  testRecord,
  testDataType,
  onNodeTest,
  nodeOutputs
}: NodeOutputTabV2Props) {
  const { setNodeTestData } = useTestData();
  const [sampleOutput, setSampleOutput] = useState<any>(null);
  const [outputFields, setOutputFields] = useState<Array<{ key: string; type: string; value: any; description: string; depth: number }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());

  // Track previous config to detect actual changes
  const [prevConfig, setPrevConfig] = useState<string>('');

  // Check if this is a trigger node
  const isTriggerNode = useMemo(() => {
    return nodeType.startsWith('TRIGGER_') || nodeType.toLowerCase().includes('trigger');
  }, [nodeType]);

  // Serialize config for comparison
  const configString = useMemo(() => {
    try {
      return JSON.stringify(config || {});
    } catch {
      return '';
    }
  }, [config]);

  // Fetch real output from backend only when config actually changes
  useEffect(() => {
    // Skip if config hasn't actually changed
    if (configString === prevConfig && sampleOutput !== null) {
      return;
    }
    const fetchRealOutput = async () => {
      if (!nodeType || !config) return;

      // Skip during server-side rendering to prevent tenant routing issues
      if (typeof window === 'undefined') {
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Prepare the request data
        const requestData: any = {
          node_type: nodeType.toLowerCase().replace(/_/g, '_'),  // Ensure correct format
          node_config: config
        };

        // Add test data for triggers or nodes with test records
        if (testRecord) {
          requestData.test_data_id = String(testRecord.id);
          requestData.test_data_type = testDataType || 'record';
        }

        // Add input data context if available
        if (inputData && Object.keys(inputData).length > 0) {
          requestData.context = inputData;
        }

        // Call the backend to get real output
        const response = await workflowsApi.testNodeStandalone(requestData);

        if (response.data?.output) {
          const output = response.data.output;
          setSampleOutput(output);

          // Store in test data context
          setNodeTestData(nodeId, {
            input: inputData || {},
            output: output
          });

          // Call onNodeTest to store in parent's nodeOutputs state
          if (onNodeTest) {
            onNodeTest(nodeId, output);
          }

          // Extract output field structure from actual data
          const fields = extractOutputFields(output);
          setOutputFields(fields);
          // Auto-expand first level objects
          setExpandedFields(new Set(fields.filter(f => f.depth === 0 && f.type === 'object').map(f => f.key)));

          // Mark this config as tested
          setPrevConfig(configString);
        } else {
          throw new Error('No output received from backend');
        }
      } catch (err: any) {
        console.error('Failed to fetch real output:', err);
        setError(err.response?.data?.error || err.message || 'Failed to generate output');

        // Fallback to empty output
        setSampleOutput(null);
        setOutputFields([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRealOutput();
  }, [nodeType, configString, prevConfig, inputData, nodeId, testRecord, setNodeTestData, onNodeTest]);

  // Recursively extract fields from actual output data
  const extractOutputFields = (data: any, prefix: string = ''): Array<{ key: string; type: string; value: any; description: string; depth: number }> => {
    const fields: Array<{ key: string; type: string; value: any; description: string; depth: number }> = [];

    if (!data || typeof data !== 'object') {
      return fields;
    }

    const depth = prefix.split('.').filter(Boolean).length;

    Object.entries(data).forEach(([key, value]) => {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      const type = getDataType(value);

      // Add the current field
      fields.push({
        key: fullKey,
        type,
        value: value,
        description: getFieldDescription(fullKey, type, value),
        depth
      });

      // Recursively add nested fields for objects and arrays
      if (type === 'object' && value !== null && !isDate(value)) {
        fields.push(...extractOutputFields(value, fullKey));
      } else if (type === 'array' && Array.isArray(value) && value.length > 0) {
        // Show structure of first array item
        if (typeof value[0] === 'object' && value[0] !== null) {
          fields.push(...extractOutputFields(value[0], `${fullKey}[0]`));
        }
      }
    });

    return fields;
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

  // Helper to check if value is a date string
  const isDate = (value: any): boolean => {
    if (typeof value !== 'string') return false;
    // ISO 8601 date format check
    return /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?)?$/.test(value);
  };

  // Helper to generate field descriptions
  const getFieldDescription = (key: string, type: string, value: any): string => {
    // Only show size/count for collections
    if (type === 'array') {
      const length = Array.isArray(value) ? value.length : 0;
      return `${length} item${length !== 1 ? 's' : ''}`;
    }
    if (type === 'object') {
      const keys = Object.keys(value || {}).length;
      return `${keys} field${keys !== 1 ? 's' : ''}`;
    }

    // For primitive types, don't show redundant descriptions
    return '';
  };

  const regenerateOutput = async () => {
    // Skip during server-side rendering
    if (typeof window === 'undefined') {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Prepare the request data
      const requestData: any = {
        node_type: nodeType.toLowerCase().replace(/_/g, '_'),
        node_config: config
      };

      // Add test data for triggers or nodes with test records
      if (testRecord) {
        requestData.test_data_id = String(testRecord.id);
        requestData.test_data_type = testDataType || 'record';
      }

      // Add input data context if available
      if (inputData && Object.keys(inputData).length > 0) {
        requestData.context = inputData;
      }

      // Call the backend to get real output
      const response = await workflowsApi.testNodeStandalone(requestData);

      if (response.data?.output) {
        const output = response.data.output;
        setSampleOutput(output);
        setNodeTestData(nodeId, {
          input: inputData || {},
          output: output
        });

        // Call onNodeTest to store in parent's nodeOutputs state
        if (onNodeTest) {
          onNodeTest(nodeId, output);
        }

        // Update prevConfig to mark this config as tested
        setPrevConfig(configString);

        // Also update the fields
        const fields = extractOutputFields(output);
        setOutputFields(fields);
        setExpandedFields(new Set(fields.filter(f => f.depth === 0 && f.type === 'object').map(f => f.key)));

        toast.success('Output regenerated from backend');
      } else {
        throw new Error('No output received from backend');
      }
    } catch (err: any) {
      console.error('Failed to regenerate output:', err);
      setError(err.response?.data?.error || err.message || 'Failed to regenerate output');
      toast.error('Failed to regenerate output');
    } finally {
      setLoading(false);
    }
  };

  const copyOutput = () => {
    if (sampleOutput) {
      navigator.clipboard.writeText(JSON.stringify(sampleOutput, null, 2));
      toast.success('Output copied to clipboard');
    }
  };

  const copyFieldPath = (fieldKey: string) => {
    const expression = `{{${nodeId}.${fieldKey}}}`;
    navigator.clipboard.writeText(expression);
    toast.success(`Copied: ${expression}`);
  };

  const toggleFieldExpansion = (fieldKey: string) => {
    setExpandedFields(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fieldKey)) {
        // Collapse this field and all children
        newSet.delete(fieldKey);
        outputFields.forEach(field => {
          if (field.key.startsWith(fieldKey + '.')) {
            newSet.delete(field.key);
          }
        });
      } else {
        // Expand this field
        newSet.add(fieldKey);
      }
      return newSet;
    });
  };

  const isFieldVisible = (field: { key: string; depth: number; type: string }) => {
    if (field.depth === 0) return true;

    // Check if any parent is collapsed
    const parts = field.key.split(/[\.\[\]]+/).filter(Boolean);

    // Build up parent keys to check
    for (let i = 1; i < parts.length; i++) {
      let parentKey = parts.slice(0, i).join('.');

      // Handle array notation - check if we need to add [0] for array items
      const parentField = outputFields.find(f => {
        return f.key === parentKey || f.key === `${parentKey}[0]`;
      });

      if (parentField && (parentField.type === 'object' || parentField.type === 'array')) {
        // For array fields, check both with and without index
        if (!expandedFields.has(parentField.key)) {
          return false;
        }
      }
    }
    return true;
  };

  const formatValue = (value: any, type: string): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';

    if (type === 'string') {
      // Truncate long strings
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
      // Format large numbers with commas
      return Number(value).toLocaleString();
    }

    if (type === 'datetime') {
      const date = new Date(value);
      // Show relative time for recent dates
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

  const getFieldTypeBadgeColor = (type: string) => {
    // Returns text color classes only for the inline type indicator
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
      {/* Error state */}
      {error && (
        <div className="bg-red-50 dark:bg-red-950/20 rounded-lg p-3">
          <div className="flex gap-2">
            <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-red-700 dark:text-red-300">
              <p className="font-medium mb-1">Failed to load output</p>
              <p className="text-red-600 dark:text-red-400">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Output Structure */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium">Output Structure</h4>
            {!loading && outputFields.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {outputFields.filter(f => f.depth === 0).length} root fields
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {!loading && outputFields.some(f => f.type === 'object' || f.type === 'array') && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs px-2"
                onClick={() => {
                  const allExpandable = outputFields
                    .filter(f => f.type === 'object' || f.type === 'array')
                    .map(f => f.key);

                  if (expandedFields.size === 0) {
                    // Expand all
                    setExpandedFields(new Set(allExpandable));
                  } else {
                    // Collapse all
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
          ) : (
            <ScrollArea className="h-[300px]">
              <div className="space-y-0.5">
                {outputFields.filter(isFieldVisible).map((field, index) => {
                  const isExpandable = field.type === 'object' || field.type === 'array';
                  const isExpanded = expandedFields.has(field.key);

                  // Extract field name properly handling array indices
                  let fieldName = field.key;
                  if (field.key.includes('.')) {
                    // Get the last part after the final dot
                    const parts = field.key.split('.');
                    fieldName = parts[parts.length - 1];
                  }
                  const isArrayIndex = fieldName.includes('[');

                  return (
                    <div
                      key={index}
                      className="group relative"
                    >
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
                            <span className={`ml-2 text-xs ${getFieldTypeBadgeColor(field.type)} whitespace-nowrap`}>
                              {field.type}
                            </span>
                          </div>

                          {/* Value/Description for objects and arrays */}
                          {isExpandable && (
                            <span className="text-xs text-muted-foreground">
                              {field.description}
                            </span>
                          )}

                          {/* Copy button */}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                            onClick={() => copyFieldPath(field.key)}
                            title={`Copy: {{${nodeId}.${field.key}}}`}
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
            </ScrollArea>
          )}
        </Card>
      </div>

      <Separator />

      {/* Sample Output Preview */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium">Sample Output</h4>
            {sampleOutput && (
              <Badge variant="secondary" className="text-xs">
                JSON
              </Badge>
            )}
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={regenerateOutput}
              disabled={loading}
              className="h-6 text-xs px-2"
            >
              {loading ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3 mr-1" />
              )}
              Regenerate
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={copyOutput}
              disabled={!sampleOutput || loading}
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
                {sampleOutput ? JSON.stringify(sampleOutput, null, 2) : 'No output generated'}
              </pre>
            </ScrollArea>
          )}
        </Card>
      </div>

      {/* Usage Hint */}
      <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-3">
        <div className="flex gap-2">
          <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-blue-700 dark:text-blue-300">
            <p className="font-medium mb-1">Using Output in Next Nodes</p>
            <p className="text-blue-600 dark:text-blue-400">
              Reference these fields in subsequent nodes using expressions like:
              <code className="ml-1 font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded break-all">
                {`{{${nodeId}.record.id}}`}
              </code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}