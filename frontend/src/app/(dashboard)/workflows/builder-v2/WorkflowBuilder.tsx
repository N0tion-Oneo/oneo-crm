/**
 * WorkflowBuilder V2 Component
 * Main component that orchestrates the workflow building experience
 * Simple, clean, backend-driven architecture
 */

'use client';

import React from 'react';
import { WorkflowCanvas } from './components/WorkflowCanvas';
import { NodePalette } from './components/NodePalette';
import { NodeConfiguration } from './components/NodeConfiguration';
import { useWorkflowBuilder } from './hooks/useWorkflowBuilder';
import { WorkflowDefinition } from './types';
import { cn } from '@/lib/utils';

interface WorkflowBuilderProps {
  initialDefinition?: WorkflowDefinition;
  onChange?: (definition: WorkflowDefinition) => void;
  className?: string;
}

export function WorkflowBuilder({
  initialDefinition,
  onChange,
  className,
}: WorkflowBuilderProps) {
  const {
    definition,
    selectedNodeId,
    selectedNode,
    selectedNodeConfig,
    nodeConfigs,
    addNode,
    updateNodePosition,
    updateNodeConfig,
    removeNode,
    addEdge,
    removeEdge,
    selectNode,
    setDefinition,
  } = useWorkflowBuilder({ initialDefinition, onChange });

  // Handle nodes change from canvas - now only called when drag ends or nodes change
  const handleNodesChange = React.useCallback((nodes: any[]) => {
    // Simply update the definition with the new nodes
    setDefinition({ ...definition, nodes });
  }, [definition, setDefinition]);

  // Handle edges change from canvas
  const handleEdgesChange = React.useCallback((edges: any[]) => {
    setDefinition({ ...definition, edges });
  }, [definition, setDefinition]);

  // Handle node configuration change
  const handleNodeConfigChange = React.useCallback((config: any) => {
    if (selectedNodeId) {
      updateNodeConfig(selectedNodeId, config);
    }
  }, [selectedNodeId, updateNodeConfig]);

  return (
    <div className={cn('flex h-full bg-background', className)}>
      {/* Left Panel - Node Palette */}
      <div className="w-64 border-r border-border flex-shrink-0">
        <NodePalette />
      </div>

      {/* Center - Canvas */}
      <div className="flex-1 relative">
        <WorkflowCanvas
          definition={definition}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onNodeSelect={selectNode}
          onNodeAdd={addNode}
          selectedNodeId={selectedNodeId}
          nodeConfigs={nodeConfigs}
        />
      </div>

      {/* Right Panel - Node Configuration */}
      <div className="w-96 border-l border-border flex-shrink-0">
        <NodeConfiguration
          node={selectedNode}
          config={selectedNodeConfig}
          onConfigChange={handleNodeConfigChange}
          onClose={() => selectNode(null)}
        />
      </div>
    </div>
  );
}