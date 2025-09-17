'use client';

import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  X, Play, AlertCircle, CheckCircle, ChevronDown, ChevronRight,
  Info, Settings, FileJson, Table, Code, Copy, RefreshCw,
  Zap, Clock, RotateCw, Package, FileText, HelpCircle, GitBranch
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowNodeType } from '../types';
import { NodeParametersTab } from './configuration/NodeParametersTab';
import { NodeSettingsTab } from './configuration/NodeSettingsTab';
import { NodeOutputTab } from './configuration/NodeOutputTab';
import { toast } from 'sonner';

interface NodeConfigurationPanelProps {
  nodeId: string | null;
  nodeType: WorkflowNodeType | null;
  nodeData: any;
  workflowId?: string;
  availableVariables: Array<{ nodeId: string; label: string; outputs: string[] }>;
  onUpdate: (nodeId: string, data: any) => void;
  onClose: () => void;
  onTest?: (nodeId: string, testRecordId?: string) => Promise<any>;
}

export function NodeConfigurationPanel({
  nodeId,
  nodeType,
  nodeData,
  workflowId,
  availableVariables,
  onUpdate,
  onClose,
  onTest
}: NodeConfigurationPanelProps) {
  const [activeTab, setActiveTab] = useState('parameters');
  const [testing, setTesting] = useState(false);
  const [testOutput, setTestOutput] = useState<any>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Reset when node changes
  useEffect(() => {
    if (nodeId) {
      setActiveTab('parameters');
      setTestOutput(null);
      setTestError(null);
      setHasChanges(false);
      setValidationErrors({});
    }
  }, [nodeId]);

  const handleTest = async (testRecordId?: string) => {
    if (!nodeId || !onTest) return;

    setTesting(true);
    setTestError(null);
    try {
      const result = await onTest(nodeId, testRecordId);
      setTestOutput(result);
      setActiveTab('output'); // Switch to output tab after testing
      toast.success('Node tested successfully');
    } catch (error: any) {
      setTestError(error.message || 'Test failed');
      toast.error('Test failed: ' + (error.message || 'Unknown error'));
    } finally {
      setTesting(false);
    }
  };

  const handleUpdate = (data: any) => {
    if (!nodeId) return;
    setHasChanges(true);
    onUpdate(nodeId, data);
  };

  const getNodeIcon = () => {
    if (!nodeType) return <Zap className="h-4 w-4" />;

    // Return appropriate icon based on node type
    if (nodeType.includes('TRIGGER')) return <Zap className="h-4 w-4" />;
    if (nodeType.includes('AI')) return <Zap className="h-4 w-4 text-purple-500" />;
    if (nodeType.includes('RECORD')) return <Package className="h-4 w-4 text-orange-500" />;
    if (nodeType.includes('CONDITION')) return <GitBranch className="h-4 w-4 text-yellow-500" />;
    return <Zap className="h-4 w-4" />;
  };

  const getNodeLabel = () => {
    if (!nodeType) return 'Configure Node';

    // Convert enum to readable label
    return nodeType
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  if (!nodeId || !nodeType) return null;

  return (
    <div className="w-96 h-full bg-background border-l flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b bg-card flex-shrink-0">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className={cn(
              "p-1.5 rounded-lg",
              nodeType?.includes('TRIGGER') && "bg-blue-100 text-blue-600",
              nodeType?.includes('AI') && "bg-purple-100 text-purple-600",
              nodeType?.includes('RECORD') && "bg-orange-100 text-orange-600"
            )}>
              {getNodeIcon()}
            </div>
            <div>
              <h3 className="font-semibold text-sm">{getNodeLabel()}</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Node ID: {nodeId.slice(-8)}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 -mr-2"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="default"
            className="flex-1"
            onClick={() => handleTest()}
            disabled={testing || Object.keys(validationErrors).length > 0}
          >
            {testing ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 mr-1.5" />
                Test Node
              </>
            )}
          </Button>

          {hasChanges && (
            <Badge variant="secondary" className="text-xs">
              Unsaved
            </Badge>
          )}
        </div>

        {/* Validation Status */}
        {Object.keys(validationErrors).length > 0 && (
          <div className="mt-3 p-2 bg-destructive/10 rounded-lg">
            <div className="flex items-center gap-1.5 text-destructive">
              <AlertCircle className="h-3.5 w-3.5" />
              <span className="text-xs font-medium">
                {Object.keys(validationErrors).length} validation error(s)
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
        <TabsList className="grid w-full grid-cols-3 p-1 mx-4 mt-4" style={{ width: 'calc(100% - 2rem)' }}>
          <TabsTrigger value="parameters" className="text-xs">
            <FileText className="h-3.5 w-3.5 mr-1" />
            Parameters
          </TabsTrigger>
          <TabsTrigger value="settings" className="text-xs">
            <Settings className="h-3.5 w-3.5 mr-1" />
            Settings
          </TabsTrigger>
          <TabsTrigger value="output" className="text-xs relative">
            <FileJson className="h-3.5 w-3.5 mr-1" />
            Output
            {testOutput && (
              <div className="absolute -top-1 -right-1 h-2 w-2 bg-green-500 rounded-full" />
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="parameters" className="flex-1 overflow-auto p-4 mt-4">
          <NodeParametersTab
            nodeType={nodeType}
            nodeData={nodeData}
            availableVariables={availableVariables}
            onUpdate={handleUpdate}
            onValidationChange={setValidationErrors}
          />
        </TabsContent>

        <TabsContent value="settings" className="flex-1 overflow-auto p-4 mt-4">
          <NodeSettingsTab
            nodeData={nodeData}
            onUpdate={handleUpdate}
          />
        </TabsContent>

        <TabsContent value="output" className="flex-1 overflow-auto p-4 mt-4">
          <NodeOutputTab
            output={testOutput}
            error={testError}
            loading={testing}
            nodeId={nodeId}
            nodeType={nodeType}
            nodeData={nodeData}
            workflowId={workflowId}
            onTest={handleTest}
          />
        </TabsContent>
      </Tabs>

      {/* Footer Help */}
      <div className="p-3 border-t bg-muted/30 flex-shrink-0">
        <div className="flex items-start gap-2">
          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground mt-0.5" />
          <div className="text-xs text-muted-foreground">
            <p className="font-medium mb-1">Tips:</p>
            <ul className="space-y-0.5">
              <li>• Click on fields to insert variables</li>
              <li>• Test node to preview output</li>
              <li>• Use settings for retry logic</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}