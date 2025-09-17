/**
 * Text list management widget for managing lists of strings
 */

import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, X, GripVertical, Upload, Download } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';

export const TextListWidget: React.FC<WidgetProps> = (props) => {
  const { value = [], onChange, uiHints = {} } = props;
  const [inputValue, setInputValue] = useState('');
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const maxItems = uiHints.max_items || 100;
  const minItems = uiHints.min_items || 0;
  const allowDuplicates = uiHints.allow_duplicates !== false;
  const sortable = uiHints.sortable !== false;
  const itemLabel = uiHints.item_label || 'item';

  const addItem = () => {
    const item = inputValue.trim();

    if (!item) return;

    if (!allowDuplicates && value.includes(item)) {
      return;
    }

    if (value.length >= maxItems) {
      return;
    }

    onChange([...value, item]);
    setInputValue('');
  };

  const removeItem = (index: number) => {
    if (value.length <= minItems) return;
    const newList = [...value];
    newList.splice(index, 1);
    onChange(newList);
  };

  const moveItem = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return;
    const newList = [...value];
    const [movedItem] = newList.splice(fromIndex, 1);
    newList.splice(toIndex, 0, movedItem);
    onChange(newList);
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
      moveItem(draggedIndex, dropIndex);
    }
    setDraggedIndex(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addItem();
    }
  };

  const importFromText = (text: string) => {
    const items = text
      .split(/[\n,;]+/)
      .map(item => item.trim())
      .filter(item => item.length > 0);

    const uniqueItems = allowDuplicates
      ? items
      : [...new Set([...value, ...items])];

    onChange(uniqueItems.slice(0, maxItems));
  };

  const exportAsText = () => {
    const text = value.join('\n');
    navigator.clipboard.writeText(text);
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pastedText = e.clipboardData.getData('text');
    if (pastedText.includes('\n') || pastedText.includes(',')) {
      e.preventDefault();
      importFromText(pastedText);
    }
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="space-y-3">
        {/* Input area */}
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={props.placeholder || `Add ${itemLabel}...`}
            disabled={props.disabled || props.readonly || value.length >= maxItems}
          />
          <Button
            type="button"
            onClick={addItem}
            disabled={props.disabled || props.readonly || !inputValue.trim() || value.length >= maxItems}
            size="sm"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>

        {/* List info and actions */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">
            {value.length} {itemLabel}{value.length !== 1 ? 's' : ''}
            {minItems > 0 && ` (min ${minItems})`}
            {maxItems < 100 && ` (max ${maxItems})`}
          </span>
          {value.length > 0 && !props.disabled && !props.readonly && (
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={exportAsText}
                title="Copy to clipboard"
              >
                <Download className="w-3 h-3" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => onChange([])}
                className="text-red-600 hover:text-red-700"
                disabled={value.length <= minItems}
              >
                Clear
              </Button>
            </div>
          )}
        </div>

        {/* Item list */}
        {value.length > 0 && (
          <div className="border rounded-lg bg-gray-50 p-2 max-h-64 overflow-y-auto">
            <div className="space-y-1">
              {value.map((item: string, index: number) => (
                <div
                  key={`${item}-${index}`}
                  className="flex items-center gap-2 p-2 bg-white rounded border hover:border-gray-300 transition-colors"
                  draggable={sortable && !props.disabled && !props.readonly}
                  onDragStart={(e) => sortable && handleDragStart(e, index)}
                  onDragOver={handleDragOver}
                  onDrop={(e) => sortable && handleDrop(e, index)}
                >
                  {sortable && !props.disabled && !props.readonly && (
                    <GripVertical className="w-4 h-4 text-gray-400 cursor-move" />
                  )}

                  <span className="flex-1 text-sm">
                    {index + 1}. {item}
                  </span>

                  {!props.disabled && !props.readonly && (
                    <button
                      type="button"
                      onClick={() => removeItem(index)}
                      className="p-1 hover:bg-gray-100 rounded"
                      disabled={value.length <= minItems}
                    >
                      <X className="w-3 h-3 text-gray-500" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Import hint */}
        {value.length === 0 && (
          <p className="text-xs text-gray-500">
            Tip: Paste multiple {itemLabel}s separated by commas or new lines to add them all at once
          </p>
        )}
      </div>
    </BaseWidgetWrapper>
  );
};