/**
 * Registry for node configurations
 * Maps node types to their configuration definitions
 *
 * NOTE: All configurations now come from backend schemas
 * This registry is kept empty as we use backend as the single source of truth
 */
import { WorkflowNodeType } from '../../../types';
import { UnifiedNodeConfig, NodeConfigRegistry } from './types';

/**
 * Central registry of node configurations.
 * ALL nodes now use backend schemas via workflowSchemaService.
 * Frontend configs have been removed - backend is the single source of truth.
 */
export const nodeConfigRegistry: Partial<NodeConfigRegistry> = {
  // Empty - all configs come from backend
};

/**
 * Get the configuration for a specific node type
 * @deprecated Use workflowSchemaService.getNodeConfig() instead
 */
export function getNodeConfig(nodeType: WorkflowNodeType): UnifiedNodeConfig | undefined {
  return nodeConfigRegistry[nodeType];
}

/**
 * Check if a node type has a configuration
 * @deprecated Use workflowSchemaService.getNodeConfig() instead
 */
export function hasNodeConfig(nodeType: WorkflowNodeType): boolean {
  return nodeType in nodeConfigRegistry;
}

/**
 * Get all available node configurations
 * @deprecated Use workflowSchemaService.fetchSchemas() instead
 */
export function getAllNodeConfigs(): UnifiedNodeConfig[] {
  return Object.values(nodeConfigRegistry).filter(Boolean) as UnifiedNodeConfig[];
}

/**
 * Get node configurations by category
 * @deprecated Use workflowSchemaService with filtering instead
 */
export function getNodeConfigsByCategory(category: UnifiedNodeConfig['category']): UnifiedNodeConfig[] {
  return getAllNodeConfigs().filter(config => config.category === category);
}