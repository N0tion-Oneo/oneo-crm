'use client';

/**
 * NodeOutputTabV3
 * Enhanced output display using hierarchical table view
 */

import React, { useEffect, useState, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  AlertCircle,
  RefreshCw,
  Copy,
  Loader2,
  ArrowLeft
} from 'lucide-react';
import { WorkflowNodeType } from '../../types';
import { useTestData } from './TestDataContext';
import { toast } from 'sonner';
import { workflowsApi } from '@/lib/api';
import { DataTableView } from './DataTableView';

interface NodeOutputTabV3Props {
  nodeId: string;
  nodeType: WorkflowNodeType;
  config: any;
  inputData?: any;
  testRecord?: any;
  testDataType?: string;
  onNodeTest?: (nodeId: string, output: any) => void;
  nodeOutputs?: Record<string, any>;
}

export function NodeOutputTabV3({
  nodeId,
  nodeType,
  config,
  inputData,
  testRecord,
  testDataType,
  onNodeTest,
  nodeOutputs
}: NodeOutputTabV3Props) {
  const { setNodeTestData } = useTestData();
  const [sampleOutput, setSampleOutput] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track previous config and input data to detect actual changes
  const [prevConfig, setPrevConfig] = useState<string>('');
  const [prevInputData, setPrevInputData] = useState<string>('');

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

  // Serialize input data for comparison
  const inputDataString = useMemo(() => {
    try {
      return JSON.stringify(inputData || {});
    } catch {
      return '';
    }
  }, [inputData]);

  // Fetch real output from backend when config or input data changes
  useEffect(() => {
    // Skip if neither config nor input data has changed
    if (configString === prevConfig && inputDataString === prevInputData && sampleOutput !== null) {
      return;
    }

    const fetchRealOutput = async () => {
      if (!nodeType || !config) return;

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

          // Store in test data context
          setNodeTestData(nodeId, {
            input: inputData || {},
            output: output
          });

          // Call onNodeTest to store in parent's nodeOutputs state
          if (onNodeTest) {
            onNodeTest(nodeId, output);
          }

          // Mark this config and input data as tested
          setPrevConfig(configString);
          setPrevInputData(inputDataString);
        } else {
          throw new Error('No output received from backend');
        }
      } catch (err: any) {
        console.error('Failed to fetch real output:', err);
        setError(err.response?.data?.error || err.message || 'Failed to generate output');

        // Fallback to empty output
        setSampleOutput(null);
      } finally {
        setLoading(false);
      }
    };

    fetchRealOutput();
  }, [nodeType, configString, prevConfig, inputDataString, prevInputData, nodeId, testRecord, setNodeTestData, onNodeTest]);

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

        // Update prevConfig and prevInputData to mark this state as tested
        setPrevConfig(configString);
        setPrevInputData(inputDataString);

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

  // Prepare display data
  const displayData = useMemo(() => {
    if (nodeOutputs && nodeOutputs[nodeId]) {
      // Use cached output if available
      return nodeOutputs[nodeId];
    }
    return sampleOutput;
  }, [sampleOutput, nodeOutputs, nodeId]);

  return (
    <div className="space-y-4">
      {/* Error state */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <p className="font-medium mb-1">Failed to load output</p>
            <p className="text-sm">{error}</p>
          </AlertDescription>
        </Alert>
      )}

      {/* Output Structure - Now using DataTableView */}
      <div>
        {loading && (
          <div className="flex items-center gap-2 mb-3">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Loading output...</span>
          </div>
        )}

        {loading && !displayData ? (
          <Card className="p-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </Card>
        ) : displayData ? (
          <DataTableView
            data={displayData}
            nodeId={nodeId}
            title=""
            initialExpanded="first-level"
            showSearch={true}
            showTypeColumn={true}
            showCopyButtons={true}
            maxHeight="350px"
            onFieldCopy={(path, value) => {
              // Custom handling for workflow field references
              const expression = `{${nodeId}.${path}}`;
              navigator.clipboard.writeText(expression);
              toast.success(`Copied: ${expression}`);
            }}
          />
        ) : (
          <Card className="p-8">
            <div className="text-center text-muted-foreground">
              <AlertCircle className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No output generated</p>
              <p className="text-xs mt-1">
                Configure the node to see expected output
              </p>
            </div>
          </Card>
        )}
      </div>

      <Separator />

      {/* Sample Output Preview */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium">Sample Output</h4>
            {displayData && (
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
              disabled={!displayData || loading}
              className="h-6 text-xs px-2"
            >
              <Copy className="h-3 w-3 mr-1" />
              Copy JSON
            </Button>
          </div>
        </div>

        <Card className="p-3 bg-muted/30">
          {loading && !displayData ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/6" />
            </div>
          ) : (
            <ScrollArea className="h-[200px]">
              <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                {displayData ? JSON.stringify(displayData, null, 2) : 'No output generated'}
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
                {`{${nodeId}.record.id}`}
              </code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}