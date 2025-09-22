/**
 * Pipeline selection widget with support for single and multiple selection
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
import { X, Loader2 } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';
import { useEntityData } from './useEntityData';

export const PipelineSelector: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {} } = props;
  const isMultiple = uiHints.widget === 'pipeline_multiselect' || uiHints.multiple;

  // Use pipelines from props if available, otherwise fetch
  const shouldFetch = !props.pipelines || props.pipelines.length === 0;
  const { data: fetchedPipelines, isLoading } = useEntityData('pipelines', {
    enabled: shouldFetch
  });

  const pipelines = props.pipelines || fetchedPipelines || [];
  const placeholder = props.placeholder || uiHints.placeholder || 'Select pipeline(s)';

  if (isMultiple) {
    return <PipelineMultiSelect {...props} pipelines={pipelines} isLoading={isLoading} />;
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
              <span>Loading pipelines...</span>
            </div>
          ) : (
            <SelectValue placeholder={placeholder} />
          )}
        </SelectTrigger>
        <SelectContent>
          {pipelines.map((pipeline: any) => {
            const pipelineId = pipeline.id || pipeline.value;
            const pipelineName = pipeline.name || pipeline.label || pipelineId;
            const pipelineSlug = pipeline.slug;

            return (
              <SelectItem key={pipelineId} value={pipelineId}>
                <div className="flex flex-col">
                  <span>{pipelineName}</span>
                  {pipelineSlug && (
                    <span className="text-xs text-gray-500">{pipelineSlug}</span>
                  )}
                </div>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </BaseWidgetWrapper>
  );
};

const PipelineMultiSelect: React.FC<WidgetProps & { pipelines: any[]; isLoading: boolean }> = ({
  value = [],
  onChange,
  pipelines,
  isLoading,
  ...props
}) => {
  const selectedValues = Array.isArray(value) ? value : [];
  const placeholder = props.placeholder || props.uiHints?.placeholder || 'Select pipelines';

  const handleToggle = (pipelineId: string) => {
    const newValues = selectedValues.includes(pipelineId)
      ? selectedValues.filter(v => v !== pipelineId)
      : [...selectedValues, pipelineId];
    onChange(newValues);
  };

  const handleRemove = (pipelineId: string) => {
    onChange(selectedValues.filter(v => v !== pipelineId));
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
                <span>Loading pipelines...</span>
              </div>
            ) : (
              <SelectValue placeholder={placeholder} />
            )}
          </SelectTrigger>
          <SelectContent>
            {pipelines.map((pipeline: any) => {
              const pipelineId = pipeline.id || pipeline.value;
              const pipelineName = pipeline.name || pipeline.label || pipelineId;
              const isSelected = selectedValues.includes(pipelineId);

              return (
                <SelectItem
                  key={pipelineId}
                  value={pipelineId}
                  className={isSelected ? 'bg-blue-50' : ''}
                >
                  <div className="flex items-center gap-2">
                    {isSelected && <span className="text-blue-600">✓</span>}
                    {pipelineName}
                  </div>
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>

        {selectedValues.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedValues.map((pipelineId) => {
              const pipeline = pipelines.find(p =>
                (p.id || p.value) === pipelineId
              );
              const pipelineName = pipeline?.name || pipeline?.label || pipelineId;

              return (
                <Badge
                  key={pipelineId}
                  variant="secondary"
                  className="flex items-center gap-1"
                >
                  {pipelineName}
                  {!props.disabled && !props.readonly && (
                    <X
                      className="w-3 h-3 cursor-pointer hover:text-red-600"
                      onClick={() => handleRemove(pipelineId)}
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