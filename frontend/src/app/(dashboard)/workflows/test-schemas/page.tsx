'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { WorkflowNodeType } from '../types';
import { workflowSchemaService } from '@/services/workflowSchemaService';
import { UnifiedConfigRenderer } from '../components/node-configs/unified/UnifiedConfigRenderer';
import { useNodeConfig } from '../components/node-configs/unified/useNodeConfig';
import { api } from '@/lib/api';
import { useWorkflowData } from '../hooks/useWorkflowData';

// Test node types that have backend schemas
const TEST_NODE_TYPES = [
  // Triggers
  { type: WorkflowNodeType.TRIGGER_MANUAL, label: 'Manual Trigger', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_RECORD_CREATED, label: 'Record Created', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_RECORD_UPDATED, label: 'Record Updated', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_RECORD_DELETED, label: 'Record Deleted', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_FORM_SUBMITTED, label: 'Form Submitted', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_SCHEDULED, label: 'Scheduled', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_WEBHOOK, label: 'Webhook', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_EMAIL_RECEIVED, label: 'Email Received', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_LINKEDIN_MESSAGE, label: 'LinkedIn Message', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_WHATSAPP_MESSAGE, label: 'WhatsApp Message', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_DATE_REACHED, label: 'Date Reached', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_PIPELINE_STAGE_CHANGED, label: 'Pipeline Stage Changed', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_WORKFLOW_COMPLETED, label: 'Workflow Completed', category: 'Triggers' },
  { type: WorkflowNodeType.TRIGGER_CONDITION_MET, label: 'Condition Met', category: 'Triggers' },
  // Data operations
  { type: WorkflowNodeType.RECORD_CREATE, label: 'Record Create', category: 'Data' },
  { type: WorkflowNodeType.RECORD_UPDATE, label: 'Record Update', category: 'Data' },
  { type: WorkflowNodeType.RECORD_FIND, label: 'Record Find', category: 'Data' },
  { type: WorkflowNodeType.RECORD_DELETE, label: 'Record Delete', category: 'Data' },
  // AI operations
  { type: WorkflowNodeType.AI_PROMPT, label: 'AI Prompt', category: 'AI' },
  { type: WorkflowNodeType.AI_ANALYSIS, label: 'AI Analysis', category: 'AI' },
  { type: WorkflowNodeType.AI_MESSAGE_GENERATOR, label: 'AI Message Generator', category: 'AI' },
  { type: WorkflowNodeType.AI_RESPONSE_EVALUATOR, label: 'AI Response Evaluator', category: 'AI' },
  { type: WorkflowNodeType.AI_CONVERSATION_LOOP, label: 'AI Conversation Loop', category: 'AI' },
  // Communication
  { type: WorkflowNodeType.UNIPILE_SEND_EMAIL, label: 'Send Email', category: 'Communication' },
  { type: WorkflowNodeType.UNIPILE_SEND_SMS, label: 'Send SMS', category: 'Communication' },
  { type: WorkflowNodeType.UNIPILE_SEND_WHATSAPP, label: 'Send WhatsApp', category: 'Communication' },
  { type: WorkflowNodeType.UNIPILE_SEND_LINKEDIN, label: 'Send LinkedIn', category: 'Communication' },
  // Control flow
  { type: WorkflowNodeType.CONDITION, label: 'Condition', category: 'Control' },
  { type: WorkflowNodeType.FOR_EACH, label: 'For Each', category: 'Control' },
  { type: WorkflowNodeType.WAIT_DELAY, label: 'Wait/Delay', category: 'Control' },
  // External
  { type: WorkflowNodeType.HTTP_REQUEST, label: 'HTTP Request', category: 'External' },
  { type: WorkflowNodeType.WEBHOOK_OUT, label: 'Webhook Out', category: 'External' },
  // CRM
  { type: WorkflowNodeType.CREATE_FOLLOW_UP_TASK, label: 'Follow Up Task', category: 'CRM' },
  { type: WorkflowNodeType.UPDATE_CONTACT_STATUS, label: 'Update Contact Status', category: 'CRM' },
  { type: WorkflowNodeType.RESOLVE_CONTACT, label: 'Resolve Contact', category: 'CRM' },
];

export default function TestSchemasPage() {
  const [selectedNode, setSelectedNode] = useState(TEST_NODE_TYPES[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendSchema, setBackendSchema] = useState<any>(null);
  const [transformedConfig, setTransformedConfig] = useState<any>(null);
  const [testConfig, setTestConfig] = useState<any>({});
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Fetch real data using the hook
  const {
    pipelines,
    users,
    userTypes,
    pipelineFields,
    fetchPipelineFields,
    loading: dataLoading,
    error: dataError
  } = useWorkflowData();

  // Fetch raw backend schemas
  const fetchBackendSchemas = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/v1/workflows/node_schemas/');
      const schemas = response.data;
      // Since we standardized to lowercase, use the type directly
      const nodeSchema = schemas[selectedNode.type];

      if (nodeSchema) {
        setBackendSchema(nodeSchema);
      } else {
        setError(`No backend schema found for ${selectedNode.type}`);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch schemas');
    } finally {
      setLoading(false);
    }
  };

  // Transform schema using backend service only
  const transformSchema = async () => {
    setLoading(true);
    setError(null);
    try {
      // Always use backend transformation - single source of truth
      console.log(`Fetching config for ${selectedNode.type} from backend`);
      const config = await workflowSchemaService.getNodeConfig(selectedNode.type);
      setTransformedConfig(config);

      // Set default values
      if (config?.defaults) {
        setTestConfig(config.defaults);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to transform schema');
    } finally {
      setLoading(false);
    }
  };

  // Load both when node changes
  useEffect(() => {
    fetchBackendSchemas();
    transformSchema();
  }, [selectedNode]);

  // Run validation
  useEffect(() => {
    if (transformedConfig?.validate) {
      const errors = transformedConfig.validate(testConfig);
      setValidationErrors(errors || {});
    }
  }, [testConfig, transformedConfig]);

  const handleRefresh = () => {
    workflowSchemaService.clearCache();
    fetchBackendSchemas();
    transformSchema();
  };

  const getFieldCount = (schema: any) => {
    if (!schema?.config_schema?.properties) return 0;
    return Object.keys(schema.config_schema.properties).length;
  };

  const getRequiredCount = (schema: any) => {
    if (!schema?.config_schema?.required) return 0;
    return schema.config_schema.required.length;
  };

  return (
    <div className="container mx-auto p-6 max-w-full">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Backend Schema Test Page</h1>
        <p className="text-muted-foreground">
          Test and verify that backend schemas are correctly fetched and transformed for the frontend.
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main content area with three-column layout */}
      <div className="flex flex-col xl:flex-row gap-6">
        {/* Left sidebar - Node Type Selector */}
        <Card className="w-full xl:w-72 h-fit flex-shrink-0">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Select Node Type</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Group nodes by category */}
            <div className="space-y-3">
              {['Triggers', 'Data', 'AI', 'Communication', 'Control', 'External', 'CRM'].map(category => {
                const categoryNodes = TEST_NODE_TYPES.filter(n => n.category === category);
                if (categoryNodes.length === 0) return null;

                return (
                  <div key={category}>
                    <h4 className="text-xs font-semibold text-muted-foreground mb-1">{category}</h4>
                    <div className="flex flex-col gap-0.5">
                      {categoryNodes.map((node) => (
                        <Button
                          key={node.type}
                          variant={selectedNode.type === node.type ? 'default' : 'ghost'}
                          size="sm"
                          className="justify-start text-sm h-8"
                          onClick={() => setSelectedNode(node)}
                        >
                          {node.label}
                        </Button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
            <Button
              onClick={handleRefresh}
              variant="outline"
              size="sm"
              className="mt-4 w-full"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Clear Cache & Refresh
            </Button>
          </CardContent>
        </Card>

        {/* Middle content area - Tabs */}
        <div className="flex-1 min-w-0">
          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center p-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-2">Loading schemas...</span>
            </div>
          )}

          {/* Schema Information Tabs */}
          {!loading && (
            <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="raw">Raw Backend Schema</TabsTrigger>
            <TabsTrigger value="transformed">Transformed Config</TabsTrigger>
            <TabsTrigger value="validation">Validation Test</TabsTrigger>
            <TabsTrigger value="batch">Test All Nodes</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <Card>
              <CardHeader>
                <CardTitle>Schema Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <h3 className="font-semibold mb-3">Backend Schema</h3>
                    {backendSchema ? (
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Node Type:</span>
                          <Badge>{backendSchema.node_type}</Badge>
                        </div>
                        <div className="flex justify-between">
                          <span>Display Name:</span>
                          <span className="font-medium">{backendSchema.display_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Total Fields:</span>
                          <Badge variant="outline">{getFieldCount(backendSchema)}</Badge>
                        </div>
                        <div className="flex justify-between">
                          <span>Required Fields:</span>
                          <Badge variant="outline">{getRequiredCount(backendSchema)}</Badge>
                        </div>
                        <div className="flex justify-between">
                          <span>Supports Replay:</span>
                          {backendSchema.supports_replay ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-gray-400" />
                          )}
                        </div>
                        <div className="flex justify-between">
                          <span>Supports Checkpoints:</span>
                          {backendSchema.supports_checkpoints ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-gray-400" />
                          )}
                        </div>
                      </div>
                    ) : (
                      <p className="text-muted-foreground">No backend schema loaded</p>
                    )}
                  </div>

                  <div>
                    <h3 className="font-semibold mb-3">Transformed Config</h3>
                    {transformedConfig ? (
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Label:</span>
                          <span className="font-medium">{transformedConfig.label}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Category:</span>
                          <Badge>{transformedConfig.category}</Badge>
                        </div>
                        <div className="flex justify-between">
                          <span>Sections:</span>
                          <Badge variant="outline">{transformedConfig.sections?.length || 0}</Badge>
                        </div>
                        <div className="flex justify-between">
                          <span>Total Fields:</span>
                          <Badge variant="outline">
                            {transformedConfig.sections?.reduce(
                              (acc: number, section: any) => acc + (section.fields?.length || 0),
                              0
                            ) || 0}
                          </Badge>
                        </div>
                        <div className="flex justify-between">
                          <span>Has Validation:</span>
                          {transformedConfig.validate ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-gray-400" />
                          )}
                        </div>
                      </div>
                    ) : (
                      <p className="text-muted-foreground">No transformed config loaded</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="raw">
            <Card>
              <CardHeader>
                <CardTitle>Raw Backend Schema (JSON)</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                  {JSON.stringify(backendSchema, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="transformed">
            <Card>
              <CardHeader>
                <CardTitle>Transformed UnifiedNodeConfig</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                  {JSON.stringify(
                    transformedConfig,
                    (key, value) => {
                      // Don't serialize functions
                      if (typeof value === 'function') {
                        return `[Function: ${key}]`;
                      }
                      return value;
                    },
                    2
                  )}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>


          <TabsContent value="validation">
            <Card>
              <CardHeader>
                <CardTitle>Validation Test</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  Current configuration and validation state
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">Current Configuration:</h4>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                    {JSON.stringify(testConfig, null, 2)}
                  </pre>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Validation Errors:</h4>
                  {Object.keys(validationErrors).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(validationErrors).map(([field, error]) => (
                        <div key={field} className="flex items-start gap-2">
                          <XCircle className="h-4 w-4 text-red-500 mt-0.5" />
                          <div>
                            <span className="font-medium">{field}:</span>
                            <span className="ml-2 text-sm text-muted-foreground">{error}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      <span>All fields are valid</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="batch">
            <BatchTestAllNodes />
          </TabsContent>
        </Tabs>
          )}
        </div>

        {/* Right panel - Form Preview */}
        <Card className="w-full xl:w-96 h-fit flex-shrink-0">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Form Preview</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Live preview of the configuration form
            </p>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                <span className="ml-2 text-sm">Loading...</span>
              </div>
            ) : transformedConfig ? (
              <>
                {/* Show loading state for data */}
                {(dataLoading.pipelines || dataLoading.users || dataLoading.userTypes) && (
                  <Alert className="mb-4">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                      Loading: {dataLoading.pipelines && 'pipelines'} {dataLoading.users && 'users'} {dataLoading.userTypes && 'types'}
                    </AlertDescription>
                  </Alert>
                )}

                {/* Show data errors if any */}
                {(dataError.pipelines || dataError.users || dataError.userTypes) && (
                  <Alert variant="destructive" className="mb-4">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                      {dataError.pipelines && <div>Pipelines: {dataError.pipelines}</div>}
                      {dataError.users && <div>Users: {dataError.users}</div>}
                      {dataError.userTypes && <div>User Types: {dataError.userTypes}</div>}
                    </AlertDescription>
                  </Alert>
                )}

                {/* Data summary */}
                <div className="mb-4 flex gap-1 flex-wrap">
                  <Badge variant="outline" className="text-xs">Pipelines: {pipelines.length}</Badge>
                  <Badge variant="outline" className="text-xs">Users: {users.length}</Badge>
                  <Badge variant="outline" className="text-xs">Types: {userTypes.length}</Badge>
                </div>

                <UnifiedConfigRenderer
                  nodeConfig={transformedConfig}
                  config={testConfig}
                  onChange={(newConfig) => {
                    setTestConfig(newConfig);

                    // Auto-fetch pipeline fields when a pipeline is selected (single)
                    if (newConfig.pipeline_id && newConfig.pipeline_id !== testConfig.pipeline_id) {
                      fetchPipelineFields(newConfig.pipeline_id);
                    }

                    // Auto-fetch pipeline fields when pipelines are selected (multi)
                    if (newConfig.pipeline_ids && Array.isArray(newConfig.pipeline_ids)) {
                      const previousIds = testConfig.pipeline_ids || [];
                      const newIds = newConfig.pipeline_ids.filter((id: string) => !previousIds.includes(id));
                      // Fetch fields for newly selected pipelines
                      newIds.forEach((id: string) => fetchPipelineFields(id));
                    }
                  }}
                  availableVariables={[
                    { nodeId: 'trigger', label: 'Trigger', outputs: ['data', 'timestamp'] },
                    { nodeId: 'previous', label: 'Previous Node', outputs: ['result', 'status'] }
                  ]}
                  pipelines={pipelines}
                  pipelineFields={(() => {
                    // For single pipeline selection
                    if (testConfig.pipeline_id) {
                      return pipelineFields[testConfig.pipeline_id];
                    }
                    // For multiple pipeline selection, aggregate all fields
                    if (testConfig.pipeline_ids && Array.isArray(testConfig.pipeline_ids)) {
                      const allFields: any[] = [];
                      testConfig.pipeline_ids.forEach((id: string) => {
                        if (pipelineFields[id]) {
                          allFields.push(...pipelineFields[id]);
                        }
                      });
                      // Remove duplicates based on field name/slug
                      const uniqueFields = allFields.filter((field, index, self) =>
                        index === self.findIndex((f) =>
                          (f.slug === field.slug && f.slug) ||
                          (f.name === field.name)
                        )
                      );
                      return uniqueFields.length > 0 ? uniqueFields : undefined;
                    }
                    return undefined;
                  })()}
                  users={users}
                  userTypes={userTypes}
                  errors={validationErrors}
                />
              </>
            ) : (
              <p className="text-muted-foreground text-sm">No config to preview</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Component to test all node types
function BatchTestAllNodes() {
  const [testResults, setTestResults] = useState<Record<string, {
    status: 'pending' | 'loading' | 'success' | 'error';
    error?: string;
    fieldCount?: number;
  }>>({});
  const [testing, setTesting] = useState(false);

  const runBatchTest = async () => {
    setTesting(true);
    const results: typeof testResults = {};

    for (const node of TEST_NODE_TYPES) {
      results[node.type] = { status: 'loading' };
      setTestResults({ ...results });

      try {
        const config = await workflowSchemaService.getNodeConfig(node.type);
        if (config) {
          const fieldCount = config.sections?.reduce(
            (acc, section) => acc + (section.fields?.length || 0),
            0
          ) || 0;
          results[node.type] = { status: 'success', fieldCount };
        } else {
          results[node.type] = { status: 'error', error: 'No configuration found' };
        }
      } catch (err) {
        results[node.type] = {
          status: 'error',
          error: err instanceof Error ? err.message : 'Failed to load'
        };
      }
      setTestResults({ ...results });
    }

    setTesting(false);
  };

  const successCount = Object.values(testResults).filter(r => r.status === 'success').length;
  const errorCount = Object.values(testResults).filter(r => r.status === 'error').length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Batch Test All Node Types</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Test loading configuration for all {TEST_NODE_TYPES.length} node types from backend
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <Button
              onClick={runBatchTest}
              disabled={testing}
              variant="default"
            >
              {testing ? 'Testing...' : 'Run Batch Test'}
            </Button>

            {Object.keys(testResults).length > 0 && (
              <div className="flex gap-4">
                <Badge variant="default">
                  Success: {successCount}/{TEST_NODE_TYPES.length}
                </Badge>
                {errorCount > 0 && (
                  <Badge variant="destructive">
                    Failed: {errorCount}
                  </Badge>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
            {TEST_NODE_TYPES.map((node) => {
              const result = testResults[node.type] || { status: 'pending' };
              return (
                <div
                  key={node.type}
                  className="flex items-center gap-2 p-2 rounded-md border"
                >
                  {result.status === 'pending' && (
                    <div className="h-4 w-4 rounded-full bg-gray-200" />
                  )}
                  {result.status === 'loading' && (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  )}
                  {result.status === 'success' && (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  )}
                  {result.status === 'error' && (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-sm font-medium">{node.label}</span>
                  {result.fieldCount !== undefined && (
                    <span className="text-xs text-muted-foreground ml-auto">
                      {result.fieldCount} fields
                    </span>
                  )}
                  {result.error && (
                    <span className="text-xs text-red-500 ml-auto truncate" title={result.error}>
                      {result.error}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}