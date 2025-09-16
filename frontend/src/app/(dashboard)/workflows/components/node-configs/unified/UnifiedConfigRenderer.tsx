'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  ChevronDown, ChevronRight, Variable,
  AlertCircle, Info, Code, Type
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { UnifiedNodeConfig, ConfigSection, ConfigField, NodeConfigComponentProps } from './types';
import { ExpressionEditor } from '../../configuration/ExpressionEditor';

interface UnifiedConfigRendererProps extends NodeConfigComponentProps {
  nodeConfig: UnifiedNodeConfig;
}

export function UnifiedConfigRenderer({
  nodeConfig,
  config,
  onChange,
  availableVariables,
  pipelines,
  workflows,
  users,
  userTypes,
  unipileAccounts,
  pipelineFields,
  errors: externalErrors = {}
}: UnifiedConfigRendererProps) {
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
    new Set(nodeConfig.sections?.filter(s => s.collapsed || s.advanced).map(s => s.id) || [])
  );
  const [expressionMode, setExpressionMode] = useState<Record<string, boolean>>({});
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Use the config directly from props instead of local state to avoid loops
  const currentConfig = config || nodeConfig.defaults || {};

  // Merge external and validation errors
  const errors = { ...validationErrors, ...externalErrors };

  // Run validation when config changes
  useEffect(() => {
    if (nodeConfig.validate) {
      const newErrors = nodeConfig.validate(currentConfig);
      setValidationErrors(newErrors || {});
    }
  }, [currentConfig, nodeConfig]);

  // Auto-populate pipeline_slug when pipeline_id exists but slug doesn't
  useEffect(() => {
    if (currentConfig.pipeline_id && !currentConfig.pipeline_slug && pipelines && pipelines.length > 0) {
      console.log('Auto-populate effect triggered:', {
        pipeline_id: currentConfig.pipeline_id,
        pipeline_slug: currentConfig.pipeline_slug,
        pipelines: pipelines.map(p => ({ id: p.id, name: p.name, slug: p.slug }))
      });
      const pipeline = pipelines.find((p: any) => p.id === currentConfig.pipeline_id);
      if (pipeline) {
        const slug = pipeline.slug || pipeline.name?.toLowerCase().replace(/\s+/g, '-');
        console.log('Auto-populating slug:', { pipeline, slug });
        if (slug) {
          onChange({ ...currentConfig, pipeline_slug: slug });
        }
      }
    }
  }, [currentConfig.pipeline_id, currentConfig.pipeline_slug, pipelines, onChange]);

  // If a custom component is provided, use it
  if (nodeConfig.customComponent) {
    const CustomComponent = nodeConfig.customComponent;
    return (
      <CustomComponent
        config={currentConfig}
        onChange={onChange}
        availableVariables={availableVariables}
        pipelines={pipelines}
        workflows={workflows}
        users={users}
        errors={errors}
      />
    );
  }

  const updateConfig = useCallback((key: string, value: any) => {
    const newConfig = { ...currentConfig, [key]: value };
    onChange(newConfig);
  }, [currentConfig, onChange]);

  const toggleSection = (sectionId: string) => {
    setCollapsedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const toggleExpressionMode = (fieldKey: string) => {
    setExpressionMode(prev => ({
      ...prev,
      [fieldKey]: !prev[fieldKey]
    }));
  };

  // Get options for a field - either from static options or dynamic data source
  const getFieldOptions = (field: ConfigField) => {
    // Special case: certain field keys should automatically use pipeline fields
    // when a pipeline is selected and no explicit optionsSource is set
    const pipelineFieldKeys = [
      'selected_fields', 'tracked_fields', 'field', 'fields',
      'ignore_fields', 'included_fields', 'excluded_fields',
      'group_by_field', 'sort_field', 'date_field'
    ];

    if (!field.optionsSource && pipelineFieldKeys.includes(field.key) && currentConfig.pipeline_id && pipelineFields) {
      // Auto-populate with pipeline fields
      return pipelineFields.map(f => ({
        value: f.slug || f.name || f.key || f.id,
        label: f.label || f.name || f.key
      }));
    }

    // If there's a dynamic source, use it
    if (field.optionsSource) {
      let sourceData: any[] = [];

      switch (field.optionsSource) {
        case 'pipelines':
          sourceData = pipelines || [];
          break;
        case 'users':
          sourceData = users || [];
          break;
        case 'userTypes':
          sourceData = userTypes || [];
          break;
        case 'unipileAccounts':
          sourceData = unipileAccounts || [];
          break;
        case 'workflows':
          sourceData = workflows || [];
          break;
        case 'pipelineFields':
          sourceData = pipelineFields || [];
          break;
      }

      // Apply filter if provided
      if (field.optionsFilter) {
        sourceData = sourceData.filter(field.optionsFilter);
      }

      // Map to options format
      if (field.optionsMap) {
        return sourceData.map(field.optionsMap);
      }

      // Default mapping
      return sourceData.map(item => ({
        value: item.id || item.value,
        label: item.name || item.label || item.email || item.title || String(item.id)
      }));
    }

    // Use static options
    return field.options || [];
  };

  const renderField = (field: ConfigField, section: ConfigSection) => {
    // Check conditional visibility
    if (field.showWhen && !field.showWhen(currentConfig)) {
      return null;
    }

    const fieldKey = field.key;
    const value = currentConfig[fieldKey] ?? field.defaultValue;
    const error = errors[fieldKey];
    const isExpression = expressionMode[fieldKey] || field.type === 'expression';

    return (
      <div key={fieldKey} className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium flex items-center gap-1.5">
            {field.label}
            {field.required && <span className="text-destructive">*</span>}
            {field.helpText && (
              <Info className="h-3 w-3 text-muted-foreground" title={field.helpText} />
            )}
          </Label>

          {field.allowExpressions && field.type !== 'expression' && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => toggleExpressionMode(fieldKey)}
              className="h-6 px-2"
            >
              {isExpression ? (
                <Type className="h-3 w-3" />
              ) : (
                <Variable className="h-3 w-3" />
              )}
            </Button>
          )}
        </div>

        {/* Render field based on type or custom render */}
        {field.customRender ? (
          field.customRender({
            field,
            value,
            onChange: (v) => updateConfig(fieldKey, v),
            error,
            config: currentConfig,
            availableVariables,
            pipelines,
            pipelineFields,
            users,
            userTypes,
            unipileAccounts,
            workflows
          })
        ) : (
          renderFieldInput(field, value, isExpression, (v) => updateConfig(fieldKey, v), fieldKey)
        )}

        {/* Error message */}
        {error && (
          <p className="text-xs text-destructive flex items-center gap-1">
            <AlertCircle className="h-3 w-3" />
            {error}
          </p>
        )}

        {/* Help text */}
        {!error && field.helpText && field.type !== 'boolean' && (
          <p className="text-xs text-muted-foreground">{field.helpText}</p>
        )}
      </div>
    );
  };

  const renderFieldInput = (
    field: ConfigField,
    value: any,
    isExpression: boolean,
    onFieldChange: (value: any) => void,
    fieldKey?: string
  ) => {
    // Expression mode
    if (isExpression && field.allowExpressions) {
      return (
        <ExpressionEditor
          value={value || ''}
          onChange={onFieldChange}
          placeholder={field.expressionPlaceholder || field.placeholder}
          availableVariables={availableVariables || []}
        />
      );
    }

    // Regular field types
    switch (field.type) {
      case 'text':
        return (
          <Input
            value={value || ''}
            onChange={(e) => onFieldChange(e.target.value)}
            placeholder={field.placeholder}
            disabled={field.disabled}
            readOnly={field.readonly}
          />
        );

      case 'textarea':
        return (
          <Textarea
            value={value || ''}
            onChange={(e) => onFieldChange(e.target.value)}
            placeholder={field.placeholder}
            disabled={field.disabled}
            readOnly={field.readonly}
            rows={field.rows || 3}
          />
        );

      case 'number':
        return (
          <Input
            type="number"
            value={value || ''}
            onChange={(e) => onFieldChange(e.target.valueAsNumber)}
            placeholder={field.placeholder}
            disabled={field.disabled}
            readOnly={field.readonly}
            min={field.min}
            max={field.max}
            step={field.step}
          />
        );

      case 'select':
        // Get options from dynamic source or use static options
        const selectOptions = getFieldOptions(field);

        // Handle custom onChange if provided
        const handleSelectChange = (newValue: string) => {
          if (field.onChange) {
            // Call custom onChange with value, config, and context
            const newConfig = field.onChange(newValue, currentConfig, {
              pipelines,
              pipelineFields,
              users,
              userTypes,
              unipileAccounts,
              workflows
            });
            // If onChange returns a new config object, use it
            if (newConfig && typeof newConfig === 'object') {
              // Use the component-level onChange to update the entire config
              onChange(newConfig);
              return;
            }
          }
          // Otherwise use default field change handler
          onFieldChange(newValue);
        };

        return (
          <Select value={value} onValueChange={handleSelectChange} disabled={field.disabled}>
            <SelectTrigger>
              <SelectValue placeholder={field.placeholder || 'Select...'} />
            </SelectTrigger>
            <SelectContent>
              {selectOptions.map(option => (
                <SelectItem key={option.value.toString()} value={option.value.toString()}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case 'boolean':
        return (
          <div className="flex items-center gap-2">
            <Switch
              checked={value || false}
              onCheckedChange={onChange}
              disabled={field.disabled}
            />
            {field.helpText && (
              <span className="text-sm text-muted-foreground">{field.helpText}</span>
            )}
          </div>
        );

      case 'multiselect':
      case 'array':
        // Get options from dynamic source or use static options
        const multiselectOptions = getFieldOptions(field);

        return (
          <div className="space-y-2">
            <div className="border rounded-lg p-2 max-h-48 overflow-y-auto">
              {multiselectOptions.length > 0 ? (
                <div className="space-y-1">
                  {multiselectOptions.map(option => (
                    <label
                      key={option.value.toString()}
                      className="flex items-center gap-2 p-1 hover:bg-muted/50 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={(value || []).includes(option.value)}
                        onChange={(e) => {
                          const currentValues = value || [];
                          if (e.target.checked) {
                            onChange([...currentValues, option.value]);
                          } else {
                            onChange(currentValues.filter((v: any) => v !== option.value));
                          }
                        }}
                        disabled={field.disabled}
                        className="rounded border-gray-300"
                      />
                      <span className="text-sm">{option.label}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-2">
                  {field.key === 'tracked_fields' || field.key === 'ignore_fields' || field.key === 'included_fields' || field.key === 'excluded_fields'
                    ? 'Select a pipeline first'
                    : 'No options available'}
                </p>
              )}
            </div>
            {(value || []).length > 0 && (
              <div className="text-xs text-muted-foreground">
                {(value || []).length} item(s) selected
              </div>
            )}
          </div>
        );

      case 'json':
      case 'code':
        return (
          <div className="border rounded-lg">
            <Textarea
              value={typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
              onChange={(e) => {
                if (field.type === 'json') {
                  try {
                    onChange(JSON.parse(e.target.value));
                  } catch {
                    onChange(e.target.value); // Keep as string if invalid JSON
                  }
                } else {
                  onChange(e.target.value);
                }
              }}
              placeholder={field.placeholder}
              disabled={field.disabled}
              readOnly={field.readonly}
              rows={field.rows || 10}
              className="font-mono text-xs"
            />
          </div>
        );

      case 'pipeline':
        // Pipeline selector - needs pipelines prop
        return (
          <Select value={value} onValueChange={onChange} disabled={field.disabled}>
            <SelectTrigger>
              <SelectValue placeholder={field.placeholder || 'Select pipeline...'} />
            </SelectTrigger>
            <SelectContent>
              {pipelines && pipelines.length > 0 ? (
                pipelines.map(pipeline => (
                  <SelectItem key={pipeline.id} value={pipeline.id}>
                    {pipeline.name}
                  </SelectItem>
                ))
              ) : (
                <div className="px-2 py-1.5 text-sm text-muted-foreground">
                  No pipelines available
                </div>
              )}
            </SelectContent>
          </Select>
        );

      case 'field':
      case 'field-select':
        // Field selector - uses pipelineFields when available, otherwise falls back to field.options
        let fieldOptions = pipelineFields?.map(f => ({
          value: f.slug || f.name || f.key || f.id,
          label: f.label || f.name || f.key
        })) || field.options || [];

        // Apply field filter if provided
        if (field.fieldFilter && pipelineFields) {
          const filteredFields = pipelineFields.filter(field.fieldFilter);
          fieldOptions = filteredFields.map(f => ({
            value: f.slug || f.name || f.key || f.id,
            label: f.label || f.name || f.key
          }));
        }

        return (
          <Select value={value} onValueChange={onChange} disabled={field.disabled}>
            <SelectTrigger>
              <SelectValue placeholder={field.placeholder || 'Select field...'} />
            </SelectTrigger>
            <SelectContent>
              {fieldOptions.length > 0 ? (
                fieldOptions.map(option => (
                  <SelectItem key={option.value.toString()} value={option.value.toString()}>
                    {option.label}
                  </SelectItem>
                ))
              ) : (
                <div className="px-2 py-1.5 text-sm text-muted-foreground">
                  {currentConfig.pipeline_id ? 'No fields available' : 'Select a pipeline first'}
                </div>
              )}
            </SelectContent>
          </Select>
        );

      case 'field-value':
        // Field value selector - shows options from a selected field's configuration
        const selectedFieldKey = field.fieldSource ? currentConfig[field.fieldSource] : null;
        let fieldValueOptions: SelectOption[] = [];

        console.log('Field-value type rendering:', {
          fieldKey: field.key,
          fieldSource: field.fieldSource,
          selectedFieldKey,
          configValue: currentConfig[field.fieldSource],
          pipelineFieldsCount: pipelineFields?.length,
          pipelineFields: pipelineFields?.map(f => ({
            key: f.key,
            name: f.name,
            slug: f.slug,
            label: f.label,
            id: f.id,
            hasOptions: !!f.field_config?.options,
            optionsCount: f.field_config?.options?.length
          }))
        });

        if (selectedFieldKey && pipelineFields) {
          // Find the selected field in pipelineFields
          const selectedField = pipelineFields.find(f =>
            (f.slug === selectedFieldKey) ||
            (f.name === selectedFieldKey) ||
            (f.key === selectedFieldKey) ||
            (f.id === selectedFieldKey)
          );

          console.log('Selected field lookup:', {
            lookingFor: selectedFieldKey,
            foundField: !!selectedField,
            selectedField: selectedField ? {
              key: selectedField.key,
              name: selectedField.name,
              slug: selectedField.slug,
              field_type: selectedField.field_type,
              field_config: selectedField.field_config,
              options: selectedField.field_config?.options
            } : null
          });

          if (selectedField) {
            // Check different possible locations for options
            const configOptions = selectedField.field_config?.options;
            const directOptions = selectedField.options;
            const config = selectedField.config;

            console.log('Checking for options in field:', {
              hasFieldConfig: !!selectedField.field_config,
              hasConfigOptions: !!configOptions,
              configOptionsValue: configOptions,
              hasDirectOptions: !!directOptions,
              directOptionsValue: directOptions,
              hasConfig: !!config,
              configValue: config
            });

            const optionsToUse = configOptions || directOptions || config?.options;

            if (optionsToUse && Array.isArray(optionsToUse)) {
              // Extract options from the field configuration
              fieldValueOptions = optionsToUse.map((opt: any) => ({
                value: typeof opt === 'string' ? opt : (opt.value || opt),
                label: typeof opt === 'string' ? opt : (opt.label || opt.value || opt)
              }));
              console.log('Extracted options:', fieldValueOptions);
            }
          }
        }

        // Fall back to field.options if provided
        if (!fieldValueOptions.length && field.options) {
          fieldValueOptions = field.options;
        }

        return (
          <Select value={value} onValueChange={onChange} disabled={field.disabled || !selectedFieldKey}>
            <SelectTrigger>
              <SelectValue placeholder={field.placeholder || 'Select value...'} />
            </SelectTrigger>
            <SelectContent>
              {fieldValueOptions.length > 0 ? (
                fieldValueOptions.map(option => (
                  <SelectItem key={option.value.toString()} value={option.value.toString()}>
                    {option.label}
                  </SelectItem>
                ))
              ) : (
                <div className="px-2 py-1.5 text-sm text-muted-foreground">
                  {selectedFieldKey ? 'No options available for this field' : 'Select a field first'}
                </div>
              )}
            </SelectContent>
          </Select>
        );

      case 'user':
        // User selector - needs users prop
        return (
          <Select value={value} onValueChange={onChange} disabled={field.disabled}>
            <SelectTrigger>
              <SelectValue placeholder={field.placeholder || 'Select user...'} />
            </SelectTrigger>
            <SelectContent>
              {users && users.length > 0 ? (
                users.map(user => (
                  <SelectItem key={user.id} value={user.id}>
                    {user.name || user.email}
                  </SelectItem>
                ))
              ) : (
                <div className="px-2 py-1.5 text-sm text-muted-foreground">
                  No users available
                </div>
              )}
            </SelectContent>
          </Select>
        );

      case 'team':
        // Team selector - would need teams data
        return (
          <Select value={value} onValueChange={onChange} disabled={field.disabled}>
            <SelectTrigger>
              <SelectValue placeholder={field.placeholder || 'Select team...'} />
            </SelectTrigger>
            <SelectContent>
              {field.options && field.options.length > 0 ? (
                field.options.map(option => (
                  <SelectItem key={option.value.toString()} value={option.value.toString()}>
                    {option.label}
                  </SelectItem>
                ))
              ) : (
                <div className="px-2 py-1.5 text-sm text-muted-foreground">
                  No teams available
                </div>
              )}
            </SelectContent>
          </Select>
        );

      case 'datetime':
        return (
          <Input
            type="datetime-local"
            value={value || ''}
            onChange={(e) => onFieldChange(e.target.value)}
            placeholder={field.placeholder}
            disabled={field.disabled}
            readOnly={field.readonly}
          />
        );

      case 'slider':
        return (
          <div className="space-y-2">
            <div className="flex items-center gap-4">
              <Input
                type="range"
                value={value ?? field.defaultValue ?? 0}
                onChange={(e) => onChange(parseFloat(e.target.value))}
                min={field.min}
                max={field.max}
                step={field.step}
                disabled={field.disabled}
                className="flex-1"
              />
              <span className="text-sm font-medium w-12 text-right">
                {value ?? field.defaultValue ?? 0}
              </span>
            </div>
          </div>
        );

      default:
        return (
          <Input
            value={value || ''}
            onChange={(e) => onFieldChange(e.target.value)}
            placeholder={field.placeholder}
            disabled={field.disabled}
            readOnly={field.readonly}
          />
        );
    }
  };

  // Check if sections are defined
  if (!nodeConfig.sections) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <p>Configuration sections not defined for this node type.</p>
        <p className="text-sm mt-2">Node type: {nodeConfig.type}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {nodeConfig.sections.map((section, index) => {
        // Check section visibility
        if (section.showWhen && !section.showWhen(currentConfig)) {
          return null;
        }

        return (
          <div key={section.id}>
            {index > 0 && <Separator className="mb-4" />}

            <Collapsible
              open={!collapsedSections.has(section.id)}
              onOpenChange={() => toggleSection(section.id)}
            >
              <CollapsibleTrigger className="flex items-center justify-between w-full hover:bg-muted/50 -mx-2 px-2 py-1 rounded-lg transition-colors">
                <div className="flex items-center gap-2">
                  {collapsedSections.has(section.id) ? (
                    <ChevronRight className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                  {section.icon && <section.icon className="h-4 w-4 text-muted-foreground" />}
                  <span className="text-sm font-medium">{section.label}</span>
                  {section.advanced && (
                    <Badge variant="secondary" className="text-xs">Advanced</Badge>
                  )}
                </div>
              </CollapsibleTrigger>

              <CollapsibleContent className="space-y-4 mt-4">
                {section.fields.map(field => (
                  <div key={field.key}>
                    {renderField(field, section)}
                  </div>
                ))}
              </CollapsibleContent>
            </Collapsible>
          </div>
        );
      })}

      {Object.keys(errors).length > 0 && (
        <div className="p-3 bg-destructive/10 rounded-lg">
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm font-medium">
              {Object.keys(errors).length} validation error(s)
            </span>
          </div>
        </div>
      )}
    </div>
  );
}