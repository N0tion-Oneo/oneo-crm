import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronRight, ChevronDown, Database, Copy, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface WorkflowContextPanelProps {
  context: Record<string, any>;
  isLoading?: boolean;
}

export function WorkflowContextPanel({ context, isLoading }: WorkflowContextPanelProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [copiedPath, setCopiedPath] = useState<string | null>(null);

  const toggleNode = (nodeId: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const copyToClipboard = (path: string) => {
    navigator.clipboard.writeText(`{{${path}}}`);
    setCopiedPath(path);
    setTimeout(() => setCopiedPath(null), 2000);
  };

  const renderValue = (value: any, path: string = '', depth: number = 0): JSX.Element => {
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground italic">null</span>;
    }

    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      return (
        <div className="flex items-center justify-between group">
          <span className="text-sm font-mono">{String(value)}</span>
          {path && (
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-2 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => copyToClipboard(path)}
            >
              {copiedPath === path ? (
                <CheckCircle2 className="h-3 w-3 text-green-500" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>
          )}
        </div>
      );
    }

    if (Array.isArray(value)) {
      return (
        <div className="space-y-1">
          <span className="text-xs text-muted-foreground">Array ({value.length} items)</span>
          <div className="ml-4 space-y-1">
            {value.slice(0, 5).map((item, index) => (
              <div key={index} className="text-sm">
                [{index}]: {renderValue(item, `${path}[${index}]`, depth + 1)}
              </div>
            ))}
            {value.length > 5 && (
              <span className="text-xs text-muted-foreground">... and {value.length - 5} more</span>
            )}
          </div>
        </div>
      );
    }

    if (typeof value === 'object') {
      const entries = Object.entries(value);
      return (
        <div className="space-y-1">
          {entries.map(([key, val]) => (
            <div key={key} className="border-l-2 border-muted pl-3 py-1">
              <div className="flex items-center justify-between group">
                <span className="text-sm font-medium text-muted-foreground">{key}:</span>
                {path && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => copyToClipboard(`${path}.${key}`)}
                  >
                    {copiedPath === `${path}.${key}` ? (
                      <CheckCircle2 className="h-3 w-3 text-green-500" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                )}
              </div>
              <div className="ml-2">
                {renderValue(val, path ? `${path}.${key}` : key, depth + 1)}
              </div>
            </div>
          ))}
        </div>
      );
    }

    return <span className="text-sm">{String(value)}</span>;
  };

  const nodeOutputs = context.nodes || {};
  const hasNodeOutputs = Object.keys(nodeOutputs).length > 0;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Database className="h-4 w-4" />
          Workflow Context
        </CardTitle>
        <CardDescription className="text-xs">
          Available data from previous nodes
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full px-4 pb-4">
          {isLoading ? (
            <div className="text-sm text-muted-foreground text-center py-8">
              Loading context...
            </div>
          ) : !hasNodeOutputs ? (
            <div className="text-sm text-muted-foreground text-center py-8">
              <Database className="h-8 w-8 mx-auto mb-2 opacity-30" />
              <p>No context data available</p>
              <p className="text-xs mt-2">Execute nodes to see their outputs</p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Node Outputs
              </div>
              {Object.entries(nodeOutputs).map(([nodeId, outputs]) => (
                <Collapsible
                  key={nodeId}
                  open={expandedNodes.has(nodeId)}
                  onOpenChange={() => toggleNode(nodeId)}
                >
                  <CollapsibleTrigger className="flex items-center gap-2 w-full text-left hover:bg-muted/50 p-2 rounded-md transition-colors">
                    {expandedNodes.has(nodeId) ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    <Badge variant="outline" className="text-xs">
                      {nodeId}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {outputs && typeof outputs === 'object' ?
                        `${Object.keys(outputs).length} fields` :
                        'data'
                      }
                    </span>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-2 ml-5">
                    <div className="bg-muted/30 rounded-md p-3">
                      {renderValue(outputs, nodeId)}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              ))}
            </div>
          )}

          {/* Other context data */}
          {Object.keys(context).filter(k => k !== 'nodes').length > 0 && (
            <>
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mt-6 mb-3">
                Other Context
              </div>
              <div className="space-y-2">
                {Object.entries(context).filter(([k]) => k !== 'nodes').map(([key, value]) => (
                  <div key={key} className="bg-muted/30 rounded-md p-3">
                    <div className="text-xs font-medium mb-1">{key}</div>
                    {renderValue(value, key)}
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Helper text */}
          <div className="mt-6 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-md">
            <p className="text-xs text-blue-700 dark:text-blue-300">
              <strong>Tip:</strong> Click the copy button next to any value to copy its template variable path.
              Use these paths in your node configurations like: <code className="font-mono bg-white/50 dark:bg-black/30 px-1 rounded">{'{{node-id.field}}'}</code>
            </p>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}