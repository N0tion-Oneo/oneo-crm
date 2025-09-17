/**
 * Central export for all workflow widgets
 */

// Core infrastructure
export { widgetRegistry } from './core/WidgetRegistry';
export { WidgetRenderer, useWidget } from './core/WidgetRenderer';
export type { WidgetProps, UIHints, WidgetDefinition, IWidgetRegistry } from './core/types';

// Basic widgets
export * from './basic';

// Entity selection widgets
export * from './entity';

// Specialized widgets
export { DynamicSelect } from './specialized/DynamicSelect';
export { TimezoneSelector } from './specialized/TimezoneSelector';

// Complex builder widgets (existing)
export { default as ScheduleBuilder } from './ScheduleBuilder';
export { default as JsonBuilder } from './JsonBuilder';
export { default as EnhancedTagInput } from './EnhancedTagInput';

// Auto-register all widgets on import
import './registerWidgets';