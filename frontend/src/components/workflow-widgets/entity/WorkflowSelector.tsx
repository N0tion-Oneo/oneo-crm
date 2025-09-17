/**
 * Workflow selection widget
 */

import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { GitBranch, X, Loader2 } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';
import { useEntityData } from './useEntityData';

export const WorkflowSelector: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {} } = props;
  const isMultiple = uiHints.widget === 'workflow_multiselect' || uiHints.multiple;

  // Use workflows from props if available, otherwise fetch
  const shouldFetch = !props.workflows || props.workflows.length === 0;
  const { data: fetchedWorkflows, isLoading } = useEntityData('workflows', {
    enabled: shouldFetch
  });

  const workflows = props.workflows || fetchedWorkflows;
  const placeholder = props.placeholder || uiHints.placeholder || 'Select workflow(s)';

  // Filter workflows if needed
  let filteredWorkflows = workflows;
  if (uiHints.filter_reusable) {
    filteredWorkflows = workflows.filter((w: any) => w.is_reusable);
  }
  if (uiHints.filter_active) {
    filteredWorkflows = filteredWorkflows.filter((w: any) => w.is_active);
  }

  if (isMultiple) {
    return (
      <WorkflowMultiSelect
        {...props}
        workflows={filteredWorkflows}
        isLoading={isLoading}
      />
    );
  }

  return (
    <BaseWidgetWrapper {...props}>
      <Select
        value={value || ''}
        onValueChange={onChange}
        disabled={props.disabled || props.readonly || isLoading}
      >
        <SelectTrigger>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading workflows...</span>
            </div>
          ) : (
            <SelectValue placeholder={placeholder} />
          )}
        </SelectTrigger>
        <SelectContent>
          {filteredWorkflows.map((workflow: any) => {
            const workflowId = workflow.id || workflow.value;
            const workflowName = workflow.name || workflow.label || workflowId;
            const isActive = workflow.is_active;

            return (
              <SelectItem key={workflowId} value={workflowId}>
                <div className="flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-gray-400" />
                  <div className="flex flex-col">
                    <span>{workflowName}</span>
                    <span className="text-xs text-gray-500">
                      {isActive ? 'Active' : 'Inactive'}
                      {workflow.is_reusable && ' • Reusable'}
                    </span>
                  </div>
                </div>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </BaseWidgetWrapper>
  );
};

const WorkflowMultiSelect: React.FC<WidgetProps & { workflows: any[]; isLoading: boolean }> = ({
  value = [],
  onChange,
  workflows,
  isLoading,
  ...props
}) => {
  const selectedValues = Array.isArray(value) ? value : [];
  const placeholder = props.placeholder || props.uiHints?.placeholder || 'Select workflows';

  const handleToggle = (workflowId: string) => {
    const newValues = selectedValues.includes(workflowId)
      ? selectedValues.filter(v => v !== workflowId)
      : [...selectedValues, workflowId];
    onChange(newValues);
  };

  const handleRemove = (workflowId: string) => {
    onChange(selectedValues.filter(v => v !== workflowId));
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="space-y-2">
        <Select
          value=""
          onValueChange={handleToggle}
          disabled={props.disabled || props.readonly || isLoading}
        >
          <SelectTrigger>
            {isLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading workflows...</span>
              </div>
            ) : (
              <SelectValue placeholder={placeholder} />
            )}
          </SelectTrigger>
          <SelectContent>
            {workflows.map((workflow: any) => {
              const workflowId = workflow.id || workflow.value;
              const workflowName = workflow.name || workflow.label || workflowId;
              const isSelected = selectedValues.includes(workflowId);

              return (
                <SelectItem
                  key={workflowId}
                  value={workflowId}
                  className={isSelected ? 'bg-blue-50' : ''}
                >
                  <div className="flex items-center gap-2">
                    {isSelected && <span className="text-blue-600">✓</span>}
                    <GitBranch className="w-4 h-4 text-gray-400" />
                    {workflowName}
                  </div>
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>

        {selectedValues.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedValues.map((workflowId) => {
              const workflow = workflows.find(w =>
                (w.id || w.value) === workflowId
              );
              const workflowName = workflow?.name || workflow?.label || workflowId;

              return (
                <Badge
                  key={workflowId}
                  variant="secondary"
                  className="flex items-center gap-1"
                >
                  <GitBranch className="w-3 h-3" />
                  {workflowName}
                  {!props.disabled && !props.readonly && (
                    <X
                      className="w-3 h-3 cursor-pointer hover:text-red-600"
                      onClick={() => handleRemove(workflowId)}
                    />
                  )}
                </Badge>
              );
            })}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
};