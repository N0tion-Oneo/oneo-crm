/**
 * Field builder widget for dynamically configuring field mappings
 */

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, X, GripVertical, ChevronDown, ChevronRight, Database } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';
import { cn } from '@/lib/utils';

interface FieldMapping {
  id: string;
  sourceField: string;
  targetField: string;
  transform?: string;
  defaultValue?: any;
  required?: boolean;
}

const TRANSFORM_OPTIONS = [
  { value: 'none', label: 'No transformation' },
  { value: 'uppercase', label: 'Convert to uppercase' },
  { value: 'lowercase', label: 'Convert to lowercase' },
  { value: 'trim', label: 'Trim whitespace' },
  { value: 'number', label: 'Convert to number' },
  { value: 'string', label: 'Convert to string' },
  { value: 'boolean', label: 'Convert to boolean' },
  { value: 'date', label: 'Parse as date' },
  { value: 'json', label: 'Parse as JSON' },
  { value: 'custom', label: 'Custom expression' },
];

export const FieldBuilderWidget: React.FC<WidgetProps> = (props) => {
  const { value = [], onChange, uiHints = {}, pipelineFields = [] } = props;
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const addFieldMapping = () => {
    const newMapping: FieldMapping = {
      id: `field-${Date.now()}`,
      sourceField: '',
      targetField: '',
      transform: 'none',
      required: false
    };
    onChange([...value, newMapping]);
    setExpandedItems(new Set([...expandedItems, newMapping.id]));
  };

  const updateFieldMapping = (index: number, updates: Partial<FieldMapping>) => {
    const newMappings = [...value];
    newMappings[index] = { ...newMappings[index], ...updates };
    onChange(newMappings);
  };

  const removeFieldMapping = (index: number) => {
    const newMappings = [...value];
    newMappings.splice(index, 1);
    onChange(newMappings);
  };

  const moveFieldMapping = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return;
    const newMappings = [...value];
    const [movedItem] = newMappings.splice(fromIndex, 1);
    newMappings.splice(toIndex, 0, movedItem);
    onChange(newMappings);
  };

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedItems(newExpanded);
  };

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== dropIndex) {
      moveFieldMapping(draggedIndex, dropIndex);
    }
    setDraggedIndex(null);
  };

  const getAvailableFields = () => {
    if (pipelineFields.length > 0) {
      return pipelineFields.map(field => ({
        value: field.slug || field.name || field.key,
        label: field.label || field.name
      }));
    }
    // Fallback to common field names
    return [
      { value: 'name', label: 'Name' },
      { value: 'email', label: 'Email' },
      { value: 'phone', label: 'Phone' },
      { value: 'status', label: 'Status' },
      { value: 'description', label: 'Description' },
      { value: 'custom', label: 'Custom Field...' },
    ];
  };

  const availableFields = getAvailableFields();

  return (
    <BaseWidgetWrapper {...props}>
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            {value.length} field mapping{value.length !== 1 ? 's' : ''} configured
          </div>
          <Button
            type="button"
            onClick={addFieldMapping}
            disabled={props.disabled || props.readonly}
            size="sm"
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Field
          </Button>
        </div>

        {/* Field mappings */}
        {value.length > 0 && (
          <div className="space-y-2">
            {value.map((mapping: FieldMapping, index: number) => {
              const isExpanded = expandedItems.has(mapping.id);

              return (
                <div
                  key={mapping.id}
                  className="border rounded-lg bg-white"
                  draggable={!props.disabled && !props.readonly}
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, index)}
                >
                  {/* Field header */}
                  <div className="flex items-center gap-2 p-3">
                    {!props.disabled && !props.readonly && (
                      <GripVertical className="w-4 h-4 text-gray-400 cursor-move" />
                    )}

                    <button
                      type="button"
                      onClick={() => toggleExpanded(mapping.id)}
                      className="p-0"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>

                    <Database className="w-4 h-4 text-gray-400" />

                    <div className="flex-1 flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {mapping.sourceField || 'Unmapped field'}
                      </span>
                      {mapping.sourceField && mapping.targetField && (
                        <>
                          <span className="text-gray-400">→</span>
                          <span className="text-sm">
                            {mapping.targetField}
                          </span>
                        </>
                      )}
                      {mapping.required && (
                        <span className="text-xs text-red-600 font-medium">Required</span>
                      )}
                    </div>

                    {!props.disabled && !props.readonly && (
                      <button
                        type="button"
                        onClick={() => removeFieldMapping(index)}
                        className="p-1 hover:bg-gray-100 rounded"
                      >
                        <X className="w-4 h-4 text-gray-500" />
                      </button>
                    )}
                  </div>

                  {/* Field details (collapsible) */}
                  {isExpanded && (
                    <div className="border-t px-3 pb-3 pt-2 space-y-3 bg-gray-50">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs font-medium text-gray-700">Source Field</label>
                          <Select
                            value={mapping.sourceField}
                            onValueChange={(val) => updateFieldMapping(index, { sourceField: val })}
                            disabled={props.disabled || props.readonly}
                          >
                            <SelectTrigger className="h-9">
                              <SelectValue placeholder="Select source field" />
                            </SelectTrigger>
                            <SelectContent>
                              {availableFields.map(field => (
                                <SelectItem key={field.value} value={field.value}>
                                  {field.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div>
                          <label className="text-xs font-medium text-gray-700">Target Field</label>
                          <Input
                            value={mapping.targetField}
                            onChange={(e) => updateFieldMapping(index, { targetField: e.target.value })}
                            placeholder="Enter target field name"
                            disabled={props.disabled || props.readonly}
                            className="h-9"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-xs font-medium text-gray-700">Transformation</label>
                        <Select
                          value={mapping.transform || 'none'}
                          onValueChange={(val) => updateFieldMapping(index, { transform: val })}
                          disabled={props.disabled || props.readonly}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {TRANSFORM_OPTIONS.map(option => (
                              <SelectItem key={option.value} value={option.value}>
                                {option.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      {mapping.transform === 'custom' && (
                        <div>
                          <label className="text-xs font-medium text-gray-700">Custom Expression</label>
                          <Input
                            value={mapping.defaultValue}
                            onChange={(e) => updateFieldMapping(index, { defaultValue: e.target.value })}
                            placeholder="e.g., {{value}}.toUpperCase()"
                            disabled={props.disabled || props.readonly}
                            className="h-9 font-mono text-xs"
                          />
                        </div>
                      )}

                      <div className="flex items-center gap-4">
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={mapping.required || false}
                            onChange={(e) => updateFieldMapping(index, { required: e.target.checked })}
                            disabled={props.disabled || props.readonly}
                            className="rounded"
                          />
                          Required field
                        </label>

                        {!mapping.required && (
                          <div className="flex items-center gap-2 flex-1">
                            <label className="text-xs text-gray-700">Default:</label>
                            <Input
                              value={mapping.defaultValue || ''}
                              onChange={(e) => updateFieldMapping(index, { defaultValue: e.target.value })}
                              placeholder="Default value if empty"
                              disabled={props.disabled || props.readonly}
                              className="h-7 text-xs"
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Empty state */}
        {value.length === 0 && (
          <div className="text-center py-8 text-gray-500 text-sm">
            No field mappings configured. Click "Add Field" to get started.
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
};