'use client';

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
import { toast } from 'sonner';
import { UnifiedConfigRenderer } from '../../components/node-configs/unified/UnifiedConfigRenderer';
import { NodeOutputTabV2 } from '../../components/configuration/NodeOutputTabV2';
import { NodeInputStructure } from '../../components/configuration/NodeInputStructure';
import { workflowSchemaService } from '@/services/workflowSchemaService';
import { useWorkflowData } from '../../hooks/useWorkflowData';
import { useWorkflowTestData } from '../../hooks/useWorkflowTestData';
import { UnifiedNodeConfig } from '../../components/node-configs/unified/types';
import { useNodeSchemas } from '../hooks/useNodeSchemas';
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
  nodeOutputs?: Record<string, any>;
  onNodeTest?: (nodeId: string, output: any) => void;
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
  workflowDefinition,
  nodeOutputs = {},
  onNodeTest
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
  const [nodeSchema, setNodeSchema] = useState<UnifiedNodeConfig | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [inputData, setInputData] = useState<any>({ sources: [], availableVariables: [] });

  // Test data state for triggers - using shared hook
  const [useRealData, setUseRealData] = useState(false);

  const isTriggerNode = node?.type.startsWith('TRIGGER_') || node?.type.toLowerCase().includes('trigger');

  // Use the shared test data hook
  const {
    testData,
    testDataType,
    selectedTestData,
    setSelectedTestData,
    loading: loadingTestData,
    error: testDataError,
    refetch: refetchTestData
  } = useWorkflowTestData({
    nodeType: node?.type || '',
    config: localConfig,
    enabled: isTriggerNode
  });

  // Load node schema when node changes
  useEffect(() => {
    if (node) {
      loadNodeSchema();
      loadInputData(node);
    }
  }, [node?.id, node?.type]);

  // Run validation when config changes
  useEffect(() => {
    if (nodeSchema?.validate) {
      const errors = nodeSchema.validate(localConfig);
      setValidationErrors(errors || {});
    }
  }, [localConfig, nodeSchema]);

  const loadNodeSchema = async () => {
    if (!node) return;

    setSchemaLoading(true);
    try {
      const schema = await workflowSchemaService.getNodeConfig(node.type);
      setNodeSchema(schema);

      // Reset config to schema defaults when switching nodes
      if (schema && schema.defaults) {
        setLocalConfig(node.data?.config || schema.defaults || {});
      }

      // Run initial validation if schema has validation
      if (schema?.validate) {
        const errors = schema.validate(localConfig || {});
        setValidationErrors(errors || {});
      }
    } catch (error) {
      console.error('Failed to load node schema:', error);
      setNodeSchema(null);
      setError('Failed to load node configuration');
    } finally {
      setSchemaLoading(false);
    }
  };

  // Auto-enable real data when test data is available
  useEffect(() => {
    if (testData.length > 0 && selectedTestData && !useRealData) {
      setUseRealData(true);
    }
  }, [testData, selectedTestData]);

  const loadInputData = (currentNode: WorkflowNode) => {
    // Find incoming edges to this node
    const incomingEdges = workflowDefinition.edges.filter(edge => edge.target === currentNode.id);
    const inputSources: any[] = [];

    incomingEdges.forEach(edge => {
      const sourceNode = workflowDefinition.nodes.find(n => n.id === edge.source);
      if (sourceNode) {
        // Get the node's actual configuration
        const nodeConfig = sourceNode.data.config || {};

        // First try to get actual output from nodeOutputs
        // Then fallback to lastOutput stored in the node
        // Finally fallback to default schema
        const actualOutput = nodeOutputs[sourceNode.id] ||
                           sourceNode.data.lastOutput ||
                           getDefaultNodeOutputs(sourceNode.type);

        inputSources.push({
          nodeId: sourceNode.id,
          label: sourceNode.data.label,
          type: sourceNode.type,
          data: actualOutput,
          config: nodeConfig
        });
      }
    });

    // Only include data from nodes that are actually connected via edges
    // This ensures data flow follows the visual workflow connections

    setInputData({
      sources: inputSources,
      availableVariables: inputSources
    });
  };

  const getDefaultNodeOutputs = (nodeType: WorkflowNodeType): any => {
    // Return realistic output structure based on node type
    // These match what the backend processors actually return

    // Record operations
    if (nodeType === WorkflowNodeType.TRIGGER_RECORD_UPDATED || nodeType === 'trigger_record_updated') {
      return {
        success: true,
        record: { id: 123, pipeline_id: "pipe_123", data: {} },
        previous_record: { id: 123, pipeline_id: "pipe_123", data: {} },
        pipeline_id: "pipe_123",
        updated_by: "user_123",
        updated_at: new Date().toISOString(),
        changed_fields: ["field1", "field2"],
        trigger_type: 'record_updated'
      };
    }

    if (nodeType === WorkflowNodeType.TRIGGER_RECORD_CREATED || nodeType === 'trigger_record_created') {
      return {
        success: true,
        record: { id: 123, pipeline_id: "pipe_123", data: {} },
        pipeline_id: "pipe_123",
        created_by: "user_123",
        created_at: new Date().toISOString(),
        trigger_type: 'record_created'
      };
    }

    if (nodeType === WorkflowNodeType.RECORD_CREATE || nodeType === 'create_record') {
      return {
        success: true,
        record: { id: 123, pipeline_id: "pipe_123", data: {} },
        created_at: new Date().toISOString()
      };
    }

    if (nodeType === WorkflowNodeType.RECORD_UPDATE || nodeType === 'update_record') {
      return {
        success: true,
        record: { id: 123, pipeline_id: "pipe_123", data: {} },
        updated_fields: [],
        updated_at: new Date().toISOString()
      };
    }

    if (nodeType === WorkflowNodeType.RECORD_FIND || nodeType === 'find_records') {
      return {
        success: true,
        records: [{ id: 123, pipeline_id: "pipe_123", data: {} }],
        count: 1
      };
    }

    // AI operations
    if (nodeType === WorkflowNodeType.AI_PROMPT || nodeType === 'ai_prompt') {
      return {
        success: true,
        result: "AI generated response",
        model: "gpt-4",
        tokens_used: 150,
        execution_time: 1.5
      };
    }

    // Communication
    if (nodeType === WorkflowNodeType.UNIPILE_SEND_EMAIL || nodeType === 'unipile_send_email') {
      return {
        success: true,
        message_id: "msg_123",
        thread_id: "thread_123",
        sent_at: new Date().toISOString()
      };
    }

    // Control flow
    if (nodeType === WorkflowNodeType.CONDITION || nodeType === 'condition') {
      return {
        success: true,
        condition_met: true,
        branch_taken: "true_branch",
        evaluation_details: {}
      };
    }

    // Default output structure
    return {
      success: true,
      data: {},
      timestamp: new Date().toISOString()
    };
  };

  // Handle config changes
  const handleConfigChange = (newConfig: any) => {
    setLocalConfig(newConfig);
    onConfigChange(newConfig);

    // Auto-fetch pipeline fields when pipeline is selected
    if (newConfig.pipeline_id && newConfig.pipeline_id !== localConfig?.pipeline_id) {
      fetchPipelineFields(newConfig.pipeline_id);
    }

    // Auto-fetch pipeline fields when pipelines are selected (multi)
    if (newConfig.pipeline_ids && Array.isArray(newConfig.pipeline_ids)) {
      const previousIds = localConfig?.pipeline_ids || [];
      const newIds = newConfig.pipeline_ids.filter((id: string) => !previousIds.includes(id));
      // Fetch fields for newly selected pipelines
      newIds.forEach((id: string) => fetchPipelineFields(id));
    }

    // Run validation using the schema
    if (nodeSchema?.validate) {
      const errors = nodeSchema.validate(newConfig);
      setValidationErrors(errors || {});
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
                <div className="pr-2">
                  {/* Input data structure display with 3 sections */}
                  <NodeInputStructure
                    sources={inputData.sources || []}
                    testData={isTriggerNode && useRealData ? selectedTestData : null}
                    isTriggerNode={isTriggerNode}
                    testDataList={testData}
                    testDataType={testDataType}
                    selectedTestData={selectedTestData}
                    onTestDataChange={setSelectedTestData}
                    useRealData={useRealData}
                    onUseRealDataChange={setUseRealData}
                    loadingTestData={loadingTestData}
                  />

                  {/* Show test data error if any */}
                  {testDataError && (
                    <Alert variant="destructive" className="mt-2">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription className="text-xs">
                        {testDataError}
                      </AlertDescription>
                    </Alert>
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
                ) : (nodeSchema || nodeConfig) ? (
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

                    {/* Configuration form - use schema-based renderer when available */}
                    {nodeSchema ? (
                      <UnifiedConfigRenderer
                        nodeConfig={nodeSchema}
                        config={localConfig}
                        onChange={handleConfigChange}
                        availableVariables={inputData.sources || []}
                        pipelines={pipelines}
                        workflows={[]}
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
                    ) : nodeConfig ? (
                      // Fallback to old config renderer if no schema
                      <UnifiedConfigRenderer
                        nodeConfig={nodeConfig}
                        config={localConfig}
                        onChange={handleConfigChange}
                        availableVariables={inputData.sources || []}
                        pipelines={pipelines}
                        pipelineFields={pipelineFields[localConfig?.pipeline_id]}
                        users={users}
                        userTypes={userTypes}
                        errors={validationErrors}
                      />
                    ) : null}
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
                      testRecord={isTriggerNode && useRealData ? selectedTestData : null}
                      testDataType={testDataType || 'record'}
                      onNodeTest={onNodeTest}
                      nodeOutputs={nodeOutputs}
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