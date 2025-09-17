/**
 * Smart renderer component that uses the widget registry
 */

import React from 'react';
import { widgetRegistry } from './WidgetRegistry';
import { WidgetRendererProps } from './types';
import { AlertCircle } from 'lucide-react';

export const WidgetRenderer: React.FC<WidgetRendererProps> = ({
  widget,
  fieldType,
  props
}) => {
  // Try to get widget from registry
  const definition = widgetRegistry.getWidget(widget, fieldType);

  if (!definition) {
    // Fallback to a basic text input with warning
    console.warn(`No widget found for "${widget}" (fieldType: ${fieldType})`);
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-amber-600 text-sm">
          <AlertCircle className="w-4 h-4" />
          <span>Unknown widget type: {widget || fieldType}</span>
        </div>
        <input
          type="text"
          value={props.value || ''}
          onChange={(e) => props.onChange(e.target.value)}
          placeholder={props.placeholder}
          disabled={props.disabled}
          readOnly={props.readonly}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    );
  }

  // Render the widget
  const element = widgetRegistry.render(widget || fieldType || 'text', props);

  // Wrap with error display if needed
  if (props.error) {
    return (
      <div className="space-y-1">
        {element}
        <p className="text-sm text-red-600">{props.error}</p>
      </div>
    );
  }

  return element;
};

/**
 * Hook to use widget registry in components
 */
export const useWidget = (widgetName: string, fieldType?: string) => {
  const definition = widgetRegistry.getWidget(widgetName, fieldType);

  return {
    exists: !!definition,
    definition,
    render: (props: any) => definition ?
      widgetRegistry.render(widgetName, props) : null
  };
};