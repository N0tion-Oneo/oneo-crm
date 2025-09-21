'use client';

import { useState, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  ChevronDown, ChevronRight, Variable,
  AlertCircle, Info, Code, Type,
  Mail, MessageSquare, Database, Zap, GitBranch, Users
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowNodeType } from '../../types';
import { pipelinesApi, usersApi, permissionsApi, communicationsApi, workflowsApi } from '@/lib/api';
import { ExpressionEditor } from './ExpressionEditor';
// Import unified configuration system with backend schemas
import { useNodeConfig } from '../node-configs/unified/useNodeConfig';
import { UnifiedConfigRenderer } from '../node-configs/unified/UnifiedConfigRenderer';

interface NodeParametersTabProps {
  nodeType: WorkflowNodeType;
  nodeData: any;
  availableVariables: Array<{ nodeId: string; label: string; outputs: string[] }>;
  onUpdate: (data: any) => void;
  onValidationChange: (errors: Record<string, string>) => void;
}

interface ParameterSection {
  id: string;
  label: string;
  icon?: React.ElementType;
  fields: ParameterField[];
  collapsed?: boolean;
  advanced?: boolean;
}

interface ParameterField {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'number' | 'select' | 'boolean' | 'expression' | 'json' | 'array';
  placeholder?: string;
  required?: boolean;
  options?: Array<{ label: string; value: string }>;
  helpText?: string;
  validation?: (value: any) => string | null;
  showWhen?: (config: any) => boolean;
  allowExpressions?: boolean;
}

export function NodeParametersTab({
  nodeType,
  nodeData,
  availableVariables,
  onUpdate,
  onValidationChange
}: NodeParametersTabProps) {
  const [config, setConfig] = useState(nodeData.config || {});
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set(['advanced']));
  const [expressionMode, setExpressionMode] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [pipelineFieldsMap, setPipelineFieldsMap] = useState<Record<string, any[]>>({});
  const [selectedFieldsMetadata, setSelectedFieldsMetadata] = useState<Record<string, any>>({});
  const [users, setUsers] = useState<any[]>([]);
  const [userTypes, setUserTypes] = useState<any[]>([]);
  const [unipileAccounts, setUnipileAccounts] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);

  // Load pipelines when needed
  useEffect(() => {
    if (needsPipeline(nodeType)) {
      loadPipelines();
    }

    // Load users if needed for certain node types
    if (nodeType === WorkflowNodeType.TASK_NOTIFY || nodeType === WorkflowNodeType.APPROVAL) {
      loadUsers();
    }

    // Load user types for approval nodes
    if (nodeType === WorkflowNodeType.APPROVAL) {
      loadUserTypes();
    }

    // Load UniPile accounts for communication nodes
    if ([
      WorkflowNodeType.UNIPILE_SEND_EMAIL,
      WorkflowNodeType.UNIPILE_SEND_LINKEDIN,
      WorkflowNodeType.UNIPILE_SEND_WHATSAPP,
      WorkflowNodeType.UNIPILE_SEND_SMS,
      WorkflowNodeType.TRIGGER_EMAIL_RECEIVED
    ].includes(nodeType)) {
      loadUnipileAccounts();
    }

    // Load workflows for sub-workflow nodes
    if (nodeType === WorkflowNodeType.SUB_WORKFLOW) {
      loadWorkflows();
    }
  }, [nodeType]);

  // Load fields when pipeline is selected
  useEffect(() => {
    if (config.pipeline_id) {
      loadPipelineFields(config.pipeline_id);
    }
  }, [config.pipeline_id]);

  // Validate on config change - validation is now handled by UnifiedConfigRenderer
  useEffect(() => {
    // The unified config system handles its own validation
    // Just pass through any errors for compatibility
    setErrors({});
    onValidationChange({});
  }, [config, nodeType, onValidationChange]);

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

  const loadPipelines = async () => {
    try {
      const response = await pipelinesApi.list();
      const pipelineList = response.data.results || response.data || [];
      console.log('Pipelines loaded from API:', pipelineList.map((p: any) => ({
        id: p.id,
        name: p.name,
        slug: p.slug
      })));
      setPipelines(pipelineList);
    } catch (error) {
      console.error('Failed to load pipelines:', error);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await usersApi.list();
      setUsers(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadUserTypes = async () => {
    try {
      const response = await permissionsApi.getUserTypes();
      setUserTypes(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to load user types:', error);
    }
  };

  const loadUnipileAccounts = async () => {
    try {
      const response = await communicationsApi.getConnections();
      const accounts = response.data.results || response.data || [];
      setUnipileAccounts(accounts);
    } catch (error) {
      console.error('Failed to load UniPile accounts:', error);
    }
  };

  const loadWorkflows = async () => {
    try {
      const response = await workflowsApi.list();
      setWorkflows(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to load workflows:', error);
    }
  };

  const loadPipelineFields = async (pipelineId: string) => {
    // Skip if no pipeline ID or if it's invalid
    if (!pipelineId || pipelineId === 'undefined' || pipelineId === 'null') {
      console.warn('Invalid pipeline ID:', pipelineId);
      return;
    }

    // Skip if we already have fields for this pipeline
    if (pipelineFieldsMap[pipelineId]) {
      console.log('Fields already loaded for pipeline:', pipelineId);
      return;
    }

    try {
      console.log('Loading fields for pipeline:', pipelineId);
      const response = await pipelinesApi.getFields(pipelineId);
      // Handle both paginated and non-paginated responses
      const fields = Array.isArray(response.data)
        ? response.data
        : (response.data?.results || response.data?.fields || []);

      // Ensure fields is always an array
      const fieldsArray = Array.isArray(fields) ? fields : [];
      console.log('Loaded fields:', fieldsArray.length);

      // Store fields in the map keyed by pipeline ID
      setPipelineFieldsMap(prev => ({
        ...prev,
        [pipelineId]: fieldsArray
      }));

      // Store metadata for selected fields
      const metadata: Record<string, any> = {};
      fieldsArray.forEach((field: any) => {
        metadata[field.name] = {
          type: field.field_type,
          options: getFieldOptions(field)
        };
      });
      setSelectedFieldsMetadata(prev => ({
        ...prev,
        ...metadata
      }));
    } catch (error: any) {
      console.error('Failed to load fields for pipeline', pipelineId, ':', error);
      console.error('Error details:', error.response?.data || error.message);
    }
  };

  /**
   * Extract predefined options from field configuration based on field type.
   */
  const getFieldOptions = (field: any) => {
    const fieldType = field.field_type;
    const fieldConfig = field.field_config || {};

    switch (fieldType) {
      case 'select':
      case 'multiselect':
        return fieldConfig.options || [];
      case 'boolean':
        return [
          { value: 'true', label: 'True' },
          { value: 'false', label: 'False' }
        ];
      default:
        return [];
    }
  };

  // Memoize the onChange handler to prevent infinite loops
  const handleUnifiedConfigChange = useCallback((newConfig: any) => {
    setConfig(newConfig);
    onUpdate({ ...nodeData, config: newConfig });

    // Auto-fetch pipeline fields when a pipeline is selected (single)
    if (newConfig.pipeline_id && newConfig.pipeline_id !== config.pipeline_id) {
      loadPipelineFields(newConfig.pipeline_id);
    }

    // Auto-fetch pipeline fields when pipelines are selected (multi)
    if (newConfig.pipeline_ids && Array.isArray(newConfig.pipeline_ids)) {
      const previousIds = config.pipeline_ids || [];
      const newIds = newConfig.pipeline_ids.filter((id: string) => !previousIds.includes(id));
      // Fetch fields for newly selected pipelines
      newIds.forEach((id: string) => loadPipelineFields(id));
    }
  }, [nodeData, onUpdate, config]);

  // Get the unified configuration from backend
  const { config: unifiedConfig, loading: configLoading, error: configError } = useNodeConfig(nodeType);

  console.log('NodeParametersTab render:', {
    nodeType,
    unifiedConfig,
    configLoading,
    configError,
    nodeData
  });

  if (configLoading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <span className="text-sm text-muted-foreground mt-2">Loading configuration...</span>
      </div>
    );
  }

  if (configError) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <AlertCircle className="h-8 w-8 mx-auto mb-2 text-destructive" />
        <p className="text-sm font-medium">Failed to load configuration</p>
        <p className="text-xs mt-1">{configError}</p>
        <p className="text-xs mt-1">Node type: {nodeType}</p>
      </div>
    );
  }

  if (!unifiedConfig) {
    // No configuration available for this node type
    return (
      <div className="p-4 text-center text-muted-foreground">
        <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No configuration available for this node type</p>
        <p className="text-xs mt-1">Node type: {nodeType}</p>
      </div>
    );
  }

  // Get the appropriate pipeline fields based on current config
  const getCurrentPipelineFields = () => {
    // For single pipeline selection
    if (config.pipeline_id) {
      return pipelineFieldsMap[config.pipeline_id];
    }
    // For multiple pipeline selection, aggregate all fields
    if (config.pipeline_ids && Array.isArray(config.pipeline_ids)) {
      const allFields: any[] = [];
      config.pipeline_ids.forEach((id: string) => {
        if (pipelineFieldsMap[id]) {
          allFields.push(...pipelineFieldsMap[id]);
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
  };

  // Use the unified configuration system
  return (
    <UnifiedConfigRenderer
      nodeConfig={unifiedConfig}
      config={config}
      onChange={handleUnifiedConfigChange}
      availableVariables={availableVariables}
      pipelines={pipelines}
      pipelineFields={getCurrentPipelineFields()}
      users={users}
      userTypes={userTypes}
      unipileAccounts={unipileAccounts}
      workflows={workflows}
      errors={errors}
    />
  );
}