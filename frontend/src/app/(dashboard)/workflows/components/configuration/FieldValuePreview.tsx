/**
 * FieldValuePreview Component
 * Smart preview of field values with expandable display
 */

import React, { useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ChevronDown,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { DataTypeIcon, detectDataType } from './DataTypeIcon';

interface FieldValuePreviewProps {
  value: any;
  path?: string;
  maxLength?: number;
  expandable?: boolean;
  className?: string;
  showType?: boolean;
}

export function FieldValuePreview({
  value,
  path,
  maxLength = 50,
  expandable = true,
  className,
  showType = false
}: FieldValuePreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const dataType = detectDataType(value);

  // Format value for display
  const formattedValue = useMemo(() => {
    if (value === null) return <span className="text-gray-400 italic">null</span>;
    if (value === undefined) return <span className="text-gray-400 italic">undefined</span>;

    switch (dataType) {
      case 'string':
        return value.length > maxLength && !isExpanded
          ? `"${value.substring(0, maxLength)}..."`
          : `"${value}"`;

      case 'number':
        return new Intl.NumberFormat().format(value);

      case 'boolean':
        return (
          <Badge
            variant={value ? 'default' : 'outline'}
            className="text-xs"
          >
            {value ? 'true' : 'false'}
          </Badge>
        );

      case 'date':
        try {
          const date = new Date(value);
          return date.toLocaleString();
        } catch {
          return value;
        }

      case 'url':
        return (
          <a
            href={value}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline inline-flex items-center gap-1"
            onClick={(e) => e.stopPropagation()}
          >
            {value.length > maxLength && !isExpanded
              ? value.substring(0, maxLength) + '...'
              : value}
            <ExternalLink className="h-3 w-3" />
          </a>
        );

      case 'array':
        if (!isExpanded) {
          return `[${value.length} items]`;
        }
        return (
          <div className="space-y-1">
            {value.map((item: any, index: number) => (
              <div key={index} className="pl-4 border-l-2 border-gray-200">
                <span className="text-gray-500 text-xs">[{index}]</span>{' '}
                <FieldValuePreview
                  value={item}
                  maxLength={maxLength}
                  expandable={false}
                />
              </div>
            ))}
          </div>
        );

      case 'object':
        const keys = Object.keys(value);
        if (!isExpanded) {
          return `{${keys.length} fields}`;
        }
        return (
          <div className="space-y-1">
            {keys.map((key) => (
              <div key={key} className="pl-4 border-l-2 border-gray-200">
                <span className="text-purple-600 font-medium">{key}:</span>{' '}
                <FieldValuePreview
                  value={value[key]}
                  maxLength={maxLength}
                  expandable={false}
                />
              </div>
            ))}
          </div>
        );

      default:
        return String(value);
    }
  }, [value, dataType, maxLength, isExpanded]);


  const needsExpansion = useMemo(() => {
    if (!expandable) return false;
    if (dataType === 'array' || dataType === 'object') return true;
    if (dataType === 'string' && value.length > maxLength) return true;
    return false;
  }, [dataType, value, maxLength, expandable]);

  return (
    <div className={cn('inline-flex items-start gap-2', className)}>
      {/* Type icon */}
      {showType && (
        <DataTypeIcon type={dataType} size="xs" />
      )}

      {/* Value display */}
      <div className="flex-1">
        {needsExpansion ? (
          <div>
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-0 text-left justify-start"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3 mr-1" />
              ) : (
                <ChevronRight className="h-3 w-3 mr-1" />
              )}
              <span className="font-mono text-xs">{formattedValue}</span>
            </Button>
          </div>
        ) : (
          <span className="font-mono text-xs">{formattedValue}</span>
        )}
      </div>

    </div>
  );
}

/**
 * FieldRow Component
 * Complete field display with path, type, and value
 */
export function FieldRow({
  path,
  value,
  depth = 0,
  isLast = false,
  onPathClick,
  onValueCopy
}: {
  path: string;
  value: any;
  depth?: number;
  isLast?: boolean;
  onPathClick?: (path: string) => void;
  onValueCopy?: (value: any, path: string) => void;
}) {
  const handlePathClick = () => {
    const fullPath = `{${path}}`;
    navigator.clipboard.writeText(fullPath);
    toast.success(`Copied: ${fullPath}`);
    onPathClick?.(path);
  };

  return (
    <div
      className={cn(
        'flex items-start gap-3 py-1.5 px-2 hover:bg-gray-50 dark:hover:bg-gray-900 rounded',
        depth > 0 && 'ml-4 border-l-2 border-gray-200 dark:border-gray-700'
      )}
    >
      {/* Tree indicator */}
      {depth > 0 && (
        <div className="flex items-center h-5">
          <div
            className={cn(
              'w-4 h-px bg-gray-300 dark:bg-gray-600',
              isLast && 'bg-transparent'
            )}
          />
        </div>
      )}

      {/* Field path */}
      <Button
        variant="ghost"
        size="sm"
        className="h-auto p-1 text-left font-mono text-xs text-purple-600 hover:text-purple-700"
        onClick={handlePathClick}
      >
        {path.split('.').pop()}
      </Button>

      {/* Data type */}
      <DataTypeIcon type={detectDataType(value)} size="xs" />

      {/* Value preview */}
      <div className="flex-1">
        <FieldValuePreview
          value={value}
          path={path}
          onCopy={onValueCopy}
        />
      </div>
    </div>
  );
}