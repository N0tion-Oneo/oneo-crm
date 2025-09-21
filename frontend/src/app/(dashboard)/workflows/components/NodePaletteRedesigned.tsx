'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
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
  icon: string;
  color: string;
  category: string;
  subcategory: string;
  isPremium?: boolean;
  isNew?: boolean;
  isBeta?: boolean;
}

// Map node types to subcategories for better organization
const getNodeSubcategory = (nodeType: WorkflowNodeType, category: string): string => {
  // Triggers
  if (nodeType.includes('TRIGGER_MANUAL') || nodeType.includes('TRIGGER_FORM')) {
    return 'User Initiated';
  }
  if (nodeType.includes('TRIGGER_SCHEDULE') || nodeType.includes('TRIGGER_DATE')) {
    return 'Time Based';
  }
  if (nodeType.includes('TRIGGER_WEBHOOK') || nodeType.includes('TRIGGER_API')) {
    return 'External';
  }
  if (nodeType.includes('TRIGGER_RECORD')) {
    return 'Data Events';
  }

  // Actions
  if (nodeType.includes('RECORD_')) {
    return 'Data Operations';
  }
  if (nodeType.includes('UNIPILE_') || nodeType.includes('EMAIL_') || nodeType.includes('TASK_NOTIFY')) {
    return 'Communication';
  }
  if (nodeType.includes('AI_')) {
    return 'AI & Automation';
  }
  if (nodeType.includes('HTTP_') || nodeType.includes('WEBHOOK_')) {
    return 'External Systems';
  }

  // Logic
  if (nodeType.includes('CONDITION') || nodeType.includes('DECISION')) {
    return 'Conditions';
  }
  if (nodeType.includes('LOOP') || nodeType.includes('FOREACH')) {
    return 'Loops';
  }
  if (nodeType.includes('WAIT') || nodeType.includes('DELAY')) {
    return 'Control Flow';
  }

  return category === 'triggers' || category === 'Triggers' ? 'General Triggers' :
         category === 'logic' || category === 'Logic' ? 'Control Flow' : 'General Actions';
};

// Map node types to colors
const getNodeColor = (nodeType: WorkflowNodeType, category: string): string => {
  // Triggers
  if (category === 'triggers' || category === 'Triggers') {
    if (nodeType.includes('MANUAL') || nodeType.includes('FORM')) return 'bg-blue-500';
    if (nodeType.includes('SCHEDULE') || nodeType.includes('DATE')) return 'bg-indigo-500';
    if (nodeType.includes('WEBHOOK') || nodeType.includes('API')) return 'bg-purple-500';
    return 'bg-violet-500';
  }

  // Actions
  if (nodeType.includes('RECORD_')) return 'bg-green-500';
  if (nodeType.includes('EMAIL_') || nodeType.includes('UNIPILE_')) return 'bg-indigo-500';
  if (nodeType.includes('AI_')) return 'bg-pink-500';
  if (nodeType.includes('HTTP_') || nodeType.includes('WEBHOOK_')) return 'bg-teal-500';

  // Logic
  if (nodeType.includes('CONDITION') || nodeType.includes('DECISION')) return 'bg-orange-500';
  if (nodeType.includes('LOOP') || nodeType.includes('FOREACH')) return 'bg-amber-500';
  if (nodeType.includes('WAIT') || nodeType.includes('DELAY')) return 'bg-yellow-500';

  return 'bg-gray-500';
};

// Map emoji icons to Lucide icons
const getIconComponent = (icon: string): React.ElementType => {
  const iconMap: Record<string, React.ElementType> = {
    '➕': Plus,
    '✏️': Edit2,
    '🗑️': Trash2,
    '⏰': Clock,
    '📅': Calendar,
    '📝': FileText,
    '👤': User,
    '🔀': GitBranch,
    '💾': Database,
    '✉️': Mail,
    '📧': Send,
    '💬': MessageSquare,
    '🤖': Bot,
    '✨': Sparkles,
    '🧠': Brain,
    '🔄': RefreshCw,
    '⏸️': PauseCircle,
    '🛑': StopCircle,
    '🌐': Globe,
    '🔗': Link,
    '🔔': Bell,
    '📊': BarChart,
    '⚙️': Settings,
    '🚀': Zap,
    '🔍': Search,
    '🎯': Target,
    '📂': FolderOpen,
    '💡': Info,
    '❓': HelpCircle,
    '✅': CheckCircle,
    '❌': X,
    '⚡': Zap,
    '🏃': Activity,
    '🔓': Unlock,
    '🔒': Lock,
  };
  return iconMap[icon] || Settings;
};

// All node templates are now loaded from backend with proper categories and subcategories
const fallbackNodeTemplates: NodeTemplate[] = [
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
  const [nodeTemplates, setNodeTemplates] = useState<NodeTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch node schemas from backend
  useEffect(() => {
    const fetchNodeSchemas = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/v1/workflows/node_schemas/');
        const schemas = response.data;

        // Transform backend schemas to NodeTemplate format
        const templates: NodeTemplate[] = Object.entries(schemas).map(([nodeType, schema]: [string, any]) => {
          // Use category from backend schema
          // Backend provides these categories: Triggers, Data, AI, Communication, Control, CRM, External, Actions
          let category: string = 'actions'; // default fallback

          // Map backend categories to frontend tab names (we have 3 tabs: triggers, logic, actions)
          if (schema.category) {
            const backendCategory = schema.category.toLowerCase();
            if (backendCategory === 'triggers') {
              category = 'triggers';
            } else if (backendCategory === 'control') {
              category = 'logic'; // Frontend uses 'logic' for control flow
            } else {
              // Data, AI, Communication, CRM, External, Actions all go to actions tab
              category = 'actions';
            }
          }

          // Use backend subcategory if available, otherwise use category for grouping
          // Backend provides both category and subcategory for better organization
          const displaySubcategory = schema.subcategory || schema.category || 'General';

          return {
            type: nodeType as WorkflowNodeType,
            label: schema.display_name || nodeType.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (l: string) => l.toUpperCase()),
            description: schema.description || '',
            icon: schema.icon || '⚙️',
            color: getNodeColor(nodeType as WorkflowNodeType, category),
            category: category,
            subcategory: displaySubcategory, // Use backend subcategory for display grouping
            // Add flags based on node type
            isPremium: nodeType.includes('AI_'),
            isNew: ['AI_MESSAGE_GENERATOR', 'AI_RESPONSE_EVALUATOR', 'AI_CONVERSATION_LOOP', 'CONVERSATION_STATE'].includes(nodeType),
            isBeta: false
          };
        });

        // Define subcategory order for better organization
        const subcategoryOrder = {
          // Trigger subcategories
          'User Initiated': 1,
          'Time Based': 2,
          'Data Events': 3,
          'Communication': 4,
          'External': 5,
          'System Events': 6,
          // Control subcategories
          'Conditional Logic': 10,
          'Loops': 11,
          'Timing': 12,
          'Human Interaction': 13,
          'Control Flow': 14,
          'Advanced': 15,
          // Main categories (when no subcategory)
          'Triggers': 20,
          'Data': 21,
          'AI': 22,
          'Communication': 23,
          'CRM': 24,
          'Control': 25,
          'External': 26,
          'Actions': 27
        };

        // Sort templates by subcategory with defined order
        templates.sort((a, b) => {
          // Get priority from subcategory order
          const aPriority = subcategoryOrder[a.subcategory] || 99;
          const bPriority = subcategoryOrder[b.subcategory] || 99;

          if (aPriority !== bPriority) {
            return aPriority - bPriority;
          }

          // Then by label alphabetically
          return a.label.localeCompare(b.label);
        });

        setNodeTemplates(templates);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch node schemas:', err);
        setError('Failed to load workflow nodes');
        // Use fallback templates
        setNodeTemplates(fallbackNodeTemplates);
      } finally {
        setLoading(false);
      }
    };

    fetchNodeSchemas();
  }, []);

  const filteredNodes = nodeTemplates.filter(node => {
    const matchesCategory = node.category.toLowerCase() === selectedCategory.toLowerCase();
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
      icon: node.icon,
      color: node.color
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  // Loading state
  if (loading) {
    return (
      <div className="py-4 space-y-4">
        <Skeleton className="h-9 w-full" />
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="py-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="py-4 space-y-4">
      <div className="relative">
        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search components..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8 h-9"
        />
      </div>

      <div className="space-y-6">
        {Object.entries(groupedNodes).map(([subcategory, nodes], categoryIndex) => (
          <div key={`category-${subcategory}-${categoryIndex}`}>
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              {subcategory}
            </h3>
            <div className="grid gap-2">
              {nodes.map((node, index) => (
                <Card
                  key={`${subcategory}-${node.type}-${index}`}
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
                      {(() => {
                        const IconComponent = getIconComponent(node.icon);
                        return <IconComponent className="h-4 w-4" />;
                      })()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-medium truncate">
                          {node.label}
                        </h4>
                        <div className="flex items-center gap-1">
                          {node.isPremium && (
                            <Badge key="premium" variant="secondary" className="text-xs px-1 py-0">
                              PRO
                            </Badge>
                          )}
                          {node.isNew && (
                            <Badge key="new" variant="default" className="text-xs px-1 py-0 bg-green-500">
                              NEW
                            </Badge>
                          )}
                          {node.isBeta && (
                            <Badge key="beta" variant="outline" className="text-xs px-1 py-0">
                              BETA
                            </Badge>
                          )}
                        </div>
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