import { Workflow } from '../types';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Play,
  Pause,
  Edit,
  Trash2,
  Clock,
  CheckCircle,
  XCircle,
  MoreVertical
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { formatDistanceToNow } from 'date-fns';

interface WorkflowListProps {
  workflows: Workflow[];
  onEdit: (workflow: Workflow) => void;
  onDelete: (workflow: Workflow) => void;
  onTrigger: (workflow: Workflow) => void;
  onToggleStatus: (workflow: Workflow) => void;
}

export function WorkflowList({
  workflows,
  onEdit,
  onDelete,
  onTrigger,
  onToggleStatus
}: WorkflowListProps) {
  const getExecutionIcon = (status?: string) => {
    switch (status) {
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getTriggerTypeBadge = (triggerType: string) => {
    const typeColors: Record<string, string> = {
      manual: 'bg-blue-100 text-blue-800',
      schedule: 'bg-purple-100 text-purple-800',
      webhook: 'bg-green-100 text-green-800',
      event: 'bg-orange-100 text-orange-800',
    };

    return (
      <Badge className={typeColors[triggerType] || 'bg-gray-100 text-gray-800'}>
        {triggerType}
      </Badge>
    );
  };

  return (
    <div className="space-y-4">
      {workflows.map((workflow) => (
        <Card key={workflow.id} className="p-6">
          <div className="flex items-start justify-between">
            {/* Left side - Workflow info */}
            <div className="flex-1 space-y-3">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-semibold">{workflow.name}</h3>
                {getTriggerTypeBadge(workflow.trigger_type)}
                <Badge variant={workflow.status === 'active' ? 'default' : 'secondary'}>
                  {workflow.status}
                </Badge>
              </div>

              {workflow.description && (
                <p className="text-sm text-muted-foreground">
                  {workflow.description}
                </p>
              )}

              <div className="flex items-center gap-6 text-sm text-muted-foreground">
                <span>
                  Created {formatDistanceToNow(new Date(workflow.created_at), { addSuffix: true })}
                </span>
                <span>
                  {workflow.execution_count} executions
                </span>
                {workflow.last_execution && (
                  <div className="flex items-center gap-1">
                    {getExecutionIcon(workflow.last_execution.status)}
                    <span>
                      Last run {formatDistanceToNow(
                        new Date(workflow.last_execution.started_at),
                        { addSuffix: true }
                      )}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Right side - Actions */}
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onTrigger(workflow)}
                disabled={workflow.status !== 'active'}
              >
                <Play className="h-4 w-4" />
              </Button>

              <Button
                size="sm"
                variant="outline"
                onClick={() => onToggleStatus(workflow)}
              >
                {workflow.status === 'active' ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" variant="ghost">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onEdit(workflow)}>
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    Duplicate
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    View Executions
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => onDelete(workflow)}
                    className="text-red-600"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}