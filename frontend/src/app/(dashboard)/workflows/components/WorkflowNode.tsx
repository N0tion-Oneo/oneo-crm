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
  FileText,
  Search,
  Trash2,
  GitBranch,
  Repeat,
  RefreshCw,
  Timer,
  PauseCircle,
  Mail,
  MessageSquare,
  MessageCircle,
  Brain,
  Sparkles,
  Globe,
  Webhook,
  Bell,
  CheckCircle,
  GitMerge,
  User,
  UserPlus,
  Plus,
  Edit,
  Hash,
  Linkedin
} from 'lucide-react';

const nodeIcons: Partial<Record<WorkflowNodeType, React.ComponentType<{ className?: string }>>> = {
  // Triggers - User Initiated
  [WorkflowNodeType.TRIGGER_MANUAL]: User,
  [WorkflowNodeType.TRIGGER_FORM_SUBMITTED]: FileText,

  // Triggers - Time Based
  [WorkflowNodeType.TRIGGER_SCHEDULE]: Clock,
  [WorkflowNodeType.TRIGGER_DATE_REACHED]: Calendar,

  // Triggers - External
  [WorkflowNodeType.TRIGGER_WEBHOOK]: Webhook,
  [WorkflowNodeType.TRIGGER_API_ENDPOINT]: Globe,

  // Triggers - Data Events
  [WorkflowNodeType.TRIGGER_RECORD_CREATED]: Plus,
  [WorkflowNodeType.TRIGGER_RECORD_UPDATED]: Edit,
  [WorkflowNodeType.TRIGGER_RECORD_DELETED]: Trash2,

  // Triggers - Communication
  [WorkflowNodeType.TRIGGER_EMAIL_RECEIVED]: Mail,
  [WorkflowNodeType.TRIGGER_LINKEDIN_MESSAGE]: Hash,
  [WorkflowNodeType.TRIGGER_WHATSAPP_MESSAGE]: MessageSquare,

  // Triggers - Other
  [WorkflowNodeType.TRIGGER_CONDITION_MET]: GitBranch,
  [WorkflowNodeType.TRIGGER_PIPELINE_STAGE_CHANGED]: GitBranch,
  [WorkflowNodeType.TRIGGER_WORKFLOW_COMPLETED]: GitMerge,

  // Data Operations
  [WorkflowNodeType.RECORD_CREATE]: Plus,
  [WorkflowNodeType.RECORD_UPDATE]: Edit,
  [WorkflowNodeType.RECORD_FIND]: Search,
  [WorkflowNodeType.RECORD_DELETE]: Trash2,
  [WorkflowNodeType.RESOLVE_CONTACT]: UserPlus,
  [WorkflowNodeType.MERGE_DATA]: GitBranch,
  [WorkflowNodeType.CREATE_FOLLOW_UP_TASK]: CheckCircle,

  // Control Flow
  [WorkflowNodeType.CONDITION]: GitBranch,
  [WorkflowNodeType.FOR_EACH]: RefreshCw,
  [WorkflowNodeType.WORKFLOW_LOOP_CONTROLLER]: RefreshCw,
  [WorkflowNodeType.WAIT_DELAY]: PauseCircle,
  [WorkflowNodeType.WAIT_FOR_RESPONSE]: MessageSquare,
  [WorkflowNodeType.WAIT_FOR_RECORD_EVENT]: Clock,
  [WorkflowNodeType.WAIT_FOR_CONDITION]: Clock,
  [WorkflowNodeType.CONVERSATION_STATE]: Database,

  // Communication
  [WorkflowNodeType.UNIPILE_SEND_EMAIL]: Mail,
  [WorkflowNodeType.UNIPILE_SEND_WHATSAPP]: MessageSquare,
  [WorkflowNodeType.UNIPILE_SEND_LINKEDIN]: Hash,
  [WorkflowNodeType.UNIPILE_SEND_SMS]: MessageCircle,
  [WorkflowNodeType.TASK_NOTIFY]: Bell,

  // AI Operations
  [WorkflowNodeType.AI_PROMPT]: Brain,
  [WorkflowNodeType.AI_ANALYSIS]: Brain,
  [WorkflowNodeType.AI_CONVERSATION_LOOP]: Brain,
  [WorkflowNodeType.AI_MESSAGE_GENERATOR]: Sparkles,
  [WorkflowNodeType.AI_RESPONSE_EVALUATOR]: Brain,

  // External
  [WorkflowNodeType.HTTP_REQUEST]: Globe,
  [WorkflowNodeType.WEBHOOK_OUT]: Link,

  // Workflow
  [WorkflowNodeType.APPROVAL]: CheckCircle,
  [WorkflowNodeType.SUB_WORKFLOW]: GitMerge,
};

const nodeColors: Partial<Record<WorkflowNodeType, string>> = {
  // Triggers - User Initiated (Blue)
  [WorkflowNodeType.TRIGGER_MANUAL]: 'border-blue-500 bg-blue-50',
  [WorkflowNodeType.TRIGGER_FORM_SUBMITTED]: 'border-blue-500 bg-blue-50',

  // Triggers - Time Based (Indigo)
  [WorkflowNodeType.TRIGGER_SCHEDULE]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.TRIGGER_DATE_REACHED]: 'border-indigo-500 bg-indigo-50',

  // Triggers - External (Purple)
  [WorkflowNodeType.TRIGGER_WEBHOOK]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.TRIGGER_API_ENDPOINT]: 'border-purple-500 bg-purple-50',

  // Triggers - Data Events (Green)
  [WorkflowNodeType.TRIGGER_RECORD_CREATED]: 'border-green-500 bg-green-50',
  [WorkflowNodeType.TRIGGER_RECORD_UPDATED]: 'border-green-500 bg-green-50',
  [WorkflowNodeType.TRIGGER_RECORD_DELETED]: 'border-green-500 bg-green-50',

  // Triggers - Communication (Purple)
  [WorkflowNodeType.TRIGGER_EMAIL_RECEIVED]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.TRIGGER_LINKEDIN_MESSAGE]: 'border-purple-500 bg-purple-50',
  [WorkflowNodeType.TRIGGER_WHATSAPP_MESSAGE]: 'border-purple-500 bg-purple-50',

  // Triggers - Other
  [WorkflowNodeType.TRIGGER_CONDITION_MET]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.TRIGGER_PIPELINE_STAGE_CHANGED]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.TRIGGER_WORKFLOW_COMPLETED]: 'border-orange-500 bg-orange-50',

  // Data Operations (Orange)
  [WorkflowNodeType.RECORD_CREATE]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.RECORD_UPDATE]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.RECORD_FIND]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.RECORD_DELETE]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.RESOLVE_CONTACT]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.MERGE_DATA]: 'border-orange-500 bg-orange-50',
  [WorkflowNodeType.CREATE_FOLLOW_UP_TASK]: 'border-orange-500 bg-orange-50',

  // Control Flow (Yellow)
  [WorkflowNodeType.CONDITION]: 'border-yellow-500 bg-yellow-50',
  [WorkflowNodeType.FOR_EACH]: 'border-yellow-500 bg-yellow-50',
  [WorkflowNodeType.WORKFLOW_LOOP_CONTROLLER]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.WAIT_DELAY]: 'border-yellow-500 bg-yellow-50',
  [WorkflowNodeType.WAIT_FOR_RESPONSE]: 'border-yellow-500 bg-yellow-50',
  [WorkflowNodeType.WAIT_FOR_RECORD_EVENT]: 'border-yellow-500 bg-yellow-50',
  [WorkflowNodeType.WAIT_FOR_CONDITION]: 'border-yellow-500 bg-yellow-50',
  [WorkflowNodeType.CONVERSATION_STATE]: 'border-pink-500 bg-pink-50',

  // Communication (Indigo)
  [WorkflowNodeType.UNIPILE_SEND_EMAIL]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.UNIPILE_SEND_WHATSAPP]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.UNIPILE_SEND_LINKEDIN]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.UNIPILE_SEND_SMS]: 'border-indigo-500 bg-indigo-50',
  [WorkflowNodeType.TASK_NOTIFY]: 'border-indigo-500 bg-indigo-50',

  // AI Operations (Pink)
  [WorkflowNodeType.AI_PROMPT]: 'border-pink-500 bg-pink-50',
  [WorkflowNodeType.AI_ANALYSIS]: 'border-pink-500 bg-pink-50',
  [WorkflowNodeType.AI_CONVERSATION_LOOP]: 'border-pink-500 bg-pink-50',
  [WorkflowNodeType.AI_MESSAGE_GENERATOR]: 'border-pink-500 bg-pink-50',
  [WorkflowNodeType.AI_RESPONSE_EVALUATOR]: 'border-pink-500 bg-pink-50',

  // External (Teal)
  [WorkflowNodeType.HTTP_REQUEST]: 'border-teal-500 bg-teal-50',
  [WorkflowNodeType.WEBHOOK_OUT]: 'border-teal-500 bg-teal-50',

  // Workflow (Purple)
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