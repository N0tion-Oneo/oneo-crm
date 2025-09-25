/**
 * DataValueFormatter
 * Utilities and components for formatting data values in the hierarchical table
 */

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  Code2,
  Database,
  Calendar,
  Hash,
  Type,
  ToggleLeft,
  List,
  AlertCircle,
  CheckCircle,
  XCircle
} from 'lucide-react';

// Type color mapping
export const TYPE_COLORS = {
  string: {
    bg: 'bg-blue-100 dark:bg-blue-950',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800'
  },
  number: {
    bg: 'bg-green-100 dark:bg-green-950',
    text: 'text-green-700 dark:text-green-300',
    border: 'border-green-200 dark:border-green-800'
  },
  boolean: {
    bg: 'bg-purple-100 dark:bg-purple-950',
    text: 'text-purple-700 dark:text-purple-300',
    border: 'border-purple-200 dark:border-purple-800'
  },
  object: {
    bg: 'bg-orange-100 dark:bg-orange-950',
    text: 'text-orange-700 dark:text-orange-300',
    border: 'border-orange-200 dark:border-orange-800'
  },
  array: {
    bg: 'bg-pink-100 dark:bg-pink-950',
    text: 'text-pink-700 dark:text-pink-300',
    border: 'border-pink-200 dark:border-pink-800'
  },
  datetime: {
    bg: 'bg-indigo-100 dark:bg-indigo-950',
    text: 'text-indigo-700 dark:text-indigo-300',
    border: 'border-indigo-200 dark:border-indigo-800'
  },
  null: {
    bg: 'bg-gray-100 dark:bg-gray-950',
    text: 'text-gray-500 dark:text-gray-400',
    border: 'border-gray-200 dark:border-gray-800'
  },
  undefined: {
    bg: 'bg-gray-100 dark:bg-gray-950',
    text: 'text-gray-500 dark:text-gray-400',
    border: 'border-gray-200 dark:border-gray-800'
  },
  indicator: {
    bg: 'bg-yellow-100 dark:bg-yellow-950',
    text: 'text-yellow-700 dark:text-yellow-300',
    border: 'border-yellow-200 dark:border-yellow-800'
  }
};

// Type icons
export function getTypeIcon(type: string) {
  switch (type) {
    case 'string':
      return <Type className="h-3 w-3" />;
    case 'number':
      return <Hash className="h-3 w-3" />;
    case 'boolean':
      return <ToggleLeft className="h-3 w-3" />;
    case 'object':
      return <Database className="h-3 w-3" />;
    case 'array':
      return <List className="h-3 w-3" />;
    case 'datetime':
      return <Calendar className="h-3 w-3" />;
    case 'null':
    case 'undefined':
      return <AlertCircle className="h-3 w-3" />;
    default:
      return <Code2 className="h-3 w-3" />;
  }
}

// Format value for display
export function formatValue(value: any, type: string): React.ReactNode {
  // Handle nullish values
  if (value === null) {
    return <span className="text-gray-400 italic">null</span>;
  }
  if (value === undefined) {
    return <span className="text-gray-400 italic">undefined</span>;
  }

  switch (type) {
    case 'string':
      return formatString(value);

    case 'number':
      return formatNumber(value);

    case 'boolean':
      return formatBoolean(value);

    case 'datetime':
      return formatDateTime(value);

    case 'object':
      return formatObject(value);

    case 'array':
      return formatArray(value);

    case 'indicator':
      return <span className="text-gray-500 italic">{value || ''}</span>;

    default:
      return formatDefault(value);
  }
}

// Format string values
function formatString(value: string): React.ReactNode {
  // Check for special string patterns
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const urlRegex = /^https?:\/\//i;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  // Email - compact display
  if (emailRegex.test(value)) {
    const [user, domain] = value.split('@');
    const truncatedUser = user.length > 10 ? user.substring(0, 10) + '...' : user;
    return (
      <span className="font-mono text-[11px]" title={value}>
        <span className="text-blue-600 dark:text-blue-400">
          {truncatedUser}@{domain}
        </span>
      </span>
    );
  }

  // URL - compact display
  if (urlRegex.test(value)) {
    try {
      const url = new URL(value);
      return (
        <span className="font-mono text-[11px]" title={value}>
          <span className="text-blue-600 dark:text-blue-400">{url.host}</span>
        </span>
      );
    } catch {
      // Invalid URL, show as regular string
    }
  }

  // UUID - compact display
  if (uuidRegex.test(value)) {
    return (
      <span className="font-mono text-[10px] text-gray-600 dark:text-gray-400" title={value}>
        {value.substring(0, 6)}...
      </span>
    );
  }

  // Regular string - truncate if too long
  const maxLength = 30;
  const displayValue = value.length > maxLength ? value.substring(0, maxLength) + '...' : value;
  return (
    <span className="text-xs" title={value.length > maxLength ? value : undefined}>
      {displayValue}
    </span>
  );
}

// Format number values
function formatNumber(value: number): React.ReactNode {
  // Format with thousand separators
  const formatted = value.toLocaleString('en-US', {
    maximumFractionDigits: 2
  });

  return (
    <span className="font-mono text-xs text-green-600 dark:text-green-400">
      {formatted}
    </span>
  );
}

// Format boolean values
function formatBoolean(value: boolean): React.ReactNode {
  return value ? (
    <span className="inline-flex items-center gap-0.5 text-green-600 dark:text-green-400 text-xs">
      <CheckCircle className="h-3 w-3" />
      <span className="font-mono text-xs">true</span>
    </span>
  ) : (
    <span className="inline-flex items-center gap-0.5 text-red-600 dark:text-red-400 text-xs">
      <XCircle className="h-3 w-3" />
      <span className="font-mono text-xs">false</span>
    </span>
  );
}

// Format datetime values
function formatDateTime(value: string | Date): React.ReactNode {
  const date = value instanceof Date ? value : new Date(value);

  // Check if valid date
  if (isNaN(date.getTime())) {
    return <span className="text-gray-400">{String(value)}</span>;
  }

  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor(diff / (1000 * 60));

  let relative = '';
  if (days > 7) {
    relative = date.toLocaleDateString();
  } else if (days > 1) {
    relative = `${days} days ago`;
  } else if (days === 1) {
    relative = 'Yesterday';
  } else if (hours > 1) {
    relative = `${hours} hours ago`;
  } else if (hours === 1) {
    relative = '1 hour ago';
  } else if (minutes > 1) {
    relative = `${minutes} minutes ago`;
  } else if (minutes === 1) {
    relative = '1 minute ago';
  } else {
    relative = 'Just now';
  }

  const absolute = date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  return (
    <span className="text-xs" title={absolute}>
      <span className="text-indigo-600 dark:text-indigo-400">{relative}</span>
    </span>
  );
}

// Format object values (collapsed view)
function formatObject(value: object): React.ReactNode {
  const keys = Object.keys(value);
  const keyCount = keys.length;

  if (keyCount === 0) {
    return <span className="text-[10px] text-gray-400 italic">empty</span>;
  }

  return (
    <span className="text-xs text-gray-600 dark:text-gray-400">
      <span className="text-orange-600 dark:text-orange-400">Obj</span>
      <span className="ml-0.5 text-[10px]">({keyCount})</span>
    </span>
  );
}

// Format array values (collapsed view)
function formatArray(value: any[]): React.ReactNode {
  const length = value.length;

  if (length === 0) {
    return <span className="text-[10px] text-gray-400 italic">empty</span>;
  }

  // Check if all items are primitives
  const allPrimitive = value.every(item => {
    const type = typeof item;
    return type === 'string' || type === 'number' || type === 'boolean' || item === null;
  });

  if (allPrimitive && length <= 3) {
    // Show inline for very small primitive arrays
    const items = value.slice(0, 3).map((item, i) => {
      const itemStr = String(item);
      const truncated = itemStr.length > 10 ? itemStr.substring(0, 10) + '...' : itemStr;
      return (
        <span key={i} className="text-[10px]">
          {i > 0 && <span className="text-gray-400">,</span>}
          {truncated}
        </span>
      );
    });

    return (
      <span className="text-xs">
        [{items}]
      </span>
    );
  }

  return (
    <span className="text-xs text-gray-600 dark:text-gray-400">
      <span className="text-pink-600 dark:text-pink-400">Arr</span>
      <span className="ml-0.5 text-[10px]">({length})</span>
    </span>
  );
}

// Default formatter
function formatDefault(value: any): React.ReactNode {
  const str = String(value);
  const truncated = str.length > 30 ? str.substring(0, 30) + '...' : str;
  return (
    <span className="font-mono text-xs text-gray-600 dark:text-gray-400" title={str.length > 30 ? str : undefined}>
      {truncated}
    </span>
  );
}

// Type badge component
interface TypeBadgeProps {
  type: string;
  className?: string;
}

export function TypeBadge({ type, className }: TypeBadgeProps) {
  const colors = TYPE_COLORS[type as keyof typeof TYPE_COLORS] || TYPE_COLORS.string;

  return (
    <Badge
      variant="outline"
      className={cn(
        'h-5 px-1.5 text-xs font-mono inline-flex items-center gap-1',
        colors.bg,
        colors.text,
        colors.border,
        className
      )}
    >
      {getTypeIcon(type)}
      <span>{type}</span>
    </Badge>
  );
}

// Copy value utility
export function copyValue(value: any, type: string): string {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';

  switch (type) {
    case 'object':
    case 'array':
      return JSON.stringify(value, null, 2);
    case 'string':
      return value;
    case 'number':
    case 'boolean':
      return String(value);
    case 'datetime':
      return new Date(value).toISOString();
    default:
      return String(value);
  }
}

// Get value for sorting
export function getSortValue(value: any, type: string): any {
  if (value === null || value === undefined) return '';

  switch (type) {
    case 'string':
      return value.toLowerCase();
    case 'number':
      return value;
    case 'boolean':
      return value ? 1 : 0;
    case 'datetime':
      return new Date(value).getTime();
    case 'object':
      return Object.keys(value).length;
    case 'array':
      return value.length;
    default:
      return String(value);
  }
}