/**
 * Refactored UnifiedConfigRenderer using the centralized widget registry
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  ChevronDown, ChevronRight, Variable,
  AlertCircle, Info, Type
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { UnifiedNodeConfig, ConfigSection, ConfigField, NodeConfigComponentProps } from './types';
import { ExpressionEditor } from '../../configuration/ExpressionEditor';

// Import widget registry and renderer
import { WidgetRenderer } from '@/components/workflow-widgets/core/WidgetRenderer';
import { widgetRegistry } from '@/components/workflow-widgets/core/WidgetRegistry';
import '@/components/workflow-widgets/registerWidgets'; // Auto-register widgets

// Import condition builder separately (not migrated yet)
import { WorkflowConditionBuilder } from '../../WorkflowConditionBuilder';

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

  // Use the config directly from props
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
      const pipeline = pipelines.find((p: any) => p.id === currentConfig.pipeline_id);
      if (pipeline) {
        const slug = pipeline.slug || pipeline.name?.toLowerCase().replace(/\s+/g, '-');
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
      <React.Suspense fallback={
        <div className="flex items-center justify-center p-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
          <span className="ml-2 text-sm">Loading component...</span>
        </div>
      }>
        <CustomComponent
          config={currentConfig}
          onChange={onChange}
          availableVariables={availableVariables}
          pipelines={pipelines}
          pipelineFields={pipelineFields}
          workflows={workflows}
          users={users}
          errors={errors}
        />
      </React.Suspense>
    );
  }

  const toggleSectionCollapse = (sectionId: string) => {
    const newCollapsed = new Set(collapsedSections);
    if (newCollapsed.has(sectionId)) {
      newCollapsed.delete(sectionId);
    } else {
      newCollapsed.add(sectionId);
    }
    setCollapsedSections(newCollapsed);
  };

  const toggleExpressionMode = (fieldKey: string) => {
    setExpressionMode(prev => ({
      ...prev,
      [fieldKey]: !prev[fieldKey]
    }));
  };

  const updateConfig = (key: string, value: any) => {
    const newConfig = { ...currentConfig, [key]: value };

    // Handle custom onChange if specified
    const field = nodeConfig.sections
      ?.flatMap(s => s.fields)
      .find(f => f.key === key);

    if (field?.onChange) {
      const modifiedConfig = field.onChange(value, newConfig, {
        pipelines,
        users,
        workflows,
        pipelineFields,
        availableVariables
      });
      onChange(modifiedConfig || newConfig);
    } else {
      onChange(newConfig);
    }
  };

  const renderField = (field: ConfigField, section: ConfigSection) => {
    // Check conditional visibility
    if (field.showWhen && !field.showWhen(currentConfig)) {
      return null;
    }

    // Skip hidden fields - they should not be rendered in the UI
    const widget = field.uiHints?.widget || field.widget;
    if (widget === 'hidden') {
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

        {/* Render field using custom render or widget registry */}
        {field.customRender ? (
          field.customRender({
            field,
            value,
            onChange: (newValueOrConfig) => {
              // If the customRender returns a full config object, use onChange directly
              // Otherwise update just the field value
              if (typeof newValueOrConfig === 'object' && newValueOrConfig !== null && 'pipeline_id' in newValueOrConfig) {
                onChange(newValueOrConfig);
              } else {
                updateConfig(fieldKey, newValueOrConfig);
              }
            },
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
          renderFieldInput(field, value, isExpression, (v) => updateConfig(fieldKey, v))
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
    onFieldChange: (value: any) => void
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

    // Special case for condition builder (not migrated to widget registry yet)
    const widget = field.uiHints?.widget || field.widget;
    if (widget === 'condition_builder' || field.type === 'conditions') {
      return (
        <WorkflowConditionBuilder
          fields={pipelineFields || []}
          value={value}
          onChange={onFieldChange}
          supportsChangeOperators={field.uiHints?.supports_change_operators}
          pipelineId={currentConfig.pipeline_id || currentConfig.pipeline_slug}
        />
      );
    }

    // Use the widget registry for everything else
    const widgetType = widget || field.type;

    // Check if widget exists in registry
    if (!widgetRegistry.has(widgetType) && widgetType) {
      console.warn(`Widget type "${widgetType}" not found in registry, falling back to text`);
    }

    return (
      <WidgetRenderer
        widget={widgetType}
        fieldType={field.type}
        props={{
          key: field.key,
          // Don't pass label - UnifiedConfigRenderer already renders it
          // Don't pass error - UnifiedConfigRenderer already renders it
          value,
          onChange: onFieldChange,
          placeholder: field.placeholder,
          disabled: field.disabled,
          readonly: field.readonly,
          required: field.required,
          // Don't pass helpText either - UnifiedConfigRenderer renders it
          uiHints: field.uiHints || {},
          config: currentConfig,
          field: { key: field.key },
          onConfigUpdate: onChange,  // Pass the full config update function
          pipelines,
          users,
          userTypes,
          workflows,
          pipelineFields,
          availableVariables
        }}
      />
    );
  };

  const renderSection = (section: ConfigSection) => {
    const isCollapsed = collapsedSections.has(section.id);
    const visibleFields = section.fields.filter(field =>
      !field.showWhen || field.showWhen(currentConfig)
    );

    if (visibleFields.length === 0) {
      return null;
    }

    return (
      <div key={section.id} className="space-y-4">
        <Collapsible
          open={!isCollapsed}
          onOpenChange={() => toggleSectionCollapse(section.id)}
        >
          <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors">
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
            {section.icon && <section.icon className="h-4 w-4" />}
            {section.label}
            {section.advanced && (
              <span className="text-xs text-muted-foreground ml-2">(Advanced)</span>
            )}
          </CollapsibleTrigger>

          <CollapsibleContent className="mt-4 space-y-4">
            {section.description && (
              <p className="text-sm text-muted-foreground">{section.description}</p>
            )}
            {visibleFields.map(field => renderField(field, section))}
          </CollapsibleContent>
        </Collapsible>
      </div>
    );
  };

  // Group sections by advanced/normal
  const normalSections = nodeConfig.sections?.filter(s => !s.advanced) || [];
  const advancedSections = nodeConfig.sections?.filter(s => s.advanced) || [];

  return (
    <div className="space-y-6">
      {/* Render normal sections */}
      {normalSections.map(renderSection)}

      {/* Separator between normal and advanced */}
      {normalSections.length > 0 && advancedSections.length > 0 && (
        <Separator />
      )}

      {/* Render advanced sections */}
      {advancedSections.map(renderSection)}

      {/* Show validation summary if there are errors */}
      {Object.keys(errors).length > 0 && (
        <div className="p-3 bg-destructive/10 rounded-md">
          <p className="text-sm font-medium text-destructive mb-2">
            Please fix the following errors:
          </p>
          <ul className="text-sm text-destructive space-y-1">
            {Object.entries(errors).map(([key, error]) => (
              <li key={key} className="flex items-start gap-1">
                <span>•</span>
                <span>{error}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}