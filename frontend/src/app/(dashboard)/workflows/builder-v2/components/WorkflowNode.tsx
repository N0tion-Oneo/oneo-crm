/**
 * WorkflowNode Component
 * Minimal node representation for workflow builder with config details
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { AlertCircle, CheckCircle } from 'lucide-react';

interface WorkflowNodeData {
  label: string;
  nodeType: string;
  icon?: string;
  config?: any;
  isValid?: boolean;
  hasErrors?: boolean;
}

const WorkflowNode = memo(({ data, selected }: NodeProps<WorkflowNodeData>) => {
  const { label, icon, nodeType, config, hasErrors } = data;

  // Determine node category for styling
  const getNodeCategory = (type: string): string => {
    if (type.startsWith('trigger_')) return 'trigger';
    if (type.includes('ai_')) return 'ai';
    if (type.includes('send_') || type.includes('email') || type.includes('sms')) return 'communication';
    if (type.includes('record_')) return 'data';
    if (['condition', 'for_each', 'wait_'].some(t => type.includes(t))) return 'control';
    return 'action';
  };

  const category = getNodeCategory(nodeType);

  const categoryColors: Record<string, string> = {
    trigger: 'border-green-500 bg-green-50',
    ai: 'border-purple-500 bg-purple-50',
    communication: 'border-blue-500 bg-blue-50',
    data: 'border-orange-500 bg-orange-50',
    control: 'border-gray-500 bg-gray-50',
    action: 'border-indigo-500 bg-indigo-50'
  };

  // Extract key config details to display
  const getConfigSummary = () => {
    if (!config) return null;

    const details: string[] = [];

    // Pipeline selection
    if (config.pipeline_id || config.pipeline_ids) {
      details.push('📊 Pipeline configured');
    }

    // Email/Message details
    if (config.to_email) {
      details.push(`📧 To: ${config.to_email}`);
    }
    if (config.subject) {
      details.push(`📋 ${config.subject.substring(0, 30)}...`);
    }

    // AI Prompt
    if (config.prompt) {
      const promptPreview = config.prompt.substring(0, 40);
      details.push(`💬 ${promptPreview}...`);
    }

    // Condition
    if (config.condition_type) {
      details.push(`🔀 ${config.condition_type}`);
    }
    if (config.conditions && config.conditions.length > 0) {
      details.push(`🎯 ${config.conditions.length} condition(s)`);
    }

    // Wait/Delay
    if (config.delay_type) {
      details.push(`⏱️ ${config.delay_type}`);
    }
    if (config.delay_minutes) {
      details.push(`⏱️ ${config.delay_minutes} min`);
    }

    // HTTP Request
    if (config.url) {
      try {
        const urlHost = new URL(config.url).hostname;
        details.push(`🌐 ${urlHost}`);
      } catch {
        details.push(`🌐 ${config.url.substring(0, 30)}...`);
      }
    }
    if (config.method) {
      details.push(`📡 ${config.method}`);
    }

    // Record operations
    if (config.field_mappings) {
      const fieldCount = Object.keys(config.field_mappings).length;
      if (fieldCount > 0) {
        details.push(`📝 ${fieldCount} fields mapped`);
      }
    }

    // User assignment
    if (config.user_id || config.user_ids) {
      details.push('👤 User assigned');
    }

    // Schedule
    if (config.schedule || config.cron_expression) {
      details.push('📅 Schedule set');
    }

    return details.slice(0, 3); // Show max 3 details
  };

  const configDetails = getConfigSummary();
  const isConfigured = configDetails && configDetails.length > 0;

  return (
    <Card
      className={cn(
        'min-w-[220px] max-w-[280px] transition-all cursor-pointer',
        categoryColors[category],
        selected && 'ring-2 ring-primary ring-offset-2',
        hasErrors && 'border-red-500 bg-red-50'
      )}
      title="Double-click to configure"
    >
      {/* Input handle */}
      {!nodeType.startsWith('trigger_') && (
        <Handle
          type="target"
          position={Position.Top}
          className="!bg-primary !w-2 !h-2"
        />
      )}

      <div className="p-3">
        {/* Node header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 flex-1">
            {icon && <span className="text-lg">{icon}</span>}
            <span className="font-medium text-sm truncate">{label}</span>
          </div>
          {/* Status indicator */}
          <div className="flex-shrink-0">
            {hasErrors ? (
              <AlertCircle className="h-4 w-4 text-red-500" />
            ) : isConfigured ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : null}
          </div>
        </div>

        {/* Config details */}
        {configDetails && configDetails.length > 0 && (
          <div className="space-y-1 mt-2 pt-2 border-t border-current/10">
            {configDetails.map((detail, index) => (
              <div key={index} className="text-xs text-gray-600 truncate">
                {detail}
              </div>
            ))}
          </div>
        )}

        {/* Node type badge */}
        <div className="mt-2">
          <Badge variant="outline" className="text-xs">
            {category}
          </Badge>
        </div>

        {/* Error indicator */}
        {hasErrors && !isConfigured && (
          <div className="mt-2 text-xs text-red-600">
            Configuration required
          </div>
        )}
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-primary !w-2 !h-2"
      />
    </Card>
  );
});

WorkflowNode.displayName = 'WorkflowNode';

export default WorkflowNode;