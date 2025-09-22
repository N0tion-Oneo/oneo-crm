/**
 * NodePalette Component
 * Backend-driven palette of draggable workflow nodes
 */

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronRight, ChevronDown, Search } from 'lucide-react';
import { useNodeSchemas } from '../hooks/useNodeSchemas';
import { NodeDefinition } from '../types';
import { cn } from '@/lib/utils';

export function NodePalette() {
  const { nodeCategories, loading, error } = useNodeSchemas();
  const [search, setSearch] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['Triggers', 'Data', 'AI']) // Default expanded
  );

  const toggleCategory = (categoryId: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  const onDragStart = (event: React.DragEvent, node: NodeDefinition) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: node.type,
      label: node.label,
      icon: node.icon
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  // Filter nodes based on search
  const filteredCategories = nodeCategories.map(category => ({
    ...category,
    nodes: category.nodes.filter(node =>
      node.label.toLowerCase().includes(search.toLowerCase()) ||
      node.type.toLowerCase().includes(search.toLowerCase())
    )
  })).filter(category => category.nodes.length > 0);

  if (loading) {
    return (
      <div className="p-4 text-center text-sm text-muted-foreground">
        Loading nodes...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-sm text-red-500">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="p-4 border-b">
        <h3 className="font-semibold text-sm mb-3">Node Palette</h3>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search nodes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-9"
          />
        </div>
      </div>

      {/* Node Categories */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {filteredCategories.map(category => (
            <Collapsible
              key={category.id}
              open={expandedCategories.has(category.id)}
              onOpenChange={() => toggleCategory(category.id)}
            >
              <CollapsibleTrigger className="flex items-center justify-between w-full p-2 hover:bg-accent rounded-md transition-colors">
                <span className="text-sm font-medium">{category.label}</span>
                <div className="flex items-center gap-1">
                  <span className="text-xs text-muted-foreground">
                    {category.nodes.length}
                  </span>
                  {expandedCategories.has(category.id) ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </div>
              </CollapsibleTrigger>

              <CollapsibleContent className="mt-1">
                <div className="space-y-1 pl-2">
                  {category.nodes.map(node => (
                    <div
                      key={node.type}
                      draggable
                      onDragStart={(e) => onDragStart(e, node)}
                      className={cn(
                        "flex items-center gap-2 p-2 rounded-md cursor-move",
                        "hover:bg-accent transition-colors",
                        "border border-transparent hover:border-border"
                      )}
                    >
                      {node.icon && (
                        <span className="text-base">{node.icon}</span>
                      )}
                      <span className="text-sm truncate">{node.label}</span>
                    </div>
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          ))}
        </div>
      </ScrollArea>

      {/* Help text */}
      <div className="p-3 border-t">
        <p className="text-xs text-muted-foreground">
          Drag nodes onto the canvas to add them to your workflow
        </p>
      </div>
    </div>
  );
}