'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Database,
  Mail,
  MessageSquare,
  FileText,
  Play,
  RefreshCw
} from 'lucide-react';
import { workflowsApi, pipelinesApi } from '@/lib/api';
import { cn } from '@/lib/utils';

interface TestResult {
  status: 'success' | 'error' | 'warning';
  output?: any;
  side_effects?: Array<{
    type: string;
    description: string;
  }>;
  logs?: Array<{
    level: string;
    message: string;
    timestamp: string;
  }>;
  execution_time?: number;
  error?: {
    type: string;
    message: string;
    traceback?: string;
  };
}

interface NodeExecutionResultsProps {
  selectedNode: any;
  testConfig: any;
  onExecute?: () => void;
}

export function NodeExecutionResults({
  selectedNode,
  testConfig,
  onExecute
}: NodeExecutionResultsProps) {
  const [selectedPipeline, setSelectedPipeline] = useState<string>('config');
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [records, setRecords] = useState<any[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<string>('');
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['output', 'side_effects']));

  // Load pipelines on mount
  useEffect(() => {
    loadPipelines();
  }, []);

  // Load records when pipeline is selected
  useEffect(() => {
    if (selectedPipeline && selectedPipeline !== 'config') {
      loadRecords();
    }
  }, [selectedPipeline]);


  const loadPipelines = async () => {
    try {
      const response = await pipelinesApi.list();
      setPipelines(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to load pipelines:', error);
      setPipelines([]);
    }
  };

  const loadRecords = async () => {
    if (!selectedPipeline || selectedPipeline === 'config') return;

    setLoadingRecords(true);
    try {
      const response = await pipelinesApi.getRecords(selectedPipeline, {
        page_size: 50,
        ordering: '-created_at'
      });
      setRecords(response.data.results || []);
    } catch (error) {
      console.error('Failed to load records:', error);
      setRecords([]);
    } finally {
      setLoadingRecords(false);
    }
  };

  const executeNode = async () => {
    if (!selectedNode || !testConfig) return;

    setExecuting(true);
    setTestResult(null);

    try {
      // Build test context
      const testContext: any = {
        pipeline_id: selectedPipeline === 'config' ? testConfig.pipeline_id : selectedPipeline,
        ...testConfig
      };

      // Add record data if selected
      if (selectedRecord && selectedRecord !== 'none') {
        const record = records.find((r: any) => String(r.id) === selectedRecord);
        if (record) {
          testContext.record = record;
          testContext.record_id = record.id;
          testContext.record_data = record.data || {};
        }
      }

      const response = await workflowsApi.testNodeStandalone({
        node_type: selectedNode.type,
        node_config: testConfig,
        test_context: testContext,
        test_mode: true // Ensure we're in test mode to prevent side effects
      });

      setTestResult(response.data);

      // Call the onExecute callback if provided
      if (onExecute) {
        onExecute();
      }
    } catch (error: any) {
      console.error('Node execution failed:', error);
      setTestResult({
        status: 'error',
        error: {
          type: 'ExecutionError',
          message: error.response?.data?.detail || error.message || 'Execution failed',
          traceback: error.response?.data?.traceback
        }
      });
    } finally {
      setExecuting(false);
    }
  };

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const getSideEffectIcon = (type: string) => {
    switch (type) {
      case 'email': return <Mail className="h-4 w-4" />;
      case 'sms': return <MessageSquare className="h-4 w-4" />;
      case 'record_created': return <Database className="h-4 w-4" />;
      case 'task_created': return <FileText className="h-4 w-4" />;
      default: return <AlertCircle className="h-4 w-4" />;
    }
  };

  const getLogLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error': return 'text-red-600';
      case 'warning': return 'text-yellow-600';
      case 'info': return 'text-blue-600';
      case 'debug': return 'text-gray-500';
      default: return 'text-gray-700';
    }
  };

  return (
    <div className="space-y-4">
      {/* Test Setup */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Test Execution Setup</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Pipeline Selection */}
          <div className="space-y-2">
            <Label>Select Test Pipeline (Optional)</Label>
            <Select value={selectedPipeline} onValueChange={setSelectedPipeline}>
              <SelectTrigger>
                <SelectValue placeholder="Use config pipeline or select test data source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="config">Use pipeline from config</SelectItem>
                {pipelines.map((pipeline: any) => (
                  <SelectItem key={pipeline.id} value={pipeline.id}>
                    {pipeline.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Record Selection */}
          {selectedPipeline && selectedPipeline !== 'config' && (
            <div className="space-y-2">
              <Label>Select Test Record (Optional)</Label>
              <Select
                value={selectedRecord}
                onValueChange={setSelectedRecord}
                disabled={loadingRecords}
              >
                <SelectTrigger>
                  <SelectValue placeholder={loadingRecords ? "Loading records..." : "Choose a record or use sample data"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No record (use sample data)</SelectItem>
                  {records.map((record: any) => {
                    // Try to find a meaningful display value from the record data
                    const displayValue =
                      record.title ||  // Check for title at root level
                      record.name ||   // Check for name at root level
                      record.data?.title ||
                      record.data?.name ||
                      record.data?.subject ||
                      record.data?.label ||
                      record.data?.email ||
                      record.data?.company ||
                      record.data?.description?.substring(0, 50) ||
                      `Record ${String(record.id).slice(0, 8)}`;

                    return (
                      <SelectItem key={record.id} value={String(record.id)}>
                        {displayValue}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Execute Button */}
          <Button
            onClick={executeNode}
            disabled={executing || !selectedNode}
            className="w-full"
          >
            {executing ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Execute Node Test
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Test Results */}
      {testResult && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center justify-between">
              Test Results
              <Badge variant={
                testResult.status === 'success' ? 'default' :
                testResult.status === 'warning' ? 'secondary' :
                'destructive'
              }>
                {testResult.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Execution Time */}
            {testResult.execution_time && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                Executed in {testResult.execution_time.toFixed(2)}ms
              </div>
            )}

            {/* Error Display */}
            {testResult.error && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-2">
                    <div className="font-semibold">{testResult.error.type}</div>
                    <div>{testResult.error.message}</div>
                    {testResult.error.traceback && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-sm">Stack Trace</summary>
                        <pre className="mt-2 text-xs overflow-x-auto whitespace-pre-wrap">
                          {testResult.error.traceback}
                        </pre>
                      </details>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Output Section */}
            {testResult.output !== undefined && (
              <div className="space-y-2">
                <button
                  onClick={() => toggleSection('output')}
                  className="flex items-center gap-2 text-sm font-medium w-full"
                >
                  {expandedSections.has('output') ?
                    <ChevronDown className="h-4 w-4" /> :
                    <ChevronRight className="h-4 w-4" />
                  }
                  Output
                </button>
                {expandedSections.has('output') && (
                  <div className="bg-muted p-3 rounded-lg">
                    <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(testResult.output, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Side Effects */}
            {testResult.side_effects && testResult.side_effects.length > 0 && (
              <div className="space-y-2">
                <button
                  onClick={() => toggleSection('side_effects')}
                  className="flex items-center gap-2 text-sm font-medium w-full"
                >
                  {expandedSections.has('side_effects') ?
                    <ChevronDown className="h-4 w-4" /> :
                    <ChevronRight className="h-4 w-4" />
                  }
                  Side Effects ({testResult.side_effects.length})
                </button>
                {expandedSections.has('side_effects') && (
                  <div className="space-y-2">
                    {testResult.side_effects.map((effect, idx) => (
                      <div key={idx} className="flex items-start gap-2 p-2 bg-muted rounded">
                        {getSideEffectIcon(effect.type)}
                        <div className="flex-1">
                          <div className="text-xs font-medium">{effect.type}</div>
                          <div className="text-xs text-muted-foreground">{effect.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Logs */}
            {testResult.logs && testResult.logs.length > 0 && (
              <div className="space-y-2">
                <button
                  onClick={() => toggleSection('logs')}
                  className="flex items-center gap-2 text-sm font-medium w-full"
                >
                  {expandedSections.has('logs') ?
                    <ChevronDown className="h-4 w-4" /> :
                    <ChevronRight className="h-4 w-4" />
                  }
                  Logs ({testResult.logs.length})
                </button>
                {expandedSections.has('logs') && (
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {testResult.logs.map((log, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-xs font-mono">
                        <span className={cn('font-semibold', getLogLevelColor(log.level))}>
                          [{log.level}]
                        </span>
                        <span className="text-muted-foreground">{log.timestamp}</span>
                        <span className="flex-1">{log.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}