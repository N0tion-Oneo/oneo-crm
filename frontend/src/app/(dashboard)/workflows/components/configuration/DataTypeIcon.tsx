/**
 * DataTypeIcon Component
 * Visual icons and badges for different data types
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import {
  Type,
  Hash,
  ToggleLeft,
  Braces,
  Brackets,
  Circle,
  Calendar,
  Link2,
  Image,
  FileText,
  Code2,
  Binary
} from 'lucide-react';

export type DataType =
  | 'string'
  | 'number'
  | 'boolean'
  | 'object'
  | 'array'
  | 'null'
  | 'undefined'
  | 'date'
  | 'url'
  | 'image'
  | 'json'
  | 'binary'
  | 'unknown';

interface DataTypeIconProps {
  type: DataType;
  className?: string;
  showLabel?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg';
}

const typeConfig: Record<DataType, {
  icon: React.ComponentType<any>;
  label: string;
  color: string;
  bgColor: string;
}> = {
  string: {
    icon: Type,
    label: 'String',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-950'
  },
  number: {
    icon: Hash,
    label: 'Number',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-950'
  },
  boolean: {
    icon: ToggleLeft,
    label: 'Boolean',
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-950'
  },
  object: {
    icon: Braces,
    label: 'Object',
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-950'
  },
  array: {
    icon: Brackets,
    label: 'Array',
    color: 'text-pink-600 dark:text-pink-400',
    bgColor: 'bg-pink-50 dark:bg-pink-950'
  },
  null: {
    icon: Circle,
    label: 'Null',
    color: 'text-gray-500 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-950'
  },
  undefined: {
    icon: Circle,
    label: 'Undefined',
    color: 'text-gray-400 dark:text-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-950'
  },
  date: {
    icon: Calendar,
    label: 'Date',
    color: 'text-cyan-600 dark:text-cyan-400',
    bgColor: 'bg-cyan-50 dark:bg-cyan-950'
  },
  url: {
    icon: Link2,
    label: 'URL',
    color: 'text-indigo-600 dark:text-indigo-400',
    bgColor: 'bg-indigo-50 dark:bg-indigo-950'
  },
  image: {
    icon: Image,
    label: 'Image',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-50 dark:bg-yellow-950'
  },
  json: {
    icon: Code2,
    label: 'JSON',
    color: 'text-violet-600 dark:text-violet-400',
    bgColor: 'bg-violet-50 dark:bg-violet-950'
  },
  binary: {
    icon: Binary,
    label: 'Binary',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-950'
  },
  unknown: {
    icon: FileText,
    label: 'Unknown',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-950'
  }
};

const sizeConfig = {
  xs: { icon: 'h-3 w-3', text: 'text-xs', padding: 'p-0.5' },
  sm: { icon: 'h-3.5 w-3.5', text: 'text-xs', padding: 'p-1' },
  md: { icon: 'h-4 w-4', text: 'text-sm', padding: 'p-1.5' },
  lg: { icon: 'h-5 w-5', text: 'text-base', padding: 'p-2' }
};

export function DataTypeIcon({
  type,
  className,
  showLabel = false,
  size = 'sm'
}: DataTypeIconProps) {
  const config = typeConfig[type] || typeConfig.unknown;
  const Icon = config.icon;
  const sizeClasses = sizeConfig[size];

  if (showLabel) {
    return (
      <Badge
        variant="outline"
        className={cn(
          'inline-flex items-center gap-1',
          config.bgColor,
          'border-current',
          sizeClasses.text,
          className
        )}
      >
        <Icon className={cn(sizeClasses.icon, config.color)} />
        <span className={config.color}>{config.label}</span>
      </Badge>
    );
  }

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center rounded',
        config.bgColor,
        sizeClasses.padding,
        className
      )}
      title={config.label}
    >
      <Icon className={cn(sizeClasses.icon, config.color)} />
    </div>
  );
}

/**
 * Helper function to detect data type
 */
export function detectDataType(value: any): DataType {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';

  const type = typeof value;

  if (type === 'string') {
    // Check for special string types
    if (/^https?:\/\//.test(value)) return 'url';
    if (/\.(jpg|jpeg|png|gif|webp|svg)$/i.test(value)) return 'image';
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) return 'date';
    return 'string';
  }

  if (type === 'number') return 'number';
  if (type === 'boolean') return 'boolean';

  if (Array.isArray(value)) return 'array';
  if (type === 'object') {
    // Check if it's a Date object
    if (value instanceof Date) return 'date';
    return 'object';
  }

  return 'unknown';
}

/**
 * DataTypeBadge Component
 * Shows type with additional info (e.g., array length, object keys)
 */
export function DataTypeBadge({
  value,
  className,
  size = 'sm'
}: {
  value: any;
  className?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
}) {
  const type = detectDataType(value);
  let label = typeConfig[type].label;
  let extra = '';

  if (type === 'array' && Array.isArray(value)) {
    extra = ` [${value.length}]`;
  } else if (type === 'object' && value && typeof value === 'object') {
    const keys = Object.keys(value).length;
    extra = ` {${keys}}`;
  } else if (type === 'string' && typeof value === 'string') {
    extra = ` (${value.length})`;
  }

  return (
    <Badge
      variant="outline"
      className={cn(
        'inline-flex items-center gap-1',
        typeConfig[type].bgColor,
        'border-current',
        sizeConfig[size].text,
        className
      )}
    >
      <DataTypeIcon type={type} size={size} />
      <span className={typeConfig[type].color}>
        {label}{extra}
      </span>
    </Badge>
  );
}