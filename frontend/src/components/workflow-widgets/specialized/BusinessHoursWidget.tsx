/**
 * Business hours configuration widget
 */

import React from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';

interface BusinessHours {
  enabled: boolean;
  days: {
    monday: { enabled: boolean; start: string; end: string };
    tuesday: { enabled: boolean; start: string; end: string };
    wednesday: { enabled: boolean; start: string; end: string };
    thursday: { enabled: boolean; start: string; end: string };
    friday: { enabled: boolean; start: string; end: string };
    saturday: { enabled: boolean; start: string; end: string };
    sunday: { enabled: boolean; start: string; end: string };
  };
  timezone?: string;
}

const DEFAULT_BUSINESS_HOURS: BusinessHours = {
  enabled: true,
  days: {
    monday: { enabled: true, start: '09:00', end: '17:00' },
    tuesday: { enabled: true, start: '09:00', end: '17:00' },
    wednesday: { enabled: true, start: '09:00', end: '17:00' },
    thursday: { enabled: true, start: '09:00', end: '17:00' },
    friday: { enabled: true, start: '09:00', end: '17:00' },
    saturday: { enabled: false, start: '09:00', end: '17:00' },
    sunday: { enabled: false, start: '09:00', end: '17:00' },
  },
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
};

export const BusinessHoursWidget: React.FC<WidgetProps> = (props) => {
  const { value = DEFAULT_BUSINESS_HOURS, onChange } = props;

  const updateDay = (
    day: keyof BusinessHours['days'],
    field: 'enabled' | 'start' | 'end',
    newValue: any
  ) => {
    onChange({
      ...value,
      days: {
        ...value.days,
        [day]: {
          ...value.days[day],
          [field]: newValue
        }
      }
    });
  };

  const toggleAllDays = (enabled: boolean) => {
    const updatedDays = { ...value.days };
    Object.keys(updatedDays).forEach(day => {
      updatedDays[day as keyof BusinessHours['days']].enabled = enabled;
    });
    onChange({ ...value, days: updatedDays });
  };

  const setAllHours = (start: string, end: string) => {
    const updatedDays = { ...value.days };
    Object.keys(updatedDays).forEach(day => {
      const dayKey = day as keyof BusinessHours['days'];
      updatedDays[dayKey].start = start;
      updatedDays[dayKey].end = end;
    });
    onChange({ ...value, days: updatedDays });
  };

  const dayLabels = {
    monday: 'Monday',
    tuesday: 'Tuesday',
    wednesday: 'Wednesday',
    thursday: 'Thursday',
    friday: 'Friday',
    saturday: 'Saturday',
    sunday: 'Sunday'
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="space-y-4">
        {/* Master toggle */}
        <div className="flex items-center justify-between pb-2 border-b">
          <Label className="text-sm font-medium">Business Hours Active</Label>
          <Switch
            checked={value.enabled}
            onCheckedChange={(checked) => onChange({ ...value, enabled: checked })}
            disabled={props.disabled || props.readonly}
          />
        </div>

        {value.enabled && (
          <>
            {/* Quick actions */}
            <div className="flex gap-2 text-xs">
              <button
                type="button"
                onClick={() => toggleAllDays(true)}
                className="text-blue-600 hover:text-blue-700"
                disabled={props.disabled || props.readonly}
              >
                Enable all days
              </button>
              <span className="text-gray-400">|</span>
              <button
                type="button"
                onClick={() => toggleAllDays(false)}
                className="text-blue-600 hover:text-blue-700"
                disabled={props.disabled || props.readonly}
              >
                Disable all days
              </button>
              <span className="text-gray-400">|</span>
              <button
                type="button"
                onClick={() => setAllHours('09:00', '17:00')}
                className="text-blue-600 hover:text-blue-700"
                disabled={props.disabled || props.readonly}
              >
                Set 9-5 for all
              </button>
            </div>

            {/* Days configuration */}
            <div className="space-y-2">
              {Object.entries(dayLabels).map(([day, label]) => {
                const dayKey = day as keyof BusinessHours['days'];
                const dayConfig = value.days[dayKey];

                return (
                  <div
                    key={day}
                    className={`flex items-center gap-3 p-2 rounded ${
                      dayConfig.enabled ? 'bg-white' : 'bg-gray-50'
                    }`}
                  >
                    <Switch
                      checked={dayConfig.enabled}
                      onCheckedChange={(checked) => updateDay(dayKey, 'enabled', checked)}
                      disabled={props.disabled || props.readonly}
                    />

                    <span className={`w-24 text-sm ${
                      dayConfig.enabled ? 'text-gray-900' : 'text-gray-400'
                    }`}>
                      {label}
                    </span>

                    <Input
                      type="time"
                      value={dayConfig.start}
                      onChange={(e) => updateDay(dayKey, 'start', e.target.value)}
                      disabled={props.disabled || props.readonly || !dayConfig.enabled}
                      className="w-28"
                    />

                    <span className="text-gray-500 text-sm">to</span>

                    <Input
                      type="time"
                      value={dayConfig.end}
                      onChange={(e) => updateDay(dayKey, 'end', e.target.value)}
                      disabled={props.disabled || props.readonly || !dayConfig.enabled}
                      className="w-28"
                    />
                  </div>
                );
              })}
            </div>

            {/* Timezone info */}
            {value.timezone && (
              <div className="text-xs text-gray-500 pt-2 border-t">
                Timezone: {value.timezone}
              </div>
            )}
          </>
        )}
      </div>
    </BaseWidgetWrapper>
  );
};