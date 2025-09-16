import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card } from '@/components/ui/card';
import { WorkflowNodeType } from '../types';
import {
  Play,
  Clock,
  Link,
  Calendar,
  Database,
  FileEdit,
  Search,
  Trash2,
  GitBranch,
  Repeat,
  Timer,
  Mail,
  MessageSquare,
  Linkedin,
  MessageCircle,
  Brain,
  Globe,
  Webhook,
  Bell,
  CheckCircle,
  GitMerge
} from 'lucide-react';

const nodeIcons: Record<WorkflowNodeType, React.ComponentType<{ className?: string }>> = {
  // Triggers
  [WorkflowNodeType.TRIGGER_MANUAL]: Play,
  [WorkflowNodeType.TRIGGER_SCHEDULE]: Clock,
  [WorkflowNodeType.TRIGGER_WEBHOOK]: Link,
  [WorkflowNodeType.TRIGGER_EVENT]: Calendar,
  [WorkflowNodeType.TRIGGER_RECORD_CREATED]: Database,
  [WorkflowNodeType.TRIGGER_RECORD_UPDATED]: FileEdit,
  [WorkflowNodeType.TRIGGER_RECORD_DELETED]: Trash2,
  [WorkflowNodeType.TRIGGER_API_ENDPOINT]: Globe,
  [WorkflowNodeType.TRIGGER_FORM_SUBMITTED]: FileEdit,
  [WorkflowNodeType.TRIGGER_EMAIL_RECEIVED]: Mail,
  [WorkflowNodeType.TRIGGER_MESSAGE_RECEIVED]: MessageSquare,
  [WorkflowNodeType.TRIGGER_DATE_REACHED]: Calendar,
  [WorkflowNodeType.TRIGGER_CONDITION_MET]: GitBranch,
  [WorkflowNodeType.TRIGGER_PIPELINE_STAGE_CHANGED]: GitBranch,
  [WorkflowNodeType.TRIGGER_ENGAGEMENT_THRESHOLD]: Bell,
  [WorkflowNodeType.TRIGGER_WORKFLOW_COMPLETED]: GitMerge,
  // Data Operations
  [WorkflowNodeType.RECORD_CREATE]: Database,
  [WorkflowNodeType.RECORD_UPDATE]: FileEdit,
  [WorkflowNodeType.RECORD_FIND]: Search,
  [WorkflowNodeType.RECORD_DELETE]: Trash2,
  // Control Flow
  [WorkflowNodeType.CONDITION]: GitBranch,
  [WorkflowNodeType.FOR_EACH]: Repeat,
  [WorkflowNodeType.WAIT_DELAY]: Timer,
  // Communication
  [WorkflowNodeType.UNIPILE_SEND_EMAIL]: Mail,
  [WorkflowNodeType.UNIPILE_SEND_WHATSAPP]: MessageSquare,
  [WorkflowNodeType.UNIPILE_SEND_LINKEDIN]: Linkedin,
  [WorkflowNodeType.UNIPILE_SEND_SMS]: MessageCircle,
  // AI
  [WorkflowNodeType.AI_PROMPT]: Brain,
  [WorkflowNodeType.AI_ANALYSIS]: Brain,
  // Utility
  [WorkflowNodeType.HTTP_REQUEST]: Globe,
  [WorkflowNodeType.WEBHOOK_OUT]: Webhook,
  [WorkflowNodeType.TASK_NOTIFY]: Bell,
  [WorkflowNodeType.APPROVAL]: CheckCircle,
  [WorkflowNodeType.SUB_WORKFLOW]: GitMerge,
};

const nodeColors: Partial<Record<WorkflowNodeType, string>> = {
  // Triggers
  [WorkflowNodeType.TRIGGER_MANUAL]: 'border-blue-500 bg-blue-50',
  [WorkflowNodeType.TRIGGER_SCHEDULE]: 'border-blue-500 bg-blue-50',
  [WorkflowNodeType.TRIGGER_WEBHOOK]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.TRIGGER_API_ENDPOINT]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.TRIGGER_RECORD_CREATED]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.TRIGGER_RECORD_UPDATED]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.TRIGGER_RECORD_DELETED]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.TRIGGER_FORM_SUBMITTED]: 'border-green-500 bg-green-50',
  [WorkflowNodeType.TRIGGER_EMAIL_RECEIVED]: 'border-green-500 bg-green-50',
  [WorkflowNodeType.TRIGGER_MESSAGE_RECEIVED]: 'border-green-500 bg-green-50',
  [WorkflowNodeType.TRIGGER_STATUS_CHANGED]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.TRIGGER_DATE_REACHED]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.TRIGGER_CONDITION_MET]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.TRIGGER_PIPELINE_STAGE_CHANGED]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.TRIGGER_ENGAGEMENT_THRESHOLD]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.TRIGGER_WORKFLOW_COMPLETED]: 'border-orange-500 bg-orange-50',
  // Communication
  [WorkflowNodeType.UNIPILE_SEND_EMAIL]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.UNIPILE_SEND_WHATSAPP]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.UNIPILE_SEND_LINKEDIN]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.UNIPILE_SEND_SMS]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.TASK_NOTIFY]: 'border-indigo-500 bg-indigo-50',
  // AI
  [WorkflowNodeType.AI_PROMPT]: 'border-pink-500 bg-pink-50',
  [WorkflowNodeType.AI_ANALYSIS]: 'border-pink-500 bg-pink-50',
  // External
  [WorkflowNodeType.HTTP_REQUEST]: 'border-teal-500 bg-teal-50',
  [WorkflowNodeType.WEBHOOK_OUT]: 'border-teal-500 bg-teal-50',
  // Logic
  [WorkflowNodeType.CONDITION]: 'border-yellow-500 bg-yellow-50',
  [WorkflowNodeType.FOR_EACH]: 'border-yellow-500 bg-yellow-50',
  [WorkflowNodeType.WAIT_DELAY]: 'border-yellow-500 bg-yellow-50',
  // Data
  [WorkflowNodeType.RECORD_CREATE]: 'border-cyan-500 bg-cyan-50',
  [WorkflowNodeType.RECORD_UPDATE]: 'border-cyan-500 bg-cyan-50',
  [WorkflowNodeType.RECORD_FIND]: 'border-cyan-500 bg-cyan-50',
  [WorkflowNodeType.RECORD_DELETE]: 'border-cyan-500 bg-cyan-50',
  // Other
  [WorkflowNodeType.APPROVAL]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.SUB_WORKFLOW]: 'border-purple-500 bg-purple-50',
};

export const WorkflowNodeComponent = memo(({ data, selected }: NodeProps) => {
  const nodeType = data.nodeType as WorkflowNodeType;
  const Icon = nodeIcons[nodeType] || Database;
  const colorClass = nodeColors[nodeType] || 'border-gray-500 bg-gray-50';
  const isTrigger = nodeType.startsWith('TRIGGER_');

  return (
    <>
      {!isTrigger && (
        <Handle
          type="target"
          position={Position.Top}
          className="w-3 h-3 bg-primary border-2 border-background"
        />
      )}

      <Card
        className={`
          px-4 py-3 min-w-[180px] cursor-pointer transition-all
          ${colorClass}
          ${selected ? 'ring-2 ring-primary shadow-lg' : 'hover:shadow-md'}
        `}
      >
        <div className="flex items-center gap-2">
          <div className={`
            p-2 rounded-md
            ${selected ? 'bg-background' : 'bg-background/50'}
          `}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <div className="font-medium text-sm">{data.label}</div>
            {data.description && (
              <div className="text-xs text-muted-foreground mt-1">
                {data.description}
              </div>
            )}
          </div>
        </div>

        {/* Show status indicator if node is configured */}
        {data.config && Object.keys(data.config).length > 0 && (
          <div className="mt-2 pt-2 border-t">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              <span className="text-xs text-muted-foreground">Configured</span>
            </div>
          </div>
        )}
      </Card>

      {/* Conditional outputs for branching nodes */}
      {nodeType === WorkflowNodeType.CONDITION && (
        <>
          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            style={{ left: '30%' }}
            className="w-3 h-3 bg-green-500 border-2 border-background"
          />
          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            style={{ left: '70%' }}
            className="w-3 h-3 bg-red-500 border-2 border-background"
          />
        </>
      )}

      {/* Default output */}
      {nodeType !== WorkflowNodeType.CONDITION && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="w-3 h-3 bg-primary border-2 border-background"
        />
      )}
    </>
  );
});

WorkflowNodeComponent.displayName = 'WorkflowNodeComponent';