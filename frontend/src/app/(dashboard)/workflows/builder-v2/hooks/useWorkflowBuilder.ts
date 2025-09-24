/**
 * useWorkflowBuilder Hook
 * Simple state management for workflow builder
 */

import { useState, useCallback } from 'react';
import { WorkflowDefinition, WorkflowNode, WorkflowEdge } from '../types';

interface UseWorkflowBuilderProps {
  initialDefinition?: WorkflowDefinition;
  onChange?: (definition: WorkflowDefinition) => void;
}

export function useWorkflowBuilder({
  initialDefinition = { nodes: [], edges: [] },
  onChange
}: UseWorkflowBuilderProps = {}) {
  const [definition, setDefinition] = useState<WorkflowDefinition>(initialDefinition);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeConfigs, setNodeConfigs] = useState<Record<string, any>>({});

  // Initialize nodeOutputs with any stored lastOutput from nodes
  const [nodeOutputs, setNodeOutputs] = useState<Record<string, any>>(() => {
    const outputs: Record<string, any> = {};
    initialDefinition.nodes.forEach(node => {
      if (node.data?.lastOutput) {
        outputs[node.id] = node.data.lastOutput;
      }
    });
    return outputs;
  });

  // Update definition and notify parent
  const updateDefinition = useCallback((newDefinition: WorkflowDefinition) => {
    setDefinition(newDefinition);
    onChange?.(newDefinition);
  }, [onChange]);

  // Add a new node
  const addNode = useCallback((node: WorkflowNode) => {
    const newDefinition = {
      ...definition,
      nodes: [...definition.nodes, node]
    };
    updateDefinition(newDefinition);

    // Initialize config for the node
    if (node.data.config) {
      setNodeConfigs(prev => ({
        ...prev,
        [node.id]: node.data.config
      }));
    }
  }, [definition, updateDefinition]);

  // Update node position
  const updateNodePosition = useCallback((nodeId: string, position: { x: number; y: number }) => {
    const newNodes = definition.nodes.map(node =>
      node.id === nodeId ? { ...node, position } : node
    );
    updateDefinition({ ...definition, nodes: newNodes });
  }, [definition, updateDefinition]);

  // Update node configuration
  const updateNodeConfig = useCallback((nodeId: string, config: any) => {
    setNodeConfigs(prev => ({
      ...prev,
      [nodeId]: config
    }));

    // Also update in the node data
    const newNodes = definition.nodes.map(node =>
      node.id === nodeId
        ? { ...node, data: { ...node.data, config } }
        : node
    );
    updateDefinition({ ...definition, nodes: newNodes });
  }, [definition, updateDefinition]);

  // Remove a node
  const removeNode = useCallback((nodeId: string) => {
    const newNodes = definition.nodes.filter(n => n.id !== nodeId);
    const newEdges = definition.edges.filter(e => e.source !== nodeId && e.target !== nodeId);
    updateDefinition({ nodes: newNodes, edges: newEdges });

    // Clean up config
    setNodeConfigs(prev => {
      const newConfigs = { ...prev };
      delete newConfigs[nodeId];
      return newConfigs;
    });

    // Clear selection if removed node was selected
    if (selectedNodeId === nodeId) {
      setSelectedNodeId(null);
    }
  }, [definition, selectedNodeId, updateDefinition]);

  // Add an edge
  const addEdge = useCallback((edge: WorkflowEdge) => {
    const newDefinition = {
      ...definition,
      edges: [...definition.edges, edge]
    };
    updateDefinition(newDefinition);
  }, [definition, updateDefinition]);

  // Remove an edge
  const removeEdge = useCallback((edgeId: string) => {
    const newEdges = definition.edges.filter(e => e.id !== edgeId);
    updateDefinition({ ...definition, edges: newEdges });
  }, [definition, updateDefinition]);

  // Select a node
  const selectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  // Update node output (e.g., after testing/execution)
  const updateNodeOutput = useCallback((nodeId: string, output: any) => {
    setNodeOutputs(prev => ({
      ...prev,
      [nodeId]: output
    }));

    // Also store in the node's data for persistence
    const newNodes = definition.nodes.map(node =>
      node.id === nodeId
        ? { ...node, data: { ...node.data, lastOutput: output } }
        : node
    );
    updateDefinition({ ...definition, nodes: newNodes });
  }, [definition, updateDefinition]);

  // Get selected node
  const selectedNode = definition.nodes.find(n => n.id === selectedNodeId) || null;
  const selectedNodeConfig = selectedNodeId ? nodeConfigs[selectedNodeId] : null;

  return {
    // State
    definition,
    selectedNodeId,
    selectedNode,
    selectedNodeConfig,
    nodeConfigs,
    nodeOutputs,

    // Actions
    addNode,
    updateNodePosition,
    updateNodeConfig,
    updateNodeOutput,
    removeNode,
    addEdge,
    removeEdge,
    selectNode,
    setDefinition: updateDefinition
  };
}