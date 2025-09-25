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
  input_context?: {
    node_type: string;
    node_config: any;
    test_context: any;
    has_trigger_data: boolean;
    has_record_data: boolean;
  };
  processing_metadata?: {
    processor_class: string;
    supports_replay: boolean;
    supports_checkpoints: boolean;
  };
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
  // Removed pipeline selector - always use config pipeline
  const [records, setRecords] = useState<any[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<string>('');
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [testData, setTestData] = useState<any[]>([]);
  const [selectedTestData, setSelectedTestData] = useState<string>('');
  const [testDataType, setTestDataType] = useState<string>('');
  const [loadingTestData, setLoadingTestData] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [lastExecutionInput, setLastExecutionInput] = useState<any>(null);

  // No longer loading pipelines - using config only

  // Load records when config has pipeline
  useEffect(() => {
    const shouldLoadRecords = testConfig?.pipeline_id || testConfig?.pipeline_ids?.length > 0;

    if (shouldLoadRecords) {
      loadRecords();
    }
  }, [testConfig?.pipeline_id, testConfig?.pipeline_ids]);

  // Load test data for triggers
  useEffect(() => {
    if (selectedNode && selectedNode.type && selectedNode.type.toLowerCase().includes('trigger')) {
      const nodeType = selectedNode.type.toLowerCase();

      // Communication triggers (email, linkedin, whatsapp) don't need pipelines
      const isCommunicationTrigger = nodeType.includes('email') ||
                                     nodeType.includes('linkedin') ||
                                     nodeType.includes('whatsapp') ||
                                     nodeType.includes('message');

      // Date reached trigger can work without pipeline when using static dates
      const isDateReachedTrigger = nodeType.includes('date_reached');
      const isUsingDynamicDateField = isDateReachedTrigger && testConfig?.date_field;

      if (isCommunicationTrigger) {
        // Load test data for communication triggers regardless of pipeline
        loadTestData();
      } else if (isDateReachedTrigger && !isUsingDynamicDateField) {
        // Date reached with static date mode - no pipeline needed
        loadTestData();
      } else {
        // Other triggers need a pipeline from config
        const hasPipeline = testConfig?.pipeline_id || testConfig?.pipeline_ids?.length > 0;
        if (hasPipeline) {
          loadTestData();
        }
      }
    }
  }, [
    selectedNode,
    testConfig?.pipeline_id,
    testConfig?.pipeline_ids,  // Also watch pipeline_ids array for record triggers
    testConfig?.form_selection,  // Reload when form selection changes
    testConfig?.mode,  // Reload when form mode changes
    testConfig?.stage,  // Reload when stage changes
    testConfig?.monitor_users,  // Reload when monitor_users changes for communication triggers
    testConfig?.date_field  // Reload when date_field changes for date triggers
  ]);


  // Removed loadPipelines - no longer needed

  const loadRecords = async () => {
    // Determine which pipeline to use from config
    let pipelineToUse: string | null = null;

    // Check both pipeline_id and pipeline_ids from config
    if (testConfig?.pipeline_id) {
      pipelineToUse = String(testConfig.pipeline_id);
    } else if (testConfig?.pipeline_ids && testConfig.pipeline_ids.length > 0) {
      pipelineToUse = String(testConfig.pipeline_ids[0]);
    }

    if (!pipelineToUse) return;

    setLoadingRecords(true);
    try {
      const response = await pipelinesApi.getRecords(pipelineToUse, {
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

  const loadTestData = async () => {
    if (!selectedNode || !selectedNode.type) return;

    const nodeType = selectedNode.type.toLowerCase();

    // Check if this is a communication trigger
    const isCommunicationTrigger = nodeType.includes('email') ||
                                   nodeType.includes('linkedin') ||
                                   nodeType.includes('whatsapp') ||
                                   nodeType.includes('message');

    // Check if this is a date reached trigger
    const isDateReachedTrigger = nodeType.includes('date_reached');
    const isUsingDynamicDateField = isDateReachedTrigger && testConfig?.date_field;

    // Determine which pipeline ID to use from config (if needed)
    let pipelineId = null;

    // Communication triggers and static date triggers don't need a pipeline
    if (!isCommunicationTrigger && !(isDateReachedTrigger && !isUsingDynamicDateField)) {
      // Other triggers and dynamic date triggers need a pipeline
      // Check both pipeline_id and pipeline_ids (some triggers use plural)
      if (testConfig?.pipeline_id) {
        pipelineId = String(testConfig.pipeline_id);
      } else if (testConfig?.pipeline_ids && testConfig.pipeline_ids.length > 0) {
        pipelineId = String(testConfig.pipeline_ids[0]);
      }

      // If no pipeline is available for triggers that need it, don't load test data
      if (!pipelineId) {
        console.log('No pipeline available for loading test data. testConfig:', testConfig);
        setTestData([]);
        setTestDataType('');
        return;
      }
    }

    setLoadingTestData(true);
    try {
      console.log('Loading test data for node type:', selectedNode.type, 'with pipeline:', pipelineId, 'and config:', testConfig);
      const response = await workflowsApi.getTestData({
        node_type: selectedNode.type,
        pipeline_id: pipelineId,
        node_config: testConfig ? JSON.stringify(testConfig) : undefined
      });

      console.log('Test data loaded:', response.data);
      setTestData(response.data.data || []);
      setTestDataType(response.data.data_type || '');
    } catch (error) {
      console.error('Failed to load test data:', error);
      setTestData([]);
      setTestDataType('');
    } finally {
      setLoadingTestData(false);
    }
  };

  const executeNode = async () => {
    if (!selectedNode || !testConfig) return;

    setExecuting(true);
    setTestResult(null);

    try {
      // Build test context
      const testContext: any = {
        pipeline_id: testConfig.pipeline_id,
        ...testConfig
      };

      // Add record data if selected
      let selectedRecordData = null;
      if (selectedRecord && selectedRecord !== 'none') {
        const record = records.find((r: any) => String(r.id) === selectedRecord);
        if (record) {
          testContext.record = record;
          testContext.record_id = record.id;
          testContext.record_data = record.data || {};
          selectedRecordData = record;
        }
      }

      // For triggers with test data, get the actual test data item
      let selectedTestDataItem = null;
      if (selectedTestData && selectedTestData !== 'none' && testData.length > 0) {
        selectedTestDataItem = testData.find((item: any) => String(item.id) === selectedTestData);
      }

      // For triggers with test data, pass the test data ID and type
      const requestData: any = {
        node_type: selectedNode.type,
        node_config: testConfig,
        test_context: testContext,
        test_mode: true // Ensure we're in test mode to prevent side effects
      };

      // Add test data if selected (for triggers)
      if (selectedTestData && selectedTestData !== 'none' && testDataType) {
        requestData.test_data_id = selectedTestData;
        requestData.test_data_type = testDataType;
      }

      // Store input data for display
      const inputData = {
        node_type: selectedNode.type,
        node_config: testConfig,
        test_context: testContext,
        test_data: selectedTestDataItem,
        test_record: selectedRecordData,
        test_data_type: testDataType
      };
      setLastExecutionInput(inputData);

      console.log('Executing node test with data:', requestData);
      const response = await workflowsApi.testNodeStandalone(requestData);
      console.log('Test execution response:', response.data);

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

  const getTriggerTestDataMessage = (nodeType: string): string => {
    const type = nodeType.toLowerCase();

    if (type.includes('webhook')) {
      return 'Webhook triggers require live data. Configure the webhook URL and send a test request to trigger this workflow.';
    }

    if (type.includes('manual')) {
      return 'Manual triggers are activated by users. No test data needed - the trigger will fire when you click "Run Workflow".';
    }

    if (type.includes('scheduled')) {
      return 'No scheduled workflows found. Create a workflow schedule to test scheduled triggers.';
    }

    if (type.includes('date_reached')) {
      return 'No records with date fields found. Select a pipeline with records containing date fields to test this trigger.';
    }

    if (type.includes('pipeline_stage')) {
      return 'No records with stage changes found. Select a pipeline with records that have stage fields to test this trigger.';
    }

    if (type.includes('workflow_completed')) {
      return 'No completed workflow executions found. Run a workflow to create test data for this trigger.';
    }

    if (type.includes('condition_met')) {
      return 'No records available to test conditions. Select a pipeline with records to evaluate condition triggers.';
    }

    if (type.includes('email')) {
      return 'No email messages found. Send or receive emails to create test data for this trigger.';
    }

    if (type.includes('linkedin') || type.includes('whatsapp')) {
      return `No ${type.includes('linkedin') ? 'LinkedIn' : 'WhatsApp'} messages found. Send or receive messages to create test data.`;
    }

    if (type.includes('form')) {
      return 'No form submissions found. Submit a form or select a pipeline with records to test this trigger.';
    }

    if (type.includes('record')) {
      return 'No records found in the selected pipeline. Create records to test this trigger.';
    }

    return 'No test data available for this trigger type. Configure the trigger settings to proceed.';
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
          {/* Test Data Selection for Triggers */}
          {selectedNode?.type?.toLowerCase().includes('trigger') && (
            <div className="space-y-2">
              <Label>
                Select Test Data for Trigger
                {testConfig?.pipeline_id && (
                  <span className="text-xs text-muted-foreground ml-2">
                    (using pipeline from config)
                  </span>
                )}
              </Label>

              {loadingTestData ? (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Loading available test data...
                  </AlertDescription>
                </Alert>
              ) : testData.length > 0 ? (
                <>
                  <Select
                    value={selectedTestData}
                    onValueChange={setSelectedTestData}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Choose test data to simulate trigger" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No test data (show configuration only)</SelectItem>
                      {testData.map((item: any) => (
                        <SelectItem key={item.id} value={String(item.id)}>
                          <div className="flex flex-col">
                            <span>{item.title}</span>
                            {item.preview && (
                              <span className="text-xs text-muted-foreground">
                                {item.preview.from || item.preview.subject || Object.values(item.preview)[0]}
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {testDataType && (
                    <p className="text-sm text-muted-foreground">
                      Test data type: {testDataType}
                    </p>
                  )}
                </>
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {getTriggerTestDataMessage(selectedNode.type)}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {/* Record Selection for non-trigger nodes */}
          {testConfig?.pipeline_id && !selectedNode?.type?.toLowerCase().includes('trigger') && (
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
        <div className="space-y-4">
          {/* Results Header Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center justify-between">
                Test Results
                <div className="flex items-center gap-2">
                  {testResult.execution_time && (
                    <div className="flex items-center gap-1 text-sm text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      <span>{testResult.execution_time.toFixed(2)}ms</span>
                    </div>
                  )}
                  <Badge variant={
                    testResult.status === 'success' ? 'default' :
                    testResult.status === 'warning' ? 'secondary' :
                    'destructive'
                  }>
                    {testResult.status}
                  </Badge>
                </div>
              </CardTitle>
            </CardHeader>
            {/* Error Display */}
            {testResult.error && (
              <CardContent className="pt-0">
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
              </CardContent>
            )}

          </Card>

          {/* 3-Panel Grid Layout */}
          {!testResult.error && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
              {/* Input Panel */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Input
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {testResult?.input_context?.has_trigger_data ? 'Trigger' :
                       testResult?.input_context?.has_record_data ? 'Record' :
                       lastExecutionInput?.test_data ? 'Test Data' :
                       lastExecutionInput?.test_record ? 'Record' :
                       'Config'}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Node Configuration */}
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">Configuration</div>
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap bg-muted p-2 rounded">
                        {JSON.stringify(lastExecutionInput?.node_config || {}, null, 2)}
                      </pre>
                    </div>

                    {/* Test Data */}
                    {(lastExecutionInput?.test_data || lastExecutionInput?.test_record) && (
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground mb-1">
                          {lastExecutionInput.test_data ? `Test Data (${lastExecutionInput.test_data_type})` : 'Test Record'}
                        </div>
                        <pre className="text-xs overflow-x-auto whitespace-pre-wrap bg-muted p-2 rounded">
                          {JSON.stringify(lastExecutionInput.test_data || lastExecutionInput.test_record, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Context */}
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">Context</div>
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap bg-muted p-2 rounded">
                        {JSON.stringify(
                          testResult?.input_context?.test_context || lastExecutionInput?.test_context || {},
                          null,
                          2
                        )}
                      </pre>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Processing Panel */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <RefreshCw className="h-4 w-4" />
                      Processing
                    </div>
                    {testResult?.processing_metadata && (
                      <Badge variant="outline" className="text-xs">
                        {testResult.processing_metadata.processor_class}
                      </Badge>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-xs">
                    {/* Node Info */}
                    <div>
                      <div className="font-semibold text-muted-foreground mb-2">Node Type</div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{selectedNode.type}</Badge>
                        {testResult?.processing_metadata && (
                          <div className="flex gap-1">
                            {testResult.processing_metadata.supports_replay && (
                              <Badge variant="outline" className="text-xs">
                                <RefreshCw className="h-3 w-3" />
                              </Badge>
                            )}
                            {testResult.processing_metadata.supports_checkpoints && (
                              <Badge variant="outline" className="text-xs">
                                <CheckCircle className="h-3 w-3" />
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Processing Steps */}
                    <div>
                      <div className="font-semibold text-muted-foreground mb-2">Processing Steps</div>
                      <ol className="space-y-1 list-decimal list-inside text-xs">
                        {selectedNode.type.startsWith('trigger_') ? (
                          <>
                            <li>Event detected/simulated</li>
                            <li>Data loaded & validated</li>
                            <li>Conditions evaluated</li>
                            <li>Output prepared</li>
                          </>
                        ) : selectedNode.type.includes('record_') ? (
                          <>
                            <li>Pipeline context loaded</li>
                            <li>Config validated</li>
                            <li>DB operation executed</li>
                            <li>Result formatted</li>
                          </>
                        ) : selectedNode.type.includes('ai_') ? (
                          <>
                            <li>Prompt processed</li>
                            <li>Variables substituted</li>
                            <li>AI model invoked</li>
                            <li>Response parsed</li>
                          </>
                        ) : selectedNode.type.includes('send_') || selectedNode.type.includes('email') ? (
                          <>
                            <li>Template loaded</li>
                            <li>Variables replaced</li>
                            <li>Channel formatting</li>
                            <li>Message queued</li>
                          </>
                        ) : selectedNode.type.includes('condition') || selectedNode.type.includes('wait') ? (
                          <>
                            <li>Conditions evaluated</li>
                            <li>Branch calculated</li>
                            <li>Path determined</li>
                            <li>State updated</li>
                          </>
                        ) : (
                          <>
                            <li>Config parsed</li>
                            <li>Input validated</li>
                            <li>Logic executed</li>
                            <li>Output generated</li>
                          </>
                        )}
                      </ol>
                    </div>

                    {/* Data Flow */}
                    <div>
                      <div className="font-semibold text-muted-foreground mb-2">Data Flow</div>
                      <div className="flex items-center justify-center gap-2 text-xs bg-muted p-2 rounded">
                        <span>Input</span>
                        <ChevronRight className="h-3 w-3" />
                        <Badge variant="default" className="text-xs">
                          {selectedNode.label || selectedNode.type}
                        </Badge>
                        <ChevronRight className="h-3 w-3" />
                        <span>Output</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Output Panel */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Output
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {testResult.output ? 'Data' : 'Empty'}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Identifiers Section - Highlighted */}
                    {testResult.output && (testResult.output.entity_id || testResult.output.entity_ids ||
                      testResult.output.record_id || testResult.output.related_ids) && (
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground mb-1 flex items-center gap-1">
                          <Badge variant="default" className="text-xs">IDs</Badge>
                          Identifiable Data
                        </div>
                        <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 p-2 rounded text-xs space-y-1">
                          {testResult.output.entity_type && (
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">Entity Type:</span>
                              <Badge variant="secondary" className="text-xs">{testResult.output.entity_type}</Badge>
                            </div>
                          )}
                          {testResult.output.entity_id && (
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">Primary ID:</span>
                              <code className="bg-white dark:bg-gray-900 px-1 py-0.5 rounded">{testResult.output.entity_id}</code>
                            </div>
                          )}
                          {testResult.output.entity_ids && (
                            <div className="flex items-start gap-2">
                              <span className="font-semibold">IDs:</span>
                              <div className="flex flex-wrap gap-1">
                                {testResult.output.entity_ids.map((id: string, idx: number) => (
                                  <code key={idx} className="bg-white dark:bg-gray-900 px-1 py-0.5 rounded">{id}</code>
                                ))}
                              </div>
                            </div>
                          )}
                          {testResult.output.record_id && (
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">Record ID:</span>
                              <code className="bg-white dark:bg-gray-900 px-1 py-0.5 rounded">{testResult.output.record_id}</code>
                            </div>
                          )}
                          {testResult.output.pipeline_id && (
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">Pipeline ID:</span>
                              <code className="bg-white dark:bg-gray-900 px-1 py-0.5 rounded">{testResult.output.pipeline_id}</code>
                            </div>
                          )}
                          {testResult.output.related_ids && Object.keys(testResult.output.related_ids).length > 0 && (
                            <div className="mt-2 pt-2 border-t border-blue-200 dark:border-blue-800">
                              <div className="font-semibold mb-1">Related IDs:</div>
                              {Object.entries(testResult.output.related_ids).map(([key, value]) => value && (
                                <div key={key} className="flex items-center gap-2 ml-2">
                                  <span className="text-muted-foreground">{key}:</span>
                                  {Array.isArray(value) ? (
                                    <div className="flex flex-wrap gap-1">
                                      {value.map((v: string, idx: number) => (
                                        <code key={idx} className="bg-white dark:bg-gray-900 px-1 py-0.5 rounded text-xs">{v}</code>
                                      ))}
                                    </div>
                                  ) : (
                                    <code className="bg-white dark:bg-gray-900 px-1 py-0.5 rounded text-xs">{String(value)}</code>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Main Output */}
                    {testResult.output !== undefined && (
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground mb-1">Full Output Data</div>
                        <pre className="text-xs overflow-x-auto whitespace-pre-wrap bg-muted p-2 rounded">
                          {JSON.stringify(testResult.output, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Side Effects */}
                    {testResult.side_effects && testResult.side_effects.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground mb-1">
                          Side Effects ({testResult.side_effects.length})
                        </div>
                        <div className="space-y-1">
                          {testResult.side_effects.map((effect, idx) => (
                            <div key={idx} className="flex items-start gap-2 p-2 bg-muted rounded text-xs">
                              {getSideEffectIcon(effect.type)}
                              <div className="flex-1">
                                <div className="font-medium">{effect.type}</div>
                                <div className="text-muted-foreground">{effect.description}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Logs */}
                    {testResult.logs && testResult.logs.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold text-muted-foreground mb-1">
                          Execution Logs ({testResult.logs.length})
                        </div>
                        <div className="space-y-1 bg-muted p-2 rounded">
                          {testResult.logs.map((log, idx) => (
                            <div key={idx} className="flex items-start gap-2 text-xs font-mono">
                              <span className={cn('font-semibold', getLogLevelColor(log.level))}>
                                [{log.level}]
                              </span>
                              <span className="flex-1">{log.message}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}