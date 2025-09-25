/**
 * useDataFlattening Hook
 * Transforms nested data structures into flat table rows for hierarchical display
 */

import { useMemo } from 'react';

export interface FlattenedField {
  key: string;           // Unique identifier for the field
  path: string;          // Full dot-notation path (e.g., "record.data.phone")
  name: string;          // Display name (last part of path)
  type: string;          // Data type
  value: any;            // Actual value
  depth: number;         // Nesting depth (0-based)
  isExpandable: boolean; // Whether this field can be expanded
  isExpanded: boolean;   // Current expansion state
  childCount: number;    // Number of direct children
  parentKey: string | null; // Parent field key
  nodeId?: string;       // Source node ID (for workflow context)
  isArrayItem: boolean;  // Whether this is an array element
  arrayIndex?: number;   // Index if array item
}

export interface DataFlatteningOptions {
  maxDepth?: number;           // Maximum depth to traverse (default: 10)
  expandedPaths?: Set<string>; // Paths that should be expanded
  includeNullish?: boolean;    // Include null/undefined values
  nodeId?: string;              // Source node identifier
  pathPrefix?: string;          // Prefix for all paths
}

/**
 * Hook to flatten nested data structures into table rows
 */
export function useDataFlattening(
  data: any,
  options: DataFlatteningOptions = {}
) {
  const {
    maxDepth = 10,
    expandedPaths = new Set<string>(),
    includeNullish = true,
    nodeId,
    pathPrefix = ''
  } = options;

  const flattenedData = useMemo(() => {
    const result: FlattenedField[] = [];

    function getDataType(value: any): string {
      if (value === null) return 'null';
      if (value === undefined) return 'undefined';
      if (Array.isArray(value)) return 'array';
      if (value instanceof Date) return 'datetime';
      if (typeof value === 'string' && isISODateString(value)) return 'datetime';
      if (typeof value === 'object') return 'object';
      if (typeof value === 'boolean') return 'boolean';
      if (typeof value === 'number') return 'number';
      return 'string';
    }

    function isISODateString(value: string): boolean {
      return /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?)?$/.test(value);
    }

    function shouldIncludeField(value: any): boolean {
      if (value === null || value === undefined) {
        return includeNullish;
      }
      return true;
    }

    function getChildCount(value: any): number {
      const type = getDataType(value);
      if (type === 'object' && value !== null) {
        return Object.keys(value).length;
      }
      if (type === 'array') {
        return value.length;
      }
      return 0;
    }

    function flattenRecursive(
      obj: any,
      currentPath: string,
      parentKey: string | null,
      depth: number
    ): void {
      // Stop at max depth
      if (depth > maxDepth) return;

      const type = getDataType(obj);
      const fieldKey = currentPath || 'root';
      const displayName = currentPath.includes('.')
        ? currentPath.split('.').pop() || currentPath
        : currentPath;

      // Add the current field
      const field: FlattenedField = {
        key: fieldKey,
        path: currentPath,
        name: displayName,
        type,
        value: obj,
        depth,
        isExpandable: type === 'object' || type === 'array',
        isExpanded: expandedPaths.has(fieldKey),
        childCount: getChildCount(obj),
        parentKey,
        nodeId,
        isArrayItem: false
      };

      result.push(field);

      // Only process children if expanded
      if (!field.isExpanded) return;

      // Process object fields
      if (type === 'object' && obj !== null) {
        // Preserve original order - don't sort
        const entries = Object.entries(obj);

        for (const [key, value] of entries) {
          if (!shouldIncludeField(value)) continue;

          const childPath = currentPath ? `${currentPath}.${key}` : key;
          flattenRecursive(value, childPath, fieldKey, depth + 1);
        }
      }

      // Process array items
      if (type === 'array' && Array.isArray(obj)) {
        // For arrays, show structure of items
        if (obj.length > 0) {
          // If all items are primitives, show them inline
          const allPrimitive = obj.every(item => {
            const itemType = getDataType(item);
            return itemType !== 'object' && itemType !== 'array';
          });

          if (allPrimitive && obj.length <= 10) {
            // Show primitive array items inline
            obj.forEach((item, index) => {
              const itemPath = `${currentPath}[${index}]`;
              const itemField: FlattenedField = {
                key: itemPath,
                path: itemPath,
                name: `[${index}]`,
                type: getDataType(item),
                value: item,
                depth: depth + 1,
                isExpandable: false,
                isExpanded: false,
                childCount: 0,
                parentKey: fieldKey,
                nodeId,
                isArrayItem: true,
                arrayIndex: index
              };
              result.push(itemField);
            });
          } else {
            // For complex arrays, show sample structure
            const sampleCount = Math.min(3, obj.length);
            for (let i = 0; i < sampleCount; i++) {
              const itemPath = `${currentPath}[${i}]`;
              flattenRecursive(obj[i], itemPath, fieldKey, depth + 1);
            }

            // Add indicator for remaining items
            if (obj.length > 3) {
              const remainingPath = `${currentPath}[...]`;
              const remainingField: FlattenedField = {
                key: remainingPath,
                path: remainingPath,
                name: `... ${obj.length - 3} more items`,
                type: 'indicator',
                value: null,
                depth: depth + 1,
                isExpandable: false,
                isExpanded: false,
                childCount: 0,
                parentKey: fieldKey,
                nodeId,
                isArrayItem: true
              };
              result.push(remainingField);
            }
          }
        } else {
          // Empty array indicator
          const emptyPath = `${currentPath}[empty]`;
          const emptyField: FlattenedField = {
            key: emptyPath,
            path: emptyPath,
            name: '(empty array)',
            type: 'indicator',
            value: null,
            depth: depth + 1,
            isExpandable: false,
            isExpanded: false,
            childCount: 0,
            parentKey: fieldKey,
            nodeId,
            isArrayItem: true
          };
          result.push(emptyField);
        }
      }
    }

    // Handle different input types
    if (!data) {
      if (includeNullish) {
        result.push({
          key: 'root',
          path: '',
          name: 'No data',
          type: 'null',
          value: null,
          depth: 0,
          isExpandable: false,
          isExpanded: false,
          childCount: 0,
          parentKey: null,
          nodeId,
          isArrayItem: false
        });
      }
    } else if (typeof data === 'object') {
      // Check if we have multiple sources (for input data)
      const isMultipleSources = nodeId && data[nodeId];

      if (isMultipleSources) {
        // Handle multiple input sources
        Object.entries(data).forEach(([sourceId, sourceData]) => {
          flattenRecursive(sourceData, sourceId, null, 0);
        });
      } else {
        // Single data source
        const startPath = pathPrefix || '';
        flattenRecursive(data, startPath, null, 0);
      }
    } else {
      // Primitive root value
      result.push({
        key: 'root',
        path: '',
        name: 'value',
        type: getDataType(data),
        value: data,
        depth: 0,
        isExpandable: false,
        isExpanded: false,
        childCount: 0,
        parentKey: null,
        nodeId,
        isArrayItem: false
      });
    }

    return result;
  }, [data, maxDepth, expandedPaths, includeNullish, nodeId, pathPrefix]);

  // Get only visible rows based on expansion state
  const visibleRows = useMemo(() => {
    const visible: FlattenedField[] = [];
    const expandedSet = new Set<string>();

    // Track which fields are expanded
    flattenedData.forEach(field => {
      if (field.isExpanded) {
        expandedSet.add(field.key);
      }
    });

    // Filter to only show visible rows
    flattenedData.forEach(field => {
      // Always show root level
      if (field.depth === 0) {
        visible.push(field);
        return;
      }

      // Check if all parents are expanded
      let currentPath = field.path;
      let allParentsExpanded = true;

      // Walk up the path checking expansion
      const pathParts = currentPath.split(/[\.\[\]]+/).filter(Boolean);
      for (let i = pathParts.length - 1; i > 0; i--) {
        const parentPath = pathParts.slice(0, i).join('.');
        const parentField = flattenedData.find(f => f.path === parentPath);

        if (parentField && !parentField.isExpanded) {
          allParentsExpanded = false;
          break;
        }
      }

      if (allParentsExpanded) {
        visible.push(field);
      }
    });

    return visible;
  }, [flattenedData]);

  return {
    allRows: flattenedData,
    visibleRows,
    totalCount: flattenedData.length,
    visibleCount: visibleRows.length
  };
}

/**
 * Utility to manage expanded state
 */
export function useExpandedState(initialExpanded: Set<string> = new Set()) {
  const [expanded, setExpanded] = useState(initialExpanded);

  const toggleExpanded = (key: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
        // Also collapse all children
        next.forEach(expandedKey => {
          if (expandedKey.startsWith(key + '.') || expandedKey.startsWith(key + '[')) {
            next.delete(expandedKey);
          }
        });
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const expandAll = (rows: FlattenedField[]) => {
    const allExpandable = rows
      .filter(r => r.isExpandable)
      .map(r => r.key);
    setExpanded(new Set(allExpandable));
  };

  const collapseAll = () => {
    setExpanded(new Set());
  };

  const expandToLevel = (level: number, rows: FlattenedField[]) => {
    const toExpand = rows
      .filter(r => r.isExpandable && r.depth < level)
      .map(r => r.key);
    setExpanded(new Set(toExpand));
  };

  return {
    expanded,
    toggleExpanded,
    expandAll,
    collapseAll,
    expandToLevel
  };
}

// Also need to import useState for useExpandedState
import { useState } from 'react';