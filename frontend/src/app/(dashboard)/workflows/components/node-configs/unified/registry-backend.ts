/**
 * New registry that fetches all node configurations from the backend
 * This replaces the old registry.ts to make backend the single source of truth
 */

import { WorkflowNodeType } from '../../../types';
import { UnifiedNodeConfig, NodeConfigRegistry } from './types';
import { workflowSchemaService } from '@/services/workflowSchemaService';

/**
 * Get the configuration for a specific node type from backend
 */
export async function getNodeConfig(nodeType: WorkflowNodeType): Promise<UnifiedNodeConfig | undefined> {
  try {
    const config = await workflowSchemaService.getNodeConfig(nodeType);
    return config || undefined;
  } catch (error) {
    console.error(`Failed to fetch config for ${nodeType}:`, error);
    return undefined;
  }
}

/**
 * Check if a node type has a configuration (async now)
 */
export async function hasNodeConfig(nodeType: WorkflowNodeType): Promise<boolean> {
  const config = await getNodeConfig(nodeType);
  return config !== undefined;
}

/**
 * Get all available node configurations from backend
 */
export async function getAllNodeConfigs(): Promise<UnifiedNodeConfig[]> {
  try {
    const schemas = await workflowSchemaService.fetchSchemas();
    const configs: UnifiedNodeConfig[] = [];

    // Transform all backend schemas to UnifiedNodeConfig
    for (const [backendType, schema] of Object.entries(schemas)) {
      // Map backend type to frontend WorkflowNodeType
      const frontendType = mapBackendToFrontendType(backendType);
      if (frontendType) {
        const config = await workflowSchemaService.getNodeConfig(frontendType);
        if (config) {
          configs.push(config);
        }
      }
    }

    return configs;
  } catch (error) {
    console.error('Failed to fetch all node configs:', error);
    return [];
  }
}

/**
 * Get node configurations by category
 */
export async function getNodeConfigsByCategory(category: UnifiedNodeConfig['category']): Promise<UnifiedNodeConfig[]> {
  const allConfigs = await getAllNodeConfigs();
  return allConfigs.filter(config => config.category === category);
}

/**
 * Map backend node type to frontend WorkflowNodeType
 * This is the inverse of the mapping in workflowSchemaService
 */
function mapBackendToFrontendType(backendType: string): WorkflowNodeType | null {
  const mapping: Record<string, WorkflowNodeType> = {
    // Data operations
    'RECORD_CREATE': WorkflowNodeType.RECORD_CREATE,
    'RECORD_UPDATE': WorkflowNodeType.RECORD_UPDATE,
    'RECORD_FIND': WorkflowNodeType.RECORD_FIND,
    'RECORD_DELETE': WorkflowNodeType.RECORD_DELETE,

    // AI nodes
    'AI_PROMPT': WorkflowNodeType.AI_PROMPT,
    'AI_ANALYSIS': WorkflowNodeType.AI_ANALYSIS,
    'AI_MESSAGE_GENERATOR': WorkflowNodeType.AI_MESSAGE_GENERATOR,
    'AI_RESPONSE_EVALUATOR': WorkflowNodeType.AI_RESPONSE_EVALUATOR,
    'AI_CONVERSATION_LOOP': WorkflowNodeType.AI_CONVERSATION_LOOP,

    // Communication
    'EMAIL': WorkflowNodeType.UNIPILE_SEND_EMAIL,
    'WHATSAPP': WorkflowNodeType.UNIPILE_SEND_WHATSAPP,
    'LINKEDIN': WorkflowNodeType.UNIPILE_SEND_LINKEDIN,
    'SMS': WorkflowNodeType.UNIPILE_SEND_SMS,

    // Control flow
    'CONDITION': WorkflowNodeType.CONDITION,
    'FOR_EACH': WorkflowNodeType.FOR_EACH,
    'WORKFLOW_LOOP': WorkflowNodeType.WORKFLOW_LOOP_CONTROLLER,
    'WAIT_DELAY': WorkflowNodeType.WAIT_DELAY,
    'WAIT_FOR_RESPONSE': WorkflowNodeType.WAIT_FOR_RESPONSE,
    'WAIT_FOR_RECORD_EVENT': WorkflowNodeType.WAIT_FOR_RECORD_EVENT,
    'WAIT_FOR_CONDITION': WorkflowNodeType.WAIT_FOR_CONDITION,

    // External
    'HTTP_REQUEST': WorkflowNodeType.HTTP_REQUEST,
    'WEBHOOK_OUT': WorkflowNodeType.WEBHOOK_OUT,

    // Utility
    'TASK_NOTIFY': WorkflowNodeType.TASK_NOTIFY,
    'CONVERSATION_STATE': WorkflowNodeType.CONVERSATION_STATE,

    // CRM
    'CONTACT_RESOLVE': WorkflowNodeType.RESOLVE_CONTACT,
    'CREATE_FOLLOW_UP_TASK': WorkflowNodeType.CREATE_FOLLOW_UP_TASK,
    'CONTACT_STATUS_UPDATE': WorkflowNodeType.UPDATE_CONTACT_STATUS,

    // Workflow
    'SUB_WORKFLOW': WorkflowNodeType.SUB_WORKFLOW,

    // Data
    'MERGE_DATA': WorkflowNodeType.MERGE_DATA,

    // More mappings can be added as needed
  };

  const frontendType = mapping[backendType];
  if (!frontendType) {
    console.warn(`No frontend mapping for backend type: ${backendType}`);
  }
  return frontendType || null;
}

/**
 * Preload all schemas at app startup for better performance
 */
export async function preloadSchemas(): Promise<void> {
  try {
    await workflowSchemaService.fetchSchemas();
    console.log('Backend schemas preloaded successfully');
  } catch (error) {
    console.error('Failed to preload schemas:', error);
  }
}

// Export a compatibility layer that matches the old registry API
// but now everything comes from backend
export const nodeConfigRegistry = new Proxy({} as Partial<NodeConfigRegistry>, {
  get: (_target, prop) => {
    console.warn('Direct nodeConfigRegistry access is deprecated. Use getNodeConfig() instead.');
    // Return undefined for any direct access - force using async getNodeConfig()
    return undefined;
  }
});