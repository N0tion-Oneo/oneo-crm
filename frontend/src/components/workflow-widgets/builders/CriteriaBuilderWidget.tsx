/**
 * Criteria builder widget for building complex filter criteria
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Plus, X, Filter, ChevronDown, ChevronRight } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';
import { cn } from '@/lib/utils';

interface CriteriaGroup {
  id: string;
  operator: 'AND' | 'OR';
  conditions: Condition[];
  groups?: CriteriaGroup[];
}

interface Condition {
  id: string;
  field: string;
  operator: string;
  value: any;
  type?: string;
}

const OPERATORS = {
  string: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not equals' },
    { value: 'contains', label: 'Contains' },
    { value: 'not_contains', label: 'Does not contain' },
    { value: 'starts_with', label: 'Starts with' },
    { value: 'ends_with', label: 'Ends with' },
    { value: 'is_empty', label: 'Is empty' },
    { value: 'is_not_empty', label: 'Is not empty' },
  ],
  number: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not equals' },
    { value: 'greater_than', label: 'Greater than' },
    { value: 'less_than', label: 'Less than' },
    { value: 'greater_than_or_equals', label: 'Greater than or equals' },
    { value: 'less_than_or_equals', label: 'Less than or equals' },
    { value: 'between', label: 'Between' },
  ],
  boolean: [
    { value: 'is', label: 'Is' },
    { value: 'is_not', label: 'Is not' },
  ],
  date: [
    { value: 'equals', label: 'Equals' },
    { value: 'before', label: 'Before' },
    { value: 'after', label: 'After' },
    { value: 'between', label: 'Between' },
    { value: 'in_last', label: 'In the last' },
    { value: 'in_next', label: 'In the next' },
  ],
};

export const CriteriaBuilderWidget: React.FC<WidgetProps> = (props) => {
  const { value = null, onChange, uiHints = {}, pipelineFields = [] } = props;
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['root']));

  const initialGroup: CriteriaGroup = value || {
    id: 'root',
    operator: 'AND',
    conditions: [],
    groups: []
  };

  const getFieldType = (fieldName: string): string => {
    const field = pipelineFields.find(f =>
      (f.slug || f.name || f.key) === fieldName
    );
    return field?.field_type || field?.type || 'string';
  };

  const getOperatorsForField = (fieldName: string) => {
    const fieldType = getFieldType(fieldName);
    const typeMap: Record<string, string> = {
      text: 'string',
      textarea: 'string',
      number: 'number',
      integer: 'number',
      decimal: 'number',
      boolean: 'boolean',
      checkbox: 'boolean',
      date: 'date',
      datetime: 'date',
    };
    const mappedType = typeMap[fieldType] || 'string';
    return OPERATORS[mappedType as keyof typeof OPERATORS] || OPERATORS.string;
  };

  const addCondition = (groupId: string) => {
    const newCondition: Condition = {
      id: `condition-${Date.now()}`,
      field: '',
      operator: 'equals',
      value: '',
    };

    const updateGroup = (group: CriteriaGroup): CriteriaGroup => {
      if (group.id === groupId) {
        return {
          ...group,
          conditions: [...group.conditions, newCondition]
        };
      }
      if (group.groups) {
        return {
          ...group,
          groups: group.groups.map(g => updateGroup(g))
        };
      }
      return group;
    };

    onChange(updateGroup(initialGroup));
  };

  const addGroup = (parentGroupId: string) => {
    const newGroup: CriteriaGroup = {
      id: `group-${Date.now()}`,
      operator: 'AND',
      conditions: [],
      groups: []
    };

    const updateGroup = (group: CriteriaGroup): CriteriaGroup => {
      if (group.id === parentGroupId) {
        return {
          ...group,
          groups: [...(group.groups || []), newGroup]
        };
      }
      if (group.groups) {
        return {
          ...group,
          groups: group.groups.map(g => updateGroup(g))
        };
      }
      return group;
    };

    const updated = updateGroup(initialGroup);
    onChange(updated);
    setExpandedGroups(new Set([...expandedGroups, newGroup.id]));
  };

  const updateCondition = (groupId: string, conditionId: string, updates: Partial<Condition>) => {
    const updateGroup = (group: CriteriaGroup): CriteriaGroup => {
      if (group.id === groupId) {
        return {
          ...group,
          conditions: group.conditions.map(c =>
            c.id === conditionId ? { ...c, ...updates } : c
          )
        };
      }
      if (group.groups) {
        return {
          ...group,
          groups: group.groups.map(g => updateGroup(g))
        };
      }
      return group;
    };

    onChange(updateGroup(initialGroup));
  };

  const removeCondition = (groupId: string, conditionId: string) => {
    const updateGroup = (group: CriteriaGroup): CriteriaGroup => {
      if (group.id === groupId) {
        return {
          ...group,
          conditions: group.conditions.filter(c => c.id !== conditionId)
        };
      }
      if (group.groups) {
        return {
          ...group,
          groups: group.groups.map(g => updateGroup(g))
        };
      }
      return group;
    };

    onChange(updateGroup(initialGroup));
  };

  const removeGroup = (parentGroupId: string, groupId: string) => {
    const updateGroup = (group: CriteriaGroup): CriteriaGroup => {
      if (group.id === parentGroupId) {
        return {
          ...group,
          groups: (group.groups || []).filter(g => g.id !== groupId)
        };
      }
      if (group.groups) {
        return {
          ...group,
          groups: group.groups.map(g => updateGroup(g))
        };
      }
      return group;
    };

    onChange(updateGroup(initialGroup));
  };

  const updateGroupOperator = (groupId: string, operator: 'AND' | 'OR') => {
    const updateGroup = (group: CriteriaGroup): CriteriaGroup => {
      if (group.id === groupId) {
        return { ...group, operator };
      }
      if (group.groups) {
        return {
          ...group,
          groups: group.groups.map(g => updateGroup(g))
        };
      }
      return group;
    };

    onChange(updateGroup(initialGroup));
  };

  const toggleGroupExpanded = (groupId: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupId)) {
      newExpanded.delete(groupId);
    } else {
      newExpanded.add(groupId);
    }
    setExpandedGroups(newExpanded);
  };

  const renderCondition = (
    condition: Condition,
    groupId: string,
    depth: number
  ) => {
    const operators = getOperatorsForField(condition.field);
    const needsValue = !['is_empty', 'is_not_empty'].includes(condition.operator);

    return (
      <div
        key={condition.id}
        className={cn(
          "flex items-center gap-2 p-2 bg-white rounded border",
          depth > 0 && "ml-4"
        )}
      >
        <Filter className="w-4 h-4 text-gray-400" />

        <Select
          value={condition.field}
          onValueChange={(val) => updateCondition(groupId, condition.id, { field: val })}
          disabled={props.disabled || props.readonly}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Select field" />
          </SelectTrigger>
          <SelectContent>
            {pipelineFields.map(field => {
              const fieldKey = field.slug || field.name || field.key;
              const fieldLabel = field.label || field.name || fieldKey;
              return (
                <SelectItem key={fieldKey} value={fieldKey}>
                  {fieldLabel}
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>

        <Select
          value={condition.operator}
          onValueChange={(val) => updateCondition(groupId, condition.id, { operator: val })}
          disabled={props.disabled || props.readonly}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {operators.map(op => (
              <SelectItem key={op.value} value={op.value}>
                {op.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {needsValue && (
          <Input
            value={condition.value || ''}
            onChange={(e) => updateCondition(groupId, condition.id, { value: e.target.value })}
            placeholder="Enter value"
            disabled={props.disabled || props.readonly}
            className="flex-1"
          />
        )}

        {!props.disabled && !props.readonly && (
          <button
            type="button"
            onClick={() => removeCondition(groupId, condition.id)}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        )}
      </div>
    );
  };

  const renderGroup = (group: CriteriaGroup, parentGroupId: string | null, depth: number = 0) => {
    const isExpanded = expandedGroups.has(group.id);
    const isRoot = group.id === 'root';

    return (
      <div
        key={group.id}
        className={cn(
          "border rounded-lg",
          depth > 0 && "ml-4 mt-2",
          isRoot ? "border-gray-200" : "border-blue-200"
        )}
      >
        <div className="p-3 bg-gray-50">
          <div className="flex items-center gap-2">
            {(group.conditions.length > 0 || (group.groups && group.groups.length > 0)) && (
              <button
                type="button"
                onClick={() => toggleGroupExpanded(group.id)}
              >
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>
            )}

            <Select
              value={group.operator}
              onValueChange={(val) => updateGroupOperator(group.id, val as 'AND' | 'OR')}
              disabled={props.disabled || props.readonly}
            >
              <SelectTrigger className="w-24 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="AND">AND</SelectItem>
                <SelectItem value="OR">OR</SelectItem>
              </SelectContent>
            </Select>

            <span className="text-sm text-gray-600">
              {group.conditions.length + (group.groups?.length || 0)} rule(s)
            </span>

            <div className="flex-1" />

            {!props.disabled && !props.readonly && (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => addCondition(group.id)}
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Condition
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => addGroup(group.id)}
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Group
                </Button>

                {!isRoot && parentGroupId && (
                  <button
                    type="button"
                    onClick={() => removeGroup(parentGroupId, group.id)}
                    className="p-1 hover:bg-gray-100 rounded"
                  >
                    <X className="w-4 h-4 text-gray-500" />
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {isExpanded && (
          <div className="p-3 space-y-2">
            {group.conditions.map(condition =>
              renderCondition(condition, group.id, depth)
            )}

            {group.groups?.map(subGroup =>
              renderGroup(subGroup, group.id, depth + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <BaseWidgetWrapper {...props}>
      {renderGroup(initialGroup, null)}
    </BaseWidgetWrapper>
  );
};