/**
 * EnhancedDataView Component
 * Multi-mode data viewer with enhanced visualization
 */

import React, { useState, useMemo, useCallback, useEffect, Fragment } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ToggleGroup,
  ToggleGroupItem,
} from '@/components/ui/toggle-group';
import {
  Code2,
  TreePine,
  FileJson,
  Search,
  X,
  Copy,
  ChevronRight,
  ChevronDown,
  Database,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { DataTypeIcon, DataTypeBadge, detectDataType } from './DataTypeIcon';
import { FieldValuePreview, FieldRow } from './FieldValuePreview';
import { toast } from 'sonner';

type ViewMode = 'table' | 'tree' | 'json' | 'schema';

interface EnhancedDataViewProps {
  data: any;
  nodeId?: string;
  title?: string;
  className?: string;
  defaultView?: ViewMode;
  showViewToggle?: boolean;
  showSearch?: boolean;
  showActions?: boolean;
  maxHeight?: string;
  sources?: any[]; // Add sources to know about node grouping
  onFieldClick?: (path: string, value: any) => void;
  onFieldCopy?: (path: string, value: any) => void;
}

export function EnhancedDataView({
  data,
  nodeId,
  title,
  className,
  defaultView = 'tree',
  showViewToggle = true,
  showSearch = true,
  showActions = true,
  maxHeight = '400px',
  sources,
  onFieldClick,
  onFieldCopy
}: EnhancedDataViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>(defaultView);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

  // Create a mapping from label to nodeId for proper path copying
  const labelToNodeIdMap = useMemo(() => {
    const map: Record<string, string> = {};
    if (sources) {
      sources.forEach(source => {
        if (source.label && source.nodeId) {
          map[source.label] = `node_${source.nodeId}`;
        }
      });
    }
    return map;
  }, [sources]);

  // Flatten data structure for easier searching and display
  const flattenedData = useMemo(() => {
    const result: Array<{
      path: string;
      displayName: string;
      value: any;
      depth: number;
      type: string;
      parent?: string;
      nodeName?: string;
      isNodeHeader?: boolean;
    }> = [];

    const flatten = (obj: any, path: string = '', depth: number = 0, parent?: string, nodeName?: string, isNodeHeader: boolean = false) => {
      if (obj === null || obj === undefined) {
        const displayName = path.includes('.') ? path.split('.').pop()! : path;
        result.push({
          path,
          displayName: displayName.replace(/\[(\d+)\]/g, '[$1]'),
          value: obj,
          depth,
          type: detectDataType(obj),
          parent,
          nodeName,
          isNodeHeader: false
        });
        return;
      }

      const type = detectDataType(obj);
      const displayName = path.includes('.') ? path.split('.').pop()! : path;

      // Special handling for node headers - only add a header row, not the data itself
      if (isNodeHeader && type === 'object') {
        // Add just the node header
        result.push({
          path,
          displayName: path,
          value: obj,
          depth,
          type,
          parent,
          nodeName: path,
          isNodeHeader: true
        });

        // Process children as regular fields
        Object.entries(obj).forEach(([key, value]) => {
          const newPath = `${path}.${key}`;
          flatten(value, newPath, depth + 1, path, path, false);
        });
        return; // Don't continue processing
      }

      // Regular field processing
      result.push({
        path,
        displayName: displayName.replace(/\[(\d+)\]/g, '[$1]'),
        value: obj,
        depth,
        type,
        parent,
        nodeName,
        isNodeHeader: false
      });

      if (type === 'object' && obj && typeof obj === 'object') {
        Object.entries(obj).forEach(([key, value]) => {
          const newPath = path ? `${path}.${key}` : key;
          flatten(value, newPath, depth + 1, path, nodeName, false);
        });
      } else if (type === 'array' && Array.isArray(obj)) {
        obj.forEach((item, index) => {
          const newPath = `${path}[${index}]`;
          flatten(item, newPath, depth + 1, path, nodeName, false);
        });
      }
    };

    // Process data - when we have sources, data is always grouped by node names
    if (data && typeof data === 'object') {
      // Data should be in format: { NodeName: nodeData, ... }
      Object.entries(data).forEach(([nodeName, nodeData]) => {
        flatten(nodeData, nodeName, 0, undefined, nodeName, true);
      });
    } else if (data) {
      // Fallback for non-object data (shouldn't happen with our structure)
      flatten(data, 'Data', 0, undefined, 'Data', true);
    }

    return result;
  }, [data, nodeId]);

  // Initialize expanded paths - expand first level by default
  useEffect(() => {
    const firstLevelPaths = flattenedData
      .filter(item => item.depth === 0)
      .map(item => item.path);
    setExpandedPaths(new Set(firstLevelPaths));
  }, [data]); // Reset when data changes

  // Filter data based on search
  const filteredData = useMemo(() => {
    if (!searchQuery) return flattenedData;

    return flattenedData.filter(item => {
      const pathMatch = item.path.toLowerCase().includes(searchQuery.toLowerCase());
      const valueMatch = item.value && String(item.value).toLowerCase().includes(searchQuery.toLowerCase());
      return pathMatch || valueMatch;
    });
  }, [flattenedData, searchQuery]);

  // Toggle path expansion
  const toggleExpanded = (path: string) => {
    setExpandedPaths(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  // Expand all paths
  const expandAll = () => {
    const allExpandablePaths = flattenedData
      .filter(item => {
        const hasChildren = flattenedData.some(f => f.parent === item.path);
        return hasChildren;
      })
      .map(item => item.path);
    setExpandedPaths(new Set(allExpandablePaths));
  };

  // Collapse all paths
  const collapseAll = () => {
    setExpandedPaths(new Set());
  };

  // Render tree view as table (like DataTableView)
  const renderTreeView = () => {
    // Get visible items (respecting parent expansion state)
    const visibleItems = filteredData.filter(item => {
      if (!item.parent) return true;
      // Check if all parent paths are expanded
      let currentPath = item.parent;
      while (currentPath) {
        if (!expandedPaths.has(currentPath)) return false;
        const parentItem = filteredData.find(i => i.path === currentPath);
        currentPath = parentItem?.parent;
      }
      return true;
    });

    const renderRow = (item: any, index: number) => {
      const hasChildren = filteredData.some(f => f.parent === item.path);
      const isExpanded = expandedPaths.has(item.path);
      const childCount = filteredData.filter(f => f.parent === item.path).length;

      // Get background color based on type and depth
      const getRowBackground = () => {
        if (item.isNodeHeader) {
          return 'bg-blue-50 dark:bg-blue-950/20 border-l-4 border-blue-500';
        }
        switch (item.depth) {
          case 0:
            return '';
          case 1:
            return 'bg-muted/20';
          case 2:
            return 'bg-muted/40';
          default:
            return 'bg-muted/60';
        }
      };

      // Special rendering for node headers
      if (item.isNodeHeader) {
        return (
          <tr
            key={`${item.path}-${index}`}
            className={cn(
              'group transition-colors text-xs',
              getRowBackground()
            )}
          >
            <td colSpan={3} className="p-2">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={() => toggleExpanded(item.path)}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </Button>
                <Database className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <span className="font-semibold text-sm text-blue-700 dark:text-blue-300">
                  {/* Format node name: remove underscores and node IDs */}
                  {item.displayName
                    .replace(/_[a-f0-9]{8}.*$/, '') // Remove node ID suffix
                    .replace(/_/g, ' ') // Replace underscores with spaces
                    .replace(/([A-Z])/g, ' $1') // Add space before capital letters
                    .trim()}
                </span>
                {!isExpanded && childCount > 0 && (
                  <Badge variant="secondary" className="ml-2 text-[10px]">
                    {childCount} fields
                  </Badge>
                )}
              </div>
            </td>
          </tr>
        );
      }

      return (
        <tr
          key={`${item.path}-${index}`}
          className={cn(
            'group hover:bg-muted/80 transition-colors text-xs relative',
            getRowBackground()
          )}
        >
          {/* Field Path */}
          <td className="p-1 overflow-hidden">
            <div className="flex items-center gap-1">
              {/* Indentation based on depth, but adjust for node-grouped data */}
              <div style={{ width: `${(item.nodeName && !item.isNodeHeader ? item.depth - 1 : item.depth) * 20}px` }} />

              {/* Expand/Collapse button */}
              {hasChildren ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 flex-shrink-0"
                  onClick={() => toggleExpanded(item.path)}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                </Button>
              ) : (
                <div className="h-4 w-4 flex-shrink-0" />
              )}

              {/* Field name - show clean display name */}
              <div className="flex items-center gap-1">
                {item.depth > 1 && !item.displayName.startsWith('[') && (
                  <span className="text-muted-foreground text-xs">└</span>
                )}
                <code className={cn(
                  'font-mono text-xs',
                  item.depth === 0 && !item.nodeName ? 'font-semibold text-primary' : '',
                  item.nodeName && item.depth === 1 ? 'text-foreground' : '',
                  item.depth > 1 ? 'text-muted-foreground' : ''
                )} style={{ overflowWrap: 'anywhere', wordBreak: 'break-all' }}>
                  {item.displayName}
                </code>
              </div>

              {/* Child count */}
              {hasChildren && !isExpanded && childCount > 0 && (
                <Badge variant="secondary" className="ml-1 text-[10px] px-1 h-4 flex-shrink-0">
                  {childCount}
                </Badge>
              )}
            </div>
          </td>

          {/* Type */}
          <td className="p-1 whitespace-nowrap">
            <Badge
              variant="outline"
              className="text-[10px] px-1 py-0 h-4 font-mono"
            >
              {item.type}
            </Badge>
          </td>

          {/* Value */}
          <td className="p-1">
            <div className="text-xs overflow-hidden" style={{ overflowWrap: 'anywhere', wordBreak: 'break-all' }}>
              <FieldValuePreview
                value={item.value}
                path={item.path}
                maxLength={50}
                expandable={false}
                showType={false}
              />
            </div>
          </td>

          {/* Hover actions overlay - covers type and value columns */}
          <td className="absolute right-0 top-0 bottom-0 left-[40%] flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none">
            <div className="absolute inset-0 bg-muted/80 backdrop-blur-sm" />
            <div className="flex items-center gap-2 z-10 pointer-events-auto">
              <Button
                variant="secondary"
                size="sm"
                className="h-7 px-3 text-xs font-medium shadow-sm hover:bg-primary hover:text-primary-foreground transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  // Convert display label back to node_id for backend compatibility
                  let copyPath = item.path;
                  if (labelToNodeIdMap) {
                    // Check if the path starts with a label that needs to be mapped
                    const pathParts = item.path.split('.');
                    const firstPart = pathParts[0];
                    if (labelToNodeIdMap[firstPart]) {
                      // Replace the label with the node_id
                      pathParts[0] = labelToNodeIdMap[firstPart];
                      copyPath = pathParts.join('.');
                    }
                  }
                  const fieldPath = `{{${copyPath}}}`;
                  navigator.clipboard.writeText(fieldPath);
                  toast.success(`Copied path: ${fieldPath}`);
                }}
              >
                <Code2 className="h-3.5 w-3.5 mr-1.5" />
                Copy Path
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="h-7 px-3 text-xs font-medium shadow-sm hover:bg-primary hover:text-primary-foreground transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  const textToCopy = typeof item.value === 'string'
                    ? item.value
                    : JSON.stringify(item.value, null, 2);
                  navigator.clipboard.writeText(textToCopy);
                  toast.success('Value copied');
                }}
              >
                <Copy className="h-3.5 w-3.5 mr-1.5" />
                Copy Value
              </Button>
            </div>
          </td>
        </tr>
      );
    };

    return (
      <div className="overflow-hidden">
        <table className="w-full text-xs">
          <colgroup>
            <col style={{ width: '40%' }} />
            <col style={{ width: '15%' }} />
            <col style={{ width: '45%' }} />
          </colgroup>
          <thead className="sticky top-0 z-10 bg-background border-b">
            <tr>
              <th className="text-left p-1 text-xs font-medium">Field Path</th>
              <th className="text-left p-1 text-xs font-medium">Type</th>
              <th className="text-left p-1 text-xs font-medium">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {visibleItems.length > 0 ? (
              visibleItems.map((item, index) => {
                const prevItem = index > 0 ? visibleItems[index - 1] : null;
                const isNewNodeSection = item.isNodeHeader && prevItem && !prevItem.isNodeHeader;

                return (
                  <React.Fragment key={`${item.path}-${index}`}>
                    {/* Add spacer between different node sections */}
                    {isNewNodeSection && (
                      <tr>
                        <td colSpan={3} className="h-2 bg-background" />
                      </tr>
                    )}
                    {renderRow(item, index)}
                  </React.Fragment>
                );
              })
            ) : (
              <tr>
                <td colSpan={3} className="text-center p-8 text-muted-foreground text-sm">
                  {searchQuery ? 'No fields match your search' : 'No data to display'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    );
  };

  // Render JSON view
  const renderJsonView = () => {
    return (
      <div className="overflow-hidden max-w-full">
        <pre
          className="font-mono text-xs bg-muted p-4 rounded"
          style={{
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            overflowWrap: 'break-word',
            tabSize: 2
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    );
  };



  return (
    <Card className={cn('overflow-hidden', className)}>
      {/* Header */}
      <div className="border-b p-3">
        <div className="flex items-center gap-3">
          {/* Title */}
          {title && (
            <h3 className="text-sm font-medium">{title}</h3>
          )}

          {/* Search */}
          {showSearch && (
            <div className="relative w-48">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
              <Input
                type="text"
                placeholder={`Search ${flattenedData.length} fields...`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-7 pl-7 pr-7 text-xs w-full"
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-7 w-7 p-0"
                  onClick={() => setSearchQuery('')}
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>
          )}

          {searchQuery && (
            <Badge variant="outline" className="text-xs">
              {filteredData.length} matches
            </Badge>
          )}

          {/* Spacer */}
          <div className="flex-1" />

          {/* Expand controls for tree view */}
          {viewMode === 'tree' && (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={expandAll}
                title="Expand All"
              >
                <Maximize2 className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={collapseAll}
                title="Collapse All"
              >
                <Minimize2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}

          {/* View mode toggle */}
          {showViewToggle && (
            <ToggleGroup
              type="single"
              value={viewMode}
              onValueChange={(value) => value && setViewMode(value as ViewMode)}
              className="h-7"
            >
              <ToggleGroupItem value="tree" size="sm" className="h-7" title="Tree View">
                <TreePine className="h-3 w-3" />
              </ToggleGroupItem>
              <ToggleGroupItem value="json" size="sm" className="h-7" title="JSON View">
                <FileJson className="h-3 w-3" />
              </ToggleGroupItem>
            </ToggleGroup>
          )}
        </div>
      </div>

      {/* Content */}
      <ScrollArea style={{ height: maxHeight }} className="p-3">
        {viewMode === 'tree' && renderTreeView()}
        {viewMode === 'json' && renderJsonView()}
      </ScrollArea>
    </Card>
  );
}