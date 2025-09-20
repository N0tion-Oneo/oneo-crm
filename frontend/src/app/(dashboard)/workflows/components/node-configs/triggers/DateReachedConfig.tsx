'use client';

import React, { useMemo } from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { FieldSelector } from '@/components/workflow-widgets/entity/FieldSelector';
import { Calendar, Clock, CalendarDays, CalendarRange } from 'lucide-react';

interface DateReachedConfigProps {
  config: any;
  onChange: (config: any) => void;
  pipelines?: any[];
  pipelineFields?: Record<string, any[]>;
  errors?: Record<string, string>;
}

export function DateReachedConfig({
  config,
  onChange,
  pipelines = [],
  pipelineFields = {},
  errors = {}
}: DateReachedConfigProps) {
  // Ensure config is never undefined
  const safeConfig = config || {};

  // Determine current mode based on which fields are present
  // If config has date_field, it's dynamic mode; otherwise static
  const currentMode = safeConfig.date_field !== undefined ? 'dynamic' : 'static';

  // Generate a human-readable schedule preview
  const schedulePreview = useMemo(() => {
    if (currentMode === 'dynamic') {
      let preview = 'Triggers when the ';
      if (safeConfig.date_field && safeConfig.pipeline_id) {
        preview += `"${safeConfig.date_field}" date is reached for each record`;
      } else if (safeConfig.pipeline_id) {
        preview += 'selected date field is reached for each record';
      } else {
        preview += 'date field value is reached for each record';
      }

      // Add offset information
      const offsetDays = safeConfig.offset_days || 0;
      const offsetHours = safeConfig.offset_hours || 0;

      if (offsetDays < 0 || offsetHours < 0) {
        const days = Math.abs(offsetDays);
        const hours = Math.abs(offsetHours);
        if (days > 0) preview += `, ${days} day${days !== 1 ? 's' : ''}`;
        if (hours > 0) preview += ` ${days > 0 ? 'and' : ','} ${hours} hour${hours !== 1 ? 's' : ''}`;
        preview += ' before';
      } else if (offsetDays > 0 || offsetHours > 0) {
        if (offsetDays > 0) preview += `, ${offsetDays} day${offsetDays !== 1 ? 's' : ''}`;
        if (offsetHours > 0) preview += ` ${offsetDays > 0 ? 'and' : ','} ${offsetHours} hour${offsetHours !== 1 ? 's' : ''}`;
        preview += ' after';
      }

      if (safeConfig.business_days_only) {
        preview += ' (adjusted to business days)';
      }

      return preview;
    }

    if (safeConfig.schedule_type === 'once') {
      if (!safeConfig.target_date) return 'One-time trigger (date not set)';
      const date = new Date(safeConfig.target_date);
      return `One-time on ${date.toLocaleDateString()} at ${date.toLocaleTimeString()}`;
    }

    // Recurring schedule
    let preview = 'Triggers ';
    const time = safeConfig.time_of_day || '09:00';

    switch (safeConfig.recurrence_pattern) {
      case 'daily':
        const interval = safeConfig.daily_interval || 1;
        preview += interval === 1 ? 'every day' : `every ${interval} days`;
        break;

      case 'weekly':
        const days = safeConfig.weekly_days || [];
        if (days.length === 0) {
          preview += 'weekly (no days selected)';
        } else if (days.length === 7) {
          preview += 'every day of the week';
        } else {
          preview += `every ${days.map((d: string) => d.slice(0, 3)).join(', ')}`;
        }
        break;

      case 'monthly':
        if (safeConfig.monthly_type === 'weekday') {
          const week = safeConfig.monthly_week || 'first';
          const day = safeConfig.monthly_weekday || 'monday';
          preview += `on the ${week} ${day} of each month`;
        } else {
          const date = safeConfig.monthly_date || 1;
          const suffix = date === 1 ? 'st' : date === 2 ? 'nd' : date === 3 ? 'rd' : 'th';
          preview += `on the ${date}${suffix} of each month`;
        }
        break;

      case 'yearly':
        const months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const month = months[safeConfig.yearly_month || 1];
        const date = safeConfig.yearly_date || 1;
        preview += `every year on ${month} ${date}`;
        break;

      default:
        preview += 'daily';
    }

    preview += ` at ${time}`;

    if (safeConfig.business_days_only) {
      preview += ' (business days only)';
    }

    return preview;
  }, [currentMode, safeConfig]);

  const handleModeChange = (newMode: string) => {
    // When switching modes, preserve common fields and clear mode-specific fields
    // The backend's default config will provide appropriate values
    const commonFields = {
      offset_days: safeConfig.offset_days,
      offset_hours: safeConfig.offset_hours,
      timezone: safeConfig.timezone,
      business_days_only: safeConfig.business_days_only
    };

    if (newMode === 'static') {
      // Switching to static mode - keep common fields only
      // Backend defaults will provide target_date if needed
      // Preserve recurring settings as they're valid for static mode
      onChange({
        ...commonFields,
        recurring: safeConfig.recurring,
        recurrence_pattern: safeConfig.recurrence_pattern
      });
    } else if (newMode === 'dynamic') {
      // Switching to dynamic mode - add empty dynamic fields
      // Clear all recurring settings as they're not valid for dynamic mode
      onChange({
        ...commonFields,
        date_field: '',
        pipeline_id: ''
        // Explicitly not including recurring fields
      });
    }
  };


  return (
    <div className="space-y-4">
      {/* Schedule Preview */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
            Schedule Preview
          </span>
        </div>
        <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
          {schedulePreview}
        </p>
      </div>

      <div>
        <Label>Date Mode</Label>
        <Select value={currentMode} onValueChange={handleModeChange}>
          <SelectTrigger>
            <SelectValue placeholder="Select mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="static">Static Date (specific date/time)</SelectItem>
            <SelectItem value="dynamic">Dynamic Date (from record field)</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500 mt-1">
          {currentMode === 'static'
            ? 'Trigger at a specific date and time'
            : 'Trigger based on a date field in your records'
          }
        </p>
      </div>

      {/* Static Mode Configuration */}
      {currentMode === 'static' && (
        <>
          <div>
            <Label>Schedule Type</Label>
            <Select
              value={safeConfig.schedule_type || 'once'}
              onValueChange={(value) => onChange({ ...safeConfig, schedule_type: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select schedule type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="once">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    One-time
                  </div>
                </SelectItem>
                <SelectItem value="recurring">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4" />
                    Recurring
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {safeConfig.schedule_type === 'once' ? (
            <div>
              <Label>Target Date & Time</Label>
              <Input
                type="datetime-local"
                value={safeConfig.target_date ?
                  new Date(safeConfig.target_date).toISOString().slice(0, 16) :
                  ''
                }
                onChange={(e) => {
                  const date = new Date(e.target.value);
                  onChange({
                    ...safeConfig,
                    target_date: date.toISOString()
                  });
                }}
              />
              {errors.target_date && (
                <p className="text-xs text-red-500 mt-1">{errors.target_date}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                Select the exact date and time to trigger the workflow
              </p>
            </div>
          ) : (
            <>
              <div>
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={safeConfig.target_date ?
                    new Date(safeConfig.target_date).toISOString().slice(0, 10) :
                    ''
                  }
                  onChange={(e) => {
                    const date = new Date(e.target.value);
                    onChange({
                      ...safeConfig,
                      target_date: date.toISOString()
                    });
                  }}
                />
                <p className="text-xs text-gray-500 mt-1">
                  When the recurring schedule should begin
                </p>
              </div>

              <div>
                <Label>Time of Day</Label>
                <Input
                  type="time"
                  value={safeConfig.time_of_day || '09:00'}
                  onChange={(e) => onChange({ ...safeConfig, time_of_day: e.target.value })}
                />
                <p className="text-xs text-gray-500 mt-1">
                  What time to trigger each occurrence
                </p>
              </div>
            </>
          )}
        </>
      )}

      {/* Dynamic Mode Configuration */}
      {currentMode === 'dynamic' && (
        <>
          <div>
            <Label>Pipeline *</Label>
            <Select
              value={safeConfig.pipeline_id || ''}
              onValueChange={(value) => onChange({ ...safeConfig, pipeline_id: value, date_field: '' })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a pipeline" />
              </SelectTrigger>
              <SelectContent>
                {Array.isArray(pipelines) && pipelines.map((pipeline) => (
                  <SelectItem key={pipeline.id} value={pipeline.id}>
                    {pipeline.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.pipeline_id && (
              <p className="text-xs text-red-500 mt-1">{errors.pipeline_id}</p>
            )}
          </div>

          {safeConfig.pipeline_id && (
            <div>
              <Label>Date Field *</Label>
              <FieldSelector
                value={safeConfig.date_field || ''}
                onChange={(value) => onChange({ ...safeConfig, date_field: value })}
                config={safeConfig}
                pipelineFields={pipelineFields[safeConfig.pipeline_id]}
                placeholder="Select a date field"
                uiHints={{
                  field_types: ['date', 'datetime'],
                  depends_on: 'pipeline_id'
                }}
              />
              {errors.date_field && (
                <p className="text-xs text-red-500 mt-1">{errors.date_field}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                The field containing the target date in your records
              </p>
            </div>
          )}
        </>
      )}

      {/* Common Configuration */}
      <div>
        <Label>Trigger Offset</Label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs">Days</Label>
            <Input
              type="number"
              min="-365"
              max="365"
              placeholder="0"
              value={safeConfig.offset_days || 0}
              onChange={(e) => onChange({
                ...config,
                offset_days: parseInt(e.target.value) || 0
              })}
            />
          </div>
          <div>
            <Label className="text-xs">Hours</Label>
            <Input
              type="number"
              min="-24"
              max="24"
              placeholder="0"
              value={safeConfig.offset_hours || 0}
              onChange={(e) => onChange({
                ...config,
                offset_hours: parseInt(e.target.value) || 0
              })}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Use negative values to trigger before the date, positive for after
        </p>
      </div>

      <div>
        <Label>Timezone</Label>
        <Select
          value={safeConfig.timezone || 'UTC'}
          onValueChange={(value) => onChange({ ...safeConfig, timezone: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="UTC">UTC</SelectItem>
            <SelectItem value="America/New_York">Eastern Time</SelectItem>
            <SelectItem value="America/Chicago">Central Time</SelectItem>
            <SelectItem value="America/Denver">Mountain Time</SelectItem>
            <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
            <SelectItem value="Europe/London">London</SelectItem>
            <SelectItem value="Europe/Paris">Paris</SelectItem>
            <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
            <SelectItem value="Australia/Sydney">Sydney</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center justify-between">
        <Label>Business Days Only</Label>
        <Switch
          checked={safeConfig.business_days_only || false}
          onCheckedChange={(checked) =>
            onChange({ ...safeConfig, business_days_only: checked })
          }
        />
      </div>
      {currentMode === 'dynamic' && safeConfig.business_days_only && (
        <p className="text-xs text-gray-500 -mt-2">
          If the date falls on a weekend, the trigger will fire on the next business day
        </p>
      )}
      {currentMode === 'static' && safeConfig.business_days_only && (
        <p className="text-xs text-gray-500 -mt-2">
          Workflow will only trigger on business days (Mon-Fri)
        </p>
      )}

      {/* Recurrence Configuration for Static Mode */}
      {currentMode === 'static' && safeConfig.schedule_type === 'recurring' && (
        <>
          <div>
            <Label>Recurrence Pattern</Label>
            <Select
              value={safeConfig.recurrence_pattern || 'daily'}
              onValueChange={(value) => onChange({ ...safeConfig, recurrence_pattern: value, recurring: true })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
                <SelectItem value="yearly">Yearly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Daily Configuration */}
          {safeConfig.recurrence_pattern === 'daily' && (
            <div>
              <Label>Repeat Every</Label>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min="1"
                  max="365"
                  value={safeConfig.daily_interval || 1}
                  onChange={(e) => onChange({ ...safeConfig, daily_interval: parseInt(e.target.value) || 1 })}
                  className="w-20"
                />
                <span className="text-sm">day(s)</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {safeConfig.daily_interval === 1 ? 'Every day' : `Every ${safeConfig.daily_interval || 1} days`}
              </p>
            </div>
          )}

          {/* Weekly Configuration */}
          {safeConfig.recurrence_pattern === 'weekly' && (
            <div>
              <Label>Days of the Week</Label>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].map((day) => (
                  <div key={day} className="flex items-center space-x-2">
                    <Checkbox
                      checked={(safeConfig.weekly_days || []).includes(day)}
                      onCheckedChange={(checked) => {
                        const days = safeConfig.weekly_days || [];
                        const newDays = checked
                          ? [...days, day]
                          : days.filter((d: string) => d !== day);
                        onChange({ ...safeConfig, weekly_days: newDays });
                      }}
                    />
                    <Label className="text-sm capitalize">{day}</Label>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Monthly Configuration */}
          {safeConfig.recurrence_pattern === 'monthly' && (
            <>
              <div>
                <Label>Monthly On</Label>
                <Select
                  value={safeConfig.monthly_type || 'date'}
                  onValueChange={(value) => onChange({ ...safeConfig, monthly_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="date">Specific Date</SelectItem>
                    <SelectItem value="weekday">Specific Weekday</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {safeConfig.monthly_type === 'date' ? (
                <div>
                  <Label>Day of Month</Label>
                  <Input
                    type="number"
                    min="1"
                    max="31"
                    value={safeConfig.monthly_date || 1}
                    onChange={(e) => onChange({ ...safeConfig, monthly_date: parseInt(e.target.value) || 1 })}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    On day {safeConfig.monthly_date || 1} of each month
                  </p>
                </div>
              ) : (
                <>
                  <div>
                    <Label>Week of Month</Label>
                    <Select
                      value={safeConfig.monthly_week || 'first'}
                      onValueChange={(value) => onChange({ ...safeConfig, monthly_week: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="first">First</SelectItem>
                        <SelectItem value="second">Second</SelectItem>
                        <SelectItem value="third">Third</SelectItem>
                        <SelectItem value="fourth">Fourth</SelectItem>
                        <SelectItem value="last">Last</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Day of Week</Label>
                    <Select
                      value={safeConfig.monthly_weekday || 'monday'}
                      onValueChange={(value) => onChange({ ...safeConfig, monthly_weekday: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="monday">Monday</SelectItem>
                        <SelectItem value="tuesday">Tuesday</SelectItem>
                        <SelectItem value="wednesday">Wednesday</SelectItem>
                        <SelectItem value="thursday">Thursday</SelectItem>
                        <SelectItem value="friday">Friday</SelectItem>
                        <SelectItem value="saturday">Saturday</SelectItem>
                        <SelectItem value="sunday">Sunday</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}
            </>
          )}

          {/* Yearly Configuration */}
          {safeConfig.recurrence_pattern === 'yearly' && (
            <>
              <div>
                <Label>Month</Label>
                <Select
                  value={String(safeConfig.yearly_month || 1)}
                  onValueChange={(value) => onChange({ ...safeConfig, yearly_month: parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[
                      { value: 1, label: 'January' },
                      { value: 2, label: 'February' },
                      { value: 3, label: 'March' },
                      { value: 4, label: 'April' },
                      { value: 5, label: 'May' },
                      { value: 6, label: 'June' },
                      { value: 7, label: 'July' },
                      { value: 8, label: 'August' },
                      { value: 9, label: 'September' },
                      { value: 10, label: 'October' },
                      { value: 11, label: 'November' },
                      { value: 12, label: 'December' }
                    ].map(({ value, label }) => (
                      <SelectItem key={value} value={String(value)}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Day of Month</Label>
                <Input
                  type="number"
                  min="1"
                  max="31"
                  value={safeConfig.yearly_date || 1}
                  onChange={(e) => onChange({ ...safeConfig, yearly_date: parseInt(e.target.value) || 1 })}
                />
              </div>
            </>
          )}

          {/* Recurrence End Options */}
          <div>
            <Label>End Recurrence</Label>
            <div className="space-y-2">
              <Input
                type="date"
                value={safeConfig.recurrence_end_date || ''}
                onChange={(e) => onChange({ ...safeConfig, recurrence_end_date: e.target.value })}
                placeholder="End date (optional)"
              />
              <Input
                type="number"
                min="1"
                max="1000"
                value={safeConfig.max_occurrences || ''}
                onChange={(e) => onChange({ ...safeConfig, max_occurrences: e.target.value ? parseInt(e.target.value) : undefined })}
                placeholder="Max occurrences (optional)"
              />
              <p className="text-xs text-gray-500">
                Leave empty for unlimited recurrence
              </p>
            </div>
          </div>
        </>
      )}

    </div>
  );
}