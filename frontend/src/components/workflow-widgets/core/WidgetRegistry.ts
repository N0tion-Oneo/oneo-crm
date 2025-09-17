/**
 * Central registry for all workflow widgets
 */

import React from 'react';
import { WidgetDefinition, WidgetProps, IWidgetRegistry } from './types';

class WidgetRegistry implements IWidgetRegistry {
  private static instance: WidgetRegistry;
  private widgets: Map<string, WidgetDefinition> = new Map();
  private fallbackWidgets: Map<string, string> = new Map();

  private constructor() {
    // Initialize fallback mappings for field types to widgets
    this.initializeFallbacks();
  }

  public static getInstance(): WidgetRegistry {
    if (!WidgetRegistry.instance) {
      WidgetRegistry.instance = new WidgetRegistry();
    }
    return WidgetRegistry.instance;
  }

  /**
   * Register a widget definition
   */
  public register(name: string, definition: WidgetDefinition): void {
    if (this.widgets.has(name)) {
      console.warn(`Widget "${name}" is already registered. Overwriting...`);
    }
    this.widgets.set(name, definition);
  }

  /**
   * Register multiple widgets at once
   */
  public registerBulk(definitions: Record<string, WidgetDefinition>): void {
    Object.entries(definitions).forEach(([name, definition]) => {
      this.register(name, definition);
    });
  }

  /**
   * Get a widget definition
   */
  public get(name: string): WidgetDefinition | undefined {
    return this.widgets.get(name);
  }

  /**
   * Check if a widget exists
   */
  public has(name: string): boolean {
    return this.widgets.has(name);
  }

  /**
   * Get all registered widgets
   */
  public getAll(): Map<string, WidgetDefinition> {
    return new Map(this.widgets);
  }

  /**
   * Get widget by name or fallback to field type
   */
  public getWidget(widgetName?: string, fieldType?: string): WidgetDefinition | undefined {
    // First try exact widget match
    if (widgetName && this.has(widgetName)) {
      return this.get(widgetName);
    }

    // Then try fallback mapping
    if (widgetName && this.fallbackWidgets.has(widgetName)) {
      const fallback = this.fallbackWidgets.get(widgetName)!;
      if (this.has(fallback)) {
        return this.get(fallback);
      }
    }

    // Finally try field type
    if (fieldType && this.has(fieldType)) {
      return this.get(fieldType);
    }

    // Field type fallback
    if (fieldType && this.fallbackWidgets.has(fieldType)) {
      const fallback = this.fallbackWidgets.get(fieldType)!;
      if (this.has(fallback)) {
        return this.get(fallback);
      }
    }

    return undefined;
  }

  /**
   * Render a widget
   */
  public render(widget: string, props: WidgetProps): React.ReactElement | null {
    const definition = this.getWidget(widget, props.uiHints?.widget);

    if (!definition) {
      console.warn(`Widget "${widget}" not found in registry`);
      return null;
    }

    const Component = definition.component;
    const mergedProps = {
      ...definition.defaultProps,
      ...props
    };

    // Apply transformer if exists
    if (definition.transformer?.fromBackend && mergedProps.value !== undefined) {
      mergedProps.value = definition.transformer.fromBackend(mergedProps.value);
    }

    // Wrap onChange to apply transformer
    if (definition.transformer?.toBackend) {
      const originalOnChange = mergedProps.onChange;
      mergedProps.onChange = (value: any) => {
        const transformedValue = definition.transformer!.toBackend!(value);
        originalOnChange(transformedValue);
      };
    }

    return React.createElement(Component, mergedProps);
  }

  /**
   * Initialize fallback mappings
   */
  private initializeFallbacks(): void {
    // Widget name aliases
    this.fallbackWidgets.set('pipeline_select', 'pipeline_selector');
    this.fallbackWidgets.set('pipeline_multiselect', 'pipeline_selector');
    this.fallbackWidgets.set('field_select', 'field_selector');
    this.fallbackWidgets.set('field_multiselect', 'field_selector');
    this.fallbackWidgets.set('user_select', 'user_selector');
    this.fallbackWidgets.set('user_multiselect', 'user_selector');
    this.fallbackWidgets.set('workflow_select', 'workflow_selector');
    this.fallbackWidgets.set('workflow_multiselect', 'workflow_selector');
    this.fallbackWidgets.set('user_type_multiselect', 'user_type_selector');
    this.fallbackWidgets.set('stage_multiselect', 'stage_selector');

    // Field type to widget mappings
    this.fallbackWidgets.set('string', 'text');
    this.fallbackWidgets.set('integer', 'number');
    this.fallbackWidgets.set('boolean', 'checkbox');
    this.fallbackWidgets.set('array', 'multiselect');

    // Complex widget aliases
    this.fallbackWidgets.set('json_editor', 'json_builder');
    this.fallbackWidgets.set('schedule', 'schedule_builder');
    this.fallbackWidgets.set('conditions', 'condition_builder');
    this.fallbackWidgets.set('tags', 'tag_input');
  }

  /**
   * Clear all registered widgets (useful for testing)
   */
  public clear(): void {
    this.widgets.clear();
    this.initializeFallbacks();
  }
}

// Export singleton instance
export const widgetRegistry = WidgetRegistry.getInstance();