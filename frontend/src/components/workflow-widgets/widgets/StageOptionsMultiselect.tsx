'use client';

import React, { useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Info } from 'lucide-react';
import { BaseWidgetProps } from '../core/types';

interface StageOptionsMultiselectProps extends BaseWidgetProps {
  value: string[];
  onChange: (value: string[]) => void;
  label?: string;
  placeholder?: string;
  helpText?: string;
  required?: boolean;
  config?: any;
  pipelineFields?: any;
  uiHints?: {
    stage_field_key?: string;
    [key: string]: any;
  };
}

export function StageOptionsMultiselect({
  value = [],
  onChange,
  label,
  placeholder,
  helpText,
  required,
  config,
  pipelineFields,
  uiHints = {}
}: StageOptionsMultiselectProps) {
  // Get the stage field from watch_fields (it's always the first/only field when stage tracking is enabled)
  const stageFieldKey = uiHints.stage_field_key || 'watch_fields';
  const watchFields = config?.[stageFieldKey];
  const stageFieldName = Array.isArray(watchFields) ? watchFields[0] : watchFields;

  // Extract options from the selected stage field
  const stageOptions = useMemo(() => {
    if (!stageFieldName || !pipelineFields) {
      return [];
    }

    // Handle both formats:
    // 1. pipelineFields as an array of fields
    // 2. pipelineFields as an object keyed by pipeline ID
    let field = null;

    if (Array.isArray(pipelineFields)) {
      field = pipelineFields.find((f: any) => 
        f.name === stageFieldName || f.slug === stageFieldName
      );
    } else if (pipelineFields && typeof pipelineFields === 'object') {
      // Search in each pipeline's fields
      const pipelineIds = config?.pipeline_ids || [];
      for (const pipelineId of pipelineIds) {
        const fields = pipelineFields[pipelineId] || [];
        field = fields.find((f: any) => 
          f.name === stageFieldName || f.slug === stageFieldName
        );
        if (field) break;
      }
    }

    if (!field) return [];

    // Extract options from various possible locations
    let options: string[] = [];

    // 1. field_config.options (backend structure)
    if (field.field_config?.options) {
      const configOptions = field.field_config.options;
      options = Array.isArray(configOptions)
        ? configOptions.map((opt: any) =>
            typeof opt === 'string' ? opt : (opt.value || opt.label)
          )
        : [];
    }
    // 2. Direct options property
    else if (field.options) {
      const directOptions = field.options;
      options = Array.isArray(directOptions)
        ? directOptions.map((opt: any) =>
            typeof opt === 'string' ? opt : (opt.value || opt.label)
          )
        : [];
    }
    // 3. choices property (alternative naming)
    else if (field.choices) {
      options = Array.isArray(field.choices) ? field.choices : [];
    }

    return options;
  }, [stageFieldName, pipelineFields, config]);

  const handleToggle = (option: string) => {
    const newValue = value.includes(option)
      ? value.filter((v: string) => v !== option)
      : [...value, option];
    onChange(newValue);
  };

  // Don't render if no stage field is selected or no options available
  if (!stageFieldName || stageOptions.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {label && (
        <div className="flex items-center gap-1.5">
          <Label className="text-sm font-medium">
            {label}
            {required && <span className="text-destructive">*</span>}
          </Label>
          {helpText && (
            <Info className="h-3 w-3 text-muted-foreground" title={helpText} />
          )}
        </div>
      )}
      
      <div className="flex flex-wrap gap-2">
        {stageOptions.map((option) => {
          const isSelected = value.includes(option);
          return (
            <Badge
              key={option}
              variant={isSelected ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => handleToggle(option)}
            >
              {option}
            </Badge>
          );
        })}
      </div>
      
      {helpText && (
        <p className="text-xs text-muted-foreground">
          {helpText}
        </p>
      )}
      
      {placeholder && value.length === 0 && (
        <p className="text-xs text-muted-foreground italic">
          {placeholder}
        </p>
      )}
    </div>
  );
}

// Widget metadata for registration
StageOptionsMultiselect.widgetType = 'stage_options_multiselect';
StageOptionsMultiselect.displayName = 'Stage Options Multiselect';
StageOptionsMultiselect.description = 'Dynamic multiselect that shows options from selected stage field';