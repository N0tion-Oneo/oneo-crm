'use client';

import React, { useMemo } from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { InfoIcon, GitBranch } from 'lucide-react';
import { BaseWidgetProps } from '../core/types';

interface StageTrackingToggleProps extends BaseWidgetProps {
  value: boolean;
  onChange: (value: boolean) => void;
  label?: string;
  helpText?: string;
  config?: any;
  pipelineFields?: any;
  onConfigUpdate?: (config: any) => void;
}

export function StageTrackingToggle({
  value = false,
  onChange,
  label,
  helpText,
  config,
  pipelineFields,
  onConfigUpdate
}: StageTrackingToggleProps) {
  const watchFields = config?.watch_fields || [];
  
  // Check if we should show the toggle
  const shouldShow = useMemo(() => {
    // Only show if exactly one field is being watched
    if (watchFields.length !== 1) return false;
    
    const fieldName = watchFields[0];
    if (!fieldName || !pipelineFields) return false;
    
    // Find the field
    let field = null;
    if (Array.isArray(pipelineFields)) {
      field = pipelineFields.find((f: any) => 
        f.name === fieldName || f.slug === fieldName
      );
    } else if (pipelineFields && typeof pipelineFields === 'object') {
      const pipelineIds = config?.pipeline_ids || [];
      for (const pipelineId of pipelineIds) {
        const fields = pipelineFields[pipelineId] || [];
        field = fields.find((f: any) => 
          f.name === fieldName || f.slug === fieldName
        );
        if (field) break;
      }
    }
    
    if (!field) return false;
    
    // Check if it's a select/choice field
    const fieldType = field.field_type?.toLowerCase() || '';
    return ['select', 'choice', 'multiselect', 'status', 'stage'].includes(fieldType);
  }, [watchFields, pipelineFields, config]);
  
  // Get the watched field info for display
  const watchedField = useMemo(() => {
    if (watchFields.length !== 1) return null;
    
    const fieldName = watchFields[0];
    if (!fieldName || !pipelineFields) return null;
    
    let field = null;
    if (Array.isArray(pipelineFields)) {
      field = pipelineFields.find((f: any) => 
        f.name === fieldName || f.slug === fieldName
      );
    } else if (pipelineFields && typeof pipelineFields === 'object') {
      const pipelineIds = config?.pipeline_ids || [];
      for (const pipelineId of pipelineIds) {
        const fields = pipelineFields[pipelineId] || [];
        field = fields.find((f: any) => 
          f.name === fieldName || f.slug === fieldName
        );
        if (field) break;
      }
    }
    
    return field;
  }, [watchFields, pipelineFields, config]);
  
  const handleChange = (checked: boolean) => {
    onChange(checked);
  };
  
  // Don't render if conditions aren't met
  if (!shouldShow) {
    // Show helpful message when no field is watched yet
    if (watchFields.length === 0) {
      return (
        <Alert>
          <InfoIcon className="h-4 w-4" />
          <AlertDescription>
            Select fields to watch above. When watching a single select/choice field, you can enable stage tracking.
          </AlertDescription>
        </Alert>
      );
    }
    
    // Show info when one field is watched but it's not a select field
    if (watchFields.length === 1 && watchedField) {
      return (
        <Alert>
          <InfoIcon className="h-4 w-4" />
          <AlertDescription>
            The field "{watchedField?.display_name || watchedField?.name || watchFields[0]}" is not a select/choice field.
            Stage tracking is only available for select, choice, or status fields.
          </AlertDescription>
        </Alert>
      );
    }
    
    // Show info when multiple fields are watched
    if (watchFields.length > 1) {
      return (
        <Alert>
          <InfoIcon className="h-4 w-4" />
          <AlertDescription>
            Stage tracking is only available when watching a single field.
            Currently watching {watchFields.length} fields.
          </AlertDescription>
        </Alert>
      );
    }
    
    return null;
  }
  
  return (
    <div className="space-y-2">
      <Alert>
        <InfoIcon className="h-4 w-4" />
        <AlertDescription>
          The field "{watchedField?.display_name || watchedField?.name}" is a select field.
          You can enable stage tracking to filter transitions between specific values.
        </AlertDescription>
      </Alert>
      
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="h-4 w-4" />
          <Label>{label || 'Track as Stage Change'}</Label>
        </div>
        <Switch
          checked={value}
          onCheckedChange={handleChange}
        />
      </div>
      
      {helpText && (
        <p className="text-xs text-muted-foreground">
          {helpText}
        </p>
      )}
    </div>
  );
}

// Widget metadata for registration
StageTrackingToggle.widgetType = 'stage_tracking_toggle';
StageTrackingToggle.displayName = 'Stage Tracking Toggle';
StageTrackingToggle.description = 'Toggle for enabling stage change tracking when watching select fields';