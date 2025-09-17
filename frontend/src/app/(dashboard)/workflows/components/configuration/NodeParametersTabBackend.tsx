'use client';

import { useState, useEffect, useCallback } from 'react';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { WorkflowNodeType } from '../../types';
import { pipelinesApi, usersApi, permissionsApi, communicationsApi, workflowsApi } from '@/lib/api';
// Use the new backend-powered registry
import { getNodeConfig } from '../node-configs/unified/registry-backend';
import { UnifiedConfigRenderer } from '../node-configs/unified/UnifiedConfigRenderer';
import { UnifiedNodeConfig } from '../node-configs/unified/types';

interface NodeParametersTabProps {
  nodeType: WorkflowNodeType;
  nodeData: any;
  availableVariables: Array<{ nodeId: string; label: string; outputs: string[] }>;
  onUpdate: (data: any) => void;
  onValidationChange: (errors: Record<string, string>) => void;
}

export function NodeParametersTabBackend({
  nodeType,
  nodeData,
  availableVariables,
  onUpdate,
  onValidationChange
}: NodeParametersTabProps) {
  const [config, setConfig] = useState(nodeData.config || {});
  const [nodeConfig, setNodeConfig] = useState<UnifiedNodeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Data sources for dropdowns
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [pipelineFields, setPipelineFields] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [userTypes, setUserTypes] = useState<any[]>([]);
  const [unipileAccounts, setUnipileAccounts] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);

  // Load node configuration from backend
  useEffect(() => {
    async function loadNodeConfig() {
      try {
        setLoading(true);
        setError(null);

        const config = await getNodeConfig(nodeType);

        if (!config) {
          setError(`No configuration found for node type: ${nodeType}`);
        } else {
          setNodeConfig(config);
        }
      } catch (err) {
        console.error('Failed to load node config:', err);
        setError(`Failed to load configuration: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    }

    loadNodeConfig();
  }, [nodeType]);

  // Load data sources based on node dependencies
  useEffect(() => {
    if (!nodeConfig) return;

    // Check dependencies and load required data
    if (nodeConfig.dependencies?.pipelines || needsPipeline(nodeType)) {
      loadPipelines();
    }

    if (nodeConfig.dependencies?.users || needsUsers(nodeType)) {
      loadUsers();
    }

    if (nodeConfig.dependencies?.workflows || nodeType === WorkflowNodeType.SUB_WORKFLOW) {
      loadWorkflows();
    }

    // Load user types for approval nodes
    if (nodeType === WorkflowNodeType.APPROVAL) {
      loadUserTypes();
    }

    // Load UniPile accounts for communication nodes
    if (isCommunicationNode(nodeType)) {
      loadUnipileAccounts();
    }
  }, [nodeConfig, nodeType]);

  // Load pipeline fields when pipeline is selected
  useEffect(() => {
    if (config.pipeline_id) {
      loadPipelineFields(config.pipeline_id);
    }
  }, [config.pipeline_id]);

  // Validate configuration
  useEffect(() => {
    if (nodeConfig?.validate) {
      const errors = nodeConfig.validate(config);
      setValidationErrors(errors);
      onValidationChange(errors);
    }
  }, [config, nodeConfig, onValidationChange]);

  const needsPipeline = (type: WorkflowNodeType) => {
    return [
      WorkflowNodeType.TRIGGER_RECORD_CREATED,
      WorkflowNodeType.TRIGGER_RECORD_UPDATED,
      WorkflowNodeType.TRIGGER_RECORD_DELETED,
      WorkflowNodeType.RECORD_CREATE,
      WorkflowNodeType.RECORD_UPDATE,
      WorkflowNodeType.RECORD_FIND,
      WorkflowNodeType.RECORD_DELETE,
      WorkflowNodeType.TRIGGER_FORM_SUBMITTED,
      WorkflowNodeType.GENERATE_FORM_LINK
    ].includes(type);
  };

  const needsUsers = (type: WorkflowNodeType) => {
    return [
      WorkflowNodeType.TASK_NOTIFY,
      WorkflowNodeType.APPROVAL
    ].includes(type);
  };

  const isCommunicationNode = (type: WorkflowNodeType) => {
    return [
      WorkflowNodeType.UNIPILE_SEND_EMAIL,
      WorkflowNodeType.UNIPILE_SEND_LINKEDIN,
      WorkflowNodeType.UNIPILE_SEND_WHATSAPP,
      WorkflowNodeType.UNIPILE_SEND_SMS,
      WorkflowNodeType.TRIGGER_EMAIL_RECEIVED
    ].includes(type);
  };

  const loadPipelines = async () => {
    try {
      const response = await pipelinesApi.list();
      const pipelineList = response.data.results || response.data || [];
      setPipelines(pipelineList);
    } catch (error) {
      console.error('Failed to load pipelines:', error);
    }
  };

  const loadPipelineFields = async (pipelineId: number) => {
    try {
      const response = await pipelinesApi.getFields(pipelineId);
      setPipelineFields(response.data || []);
    } catch (error) {
      console.error('Failed to load pipeline fields:', error);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await usersApi.list();
      setUsers(response.data || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadUserTypes = async () => {
    try {
      const response = await permissionsApi.getUserTypes();
      setUserTypes(response.data || []);
    } catch (error) {
      console.error('Failed to load user types:', error);
    }
  };

  const loadUnipileAccounts = async () => {
    try {
      const response = await communicationsApi.getUnipileAccounts();
      setUnipileAccounts(response.data || []);
    } catch (error) {
      console.error('Failed to load UniPile accounts:', error);
    }
  };

  const loadWorkflows = async () => {
    try {
      const response = await workflowsApi.list();
      setWorkflows(response.data || []);
    } catch (error) {
      console.error('Failed to load workflows:', error);
    }
  };

  const handleConfigChange = useCallback((newConfig: any) => {
    setConfig(newConfig);
    onUpdate({ ...nodeData, config: newConfig });
  }, [nodeData, onUpdate]);

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Spinner className="h-8 w-8" />
        <span className="ml-2">Loading configuration...</span>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  // Show message if no config available
  if (!nodeConfig) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <p>No configuration available for this node type.</p>
        <p className="text-sm mt-2">Node type: {nodeType}</p>
      </div>
    );
  }

  // Render the unified config using backend schema
  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-lg font-semibold">{nodeConfig.label}</h3>
        {nodeConfig.description && (
          <p className="text-sm text-muted-foreground mt-1">{nodeConfig.description}</p>
        )}
      </div>

      <UnifiedConfigRenderer
        nodeConfig={nodeConfig}
        config={config}
        onChange={handleConfigChange}
        availableVariables={availableVariables}
        pipelines={pipelines}
        workflows={workflows}
        users={users}
        userTypes={userTypes}
        unipileAccounts={unipileAccounts}
        pipelineFields={pipelineFields}
        errors={validationErrors}
      />
    </div>
  );
}