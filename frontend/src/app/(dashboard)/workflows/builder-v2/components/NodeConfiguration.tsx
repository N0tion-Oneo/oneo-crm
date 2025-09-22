/**
 * NodeConfiguration Component
 * Reuses UnifiedConfigRenderer for node configuration
 */

import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, X, AlertCircle } from 'lucide-react';
import { UnifiedConfigRenderer } from '../../components/node-configs/unified/UnifiedConfigRenderer';
import { useNodeSchemas } from '../hooks/useNodeSchemas';
import { useWorkflowData } from '../../hooks/useWorkflowData';
import { WorkflowNode } from '../types';
import { WorkflowNodeType } from '../../types';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface NodeConfigurationProps {
  node: WorkflowNode | null;
  config: any;
  onConfigChange: (config: any) => void;
  onClose: () => void;
}

export function NodeConfiguration({
  node,
  config,
  onConfigChange,
  onClose,
}: NodeConfigurationProps) {
  const { getNodeSchema, getNodeDefinition } = useNodeSchemas();
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Load node schema when node changes
  useEffect(() => {
    if (node) {
      loadNodeSchema(node.type);
    }
  }, [node?.type]);

  const loadNodeSchema = async (nodeType: WorkflowNodeType) => {
    setLoading(true);
    setError(null);

    try {
      const schema = await getNodeSchema(nodeType);
      setNodeConfig(schema);

      // Run initial validation if schema has validation
      if (schema?.validate) {
        const errors = schema.validate(config || {});
        setValidationErrors(errors || {});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load node configuration');
    } finally {
      setLoading(false);
    }
  };

  // Handle config changes
  const handleConfigChange = (newConfig: any) => {
    onConfigChange(newConfig);

    // Run validation
    if (nodeConfig?.validate) {
      const errors = nodeConfig.validate(newConfig);
      setValidationErrors(errors || {});
    }

    // Auto-fetch pipeline fields when pipeline is selected
    if (newConfig.pipeline_id && newConfig.pipeline_id !== config?.pipeline_id) {
      fetchPipelineFields(newConfig.pipeline_id);
    }

    // Handle multiple pipeline selections
    if (newConfig.pipeline_ids && Array.isArray(newConfig.pipeline_ids)) {
      const previousIds = config?.pipeline_ids || [];
      const newIds = newConfig.pipeline_ids.filter((id: string) => !previousIds.includes(id));
      newIds.forEach((id: string) => fetchPipelineFields(id));
    }
  };

  if (!node) {
    return (
      <Card className="h-full flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <p className="text-sm">Select a node to configure</p>
        </div>
      </Card>
    );
  }

  const nodeDefinition = getNodeDefinition(node.type);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {nodeDefinition?.icon && (
              <span className="text-lg">{nodeDefinition.icon}</span>
            )}
            <CardTitle className="text-lg">{nodeDefinition?.label || node.type}</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <ScrollArea className="flex-1">
        <CardContent className="pt-4">
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

              {/* Data errors */}
              {(dataError.pipelines || dataError.users || dataError.userTypes) && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    Error loading data
                  </AlertDescription>
                </Alert>
              )}

              {/* Configuration form */}
              <UnifiedConfigRenderer
                nodeConfig={nodeConfig}
                config={config || {}}
                onChange={handleConfigChange}
                availableVariables={[
                  { nodeId: 'trigger', label: 'Trigger', outputs: ['data', 'timestamp'] },
                  { nodeId: 'previous', label: 'Previous Node', outputs: ['result', 'status'] },
                ]}
                pipelines={pipelines}
                pipelineFields={(() => {
                  // Aggregate pipeline fields based on selection
                  if (config?.pipeline_id) {
                    return pipelineFields[config.pipeline_id];
                  }
                  if (config?.pipeline_ids && Array.isArray(config.pipeline_ids)) {
                    const allFields: any[] = [];
                    config.pipeline_ids.forEach((id: string) => {
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
        </CardContent>
      </ScrollArea>
    </Card>
  );
}