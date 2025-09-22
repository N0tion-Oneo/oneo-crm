/**
 * WorkflowBuilder V2 Component
 * Main component that orchestrates the workflow building experience
 * Simple, clean, backend-driven architecture
 */

'use client';

import React, { useState } from 'react';
import { WorkflowCanvas } from './components/WorkflowCanvas';
import { NodePalette } from './components/NodePalette';
import { NodeConfigModal } from './components/NodeConfigModal';
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

  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

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

  // Handle node configuration save
  const handleNodeConfigSave = React.useCallback((config: any) => {
    if (selectedNodeId) {
      updateNodeConfig(selectedNodeId, config);
    }
    setIsConfigModalOpen(false);
  }, [selectedNodeId, updateNodeConfig]);

  // Handle node double-click to open config modal
  const handleNodeDoubleClick = React.useCallback((nodeId: string) => {
    selectNode(nodeId);
    setIsConfigModalOpen(true);
  }, [selectNode]);

  // Handle modal close
  const handleModalClose = React.useCallback(() => {
    setIsConfigModalOpen(false);
  }, []);

  return (
    <div className={cn('flex h-full bg-background', className)}>
      {/* Left Panel - Node Palette */}
      <div className="w-64 border-r border-border flex-shrink-0">
        <NodePalette />
      </div>

      {/* Main Canvas - Full Width */}
      <div className="flex-1 relative">
        <WorkflowCanvas
          definition={definition}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onNodeSelect={selectNode}
          onNodeAdd={addNode}
          onNodeDoubleClick={handleNodeDoubleClick}
          selectedNodeId={selectedNodeId}
          nodeConfigs={nodeConfigs}
        />
      </div>

      {/* Configuration Modal */}
      <NodeConfigModal
        isOpen={isConfigModalOpen}
        onClose={handleModalClose}
        node={selectedNode}
        config={selectedNodeConfig}
        onConfigChange={handleNodeConfigChange}
        onSave={handleNodeConfigSave}
        workflowDefinition={definition}
      />
    </div>
  );
}