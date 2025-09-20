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
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['output', 'side_effects']));

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
      if (selectedRecord && selectedRecord !== 'none') {
        const record = records.find((r: any) => String(r.id) === selectedRecord);
        if (record) {
          testContext.record = record;
          testContext.record_id = record.id;
          testContext.record_data = record.data || {};
        }
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

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
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