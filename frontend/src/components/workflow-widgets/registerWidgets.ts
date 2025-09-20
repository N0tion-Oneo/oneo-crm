/**
 * Register all widgets with the central registry
 */

import { widgetRegistry } from './core/WidgetRegistry';
import React from 'react';

// Basic widgets
import {
  TextWidget,
  TextareaWidget,
  PasswordWidget,
  NumberWidget,
  SliderWidget,
  CheckboxWidget,
  RadioWidget,
  SelectWidget,
  MultiselectWidget,
  DateWidget,
  TimeWidget,
  DateTimeWidget,
  TimeRangeWidget
} from './basic';

// Entity widgets
import {
  PipelineSelector,
  FieldSelector,
  UserSelector,
  UserTypeSelector,
  WorkflowSelector
} from './entity';

// Specialized widgets
import { DynamicSelect } from './specialized/DynamicSelect';
import { TimezoneSelector } from './specialized/TimezoneSelector';
import { BusinessHoursWidget } from './specialized/BusinessHoursWidget';
import { EmailListWidget } from './specialized/EmailListWidget';
import { TextListWidget } from './specialized/TextListWidget';
import { RichTextEditor } from './specialized/RichTextEditor';

// Builder widgets
import { FieldBuilderWidget } from './builders/FieldBuilderWidget';
import { CriteriaBuilderWidget } from './builders/CriteriaBuilderWidget';

// Existing complex widgets
import { ScheduleBuilder } from './ScheduleBuilder';
import { JsonBuilder } from './JsonBuilder';
import { EnhancedTagInput } from './EnhancedTagInput';

// Workflow widgets
import { UserEnrichedSelectWidget } from './inputs/UserEnrichedSelectWidget';

/**
 * Register all widgets
 */
export function registerAllWidgets() {
  // Basic text widgets
  widgetRegistry.register('text', {
    name: 'text',
    component: TextWidget
  });

  widgetRegistry.register('textarea', {
    name: 'textarea',
    component: TextareaWidget
  });

  widgetRegistry.register('password', {
    name: 'password',
    component: PasswordWidget
  });

  widgetRegistry.register('readonly_text', {
    name: 'readonly_text',
    component: TextWidget  // TextWidget handles readonly display
  });

  // Number widgets
  widgetRegistry.register('number', {
    name: 'number',
    component: NumberWidget
  });

  widgetRegistry.register('slider', {
    name: 'slider',
    component: SliderWidget
  });

  // Boolean widgets
  widgetRegistry.register('checkbox', {
    name: 'checkbox',
    component: CheckboxWidget
  });

  widgetRegistry.register('radio', {
    name: 'radio',
    component: RadioWidget
  });

  // Selection widgets
  widgetRegistry.register('select', {
    name: 'select',
    component: SelectWidget
  });

  widgetRegistry.register('multiselect', {
    name: 'multiselect',
    component: MultiselectWidget
  });

  // Date/Time widgets
  widgetRegistry.register('date', {
    name: 'date',
    component: DateWidget
  });

  widgetRegistry.register('time', {
    name: 'time',
    component: TimeWidget
  });

  widgetRegistry.register('datetime', {
    name: 'datetime',
    component: DateTimeWidget
  });

  widgetRegistry.register('time_range', {
    name: 'time_range',
    component: TimeRangeWidget
  });

  // Entity selection widgets
  widgetRegistry.register('pipeline_selector', {
    name: 'pipeline_selector',
    component: PipelineSelector
  });

  widgetRegistry.register('pipeline_select', {
    name: 'pipeline_select',
    component: PipelineSelector
  });

  widgetRegistry.register('pipeline_multiselect', {
    name: 'pipeline_multiselect',
    component: PipelineSelector
  });

  widgetRegistry.register('field_selector', {
    name: 'field_selector',
    component: FieldSelector
  });

  widgetRegistry.register('field_select', {
    name: 'field_select',
    component: FieldSelector
  });

  widgetRegistry.register('field_multiselect', {
    name: 'field_multiselect',
    component: FieldSelector
  });

  widgetRegistry.register('user_selector', {
    name: 'user_selector',
    component: UserSelector
  });

  widgetRegistry.register('user_select', {
    name: 'user_select',
    component: UserSelector
  });

  widgetRegistry.register('user_multiselect', {
    name: 'user_multiselect',
    component: UserSelector
  });

  widgetRegistry.register('user_type_selector', {
    name: 'user_type_selector',
    component: UserTypeSelector
  });

  widgetRegistry.register('user_type_multiselect', {
    name: 'user_type_multiselect',
    component: UserTypeSelector
  });

  widgetRegistry.register('workflow_selector', {
    name: 'workflow_selector',
    component: WorkflowSelector
  });

  widgetRegistry.register('workflow_select', {
    name: 'workflow_select',
    component: WorkflowSelector
  });

  widgetRegistry.register('workflow_multiselect', {
    name: 'workflow_multiselect',
    component: WorkflowSelector
  });

  // User enriched selector for workflows
  widgetRegistry.register('user_enriched_select', {
    name: 'user_enriched_select',
    component: UserEnrichedSelectWidget as any
  });

  // Specialized widgets
  widgetRegistry.register('dynamic_select', {
    name: 'dynamic_select',
    component: DynamicSelect
  });

  widgetRegistry.register('timezone_select', {
    name: 'timezone_select',
    component: TimezoneSelector
  });

  // Complex builder widgets
  widgetRegistry.register('schedule_builder', {
    name: 'schedule_builder',
    component: ScheduleBuilder as any
  });

  widgetRegistry.register('json_builder', {
    name: 'json_builder',
    component: JsonBuilder as any
  });

  widgetRegistry.register('json_editor', {
    name: 'json_editor',
    component: JsonBuilder as any  // Same component, different styling
  });

  widgetRegistry.register('tag_input', {
    name: 'tag_input',
    component: EnhancedTagInput as any
  });

  widgetRegistry.register('tags', {
    name: 'tags',
    component: EnhancedTagInput as any
  });

  // Additional specialized widgets
  widgetRegistry.register('business_hours', {
    name: 'business_hours',
    component: BusinessHoursWidget
  });

  widgetRegistry.register('email_list', {
    name: 'email_list',
    component: EmailListWidget
  });

  widgetRegistry.register('text_list', {
    name: 'text_list',
    component: TextListWidget
  });

  widgetRegistry.register('rich_text_editor', {
    name: 'rich_text_editor',
    component: RichTextEditor
  });

  widgetRegistry.register('rich_text', {
    name: 'rich_text',
    component: RichTextEditor
  });

  // Builder widgets
  widgetRegistry.register('field_builder', {
    name: 'field_builder',
    component: FieldBuilderWidget
  });

  widgetRegistry.register('criteria_builder', {
    name: 'criteria_builder',
    component: CriteriaBuilderWidget
  });

  // Stage tracking widgets
  widgetRegistry.register('stage_options_multiselect', {
    name: 'stage_options_multiselect',
    component: React.lazy(() => import('./widgets/StageOptionsMultiselect').then(m => ({ default: m.StageOptionsMultiselect })))
  });

  widgetRegistry.register('stage_tracking_toggle', {
    name: 'stage_tracking_toggle',
    component: React.lazy(() => import('./widgets/StageTrackingToggle').then(m => ({ default: m.StageTrackingToggle })))
  });

  // TODO: Register these widgets as they're built:
  // - condition_builder (already exists, needs integration)
  // - data_source_builder
  // - branch_mapper
  // - file_upload
  // - external_check_config
}

// Auto-register on import
registerAllWidgets();