/**
 * ConnectionBadge Component
 * Shows connection source with node icon and status
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
  Link2,
  Zap,
  Database,
  Mail,
  MessageSquare,
  Webhook,
  FileText,
  User,
  Calendar,
  Bot,
  Filter,
  GitBranch,
  Repeat,
  Timer,
  Send,
  Hash,
  Globe,
  Search
} from 'lucide-react';

interface ConnectionBadgeProps {
  nodeType?: string;
  nodeLabel: string;
  nodeId?: string;
  status?: 'connected' | 'configured' | 'error' | 'pending';
  hasData?: boolean;
  dataCount?: number;
  onClick?: () => void;
  className?: string;
}

// Map node types to icons
const getNodeIcon = (nodeType?: string) => {
  if (!nodeType) return Link2;

  const type = nodeType.toLowerCase();

  // Triggers
  if (type.includes('trigger_manual')) return Zap;
  if (type.includes('trigger_scheduled')) return Calendar;
  if (type.includes('trigger_webhook')) return Webhook;
  if (type.includes('trigger_record')) return Database;
  if (type.includes('trigger_email')) return Mail;
  if (type.includes('trigger_form')) return FileText;

  // Data operations
  if (type.includes('create_record')) return Database;
  if (type.includes('update_record')) return Database;
  if (type.includes('find_record')) return Search;
  if (type.includes('filter')) return Filter;

  // Communications
  if (type.includes('email')) return Mail;
  if (type.includes('message') || type.includes('sms')) return MessageSquare;
  if (type.includes('webhook')) return Webhook;

  // AI
  if (type.includes('ai_')) return Bot;

  // Control
  if (type.includes('condition')) return GitBranch;
  if (type.includes('for_each') || type.includes('loop')) return Repeat;
  if (type.includes('wait') || type.includes('delay')) return Timer;

  // Utility
  if (type.includes('http')) return Globe;
  if (type.includes('assign')) return User;

  // Default
  return type.includes('send') ? Send : Hash;
};

// Get status color
const getStatusColor = (status?: string, hasData?: boolean) => {
  if (hasData) return 'border-green-500 bg-green-50 dark:bg-green-950';

  switch (status) {
    case 'connected':
      return 'border-blue-500 bg-blue-50 dark:bg-blue-950';
    case 'configured':
      return 'border-purple-500 bg-purple-50 dark:bg-purple-950';
    case 'error':
      return 'border-red-500 bg-red-50 dark:bg-red-950';
    case 'pending':
      return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950';
    default:
      return 'border-gray-300 dark:border-gray-600';
  }
};

// Get status icon
const getStatusIcon = (status?: string, hasData?: boolean) => {
  if (hasData) return <CheckCircle2 className="h-3 w-3 text-green-500" />;

  switch (status) {
    case 'connected':
      return <Link2 className="h-3 w-3 text-blue-500" />;
    case 'configured':
      return <CheckCircle2 className="h-3 w-3 text-purple-500" />;
    case 'error':
      return <AlertCircle className="h-3 w-3 text-red-500" />;
    case 'pending':
      return <Clock className="h-3 w-3 text-yellow-500" />;
    default:
      return null;
  }
};

export function ConnectionBadge({
  nodeType,
  nodeLabel,
  nodeId,
  status = 'connected',
  hasData = false,
  dataCount,
  onClick,
  className
}: ConnectionBadgeProps) {
  const Icon = getNodeIcon(nodeType);
  const statusColor = getStatusColor(status, hasData);
  const StatusIcon = getStatusIcon(status, hasData);

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 px-3 py-1.5 rounded-full border-2',
        'transition-all duration-200',
        statusColor,
        onClick && 'cursor-pointer hover:scale-105',
        className
      )}
      onClick={onClick}
    >
      {/* Node icon */}
      <Icon className="h-4 w-4 text-gray-600 dark:text-gray-400" />

      {/* Node label */}
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {nodeLabel}
      </span>

      {/* Node ID (shortened) */}
      {nodeId && (
        <span className="text-xs text-gray-500 dark:text-gray-500">
          #{nodeId.slice(0, 8)}
        </span>
      )}

      {/* Data count badge */}
      {dataCount !== undefined && dataCount > 0 && (
        <Badge variant="secondary" className="h-5 px-1.5 text-xs">
          {dataCount}
        </Badge>
      )}

      {/* Status icon */}
      {StatusIcon}
    </div>
  );
}

/**
 * ConnectionList Component
 * Shows a list of connections
 */
export function ConnectionList({
  connections,
  className
}: {
  connections: Array<{
    nodeType?: string;
    nodeLabel: string;
    nodeId?: string;
    status?: 'connected' | 'configured' | 'error' | 'pending';
    hasData?: boolean;
    dataCount?: number;
  }>;
  className?: string;
}) {
  if (connections.length === 0) {
    return (
      <div className={cn('text-sm text-muted-foreground', className)}>
        No connections
      </div>
    );
  }

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {connections.map((connection, index) => (
        <ConnectionBadge
          key={`${connection.nodeId}-${index}`}
          {...connection}
        />
      ))}
    </div>
  );
}