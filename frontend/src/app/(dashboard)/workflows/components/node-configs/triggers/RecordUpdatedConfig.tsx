'use client';

import React, { useMemo, useEffect, useState } from 'react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { InfoIcon, GitBranch } from 'lucide-react';

interface RecordUpdatedConfigProps {
  config: any;
  onChange: (config: any) => void;
  pipelines?: any[];
  pipelineFields?: Record<string, any[]>;
  errors?: Record<string, string>;
}

export function RecordUpdatedConfig({
  config,
  onChange,
  pipelines = [],
  pipelineFields = {},
  errors = {}
}: RecordUpdatedConfigProps) {
  console.log('[RecordUpdatedConfig] RENDER', {
    config,
    pipelines: pipelines?.length,
    pipelineFields: Object.keys(pipelineFields || {}),
    timestamp: new Date().toISOString()
  });

  const safeConfig = config || {};
  const [stageFieldOptions, setStageFieldOptions] = useState<string[]>([]);

  // Check if we should show stage tracking options
  const shouldShowStageTracking = useMemo(() => {
    const watchFields = safeConfig.watch_fields || [];
    // Only show if exactly one field is being watched
    return watchFields.length === 1;
  }, [safeConfig.watch_fields]);

  // Get the watched field info
  const watchedField = useMemo(() => {
    if (!shouldShowStageTracking) return null;

    const watchFields = safeConfig.watch_fields || [];
    const fieldName = watchFields[0];

    // Handle both formats:
    // 1. pipelineFields as an object keyed by pipeline ID
    // 2. pipelineFields as a direct array of fields

    // If pipelineFields is an array, search directly in it
    if (Array.isArray(pipelineFields)) {
      const field = pipelineFields.find((f: any) => f.name === fieldName || f.slug === fieldName);
      if (field) return field;
    }
    // If pipelineFields is an object, search in each pipeline's fields
    else if (pipelineFields && typeof pipelineFields === 'object') {
      const pipelineIds = safeConfig.pipeline_ids || [];
      for (const pipelineId of pipelineIds) {
        const fields = pipelineFields[pipelineId] || [];
        const field = fields.find((f: any) => f.name === fieldName || f.slug === fieldName);
        if (field) return field;
      }
    }

    return null;
  }, [shouldShowStageTracking, safeConfig.watch_fields, safeConfig.pipeline_ids, pipelineFields]);

  // Check if the watched field is a select/choice field
  const isSelectField = useMemo(() => {
    if (!watchedField) return false;
    return ['select', 'choice', 'multiselect', 'status', 'stage'].includes(
      watchedField.field_type?.toLowerCase() || ''
    );
  }, [watchedField]);

  // Get options from the select field
  useEffect(() => {
    if (isSelectField && watchedField) {

      let options: string[] = [];

      // Check various possible locations for options
      // 1. field_config.options (backend structure)
      if (watchedField.field_config?.options) {
        const configOptions = watchedField.field_config.options;
        options = Array.isArray(configOptions)
          ? configOptions.map((opt: any) =>
              typeof opt === 'string' ? opt : (opt.value || opt.label)
            )
          : [];
      }
      // 2. Direct options property
      else if (watchedField.options) {
        const directOptions = watchedField.options;
        options = Array.isArray(directOptions)
          ? directOptions.map((opt: any) =>
              typeof opt === 'string' ? opt : (opt.value || opt.label)
            )
          : [];
      }
      // 3. choices property (alternative naming)
      else if (watchedField.choices) {
        options = Array.isArray(watchedField.choices) ? watchedField.choices : [];
      }

      console.log('[RecordUpdatedConfig] Extracted options:', options);
      setStageFieldOptions(options);
    } else {
      setStageFieldOptions([]);
    }
  }, [isSelectField, watchedField]);

  // Auto-set stage_field when track_stage_changes is enabled
  useEffect(() => {
    console.log('[RecordUpdatedConfig] useEffect for stage_field auto-set', {
      track_stage_changes: safeConfig.track_stage_changes,
      shouldShowStageTracking,
      stage_field: safeConfig.stage_field,
      watch_fields: safeConfig.watch_fields,
      timestamp: new Date().toISOString()
    });

    if (safeConfig.track_stage_changes && shouldShowStageTracking && !safeConfig.stage_field) {
      const watchFields = safeConfig.watch_fields || [];
      if (watchFields.length === 1) {
        console.log('[RecordUpdatedConfig] Auto-setting stage_field to:', watchFields[0]);
        onChange({ ...safeConfig, stage_field: watchFields[0] });
      }
    }
  }, [safeConfig.track_stage_changes, shouldShowStageTracking, safeConfig.stage_field, safeConfig.watch_fields]);

  console.log('[RecordUpdatedConfig] Render conditions:', {
    shouldShowStageTracking,
    isSelectField,
    watchedField,
    watchFields: safeConfig.watch_fields,
    pipelineFields: Array.isArray(pipelineFields) ? 'array' : typeof pipelineFields
  });

  return (
    <div className="space-y-4">
      {/* Show helpful message when no field is watched yet */}
      {(!safeConfig.watch_fields || safeConfig.watch_fields.length === 0) && (
        <Alert>
          <InfoIcon className="h-4 w-4" />
          <AlertDescription>
            Select fields to watch above. When watching a single select/choice field, you can enable stage tracking.
          </AlertDescription>
        </Alert>
      )}

      {/* Show info when one field is watched but it's not a select field */}
      {shouldShowStageTracking && !isSelectField && watchedField && (
        <Alert>
          <InfoIcon className="h-4 w-4" />
          <AlertDescription>
            The field "{watchedField?.display_name || watchedField?.name || safeConfig.watch_fields?.[0]}" is not a select/choice field.
            Stage tracking is only available for select, choice, or status fields.
          </AlertDescription>
        </Alert>
      )}

      {/* Show stage tracking toggle only when exactly one field is watched */}
      {shouldShowStageTracking && isSelectField && (
        <>
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
              <Label>Track as Stage Change</Label>
            </div>
            <Switch
              checked={safeConfig.track_stage_changes || false}
              onCheckedChange={(checked) =>
                onChange({
                  ...safeConfig,
                  track_stage_changes: checked,
                  stage_field: checked ? (safeConfig.watch_fields?.[0] || '') : undefined
                })
              }
            />
          </div>

          {safeConfig.track_stage_changes && (
            <>
              {/* From Stages */}
              <div>
                <Label>From Stages (Optional)</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {stageFieldOptions.map((option) => {
                    const isSelected = (safeConfig.from_stages || []).includes(option);
                    return (
                      <Badge
                        key={option}
                        variant={isSelected ? "default" : "outline"}
                        className="cursor-pointer"
                        onClick={() => {
                          const fromStages = safeConfig.from_stages || [];
                          const newFromStages = isSelected
                            ? fromStages.filter((s: string) => s !== option)
                            : [...fromStages, option];
                          onChange({ ...safeConfig, from_stages: newFromStages });
                        }}
                      >
                        {option}
                      </Badge>
                    );
                  })}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Only trigger when moving from these stages. Leave empty for any stage.
                </p>
              </div>

              {/* To Stages */}
              <div>
                <Label>To Stages (Optional)</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {stageFieldOptions.map((option) => {
                    const isSelected = (safeConfig.to_stages || []).includes(option);
                    return (
                      <Badge
                        key={option}
                        variant={isSelected ? "default" : "outline"}
                        className="cursor-pointer"
                        onClick={() => {
                          const toStages = safeConfig.to_stages || [];
                          const newToStages = isSelected
                            ? toStages.filter((s: string) => s !== option)
                            : [...toStages, option];
                          onChange({ ...safeConfig, to_stages: newToStages });
                        }}
                      >
                        {option}
                      </Badge>
                    );
                  })}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Only trigger when moving to these stages. Leave empty for any stage.
                </p>
              </div>

              {/* Stage Direction */}
              <div>
                <Label>Stage Direction</Label>
                <Select
                  value={safeConfig.stage_direction || 'any'}
                  onValueChange={(value) => onChange({ ...safeConfig, stage_direction: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any direction</SelectItem>
                    <SelectItem value="forward">Forward only (progress)</SelectItem>
                    <SelectItem value="backward">Backward only (regression)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">
                  Filter based on the direction of stage movement
                </p>
              </div>

              {/* Track Stage Duration */}
              <div className="flex items-center justify-between">
                <Label>Track Stage Duration</Label>
                <Switch
                  checked={safeConfig.track_stage_duration || false}
                  onCheckedChange={(checked) =>
                    onChange({ ...safeConfig, track_stage_duration: checked })
                  }
                />
              </div>
              {safeConfig.track_stage_duration && (
                <p className="text-xs text-gray-500 -mt-2">
                  Include how long the record was in the previous stage
                </p>
              )}
            </>
          )}
        </>
      )}

      {/* Show info when multiple fields are watched */}
      {safeConfig.watch_fields?.length > 1 && (
        <Alert>
          <InfoIcon className="h-4 w-4" />
          <AlertDescription>
            Stage tracking is only available when watching a single field.
            Currently watching {safeConfig.watch_fields.length} fields.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}