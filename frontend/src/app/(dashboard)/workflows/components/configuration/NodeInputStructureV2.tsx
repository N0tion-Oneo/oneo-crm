/**
 * NodeInputStructureV2
 * Enhanced input data display using hierarchical table view
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Code2,
  Database,
  AlertCircle,
  Copy,
  Loader2,
  User,
  ArrowRight
} from 'lucide-react';
import { toast } from 'sonner';
import { DataTableView } from './DataTableView';

interface NodeInputStructureV2Props {
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
  nodeType?: string;
}

export function NodeInputStructureV2({
  sources,
  testData,
  isTriggerNode,
  testDataList = [],
  testDataType = '',
  selectedTestData,
  onTestDataChange,
  useRealData = false,
  onUseRealDataChange,
  loadingTestData = false,
  nodeType
}: NodeInputStructureV2Props) {
  const [loading, setLoading] = useState(false);

  // Prepare input data for display
  const inputData = useMemo(() => {
    if (isTriggerNode) {
      // For trigger nodes, we need to show the proper trigger output structure
      if (useRealData && selectedTestData) {
        // When using real data, we need to format it as trigger output
        // The testData from getDefaultNodeOutputs already has the right structure
        // But we need to inject the real selected test data into the record field
        if (testData && typeof testData === 'object' && 'record' in testData) {
          // Use the trigger structure from testData but with real record data
          return {
            ...testData,
            record: selectedTestData,
            // For record_updated trigger, also set previous_record
            ...(nodeType?.includes('record_updated') ? {
              previous_record: selectedTestData
            } : {})
          };
        }
        // Fallback if testData structure is not available
        return {
          trigger: selectedTestData
        };
      } else if (testData) {
        // Mock data - already properly structured from getDefaultNodeOutputs
        return testData;
      }
    } else if (sources && sources.length > 0) {
      // Combine data from multiple sources
      if (sources.length === 1) {
        // Single source - show data directly, but still indicate the source node
        const source = sources[0];
        // For single source, we can show the data directly without nesting
        // but let's add a reference to which node it came from
        return source.data || {};
      } else {
        // Multiple sources - group by node with clear labeling
        const grouped: any = {};
        sources.forEach((source, index) => {
          if (source.data) {
            // Create a descriptive key for each source node
            // Format: "NodeLabel (node_id)" or just "NodeLabel" if id matches label
            const nodeKey = source.label || `Node_${index + 1}`;
            const nodeIdentifier = source.nodeId && source.nodeId !== source.label
              ? `${nodeKey}_${source.nodeId.substring(0, 8)}`
              : nodeKey;

            grouped[nodeIdentifier] = source.data;
          }
        });
        return grouped;
      }
    }
    return null;
  }, [sources, testData, isTriggerNode, useRealData, selectedTestData, nodeType]);

  // Helper to get test data display name
  const getTestDataDisplayName = (data: any, dataType: string): string => {
    if (!data) return 'Test Data';

    // Handle different data types
    if (dataType === 'email' || dataType === 'email_message') {
      if (data.subject) return data.subject;
      if (data.from) return `Email from ${data.from}`;
      return 'Email Message';
    }

    if (dataType === 'linkedin_message' || dataType === 'whatsapp_message') {
      const platform = dataType.includes('linkedin') ? 'LinkedIn' : 'WhatsApp';
      if (data.from) return `${platform} from ${data.from}`;
      if (data.message) return data.message.substring(0, 50);
      return `${platform} Message`;
    }

    if (dataType === 'webhook') {
      if (data.method && data.path) return `${data.method} ${data.path}`;
      return 'Webhook Data';
    }

    if (dataType === 'form_submission') {
      if (data.form_name) return `Form: ${data.form_name}`;
      return 'Form Submission';
    }

    // Default record handling
    if (data.title || data.display_name || data.name) {
      return data.title || data.display_name || data.name;
    }

    if (data.data?.name || data.data?.title) {
      return data.data.name || data.data.title;
    }

    return `Record ${data.id || ''}`;
  };

  // Copy sample JSON
  const copySampleInput = () => {
    if (inputData) {
      navigator.clipboard.writeText(JSON.stringify(inputData, null, 2));
      toast.success('Sample input copied to clipboard');
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
                            return (
                              <SelectItem key={item.id} value={String(item.id)}>
                                <div className="flex items-center gap-2">
                                  <User className="h-3 w-3" />
                                  <span className="font-medium">{displayName}</span>
                                </div>
                              </SelectItem>
                            );
                          })}
                        </SelectContent>
                      </Select>

                      {/* Preview selected data */}
                      {selectedTestData && testDataType === 'form_submission' && selectedTestData.preview?.submitted_data && (
                        <div className="mt-2 p-2 bg-muted/50 rounded-md">
                          <div className="text-xs text-muted-foreground mb-1">Form Data Preview:</div>
                          <div className="space-y-1">
                            {Object.entries(selectedTestData.preview.submitted_data).slice(0, 3).map(([key, value]: [string, any]) => (
                              <div key={key} className="flex items-start gap-2 text-xs">
                                <span className="font-medium text-muted-foreground">{key}:</span>
                                <span className="text-foreground">
                                  {typeof value === 'object' ? JSON.stringify(value).substring(0, 50) : String(value).substring(0, 50)}
                                </span>
                              </div>
                            ))}
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
                  No test data available. Configure the trigger to load test data.
                </div>
              )}
            </Card>
          </div>

          <Separator />
        </>
      )}

      {/* Section 2: Input Structure - Now using DataTableView */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
          <h3 className="font-semibold text-sm">Input Data</h3>
          {sources.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {sources.length} {sources.length === 1 ? 'source' : 'sources'}
            </Badge>
          )}
        </div>

        {/* Show source nodes when there are any */}
        {sources.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-muted-foreground mb-2">Available data from upstream nodes:</div>
            <div className="flex flex-wrap gap-2">
              {sources.map((source, index) => (
                <Badge
                  key={source.nodeId || index}
                  variant={source.isDirectConnection ? "default" : "outline"}
                  className="text-xs"
                  title={source.isDirectConnection ? "Direct connection" : `${source.depth} levels upstream`}
                >
                  <Database className="h-3 w-3 mr-1" />
                  {source.label || `Node ${index + 1}`}
                  {!source.isDirectConnection && (
                    <span className="ml-1 text-[10px] opacity-60">
                      ({source.depth} levels up)
                    </span>
                  )}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {loading ? (
          <Card className="p-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </Card>
        ) : inputData ? (
          <DataTableView
            data={inputData}
            title=""
            initialExpanded="first-level"
            showSearch={true}
            showTypeColumn={true}
            showCopyButtons={true}
            maxHeight="350px"
            onFieldCopy={(path, value) => {
              // Field path already copied by DataTableView
              // Can add additional handling here if needed
            }}
          />
        ) : (
          <Card className="p-8">
            <div className="text-center text-muted-foreground">
              <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No input data</p>
              <p className="text-xs mt-1">
                {isTriggerNode
                  ? 'This is a trigger node - it starts the workflow'
                  : 'Connect nodes to provide input data'}
              </p>
            </div>
          </Card>
        )}
      </div>

      <Separator />

      {/* Section 3: Sample Input (JSON) */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium">Sample Input</h4>
            {inputData && (
              <Badge variant="secondary" className="text-xs">
                JSON
              </Badge>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={copySampleInput}
            disabled={!inputData || loading}
            className="h-6 text-xs px-2"
          >
            <Copy className="h-3 w-3 mr-1" />
            Copy JSON
          </Button>
        </div>

        <Card className="p-3 bg-muted/30">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/6" />
            </div>
          ) : (
            <ScrollArea className="h-[200px]">
              <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                {inputData ? JSON.stringify(inputData, null, 2) : 'No input data available'}
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
              {isTriggerNode ? (
                <code className="ml-1 font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded">
                  {'{{trigger.record.id}}'}, {'{{trigger.pipeline_id}}'}
                </code>
              ) : sources.length > 1 ? (
                <>
                  <br />
                  {sources.map((source, index) => (
                    <code key={source.nodeId || index} className="ml-1 font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded text-[10px]">
                      {`{{${source.label || `Node_${index + 1}`}.field}}`}{index < sources.length - 1 ? ', ' : ''}
                    </code>
                  ))}
                </>
              ) : (
                <code className="ml-1 font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded">
                  {sources.length > 0 && sources[0].nodeId
                    ? `{{${sources[0].nodeId}.field}}`
                    : '{{nodeId.field}}'}
                </code>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}