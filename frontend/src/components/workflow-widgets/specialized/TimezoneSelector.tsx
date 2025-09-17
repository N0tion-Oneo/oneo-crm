/**
 * Timezone selection widget
 */

import React, { useMemo } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
} from '@/components/ui/select';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';

// Common timezones grouped by region
const TIMEZONE_GROUPS = {
  'North America': [
    { value: 'America/New_York', label: 'Eastern Time (ET)', offset: 'UTC-5/-4' },
    { value: 'America/Chicago', label: 'Central Time (CT)', offset: 'UTC-6/-5' },
    { value: 'America/Denver', label: 'Mountain Time (MT)', offset: 'UTC-7/-6' },
    { value: 'America/Phoenix', label: 'Arizona Time', offset: 'UTC-7' },
    { value: 'America/Los_Angeles', label: 'Pacific Time (PT)', offset: 'UTC-8/-7' },
    { value: 'America/Anchorage', label: 'Alaska Time', offset: 'UTC-9/-8' },
    { value: 'Pacific/Honolulu', label: 'Hawaii Time', offset: 'UTC-10' },
  ],
  'Europe': [
    { value: 'Europe/London', label: 'London (GMT/BST)', offset: 'UTC+0/+1' },
    { value: 'Europe/Paris', label: 'Central European Time', offset: 'UTC+1/+2' },
    { value: 'Europe/Berlin', label: 'Berlin Time', offset: 'UTC+1/+2' },
    { value: 'Europe/Moscow', label: 'Moscow Time', offset: 'UTC+3' },
    { value: 'Europe/Istanbul', label: 'Istanbul Time', offset: 'UTC+3' },
  ],
  'Asia': [
    { value: 'Asia/Dubai', label: 'Dubai Time', offset: 'UTC+4' },
    { value: 'Asia/Karachi', label: 'Pakistan Time', offset: 'UTC+5' },
    { value: 'Asia/Kolkata', label: 'India Time', offset: 'UTC+5:30' },
    { value: 'Asia/Shanghai', label: 'China Time', offset: 'UTC+8' },
    { value: 'Asia/Tokyo', label: 'Japan Time', offset: 'UTC+9' },
    { value: 'Asia/Seoul', label: 'Korea Time', offset: 'UTC+9' },
  ],
  'Pacific': [
    { value: 'Australia/Sydney', label: 'Sydney Time', offset: 'UTC+10/+11' },
    { value: 'Australia/Melbourne', label: 'Melbourne Time', offset: 'UTC+10/+11' },
    { value: 'Pacific/Auckland', label: 'New Zealand Time', offset: 'UTC+12/+13' },
  ],
  'Other': [
    { value: 'UTC', label: 'UTC', offset: 'UTC+0' },
    { value: 'America/Toronto', label: 'Toronto Time', offset: 'UTC-5/-4' },
    { value: 'America/Mexico_City', label: 'Mexico City Time', offset: 'UTC-6/-5' },
    { value: 'America/Sao_Paulo', label: 'São Paulo Time', offset: 'UTC-3' },
    { value: 'Africa/Johannesburg', label: 'South Africa Time', offset: 'UTC+2' },
  ]
};

export const TimezoneSelector: React.FC<WidgetProps> = (props) => {
  const { value, onChange } = props;

  const currentTimezone = useMemo(() => {
    // Try to get user's current timezone
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return 'UTC';
    }
  }, []);

  const placeholder = props.placeholder || props.uiHints?.placeholder || 'Select timezone';

  return (
    <BaseWidgetWrapper {...props}>
      <Select
        value={value || currentTimezone}
        onValueChange={onChange}
        disabled={props.disabled || props.readonly}
      >
        <SelectTrigger>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {/* Current timezone option */}
          <SelectItem value={currentTimezone}>
            <div className="flex items-center gap-2">
              <span className="text-blue-600">📍</span>
              Current timezone ({currentTimezone})
            </div>
          </SelectItem>

          {/* Grouped timezone options */}
          {Object.entries(TIMEZONE_GROUPS).map(([region, timezones]) => (
            <SelectGroup key={region}>
              <SelectLabel>{region}</SelectLabel>
              {timezones.map((tz) => (
                <SelectItem key={tz.value} value={tz.value}>
                  <div className="flex justify-between items-center w-full">
                    <span>{tz.label}</span>
                    <span className="text-xs text-gray-500 ml-2">{tz.offset}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectGroup>
          ))}
        </SelectContent>
      </Select>
    </BaseWidgetWrapper>
  );
};