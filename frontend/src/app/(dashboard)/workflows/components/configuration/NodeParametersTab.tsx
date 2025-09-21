'use client';

import { useState, useEffect } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2 } from 'lucide-react';
import { WorkflowNodeType } from '../../types';
import { api } from '@/lib/api';
// Import unified configuration system with backend schemas
import { UnifiedConfigRenderer } from '../node-configs/unified/UnifiedConfigRenderer';
import { useWorkflowData } from '../../hooks/useWorkflowData';
import { workflowSchemaService } from '@/services/workflowSchemaService';

interface NodeParametersTabProps {
  nodeType: WorkflowNodeType;
  nodeData: any;
  availableVariables: Array<{ nodeId: string; label: string; outputs: string[] }>;
  onUpdate: (data: any) => void;
  onValidationChange: (errors: Record<string, string>) => void;
}

export function NodeParametersTab({
  nodeType,
  nodeData,
  availableVariables,
  onUpdate,
  onValidationChange
}: NodeParametersTabProps) {
  const [config, setConfig] = useState(nodeData.config || {});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [backendSchema, setBackendSchema] = useState<any>(null);
  const [schemaLoading, setSchemaLoading] = useState(true);
  const [schemaError, setSchemaError] = useState<string | null>(null);

  // Use the workflow data hook to get real data
  const {
    pipelines,
    users,
    userTypes,
    pipelineFields,
    fetchPipelineFields,
    loading: dataLoading,
    error: dataError
  } = useWorkflowData();

  // Fetch backend schema when node type changes
  useEffect(() => {
    fetchNodeSchema();
  }, [nodeType]);

  // Fetch pipeline fields when pipeline is selected
  useEffect(() => {
    if (config.pipeline_id && fetchPipelineFields) {
      fetchPipelineFields(config.pipeline_id);
    }
  }, [config.pipeline_id, fetchPipelineFields]);

  const fetchNodeSchema = async () => {
    setSchemaLoading(true);
    setSchemaError(null);

    try {
      // Fetch all node schemas from backend
      const response = await api.get('/api/v1/workflows/node_schemas/');
      const schemas = response.data;

      // Get the schema for the current node type
      const nodeSchema = schemas[nodeType];

      if (nodeSchema) {
        // Transform backend schema to unified config format
        const transformedSchema = workflowSchemaService.transformBackendSchema(
          nodeSchema,
          nodeType
        );
        setBackendSchema(transformedSchema);
      } else {
        setSchemaError(`No schema found for node type: ${nodeType}`);
      }
    } catch (err: any) {
      console.error('Failed to fetch node schema:', err);
      setSchemaError(err.message || 'Failed to load node configuration');
    } finally {
      setSchemaLoading(false);
    }
  };

  const handleConfigChange = (newConfig: any) => {
    setConfig(newConfig);
    onUpdate({ ...nodeData, config: newConfig });

    // Fetch pipeline fields if pipeline changed
    if (newConfig.pipeline_id && newConfig.pipeline_id !== config.pipeline_id) {
      fetchPipelineFields(newConfig.pipeline_id);
    }
  };

  const handleValidationChange = (validationErrors: Record<string, string>) => {
    setErrors(validationErrors);
    onValidationChange(validationErrors);
  };

  // Loading state
  if (schemaLoading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground mt-2">Loading configuration...</span>
      </div>
    );
  }

  // Error state
  if (schemaError) {
    return (
      <Alert variant="destructive" className="m-4">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {schemaError}
        </AlertDescription>
      </Alert>
    );
  }

  // No schema available (fallback for unsupported node types)
  if (!backendSchema) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No configuration available for this node type</p>
        <p className="text-xs mt-1 opacity-70">Node type: {nodeType}</p>
      </div>
    );
  }

  // Render the unified configuration from backend schema
  return (
    <UnifiedConfigRenderer
      nodeConfig={backendSchema}
      config={config}
      onChange={handleConfigChange}
      availableVariables={availableVariables}
      pipelines={pipelines}
      pipelineFields={pipelineFields}
      users={users}
      userTypes={userTypes}
      errors={errors}
      onValidationChange={handleValidationChange}
    />
  );
}