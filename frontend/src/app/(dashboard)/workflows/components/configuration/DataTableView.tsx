/**
 * DataTableView Component
 * Hierarchical table view for displaying nested data structures
 */

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Copy,
  Search,
  Maximize2,
  Minimize2,
  Filter,
  SortAsc,
  SortDesc,
  X,
  Database
} from 'lucide-react';
import { toast } from 'sonner';
import {
  useDataFlattening,
  useExpandedState,
  type FlattenedField
} from './useDataFlattening';
import {
  formatValue,
  TypeBadge,
  copyValue,
  getSortValue
} from './DataValueFormatter';

export interface DataTableViewProps {
  data: any;
  nodeId?: string;
  title?: string;
  className?: string;
  maxHeight?: string;
  initialExpanded?: 'none' | 'first-level' | 'all';
  showSearch?: boolean;
  showTypeColumn?: boolean;
  showCopyButtons?: boolean;
  onFieldCopy?: (path: string, value: any) => void;
}

type SortField = 'path' | 'type' | 'value' | null;
type SortOrder = 'asc' | 'desc';

export function DataTableView({
  data,
  nodeId,
  title,
  className,
  maxHeight = '400px',
  initialExpanded = 'first-level',
  showSearch = true,
  showTypeColumn = true,
  showCopyButtons = true,
  onFieldCopy
}: DataTableViewProps) {
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  // Sort state
  const [sortField, setSortField] = useState<SortField>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // View state
  const [isExpanded, setIsExpanded] = useState(false);

  // Initialize expanded state based on prop
  const getInitialExpanded = () => {
    if (initialExpanded === 'none') return new Set<string>();
    if (initialExpanded === 'all') return new Set<string>(); // Will expand all after data loads
    // Default: first level
    return new Set<string>();
  };

  // Expansion management
  const {
    expanded,
    toggleExpanded,
    expandAll: expandAllRows,
    collapseAll,
    expandToLevel
  } = useExpandedState(getInitialExpanded());

  // Check if data appears to be grouped by node sources
  const isGroupedByNode = useMemo(() => {
    if (!data || typeof data !== 'object') return false;
    // Check if all top-level keys look like node identifiers
    const keys = Object.keys(data);
    // If we have multiple top-level keys and they contain node-like data structures
    return keys.length > 1 && keys.every(key => {
      const val = data[key];
      return typeof val === 'object' && val !== null &&
             (val.success !== undefined || val.record !== undefined || val.data !== undefined);
    });
  }, [data]);

  // Flatten data
  const { visibleRows, allRows } = useDataFlattening(data, {
    expandedPaths: expanded,
    nodeId,
    includeNullish: true
  });

  // Initialize expansion on mount
  useEffect(() => {
    if (initialExpanded === 'first-level' && allRows.length > 0) {
      // Expand first level objects/arrays
      const firstLevel = allRows.filter(r => r.depth === 0 && r.isExpandable);
      firstLevel.forEach(row => toggleExpanded(row.key));
    } else if (initialExpanded === 'all' && allRows.length > 0) {
      expandAllRows(allRows);
    }
  }, [initialExpanded, allRows.length === 0]); // Only on initial load

  // Filter rows based on search
  const filteredRows = useMemo(() => {
    if (!searchQuery) return visibleRows;

    const query = searchQuery.toLowerCase();
    return visibleRows.filter(row => {
      // Search in path
      if (row.path.toLowerCase().includes(query)) return true;
      // Search in value (for primitives)
      if (row.value !== null && row.value !== undefined) {
        const valueStr = String(row.value).toLowerCase();
        if (valueStr.includes(query)) return true;
      }
      // Search in type
      if (row.type.toLowerCase().includes(query)) return true;
      return false;
    });
  }, [visibleRows, searchQuery]);

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortField) return filteredRows;

    const sorted = [...filteredRows].sort((a, b) => {
      let aVal, bVal;

      switch (sortField) {
        case 'path':
          aVal = a.path.toLowerCase();
          bVal = b.path.toLowerCase();
          break;
        case 'type':
          aVal = a.type;
          bVal = b.type;
          break;
        case 'value':
          aVal = getSortValue(a.value, a.type);
          bVal = getSortValue(b.value, b.type);
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [filteredRows, sortField, sortOrder]);

  // Handle sorting
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle order
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // New field
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Handle field copy
  const handleCopyField = (row: FlattenedField) => {
    const expression = nodeId ? `{${nodeId}.${row.path}}` : `{${row.path}}`;
    navigator.clipboard.writeText(expression);
    toast.success(`Copied: ${expression}`);
    onFieldCopy?.(row.path, row.value);
  };

  // Handle value copy
  const handleCopyValue = (row: FlattenedField) => {
    const textToCopy = copyValue(row.value, row.type);
    navigator.clipboard.writeText(textToCopy);
    toast.success('Value copied to clipboard');
  };

  // Get background color based on depth for visual hierarchy
  const getRowBackground = (depth: number, path: string) => {
    // If this is grouped node data, add special styling for top-level nodes
    if (isGroupedByNode && depth === 0) {
      return 'bg-primary/5 border-l-4 border-primary/30'; // Highlight node groups
    }

    switch (depth) {
      case 0:
        return ''; // No background for root level
      case 1:
        return 'bg-muted/30'; // Light background for level 1
      case 2:
        return 'bg-muted/50'; // Medium background for level 2
      default:
        return 'bg-muted/70'; // Darker background for deeper levels
    }
  };

  // Calculate stats
  const stats = {
    total: allRows.length,
    visible: visibleRows.length,
    filtered: filteredRows.length,
    expandable: allRows.filter(r => r.isExpandable).length
  };

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        {title && (
          <h4 className="text-sm font-medium">{title}</h4>
        )}
        <div className="flex items-center gap-2">
          {/* Search */}
          {showSearch && (
            <div className="relative">
              {isSearching ? (
                <div className="flex items-center gap-2">
                  <Input
                    type="text"
                    placeholder="Search fields..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="h-7 w-48 text-xs"
                    autoFocus
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => {
                      setSearchQuery('');
                      setIsSearching(false);
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => setIsSearching(true)}
                >
                  <Search className="h-3 w-3 mr-1" />
                  <span className="text-xs">Search</span>
                </Button>
              )}
            </div>
          )}

          {/* Expand controls */}
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={() => expandToLevel(1, allRows)}
            >
              <span className="text-xs">Level 1</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={() => expandToLevel(2, allRows)}
            >
              <span className="text-xs">Level 2</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={() => expandAllRows(allRows)}
            >
              <span className="text-xs">Expand All</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={collapseAll}
            >
              <span className="text-xs">Collapse</span>
            </Button>
          </div>

          {/* View toggle */}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <Minimize2 className="h-3 w-3" />
            ) : (
              <Maximize2 className="h-3 w-3" />
            )}
          </Button>
        </div>
      </div>

      {/* Stats bar */}
      {searchQuery && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Showing {stats.filtered} of {stats.visible} visible fields</span>
          {searchQuery && (
            <Badge variant="secondary" className="text-xs">
              matching "{searchQuery}"
            </Badge>
          )}
        </div>
      )}

      {/* Table */}
      <Card className="overflow-hidden">
        <div
          className="overflow-auto"
          style={{ maxHeight: isExpanded ? '600px' : maxHeight }}
        >
          <table className="w-full text-xs table-fixed">
              <colgroup>
                <col style={{ width: '40%' }} />
                {showTypeColumn && <col style={{ width: '15%' }} />}
                <col style={{ width: showTypeColumn ? '30%' : '45%' }} />
                {showCopyButtons && <col style={{ width: '15%' }} />}
              </colgroup>
              <thead className="sticky top-0 z-10 bg-background border-b">
                <tr>
                  <th className="text-left p-1 text-xs">
                    <button
                      className="inline-flex items-center gap-1 text-xs font-medium hover:text-primary"
                      onClick={() => handleSort('path')}
                    >
                      Field Path
                      {sortField === 'path' && (
                        sortOrder === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                      )}
                    </button>
                  </th>
                  {showTypeColumn && (
                    <th className="text-left p-1 text-xs">
                      <button
                        className="inline-flex items-center gap-1 text-xs font-medium hover:text-primary"
                        onClick={() => handleSort('type')}
                      >
                        Type
                        {sortField === 'type' && (
                          sortOrder === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                        )}
                      </button>
                    </th>
                  )}
                  <th className="text-left p-1 text-xs">
                    <button
                      className="inline-flex items-center gap-1 text-xs font-medium hover:text-primary"
                      onClick={() => handleSort('value')}
                    >
                      Value
                      {sortField === 'value' && (
                        sortOrder === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                      )}
                    </button>
                  </th>
                  {showCopyButtons && (
                    <th className="text-center p-1 text-xs">
                      <span className="text-xs font-medium">Copy</span>
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
              {sortedRows.length === 0 ? (
                <tr>
                  <td
                    colSpan={showTypeColumn ? (showCopyButtons ? 4 : 3) : (showCopyButtons ? 3 : 2)}
                    className="text-center p-8 text-muted-foreground text-sm"
                  >
                    {searchQuery ? 'No fields match your search' : 'No data to display'}
                  </td>
                </tr>
              ) : (
                sortedRows.map((row, index) => (
                  <DataTableRow
                    key={row.key}
                    row={row}
                    index={index}
                    showTypeColumn={showTypeColumn}
                    showCopyButtons={showCopyButtons}
                    onToggleExpand={() => toggleExpanded(row.key)}
                    onCopyField={() => handleCopyField(row)}
                    onCopyValue={() => handleCopyValue(row)}
                    getRowBackground={getRowBackground}
                    isGroupedByNode={isGroupedByNode}
                  />
                ))
              )}
              </tbody>
            </table>
        </div>
      </Card>
    </div>
  );
}

// Individual row component
interface DataTableRowProps {
  row: FlattenedField;
  index: number;
  showTypeColumn: boolean;
  showCopyButtons: boolean;
  onToggleExpand: () => void;
  onCopyField: () => void;
  onCopyValue: () => void;
  getRowBackground: (depth: number, path: string) => string;
  isGroupedByNode: boolean;
}

function DataTableRow({
  row,
  index,
  showTypeColumn,
  showCopyButtons,
  onToggleExpand,
  onCopyField,
  onCopyValue,
  getRowBackground,
  isGroupedByNode
}: DataTableRowProps) {
  // Add visual indicators for node groups
  const isNodeGroupHeader = isGroupedByNode && row.depth === 0;

  return (
    <tr
      className={cn(
        'group hover:bg-muted/80 transition-colors text-xs',
        getRowBackground(row.depth, row.path),
        isNodeGroupHeader && 'font-semibold'
      )}
    >
      {/* Field Path */}
      <td className="p-1 overflow-hidden">
        <div className="flex items-center gap-1">
          {/* Expand/Collapse button */}
          {row.isExpandable ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-4 w-4 p-0 flex-shrink-0"
              onClick={onToggleExpand}
            >
              {row.isExpanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
            </Button>
          ) : (
            <div className="h-4 w-4 flex-shrink-0" /> // Spacer
          )}

          {/* Field path - show full path for clarity */}
          {isNodeGroupHeader ? (
            <div className="flex items-center gap-1">
              <Database className="h-3 w-3 text-primary" />
              <span className="text-xs font-semibold text-primary">
                {row.path || row.name}
              </span>
            </div>
          ) : (
            <code className={cn(
              'font-mono text-xs truncate',
              row.isArrayItem && 'text-muted-foreground',
              row.depth > 0 && !isGroupedByNode && 'text-muted-foreground'
            )}>
              {row.path || row.name}
            </code>
          )}

          {/* Child count for expandable fields */}
          {row.isExpandable && row.childCount > 0 && !row.isExpanded && (
            <Badge variant="secondary" className="ml-1 text-[10px] px-1 h-4 flex-shrink-0">
              {row.childCount}
            </Badge>
          )}
        </div>
      </td>

      {/* Type */}
      {showTypeColumn && (
        <td className="p-1 whitespace-nowrap">
          {row.type !== 'indicator' && (
            <Badge
              variant="outline"
              className="text-[10px] px-1 py-0 h-4 font-mono"
            >
              {row.type}
            </Badge>
          )}
        </td>
      )}

      {/* Value */}
      <td className="p-1">
        <div className="break-words text-xs" style={{ maxWidth: '200px' }}>
          {!row.isExpandable || row.isExpanded ? (
            formatValue(row.value, row.type)
          ) : (
            <span className="text-[10px] text-muted-foreground italic">
              expand
            </span>
          )}
        </div>
      </td>

      {/* Actions */}
      {showCopyButtons && (
        <td className="p-1 whitespace-nowrap">
          <div className="flex items-center justify-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
            {row.type !== 'indicator' && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={onCopyField}
                  title="Copy field path"
                >
                  <Code2 className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={onCopyValue}
                  title="Copy value"
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </>
            )}
          </div>
        </td>
      )}
    </tr>
  );
}

// Need to import Code2
import { Code2 } from 'lucide-react';