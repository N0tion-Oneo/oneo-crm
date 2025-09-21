'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Table as TableIcon, FileJson, Code, Copy, Check,
  AlertCircle, RefreshCw, PlayCircle, Database,
  FileText, Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { workflowsApi } from '@/lib/api';

interface NodeOutputTabProps {
  output: any;
  error: string | null;
  loading?: boolean;
  nodeId?: string;
  nodeType?: string;
  nodeData?: any;
  workflowId?: string;
  onTest?: (testRecordId?: string) => void;
}

export function NodeOutputTab({
  output,
  error,
  loading = false,
  nodeId,
  nodeType,
  nodeData,
  workflowId,
  onTest
}: NodeOutputTabProps) {
  const [viewMode, setViewMode] = useState<'table' | 'json' | 'schema'>('table');
  const [copied, setCopied] = useState(false);
  const [testRecords, setTestRecords] = useState<any[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<string>('sample');
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [showRecordSelector, setShowRecordSelector] = useState(false);

  // Fetch test records when pipeline changes or when trigger nodes are selected
  useEffect(() => {
    // Check for pipeline_id in both locations (config and direct)
    const pipelineId = nodeData?.config?.pipeline_id || nodeData?.pipeline_id;

    console.log('NodeOutputTab useEffect triggered:', {
      workflowId,
      pipeline_id: pipelineId,
      nodeType,
      nodeData,
      fullNodeData: JSON.stringify(nodeData)
    });

    // Always show selector if we have a workflow (including new workflows)
    if (workflowId && workflowId !== '') {
      setShowRecordSelector(true);

      // Fetch records if we have a pipeline_id
      if (pipelineId) {
        console.log('Fetching records for pipeline:', pipelineId);
        fetchTestRecords();
      } else {
        console.log('No pipeline_id found in nodeData or nodeData.config');
      }
    } else if (workflowId === 'new' || pipelineId) {
      // For new workflows or when we have a pipeline_id, still show the selector
      setShowRecordSelector(true);

      if (pipelineId) {
        console.log('Fetching records for pipeline:', pipelineId);
        fetchTestRecords();
      }
    } else {
      console.log('No workflowId provided or workflowId is empty');
    }
  }, [nodeData?.config?.pipeline_id, nodeData?.pipeline_id, nodeType, workflowId]);

  const fetchTestRecords = async () => {
    // Check for pipeline_id in both locations
    const pipelineId = nodeData?.config?.pipeline_id || nodeData?.pipeline_id;

    if (!pipelineId) {
      console.log('Missing pipeline_id for fetching records');
      return;
    }

    // Use 'new' for new workflows, or the actual workflowId
    const effectiveWorkflowId = (!workflowId || workflowId === '') ? 'new' : workflowId;

    console.log('Fetching test records with:', {
      effectiveWorkflowId,
      pipeline_id: pipelineId,
      node_type: nodeType
    });

    setLoadingRecords(true);
    try {
      const response = await workflowsApi.getTestRecords(effectiveWorkflowId, {
        pipeline_id: pipelineId,
        node_type: nodeType
      });

      console.log('Test records response:', response.data);

      if (response.data?.records) {
        setTestRecords(response.data.records);
        console.log(`Loaded ${response.data.records.length} records`);

        // Check if this is sample data
        if (response.data.is_sample_data) {
          console.log('Using sample data for testing');
        }

        // Default to sample data if no record is selected
        if (!selectedRecordId || selectedRecordId === '') {
          setSelectedRecordId('sample');
        }
      } else {
        console.log('No records in response');
        setTestRecords([]);
      }
    } catch (error) {
      console.error('Failed to fetch test records:', error);
      setTestRecords([]);
    } finally {
      setLoadingRecords(false);
    }
  };

  const handleTestWithRecord = () => {
    console.log('handleTestWithRecord called with selectedRecordId:', selectedRecordId);
    if (onTest) {
      // Pass the selected record ID, or undefined for sample data
      const recordId = selectedRecordId === 'sample' ? undefined : selectedRecordId;
      console.log('Calling onTest with recordId:', recordId);
      onTest(recordId);
    }
  };

  const formatRecordTitle = (record: any) => {
    const date = new Date(record.created_at).toLocaleDateString();
    return `${record.title} - ${date}`;
  };

  const copyToClipboard = () => {
    const text = JSON.stringify(output, null, 2);
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Output copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  // Process output for table view
  const getTableData = () => {
    if (!output) return { headers: [], rows: [] };

    // If output is an array of objects
    if (Array.isArray(output)) {
      if (output.length === 0) return { headers: [], rows: [] };

      const headers = Object.keys(output[0]);
      const rows = output.map(item =>
        headers.map(header => {
          const value = item[header];
          if (value === null) return 'null';
          if (value === undefined) return 'undefined';
          if (typeof value === 'object') return JSON.stringify(value);
          return String(value);
        })
      );
      return { headers, rows };
    }

    // If output is a single object
    if (typeof output === 'object' && output !== null) {
      const headers = ['Property', 'Value'];
      const rows = Object.entries(output).map(([key, value]) => {
        let displayValue = value;
        if (value === null) displayValue = 'null';
        else if (value === undefined) displayValue = 'undefined';
        else if (typeof value === 'object') displayValue = JSON.stringify(value);
        else displayValue = String(value);

        return [key, displayValue];
      });
      return { headers, rows };
    }

    // For primitive values
    return {
      headers: ['Value'],
      rows: [[String(output)]]
    };
  };

  // Get schema from output
  const getSchema = () => {
    if (!output) return {};

    const analyzeType = (value: any): string => {
      if (value === null) return 'null';
      if (Array.isArray(value)) {
        if (value.length > 0) {
          return `array<${analyzeType(value[0])}>`;
        }
        return 'array';
      }
      if (typeof value === 'object') {
        return 'object';
      }
      return typeof value;
    };

    if (Array.isArray(output) && output.length > 0) {
      const schema: Record<string, Set<string>> = {};
      output.forEach(item => {
        if (typeof item === 'object' && item !== null) {
          Object.entries(item).forEach(([key, value]) => {
            if (!schema[key]) schema[key] = new Set();
            schema[key].add(analyzeType(value));
          });
        }
      });

      return Object.fromEntries(
        Object.entries(schema).map(([key, types]) => [key, Array.from(types).join(' | ')])
      );
    }

    if (typeof output === 'object' && output !== null) {
      return Object.fromEntries(
        Object.entries(output).map(([key, value]) => [key, analyzeType(value)])
      );
    }

    return { value: analyzeType(output) };
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <RefreshCw className="h-8 w-8 animate-spin mb-3" />
        <p className="text-sm">Testing node...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-destructive mb-1">Test Failed</h4>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        </div>

        <div className="text-center py-4">
          <p className="text-sm text-muted-foreground mb-2">
            Fix the configuration and try again
          </p>
        </div>
      </div>
    );
  }

  if (!output) {
    return (
      <div className="space-y-4">
        {/* Record Selector Section */}
        {showRecordSelector && (
          <div className="space-y-4 p-4 bg-muted/30 rounded-lg">
            <div className="space-y-2">
              <Label className="text-sm font-medium">Test Data Source</Label>
              <Select value={selectedRecordId} onValueChange={setSelectedRecordId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a record to use as test data" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sample">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <span>Use Sample Data</span>
                    </div>
                  </SelectItem>
                  {loadingRecords && (
                    <SelectItem value="loading" disabled>
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Loading records...</span>
                      </div>
                    </SelectItem>
                  )}
                  {!loadingRecords && testRecords.length === 0 && (nodeData?.config?.pipeline_id || nodeData?.pipeline_id) && (
                    <SelectItem value="no-records" disabled>
                      <span className="text-muted-foreground">No records found in this pipeline</span>
                    </SelectItem>
                  )}
                  {testRecords.map((record) => (
                    <SelectItem key={record.id} value={record.id}>
                      <div className="flex flex-col">
                        <span className="font-medium">{record.title || `Record ${record.id.slice(-8)}`}</span>
                        {record.preview && Object.keys(record.preview).length > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {Object.entries(record.preview)
                              .slice(0, 2)
                              .map(([k, v]) => `${k}: ${v}`)
                              .join(', ')}
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {selectedRecordId === 'sample'
                  ? 'Using generated sample data for testing'
                  : 'Using actual record data from your pipeline'}
              </p>
            </div>

            <Button
              onClick={handleTestWithRecord}
              className="w-full"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <PlayCircle className="h-4 w-4 mr-2" />
                  Test with {selectedRecordId === 'sample' ? 'Sample Data' : 'Selected Record'}
                </>
              )}
            </Button>
          </div>
        )}

        {/* No output message */}
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <PlayCircle className="h-8 w-8 mb-3 opacity-50" />
          <p className="text-sm font-medium mb-1">No Output Yet</p>
          <p className="text-xs">
            {showRecordSelector
              ? 'Select test data above and click Test to see the output'
              : 'Test the node to see output here'}
          </p>
        </div>
      </div>
    );
  }

  const { headers, rows } = getTableData();
  const schema = getSchema();
  const itemCount = Array.isArray(output) ? output.length : 1;

  return (
    <div className="space-y-4">
      {/* Output Stats */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-xs">
            <Database className="h-3 w-3 mr-1" />
            {itemCount} {itemCount === 1 ? 'item' : 'items'}
          </Badge>
          <Badge variant="secondary" className="text-xs">
            {typeof output === 'object' ? 'Object' : typeof output}
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={copyToClipboard}
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </Button>
      </div>

      {/* View Tabs */}
      <Tabs value={viewMode} onValueChange={(v: any) => setViewMode(v)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="table" className="text-xs">
            <TableIcon className="h-3.5 w-3.5 mr-1" />
            Table
          </TabsTrigger>
          <TabsTrigger value="json" className="text-xs">
            <FileJson className="h-3.5 w-3.5 mr-1" />
            JSON
          </TabsTrigger>
          <TabsTrigger value="schema" className="text-xs">
            <Code className="h-3.5 w-3.5 mr-1" />
            Schema
          </TabsTrigger>
        </TabsList>

        <TabsContent value="table" className="mt-4">
          <div className="border rounded-lg overflow-hidden">
            <ScrollArea className="h-[300px]">
              <table className="w-full">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    {headers.map((header, index) => (
                      <th
                        key={index}
                        className="text-left text-xs font-medium text-muted-foreground px-3 py-2 border-b"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.length === 0 ? (
                    <tr>
                      <td colSpan={headers.length} className="text-center py-4 text-sm text-muted-foreground">
                        No data
                      </td>
                    </tr>
                  ) : (
                    rows.map((row, rowIndex) => (
                      <tr key={rowIndex} className="hover:bg-muted/30">
                        {row.map((cell, cellIndex) => (
                          <td
                            key={cellIndex}
                            className="text-xs px-3 py-2 border-b max-w-[200px] truncate"
                            title={String(cell)}
                          >
                            {String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </ScrollArea>
          </div>
        </TabsContent>

        <TabsContent value="json" className="mt-4">
          <ScrollArea className="h-[300px] border rounded-lg">
            <pre className="p-3 text-xs font-mono whitespace-pre-wrap break-words overflow-wrap-anywhere">
              {JSON.stringify(output, null, 2)}
            </pre>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="schema" className="mt-4">
          <div className="border rounded-lg">
            <ScrollArea className="h-[300px]">
              <table className="w-full">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="text-left text-xs font-medium text-muted-foreground px-3 py-2 border-b">
                      Field
                    </th>
                    <th className="text-left text-xs font-medium text-muted-foreground px-3 py-2 border-b">
                      Type
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(schema).map(([field, type]) => (
                    <tr key={field} className="hover:bg-muted/30">
                      <td className="text-xs font-mono px-3 py-2 border-b">
                        {field}
                      </td>
                      <td className="text-xs px-3 py-2 border-b">
                        <Badge variant="outline" className="text-xs font-mono">
                          {type}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollArea>
          </div>
        </TabsContent>
      </Tabs>

      {/* Output Path Helper */}
      <div className="p-3 bg-muted/50 rounded-lg">
        <p className="text-xs font-medium mb-1.5">Use in next nodes:</p>
        <div className="flex flex-wrap gap-1">
          {Array.isArray(output) && output.length > 0 && typeof output[0] === 'object' ? (
            Object.keys(output[0]).slice(0, 3).map(key => (
              <Badge key={key} variant="secondary" className="text-xs font-mono">
                {`{{node.${key}}}`}
              </Badge>
            ))
          ) : typeof output === 'object' && output !== null ? (
            Object.keys(output).slice(0, 3).map(key => (
              <Badge key={key} variant="secondary" className="text-xs font-mono">
                {`{{node.${key}}}`}
              </Badge>
            ))
          ) : (
            <Badge variant="secondary" className="text-xs font-mono">
              {`{{node.value}}`}
            </Badge>
          )}
          {((Array.isArray(output) && output.length > 0 && Object.keys(output[0]).length > 3) ||
            (typeof output === 'object' && output !== null && Object.keys(output).length > 3)) && (
            <span className="text-xs text-muted-foreground">...</span>
          )}
        </div>
      </div>
    </div>
  );
}