'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { useState } from 'react';
import {
  Zap, Clock, Calendar, FileText, User, GitBranch,
  Database, Send, MessageSquare, Mail, Bot, Code,
  Filter, ArrowRightLeft, Shuffle, PauseCircle, StopCircle,
  RefreshCw, AlertCircle, CheckCircle, Package, Settings,
  Search, Target, Sparkles, Workflow, Hash, Globe,
  FileCode, Terminal, Webhook, Link, UserPlus, UserCheck,
  Bell, BarChart, PieChart, TrendingUp, Shield, Key,
  Cloud, Download, Upload, FolderOpen, Save, Edit,
  Eye, EyeOff, Lock, Unlock, Copy, Trash, Archive,
  Plus, Minus, X, Check, Info, HelpCircle, ChevronRight,
  Edit2, Brain, Activity, Trash2
} from 'lucide-react';
import { WorkflowNodeType } from '../types';
import { cn } from '@/lib/utils';

interface NodePaletteRedesignedProps {
  selectedCategory: string;
}

interface NodeTemplate {
  type: WorkflowNodeType;
  label: string;
  description: string;
  icon: React.ElementType;
  color: string;
  category: 'triggers' | 'actions' | 'logic';
  subcategory: string;
  isPremium?: boolean;
  isNew?: boolean;
  isBeta?: boolean;
}

const nodeTemplates: NodeTemplate[] = [
  // Triggers - User Initiated
  {
    type: WorkflowNodeType.TRIGGER_MANUAL,
    label: 'Manual Trigger',
    description: 'Start workflow manually',
    icon: User,
    color: 'bg-blue-500',
    category: 'triggers',
    subcategory: 'User Initiated'
  },
  {
    type: WorkflowNodeType.TRIGGER_FORM_SUBMITTED,
    label: 'Form Submitted',
    description: 'When form is submitted',
    icon: FileText,
    color: 'bg-blue-500',
    category: 'triggers',
    subcategory: 'User Initiated'
  },

  // Triggers - Time Based
  {
    type: WorkflowNodeType.TRIGGER_SCHEDULE,
    label: 'Schedule',
    description: 'Run on a schedule',
    icon: Clock,
    color: 'bg-indigo-500',
    category: 'triggers',
    subcategory: 'Time Based'
  },
  {
    type: WorkflowNodeType.TRIGGER_DATE_REACHED,
    label: 'Date Reached',
    description: 'Trigger on specific date',
    icon: Calendar,
    color: 'bg-indigo-500',
    category: 'triggers',
    subcategory: 'Time Based'
  },

  // Triggers - External
  {
    type: WorkflowNodeType.TRIGGER_WEBHOOK,
    label: 'Webhook',
    description: 'Trigger via webhook',
    icon: Webhook,
    color: 'bg-purple-500',
    category: 'triggers',
    subcategory: 'External'
  },
  {
    type: WorkflowNodeType.TRIGGER_API_ENDPOINT,
    label: 'API Endpoint',
    description: 'Trigger via API call',
    icon: Globe,
    color: 'bg-purple-500',
    category: 'triggers',
    subcategory: 'External'
  },
  {
    type: WorkflowNodeType.TRIGGER_RECORD_CREATED,
    label: 'Record Created',
    description: 'When a new record is created',
    icon: Plus,
    color: 'bg-green-500',
    category: 'triggers',
    subcategory: 'Data Events'
  },
  {
    type: WorkflowNodeType.TRIGGER_RECORD_UPDATED,
    label: 'Record Updated',
    description: 'When a record or field is updated',
    icon: Edit,
    color: 'bg-green-500',
    category: 'triggers',
    subcategory: 'Data Events'
  },
  {
    type: WorkflowNodeType.TRIGGER_RECORD_DELETED,
    label: 'Record Deleted',
    description: 'When a record is deleted',
    icon: Trash,
    color: 'bg-green-500',
    category: 'triggers',
    subcategory: 'Data Events'
  },
  {
    type: WorkflowNodeType.TRIGGER_EMAIL_RECEIVED,
    label: 'Email Received',
    description: 'When email is received',
    icon: Mail,
    color: 'bg-purple-500',
    category: 'triggers',
    subcategory: 'Communication'
  },
  {
    type: WorkflowNodeType.TRIGGER_LINKEDIN_MESSAGE,
    label: 'LinkedIn Message',
    description: 'When LinkedIn message received',
    icon: Hash,
    color: 'bg-purple-500',
    category: 'triggers',
    subcategory: 'Communication'
  },
  {
    type: WorkflowNodeType.TRIGGER_WHATSAPP_MESSAGE,
    label: 'WhatsApp Message',
    description: 'When WhatsApp message received',
    icon: MessageSquare,
    color: 'bg-purple-500',
    category: 'triggers',
    subcategory: 'Communication'
  },

  // Actions - Data
  {
    type: WorkflowNodeType.RECORD_CREATE,
    label: 'Create Record',
    description: 'Create a new record',
    icon: Plus,
    color: 'bg-orange-500',
    category: 'actions',
    subcategory: 'Data Operations'
  },
  {
    type: WorkflowNodeType.RECORD_UPDATE,
    label: 'Update Record',
    description: 'Update existing record',
    icon: Edit,
    color: 'bg-orange-500',
    category: 'actions',
    subcategory: 'Data Operations'
  },
  {
    type: WorkflowNodeType.RECORD_FIND,
    label: 'Find Record',
    description: 'Search for records',
    icon: Search,
    color: 'bg-orange-500',
    category: 'actions',
    subcategory: 'Data Operations'
  },
  {
    type: WorkflowNodeType.RECORD_DELETE,
    label: 'Delete Record',
    description: 'Delete a record',
    icon: Trash2,
    color: 'bg-orange-500',
    category: 'actions',
    subcategory: 'Data Operations'
  },
  {
    type: WorkflowNodeType.RESOLVE_CONTACT,
    label: 'Find or Create Record',
    description: 'Find existing or create new record',
    icon: UserPlus,
    color: 'bg-orange-500',
    category: 'actions',
    subcategory: 'Data Operations'
  },
  {
    type: WorkflowNodeType.MERGE_DATA,
    label: 'Merge Data',
    description: 'Combine data from multiple sources',
    icon: GitBranch,
    color: 'bg-orange-500',
    category: 'actions',
    subcategory: 'Data Operations'
  },
  {
    type: WorkflowNodeType.CREATE_FOLLOW_UP_TASK,
    label: 'Create Follow-up Task',
    description: 'Create a task for follow-up',
    icon: CheckCircle,
    color: 'bg-orange-500',
    category: 'actions',
    subcategory: 'Data Operations'
  },

  // Actions - Communication (UniPile)
  {
    type: WorkflowNodeType.UNIPILE_SEND_EMAIL,
    label: 'Send Email',
    description: 'Send email via UniPile',
    icon: Mail,
    color: 'bg-indigo-500',
    category: 'actions',
    subcategory: 'Communication'
  },
  {
    type: WorkflowNodeType.UNIPILE_SEND_WHATSAPP,
    label: 'Send WhatsApp',
    description: 'Send WhatsApp message',
    icon: MessageSquare,
    color: 'bg-indigo-500',
    category: 'actions',
    subcategory: 'Communication'
  },
  {
    type: WorkflowNodeType.UNIPILE_SEND_LINKEDIN,
    label: 'Send LinkedIn',
    description: 'Send LinkedIn message',
    icon: Hash,
    color: 'bg-indigo-500',
    category: 'actions',
    subcategory: 'Communication'
  },
  {
    type: WorkflowNodeType.UNIPILE_SEND_SMS,
    label: 'Send SMS',
    description: 'Send SMS message',
    icon: MessageSquare,
    color: 'bg-indigo-500',
    category: 'actions',
    subcategory: 'Communication'
  },
  {
    type: WorkflowNodeType.TASK_NOTIFY,
    label: 'Send Notification',
    description: 'Create task/notification',
    icon: Bell,
    color: 'bg-indigo-500',
    category: 'actions',
    subcategory: 'Communication'
  },

  // Actions - AI
  {
    type: WorkflowNodeType.AI_PROMPT,
    label: 'AI Prompt',
    description: 'Process with AI',
    icon: Sparkles,
    color: 'bg-pink-500',
    category: 'actions',
    subcategory: 'AI & Automation',
    isPremium: true
  },
  {
    type: WorkflowNodeType.AI_ANALYSIS,
    label: 'AI Analysis',
    description: 'Analyze with AI',
    icon: Brain,
    color: 'bg-pink-500',
    category: 'actions',
    subcategory: 'AI & Automation',
    isPremium: true
  },
  {
    type: WorkflowNodeType.AI_CONVERSATION_LOOP,
    label: 'AI Conversation',
    description: 'AI-powered conversation flow',
    icon: Bot,
    color: 'bg-pink-500',
    category: 'actions',
    subcategory: 'AI & Automation',
    isPremium: true,
    isNew: true
  },
  {
    type: WorkflowNodeType.AI_MESSAGE_GENERATOR,
    label: 'AI Message Generator',
    description: 'Generate contextual messages with AI',
    icon: Sparkles,
    color: 'bg-pink-500',
    category: 'actions',
    subcategory: 'AI & Automation',
    isNew: true
  },
  {
    type: WorkflowNodeType.AI_RESPONSE_EVALUATOR,
    label: 'AI Response Evaluator',
    description: 'Evaluate responses with AI',
    icon: Brain,
    color: 'bg-pink-500',
    category: 'actions',
    subcategory: 'AI & Automation',
    isNew: true
  },
  {
    type: WorkflowNodeType.CONVERSATION_STATE,
    label: 'Conversation State',
    description: 'Manage conversation state',
    icon: Database,
    color: 'bg-pink-500',
    category: 'actions',
    subcategory: 'AI & Automation',
    isNew: true
  },

  // Actions - External
  {
    type: WorkflowNodeType.HTTP_REQUEST,
    label: 'HTTP Request',
    description: 'Make HTTP API call',
    icon: Globe,
    color: 'bg-teal-500',
    category: 'actions',
    subcategory: 'External Systems'
  },
  {
    type: WorkflowNodeType.WEBHOOK_OUT,
    label: 'Send Webhook',
    description: 'Send webhook to external system',
    icon: Link,
    color: 'bg-teal-500',
    category: 'actions',
    subcategory: 'External Systems'
  },

  // Logic - Control Flow
  {
    type: WorkflowNodeType.CONDITION,
    label: 'If/Then',
    description: 'Conditional branching',
    icon: GitBranch,
    color: 'bg-yellow-500',
    category: 'logic',
    subcategory: 'Control Flow'
  },
  {
    type: WorkflowNodeType.FOR_EACH,
    label: 'For Each',
    description: 'Loop through items',
    icon: RefreshCw,
    color: 'bg-yellow-500',
    category: 'logic',
    subcategory: 'Control Flow'
  },
  {
    type: WorkflowNodeType.WORKFLOW_LOOP_CONTROLLER,
    label: 'Loop Controller',
    description: 'Control node that loops workflow sections',
    icon: RefreshCw,
    color: 'bg-indigo-500',
    category: 'logic',
    subcategory: 'Control Flow',
    isNew: true
  },
  {
    type: WorkflowNodeType.WAIT_DELAY,
    label: 'Wait/Delay',
    description: 'Pause execution',
    icon: PauseCircle,
    color: 'bg-yellow-500',
    category: 'logic',
    subcategory: 'Control Flow'
  },
  {
    type: WorkflowNodeType.WAIT_FOR_RESPONSE,
    label: 'Wait for Response',
    description: 'Wait for communication reply',
    icon: MessageSquare,
    color: 'bg-yellow-500',
    category: 'logic',
    subcategory: 'Control Flow'
  },
  {
    type: WorkflowNodeType.WAIT_FOR_RECORD_EVENT,
    label: 'Wait for Event',
    description: 'Wait for record change',
    icon: Activity,
    color: 'bg-yellow-500',
    category: 'logic',
    subcategory: 'Control Flow'
  },
  {
    type: WorkflowNodeType.WAIT_FOR_CONDITION,
    label: 'Wait for Condition',
    description: 'Wait for complex condition',
    icon: GitBranch,
    color: 'bg-yellow-500',
    category: 'logic',
    subcategory: 'Control Flow'
  },

  // Logic - Human Interaction
  {
    type: WorkflowNodeType.APPROVAL,
    label: 'Approval',
    description: 'Require human approval',
    icon: UserCheck,
    color: 'bg-cyan-500',
    category: 'logic',
    subcategory: 'Human Interaction'
  },

  // Logic - Advanced
  {
    type: WorkflowNodeType.SUB_WORKFLOW,
    label: 'Sub-workflow',
    description: 'Call another workflow',
    icon: Workflow,
    color: 'bg-purple-500',
    category: 'logic',
    subcategory: 'Advanced'
  }
];

export function NodePaletteRedesigned({ selectedCategory }: NodePaletteRedesignedProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredNodes = nodeTemplates.filter(node => {
    const matchesCategory = node.category === selectedCategory;
    const matchesSearch = searchQuery === '' ||
      node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const groupedNodes = filteredNodes.reduce((acc, node) => {
    if (!acc[node.subcategory]) {
      acc[node.subcategory] = [];
    }
    acc[node.subcategory].push(node);
    return acc;
  }, {} as Record<string, NodeTemplate[]>);

  const onDragStart = (event: React.DragEvent, node: NodeTemplate) => {
    // Pass the full node data as JSON
    event.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: node.type,
      label: node.label,
      description: node.description,
      icon: node.icon.name,
      color: node.color
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="py-4 space-y-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search components..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8 h-9"
        />
      </div>

      {/* Node Groups */}
      <div className="space-y-6">
        {Object.entries(groupedNodes).map(([subcategory, nodes]) => (
          <div key={subcategory}>
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              {subcategory}
            </h3>
            <div className="grid gap-2">
              {nodes.map((node) => (
                <Card
                  key={node.type}
                  className={cn(
                    "p-3 cursor-move hover:shadow-md transition-all hover:scale-[1.02]",
                    "border hover:border-primary/50"
                  )}
                  draggable
                  onDragStart={(e) => onDragStart(e, node)}
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "p-2 rounded-lg text-white",
                      node.color
                    )}>
                      <node.icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-medium truncate">
                          {node.label}
                        </h4>
                        {node.isPremium && (
                          <Badge variant="secondary" className="text-xs px-1 py-0">
                            PRO
                          </Badge>
                        )}
                        {node.isNew && (
                          <Badge variant="default" className="text-xs px-1 py-0 bg-green-500">
                            NEW
                          </Badge>
                        )}
                        {node.isBeta && (
                          <Badge variant="outline" className="text-xs px-1 py-0">
                            BETA
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {node.description}
                      </p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>

      {filteredNodes.length === 0 && (
        <div className="text-center py-8">
          <p className="text-sm text-muted-foreground">
            No components found matching "{searchQuery}"
          </p>
        </div>
      )}
    </div>
  );
}