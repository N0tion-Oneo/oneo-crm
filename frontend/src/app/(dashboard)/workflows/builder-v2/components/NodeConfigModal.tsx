/**
 * NodeConfigModal Component
 * 3-panel modal for node configuration showing data flow
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import {
  ArrowRight,
  Settings,
  ArrowLeft,
  X,
  AlertCircle,
  Loader2,
  Database,
  Variable,
  CheckCircle,
  Code2,
  User,
  RefreshCw
} from 'lucide-react';
import { UnifiedConfigRenderer } from '../../components/node-configs/unified/UnifiedConfigRenderer';
import { NodeOutputTabV2 } from '../../components/configuration/NodeOutputTabV2';
import { useNodeSchemas } from '../hooks/useNodeSchemas';
import { useWorkflowData } from '../../hooks/useWorkflowData';
import { WorkflowNode, WorkflowEdge, WorkflowDefinition } from '../types';
import { WorkflowNodeType } from '../../types';
import { TestDataProvider, useTestData } from '../../components/configuration/TestDataContext';

interface NodeConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  node: WorkflowNode | null;
  config: any;
  onConfigChange: (config: any) => void;
  onSave: (config: any) => void;
  workflowDefinition: WorkflowDefinition;
}

// Helper function to get the best display name for a record
const getRecordDisplayName = (record: any): string => {
  if (!record) return `Record`;

  // First check top-level fields (computed/special fields from backend)
  const topLevelFields = ['title', 'display_name', 'name'];
  for (const field of topLevelFields) {
    if (record[field] && typeof record[field] === 'string' && record[field].trim() !== '') {
      return record[field];
    }
  }

  // Then check data object fields
  if (record.data) {
    const dataFields = ['title', 'name', 'full_name', 'display_name', 'first_name', 'last_name', 'email', 'company', 'label'];

    for (const field of dataFields) {
      if (record.data[field] && typeof record.data[field] === 'string' && record.data[field].trim() !== '') {
        return record.data[field];
      }
    }

    // If we have first_name and last_name in data, combine them
    if (record.data.first_name && record.data.last_name) {
      return `${record.data.first_name} ${record.data.last_name}`;
    }
  }

  // Fall back to ID
  return `Record ${String(record.id || '').slice(0, 8)}`;
};

function NodeConfigModalInner({
  isOpen,
  onClose,
  node,
  config,
  onConfigChange,
  onSave,
  workflowDefinition
}: NodeConfigModalProps) {
  const { getNodeSchema, getNodeDefinition } = useNodeSchemas();
  const { loadPipelineRecords } = useTestData();
  const {
    pipelines,
    users,
    userTypes,
    pipelineFields,
    fetchPipelineFields,
    loading: dataLoading,
    error: dataError,
  } = useWorkflowData();

  const [nodeConfig, setNodeConfig] = useState<any>(null);
  const [localConfig, setLocalConfig] = useState<any>(config || {});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [inputData, setInputData] = useState<any>({});

  // Test data state for triggers
  const [testRecords, setTestRecords] = useState<any[]>([]);
  const [selectedTestRecord, setSelectedTestRecord] = useState<any>(null);
  const [loadingTestRecords, setLoadingTestRecords] = useState(false);
  const [useRealData, setUseRealData] = useState(false);

  const isTriggerNode = node?.type.startsWith('TRIGGER_') || node?.type.toLowerCase().includes('trigger');

  // Load node schema when node changes
  useEffect(() => {
    if (node) {
      loadNodeSchema(node.type);
      setLocalConfig(config || {});
      loadInputData(node);

      // Load test records for trigger nodes
      if (isTriggerNode && (config?.pipeline_id || config?.pipeline_ids?.length)) {
        loadTestRecordsForTrigger();
      }
    }
  }, [node?.id, node?.type, config?.pipeline_id, config?.pipeline_ids]);

  const loadNodeSchema = async (nodeType: WorkflowNodeType) => {
    setLoading(true);
    setError(null);

    try {
      const schema = await getNodeSchema(nodeType);
      setNodeConfig(schema);

      // Run initial validation if schema has validation
      if (schema?.validate) {
        const errors = schema.validate(localConfig || {});
        setValidationErrors(errors || {});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load node configuration');
    } finally {
      setLoading(false);
    }
  };

  const loadTestRecordsForTrigger = async () => {
    const pipelineId = localConfig?.pipeline_id || localConfig?.pipeline_ids?.[0];
    if (!pipelineId) return;

    setLoadingTestRecords(true);
    try {
      const records = await loadPipelineRecords(pipelineId);
      setTestRecords(records);
      if (records.length > 0 && !selectedTestRecord) {
        setSelectedTestRecord(records[0]);
        setUseRealData(true);
      }
    } catch (error) {
      console.error('Failed to load test records:', error);
      setTestRecords([]);
    } finally {
      setLoadingTestRecords(false);
    }
  };

  const loadInputData = (currentNode: WorkflowNode) => {
    // Find incoming edges to this node
    const incomingEdges = workflowDefinition.edges.filter(edge => edge.target === currentNode.id);
    const inputSources: any[] = [];

    incomingEdges.forEach(edge => {
      const sourceNode = workflowDefinition.nodes.find(n => n.id === edge.source);
      if (sourceNode) {
        inputSources.push({
          nodeId: sourceNode.id,
          label: sourceNode.data.label,
          type: sourceNode.type,
          outputs: getNodeOutputFields(sourceNode.type)
        });
      }
    });

    // Add trigger data if this is not a trigger node
    if (!currentNode.type.startsWith('trigger_')) {
      const triggerNode = workflowDefinition.nodes.find(n => n.type.startsWith('trigger_'));
      if (triggerNode) {
        inputSources.unshift({
          nodeId: 'trigger',
          label: 'Trigger Data',
          type: triggerNode.type,
          outputs: getNodeOutputFields(triggerNode.type)
        });
      }
    }

    setInputData({
      sources: inputSources,
      availableVariables: inputSources
    });
  };

  const getNodeOutputFields = (nodeType: WorkflowNodeType): string[] => {
    // Return common output fields based on node type
    switch (nodeType) {
      case WorkflowNodeType.RECORD_FIND:
      case WorkflowNodeType.RECORD_CREATE:
      case WorkflowNodeType.RECORD_UPDATE:
        return ['record', 'record.id', 'record.data', 'success'];
      case WorkflowNodeType.UNIPILE_SEND_EMAIL:
        return ['message_id', 'status', 'sent_at', 'success'];
      case WorkflowNodeType.AI_PROMPT:
        return ['result', 'model', 'tokens', 'success'];
      case WorkflowNodeType.CONDITION:
        return ['condition_met', 'branch', 'success'];
      default:
        return ['data', 'success', 'timestamp'];
    }
  };

  // Handle config changes
  const handleConfigChange = (newConfig: any) => {
    setLocalConfig(newConfig);
    onConfigChange(newConfig);

    // Run validation
    if (nodeConfig?.validate) {
      const errors = nodeConfig.validate(newConfig);
      setValidationErrors(errors || {});
    }

    // Auto-fetch pipeline fields when pipeline is selected
    if (newConfig.pipeline_id && newConfig.pipeline_id !== localConfig?.pipeline_id) {
      fetchPipelineFields(newConfig.pipeline_id);
    }

    // Handle multiple pipeline selections
    if (newConfig.pipeline_ids && Array.isArray(newConfig.pipeline_ids)) {
      const previousIds = localConfig?.pipeline_ids || [];
      const newIds = newConfig.pipeline_ids.filter((id: string) => !previousIds.includes(id));
      newIds.forEach((id: string) => fetchPipelineFields(id));
    }
  };

  const handleSave = () => {
    // Validate before saving
    if (Object.keys(validationErrors).length > 0) {
      return;
    }
    onSave(localConfig);
    onClose();
  };

  if (!node) {
    return null;
  }

  const nodeDefinition = getNodeDefinition(node.type);
  const hasValidationErrors = Object.keys(validationErrors).length > 0;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[90vh] p-0 overflow-hidden flex flex-col">
          <DialogHeader className="px-6 py-4 border-b">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {nodeDefinition?.icon && (
                  <span className="text-2xl">{nodeDefinition.icon}</span>
                )}
                <div>
                  <DialogTitle className="text-xl">
                    Configure: {nodeDefinition?.label || node.type}
                  </DialogTitle>
                  <DialogDescription className="text-sm mt-1">
                    Set up how data flows through this node
                  </DialogDescription>
                </div>
              </div>
              <Badge variant="outline" className="ml-4">
                {nodeDefinition?.category || 'action'}
              </Badge>
            </div>
          </DialogHeader>

          <div className="flex flex-1 overflow-hidden">
            {/* Left Panel - Input Data */}
            <div className="flex-1 border-r p-4 overflow-hidden">
              <div className="flex items-center gap-2 mb-4">
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <h3 className="font-semibold text-sm">Input Data</h3>
                <Badge variant="secondary" className="text-xs">
                  {inputData.sources?.length || 0} sources
                </Badge>
              </div>

              <ScrollArea className="h-[calc(90vh-12rem)]">
                <div className="space-y-3 pr-2">
                  {/* Test Data Selector for Triggers */}
                  {isTriggerNode && (localConfig?.pipeline_id || localConfig?.pipeline_ids?.length > 0) ? (
                    <div className="space-y-3">
                      <div className="text-xs text-muted-foreground">
                        Select test data for this trigger:
                      </div>

                      {/* Toggle between real and mock data */}
                      <div className="flex items-center gap-2">
                        <Button
                          variant={useRealData ? "default" : "outline"}
                          size="sm"
                          onClick={() => setUseRealData(true)}
                          disabled={testRecords.length === 0}
                          className="flex-1"
                        >
                          <Database className="h-4 w-4 mr-2" />
                          Real Records ({testRecords.length})
                        </Button>
                        <Button
                          variant={!useRealData ? "default" : "outline"}
                          size="sm"
                          onClick={() => setUseRealData(false)}
                          className="flex-1"
                        >
                          <Code2 className="h-4 w-4 mr-2" />
                          Sample Data
                        </Button>
                      </div>

                      {/* Record selector when using real data */}
                      {useRealData && testRecords.length > 0 && (
                        <Card className="p-3 space-y-2">
                          <Label className="text-xs">Select a test record:</Label>
                          <Select
                            value={selectedTestRecord ? String(selectedTestRecord.id) : ''}
                            onValueChange={(value) => {
                              const record = testRecords.find(r => String(r.id) === value);
                              setSelectedTestRecord(record);
                            }}
                          >
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder="Select a test record" />
                            </SelectTrigger>
                            <SelectContent>
                              {testRecords.map((record) => {
                                const displayName = getRecordDisplayName(record);
                                const email = record.data?.email || record.email;

                                return (
                                  <SelectItem key={record.id} value={String(record.id)}>
                                    <div className="flex items-center gap-2">
                                      <User className="h-3 w-3" />
                                      <span className="font-medium">
                                        {displayName}
                                      </span>
                                      {email && email !== displayName && (
                                        <span className="text-xs text-muted-foreground">
                                          ({email})
                                        </span>
                                      )}
                                    </div>
                                  </SelectItem>
                                );
                              })}
                            </SelectContent>
                          </Select>

                          {/* Show selected record preview */}
                          {selectedTestRecord && (
                            <div className="bg-muted/30 rounded-lg p-2">
                              <div className="flex items-center justify-between mb-2">
                                <p className="text-xs font-medium">Test Data Preview:</p>
                                <Badge variant="secondary" className="text-xs">
                                  {getRecordDisplayName(selectedTestRecord)}
                                </Badge>
                              </div>
                              <ScrollArea className="h-[300px] border rounded">
                                <pre className="text-xs font-mono p-2">
                                  {JSON.stringify(selectedTestRecord || {}, null, 2)}
                                </pre>
                              </ScrollArea>
                            </div>
                          )}
                        </Card>
                      )}

                      {/* Loading indicator */}
                      {loadingTestRecords && (
                        <Card className="p-3">
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Loading test records...
                          </div>
                        </Card>
                      )}

                      {/* Sample data preview when not using real data */}
                      {!useRealData && (
                        <Card className="p-3">
                          <p className="text-xs font-medium mb-1">Sample Trigger Data:</p>
                          <div className="text-xs text-muted-foreground">
                            A mock record will be generated based on the pipeline fields
                          </div>
                        </Card>
                      )}
                    </div>
                  ) : inputData.sources?.length > 0 ? (
                    <>
                      <div className="text-xs text-muted-foreground mb-2">
                        Available data from previous nodes:
                      </div>
                      {inputData.sources.map((source: any, index: number) => (
                        <Card key={index} className="p-3">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <Database className="h-4 w-4 text-muted-foreground" />
                              <span className="font-medium text-sm">{source.label}</span>
                            </div>
                            <Badge variant="outline" className="text-xs">
                              {source.nodeId}
                            </Badge>
                          </div>
                          <div className="space-y-1 mt-2">
                            {source.outputs?.map((field: string) => (
                              <div key={field} className="flex items-center gap-2 text-xs">
                                <Variable className="h-3 w-3 text-muted-foreground" />
                                <code className="font-mono bg-muted px-1 rounded">
                                  {`{{${source.nodeId}.${field}}}`}
                                </code>
                              </div>
                            ))}
                          </div>
                        </Card>
                      ))}

                      <Alert className="mt-3">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription className="text-xs">
                          Use these variables in the configuration by typing
                          <code className="mx-1 font-mono bg-muted px-1 rounded">{`{{nodeId.field}}`}</code>
                          in text fields that support expressions.
                        </AlertDescription>
                      </Alert>
                    </>
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p className="text-sm">No input data</p>
                      <p className="text-xs mt-1">
                        {node.type.startsWith('trigger_')
                          ? 'This is a trigger node - it starts the workflow'
                          : 'Connect nodes to provide input data'}
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>

            {/* Center Panel - Configuration */}
            <div className="flex-[1.5] border-r p-4 overflow-hidden">
              <div className="flex items-center gap-2 mb-4">
                <Settings className="h-4 w-4 text-muted-foreground" />
                <h3 className="font-semibold text-sm">Configuration</h3>
                {hasValidationErrors && (
                  <Badge variant="destructive" className="text-xs">
                    {Object.keys(validationErrors).length} errors
                  </Badge>
                )}
              </div>

              <ScrollArea className="h-[calc(90vh-12rem)]">
                <div className="pr-2">
                {loading ? (
                  <div className="flex items-center justify-center p-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span className="ml-2 text-sm">Loading configuration...</span>
                  </div>
                ) : error ? (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                ) : nodeConfig ? (
                  <>
                    {/* Data loading indicators */}
                    {(dataLoading.pipelines || dataLoading.users || dataLoading.userTypes) && (
                      <Alert className="mb-4">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <AlertDescription className="text-xs">
                          Loading data...
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Configuration form */}
                    <UnifiedConfigRenderer
                      nodeConfig={nodeConfig}
                      config={localConfig}
                      onChange={handleConfigChange}
                      availableVariables={inputData.sources || []}
                      pipelines={pipelines}
                      pipelineFields={(() => {
                        // Aggregate pipeline fields based on selection
                        if (localConfig?.pipeline_id) {
                          return pipelineFields[localConfig.pipeline_id];
                        }
                        if (localConfig?.pipeline_ids && Array.isArray(localConfig.pipeline_ids)) {
                          const allFields: any[] = [];
                          localConfig.pipeline_ids.forEach((id: string) => {
                            if (pipelineFields[id]) {
                              allFields.push(...pipelineFields[id]);
                            }
                          });
                          return allFields.length > 0 ? allFields : undefined;
                        }
                        return undefined;
                      })()}
                      users={users}
                      userTypes={userTypes}
                      errors={validationErrors}
                    />
                  </>
                ) : (
                  <div className="text-center text-muted-foreground p-4">
                    <p className="text-sm">No configuration available for this node type</p>
                  </div>
                )}
                </div>
              </ScrollArea>
            </div>

            {/* Right Panel - Output Data */}
            <div className="flex-1 p-4 overflow-hidden">
              <div className="flex items-center gap-2 mb-4">
                <ArrowLeft className="h-4 w-4 text-muted-foreground" />
                <h3 className="font-semibold text-sm">Output Data</h3>
                <Badge variant="secondary" className="text-xs">
                  Expected
                </Badge>
              </div>

              <ScrollArea className="h-[calc(90vh-12rem)]">
                <div className="pr-2">
                {node && (
                  <NodeOutputTabV2
                    nodeId={node.id}
                    nodeType={node.type}
                    config={localConfig}
                    inputData={inputData}
                    testRecord={useRealData ? selectedTestRecord : null}
                  />
                )}
                </div>
              </ScrollArea>
            </div>
          </div>

          <DialogFooter className="px-6 py-4 border-t">
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                {hasValidationErrors && (
                  <div className="flex items-center gap-2 text-destructive text-sm">
                    <AlertCircle className="h-4 w-4" />
                    <span>Fix errors before saving</span>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={hasValidationErrors}>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Save Configuration
                </Button>
              </div>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
  );
}

export function NodeConfigModal(props: NodeConfigModalProps) {
  return (
    <TestDataProvider>
      <NodeConfigModalInner {...props} />
    </TestDataProvider>
  );
}