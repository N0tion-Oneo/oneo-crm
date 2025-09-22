/**
 * Workflow Builder V2 - Type Definitions
 * Simple, backend-driven type system
 */

import { WorkflowNodeType } from '../../types';

// Core workflow types - matching backend exactly
export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  position: { x: number; y: number };
  data: {
    label?: string;
    config?: Record<string, any>; // Node-specific configuration from backend
    [key: string]: any; // Allow backend to send additional data
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  label?: string;
  type?: string;
}

// Node palette types
export interface NodeCategory {
  id: string;
  label: string;
  icon?: React.ComponentType<any>;
  nodes: NodeDefinition[];
}

export interface NodeDefinition {
  type: WorkflowNodeType;
  label: string;
  description?: string;
  icon?: string;
  category: string;
}

// Builder state
export interface WorkflowBuilderState {
  definition: WorkflowDefinition;
  selectedNodeId: string | null;
  nodeConfigs: Record<string, any>; // Configurations keyed by node ID
}