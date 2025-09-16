import React from 'react';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { ConditionBuilder } from './ConditionBuilder';

interface TriggerConfigProps {
  config: any;
  updateConfig: (key: string, value: any) => void;
  pipelines: any[];
  pipelineFields: any[];
  loadingFields: boolean;
}

export function RecordUpdatedTrigger({
  config,
  updateConfig,
  pipelines,
  pipelineFields,
  loadingFields
}: TriggerConfigProps) {
  return (
    <div className="space-y-4">
      <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-sm text-amber-800">
          📝 Trigger when records are updated in your pipelines
        </p>
      </div>

      <div>
        <Label>Which pipeline to monitor?</Label>
        <Select
          value={config.pipeline_id ? String(config.pipeline_id) : ''}
          onValueChange={(value) => {
            // Update pipeline_id which will be the main field
            updateConfig('pipeline_id', value);
            // Also set pipeline_ids for backend compatibility
            if (value) {
              updateConfig('pipeline_ids', [value]);
            }
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Choose a pipeline" />
          </SelectTrigger>
          <SelectContent>
            {pipelines.map(pipeline => (
              <SelectItem key={pipeline.id} value={String(pipeline.id)}>
                {pipeline.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {config.pipeline_id && (
        <>
          <div>
            <Label>Monitor which fields?</Label>
            <RadioGroup
              value={config.watch_all_fields !== false ? 'all' : 'specific'}
              onValueChange={(value) => {
                const watchAll = value === 'all';
                updateConfig('watch_all_fields', watchAll);
                if (watchAll) {
                  updateConfig('specific_fields', []);
                }
              }}
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="all" />
                <Label className="font-normal">All fields</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="specific" />
                <Label className="font-normal">Specific fields only</Label>
              </div>
            </RadioGroup>
          </div>

          {!config.watch_all_fields && (
            <div>
              <Label>Which fields to monitor? (select multiple)</Label>
              <div className="border rounded-lg p-3 max-h-48 overflow-y-auto space-y-2">
                {loadingFields ? (
                  <p className="text-sm text-muted-foreground">Loading fields...</p>
                ) : pipelineFields.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No fields available</p>
                ) : (
                  pipelineFields.map((field: any) => (
                    <div key={field.slug} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`field-${field.slug}`}
                        checked={(config.specific_fields || []).includes(field.slug)}
                        onChange={(e) => {
                          const fields = config.specific_fields || [];
                          if (e.target.checked) {
                            updateConfig('specific_fields', [...fields, field.slug]);
                          } else {
                            updateConfig('specific_fields', fields.filter((f: string) => f !== field.slug));
                          }
                        }}
                        className="rounded border-gray-300"
                      />
                      <label htmlFor={`field-${field.slug}`} className="text-sm cursor-pointer">
                        {field.display_name || field.name}
                        <span className="text-xs text-muted-foreground ml-2">({field.field_type})</span>
                      </label>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          <div>
            <Label>Exclude any fields from monitoring?</Label>
            <Switch
              checked={config.has_ignore_fields || false}
              onCheckedChange={(checked) => {
                updateConfig('has_ignore_fields', checked);
                if (!checked) {
                  updateConfig('ignore_fields', []);
                }
              }}
            />
          </div>

          {config.has_ignore_fields && (
            <div>
              <Label>Fields to ignore (never trigger on these)</Label>
              <div className="border rounded-lg p-3 max-h-48 overflow-y-auto space-y-2">
                {pipelineFields.map((field: any) => (
                  <div key={field.slug} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id={`ignore-${field.slug}`}
                      checked={(config.ignore_fields || []).includes(field.slug)}
                      onChange={(e) => {
                        const fields = config.ignore_fields || [];
                        if (e.target.checked) {
                          updateConfig('ignore_fields', [...fields, field.slug]);
                        } else {
                          updateConfig('ignore_fields', fields.filter((f: string) => f !== field.slug));
                        }
                      }}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor={`ignore-${field.slug}`} className="text-sm cursor-pointer">
                      {field.display_name || field.name}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <div>
              <Label className="font-normal">Only trigger on actual changes</Label>
              <p className="text-xs text-muted-foreground">
                Ignore updates where field values don't actually change
              </p>
            </div>
            <Switch
              checked={config.require_actual_changes !== false}
              onCheckedChange={(checked) => updateConfig('require_actual_changes', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label className="font-normal">Add field conditions</Label>
              <p className="text-xs text-muted-foreground">
                Only trigger when records match specific conditions
              </p>
            </div>
            <Switch
              checked={config.has_field_filters || false}
              onCheckedChange={(checked) => {
                updateConfig('has_field_filters', checked);
                if (!checked) {
                  updateConfig('field_filters', {});
                }
              }}
            />
          </div>

          {config.has_field_filters && (
            <div>
              <Label>Only trigger when these conditions are met</Label>
              <ConditionBuilder
                fields={pipelineFields}
                conditions={config.field_filter_conditions || []}
                onChange={(conditions) => {
                  updateConfig('field_filter_conditions', conditions);
                  // Convert to backend field_filters format
                  const filters: any = {};
                  conditions.forEach((condition: any) => {
                    if (condition.field && condition.operator && condition.value) {
                      filters[condition.field] = {
                        operator: condition.operator,
                        value: condition.value,
                        value_to: condition.value_to
                      };
                    }
                  });
                  updateConfig('field_filters', filters);
                }}
                logicalOperator={config.filter_logic || 'AND'}
                onLogicalOperatorChange={(op) => updateConfig('filter_logic', op)}
              />
            </div>
          )}

          {config.watch_all_fields === false && config.specific_fields?.length === 1 && (
            <div>
              <Label>Minimum change threshold (optional)</Label>
              <Input
                type="number"
                min="0"
                max="1"
                step="0.01"
                placeholder="e.g., 0.1 for 10% change"
                value={config.minimum_change_threshold || ''}
                onChange={(e) => updateConfig('minimum_change_threshold', parseFloat(e.target.value))}
              />
              <p className="text-xs text-muted-foreground mt-1">
                For numeric fields: Only trigger if value changes by this percentage
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function FieldChangedTrigger({
  config,
  updateConfig,
  pipelines,
  pipelineFields,
  loadingFields
}: TriggerConfigProps) {
  const selectedField = config.watched_fields?.[0] ?
    pipelineFields.find((f: any) => f.slug === config.watched_fields[0]) : null;

  const handleFieldSelect = (fieldSlug: string) => {
    updateConfig('watched_fields', fieldSlug ? [fieldSlug] : []);
    // Reset value filters when field changes
    updateConfig('value_filters', {});
    updateConfig('change_types', ['any']);
  };

  return (
    <div className="space-y-4">
      <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
        <p className="text-sm text-purple-800">
          🔄 Trigger when specific field values change
        </p>
      </div>

      <div>
        <Label>Which pipeline to monitor?</Label>
        <Select
          value={config.pipeline_id ? String(config.pipeline_id) : ''}
          onValueChange={(value) => {
            updateConfig('pipeline_id', value);
            // Also set pipeline_ids for backend compatibility
            if (value) {
              updateConfig('pipeline_ids', [value]);
            }
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Choose a pipeline" />
          </SelectTrigger>
          <SelectContent>
            {pipelines.map(pipeline => (
              <SelectItem key={pipeline.id} value={String(pipeline.id)}>
                {pipeline.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {config.pipeline_id && (
        <>
          <div>
            <Label>Which field to watch?</Label>
            <Select
              value={config.watched_fields?.[0] || ''}
              onValueChange={handleFieldSelect}
              disabled={loadingFields}
            >
              <SelectTrigger>
                <SelectValue placeholder={loadingFields ? "Loading fields..." : "Choose a field"} />
              </SelectTrigger>
              <SelectContent>
                {pipelineFields.map((field: any) => (
                  <SelectItem key={field.slug} value={field.slug}>
                    {field.display_name || field.name}
                    <span className="text-xs text-muted-foreground ml-2">
                      ({field.field_type})
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedField && (
            <>
              <div>
                <Label>Trigger on what type of change?</Label>
                <RadioGroup
                  value={config.change_types?.[0] || 'any'}
                  onValueChange={(value) => {
                    updateConfig('change_types', [value]);
                    // Clear value filters if switching to a mode that doesn't need them
                    if (['any', 'increases', 'decreases'].includes(value)) {
                      updateConfig('value_filters', {});
                    }
                  }}
                >
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="any" />
                      <Label className="font-normal">Any change</Label>
                    </div>

                    {selectedField.field_type === 'number' && (
                      <>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="increases" />
                          <Label className="font-normal">Value increases</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="decreases" />
                          <Label className="font-normal">Value decreases</Label>
                        </div>
                      </>
                    )}

                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="specific_change" />
                      <Label className="font-normal">Changes to specific value</Label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="from_to" />
                      <Label className="font-normal">Changes from one value to another</Label>
                    </div>
                  </div>
                </RadioGroup>
              </div>

              {config.change_types?.[0] === 'specific_change' && (
                <div>
                  <Label>Trigger when field changes to:</Label>
                  {renderFieldValueInput(selectedField, config.to_value || '', (value) => {
                    const filters = { ...config.value_filters };
                    filters[selectedField.slug] = { to: value };
                    updateConfig('value_filters', filters);
                    updateConfig('to_value', value); // For UI
                  })}
                </div>
              )}

              {config.change_types?.[0] === 'from_to' && (
                <>
                  <div>
                    <Label>From value:</Label>
                    {renderFieldValueInput(selectedField, config.from_value || '', (value) => {
                      const filters = { ...config.value_filters };
                      if (!filters[selectedField.slug]) filters[selectedField.slug] = {};
                      filters[selectedField.slug].from = value;
                      updateConfig('value_filters', filters);
                      updateConfig('from_value', value); // For UI
                    })}
                  </div>
                  <div>
                    <Label>To value:</Label>
                    {renderFieldValueInput(selectedField, config.to_value || '', (value) => {
                      const filters = { ...config.value_filters };
                      if (!filters[selectedField.slug]) filters[selectedField.slug] = {};
                      filters[selectedField.slug].to = value;
                      updateConfig('value_filters', filters);
                      updateConfig('to_value', value); // For UI
                    })}
                  </div>
                </>
              )}

              {selectedField.field_type === 'number' && ['increases', 'decreases'].includes(config.change_types?.[0]) && (
                <div>
                  <Label>Change threshold (optional)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Minimum change amount"
                    value={config.change_threshold || ''}
                    onChange={(e) => updateConfig('change_threshold', parseFloat(e.target.value))}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Only trigger if value changes by at least this amount
                  </p>
                </div>
              )}

              <div className="flex items-center justify-between">
                <div>
                  <Label className="font-normal">Ignore null/empty changes</Label>
                  <p className="text-xs text-muted-foreground">
                    Don't trigger when field becomes empty or null
                  </p>
                </div>
                <Switch
                  checked={config.ignore_null_changes !== false}
                  onCheckedChange={(checked) => updateConfig('ignore_null_changes', checked)}
                />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

// Helper function to render appropriate input for field type
function renderFieldValueInput(field: any, value: any, onChange: (value: any) => void) {
  const options = field.field_config?.options || [];

  switch (field.field_type) {
    case 'select':
    case 'multiselect':
      return (
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger>
            <SelectValue placeholder="Choose value" />
          </SelectTrigger>
          <SelectContent>
            {options.map((option: any) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );

    case 'boolean':
      return (
        <RadioGroup value={value?.toString() || ''} onValueChange={onChange}>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="true" />
            <Label className="font-normal">Checked</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="false" />
            <Label className="font-normal">Not checked</Label>
          </div>
        </RadioGroup>
      );

    case 'number':
      return (
        <Input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter value"
        />
      );

    case 'date':
      return (
        <Input
          type={field.field_config?.include_time ? 'datetime-local' : 'date'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      );

    default:
      return (
        <Input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={`Enter ${field.display_name || field.name}`}
        />
      );
  }
}