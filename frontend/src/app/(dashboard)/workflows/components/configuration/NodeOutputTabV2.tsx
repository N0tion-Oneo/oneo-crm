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
  Loader2
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
}

export function NodeOutputTabV2({
  nodeId,
  nodeType,
  config,
  inputData,
  testRecord
}: NodeOutputTabV2Props) {
  const { setNodeTestData } = useTestData();
  const [sampleOutput, setSampleOutput] = useState<any>(null);
  const [outputFields, setOutputFields] = useState<Array<{ key: string; type: string; description: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if this is a trigger node
  const isTriggerNode = useMemo(() => {
    return nodeType.startsWith('TRIGGER_') || nodeType.toLowerCase().includes('trigger');
  }, [nodeType]);

  // Fetch real output from backend when config, input or test record changes
  useEffect(() => {
    const fetchRealOutput = async () => {
      if (!nodeType || !config) return;

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
          requestData.test_data_type = 'record';
        }

        // Add input data context if available
        if (inputData && Object.keys(inputData).length > 0) {
          requestData.test_context = inputData;
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

          // Extract output field structure
          const fields = extractOutputFields(nodeType, output);
          setOutputFields(fields);
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
  }, [nodeType, config, inputData, nodeId, testRecord, setNodeTestData]);

  const extractOutputFields = (type: WorkflowNodeType, output: any): Array<{ key: string; type: string; description: string }> => {
    const fields: Array<{ key: string; type: string; description: string }> = [];

    // Common fields
    fields.push({ key: 'success', type: 'boolean', description: 'Operation success status' });

    // Type-specific fields
    switch (type) {
      case WorkflowNodeType.RECORD_FIND:
      case WorkflowNodeType.RECORD_CREATE:
      case WorkflowNodeType.RECORD_UPDATE:
        fields.push({ key: 'record', type: 'object', description: 'The record data' });
        fields.push({ key: 'record.id', type: 'string', description: 'Record ID' });
        fields.push({ key: 'record.data', type: 'object', description: 'Record fields' });
        break;

      case WorkflowNodeType.UNIPILE_SEND_EMAIL:
      case WorkflowNodeType.UNIPILE_SEND_SMS:
      case WorkflowNodeType.UNIPILE_SEND_WHATSAPP:
      case WorkflowNodeType.UNIPILE_SEND_LINKEDIN:
        fields.push({ key: 'message_id', type: 'string', description: 'Message ID' });
        fields.push({ key: 'status', type: 'string', description: 'Delivery status' });
        fields.push({ key: 'sent_at', type: 'datetime', description: 'Timestamp' });
        break;

      case WorkflowNodeType.AI_PROMPT:
      case WorkflowNodeType.AI_ANALYSIS:
        fields.push({ key: 'result', type: 'string', description: 'AI response' });
        fields.push({ key: 'model', type: 'string', description: 'Model used' });
        fields.push({ key: 'tokens', type: 'number', description: 'Tokens consumed' });
        break;

      case WorkflowNodeType.CONDITION:
        fields.push({ key: 'condition_met', type: 'boolean', description: 'Condition result' });
        fields.push({ key: 'branch', type: 'string', description: 'Branch taken (true/false)' });
        fields.push({ key: 'evaluated_conditions', type: 'array', description: 'Conditions evaluated' });
        break;

      case WorkflowNodeType.FOR_EACH:
        fields.push({ key: 'items_processed', type: 'number', description: 'Number of items' });
        fields.push({ key: 'results', type: 'array', description: 'Processing results' });
        fields.push({ key: 'iteration_count', type: 'number', description: 'Total iterations' });
        break;

      case WorkflowNodeType.HTTP_REQUEST:
        fields.push({ key: 'status_code', type: 'number', description: 'HTTP status code' });
        fields.push({ key: 'response', type: 'object', description: 'Response data' });
        fields.push({ key: 'headers', type: 'object', description: 'Response headers' });
        break;

      case WorkflowNodeType.WAIT_DELAY:
        fields.push({ key: 'waited_for', type: 'number', description: 'Minutes waited' });
        fields.push({ key: 'continued_at', type: 'datetime', description: 'Resume time' });
        break;

      default:
        // Extract from actual output
        if (output && typeof output === 'object') {
          Object.keys(output).forEach(key => {
            if (key !== 'success') {
              const type = Array.isArray(output[key]) ? 'array' : typeof output[key];
              fields.push({ key, type, description: `Output field: ${key}` });
            }
          });
        }
    }

    return fields;
  };

  const regenerateOutput = async () => {
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
        requestData.test_data_type = 'record';
      }

      // Add input data context if available
      if (inputData && Object.keys(inputData).length > 0) {
        requestData.test_context = inputData;
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

  const getFieldTypeIcon = (type: string) => {
    switch (type) {
      case 'object':
      case 'array':
        return <Database className="h-3 w-3" />;
      case 'boolean':
        return <CheckCircle className="h-3 w-3" />;
      default:
        return <Code2 className="h-3 w-3" />;
    }
  };

  const getFieldTypeBadgeColor = (type: string) => {
    switch (type) {
      case 'string':
        return 'bg-blue-100 text-blue-700';
      case 'number':
        return 'bg-green-100 text-green-700';
      case 'boolean':
        return 'bg-purple-100 text-purple-700';
      case 'object':
        return 'bg-orange-100 text-orange-700';
      case 'array':
        return 'bg-pink-100 text-pink-700';
      case 'datetime':
        return 'bg-indigo-100 text-indigo-700';
      default:
        return 'bg-gray-100 text-gray-700';
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
          <h4 className="text-sm font-medium">Output Structure</h4>
          <Badge variant="outline" className="text-xs">
            {loading ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              `${outputFields.length} fields`
            )}
          </Badge>
        </div>

        <Card className="p-3">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : (
            <ScrollArea className="h-[150px]">
              <div className="space-y-2">
                {outputFields.map((field, index) => (
                <div key={index} className="flex items-start gap-2 text-xs">
                  <div className="flex items-center gap-1 min-w-[100px]">
                    {getFieldTypeIcon(field.type)}
                    <code className="font-mono">{field.key}</code>
                  </div>
                  <Badge
                    variant="secondary"
                    className={`text-xs h-5 ${getFieldTypeBadgeColor(field.type)}`}
                  >
                    {field.type}
                  </Badge>
                  <span className="text-muted-foreground flex-1">
                    {field.description}
                  </span>
                </div>
              ))}
            </div>
          </ScrollArea>
          )}
        </Card>
      </div>

      <Separator />

      {/* Sample Output Preview */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium">Sample Output</h4>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={regenerateOutput}
              disabled={loading}
              className="h-7 px-2"
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
              className="h-7 px-2"
            >
              <Copy className="h-3 w-3 mr-1" />
              Copy
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
              <pre className="text-xs font-mono">
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
              <code className="ml-1 font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded">
                {`{{${nodeId}.record.id}}`}
              </code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}