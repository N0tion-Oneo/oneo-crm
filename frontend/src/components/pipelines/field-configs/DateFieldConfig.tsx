'use client'

import {
  Checkbox,
  Label,
  RadioGroup,
  RadioGroupItem,
  Separator,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui'
import { FieldOption } from '../config-components/FieldOption'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'

interface DateFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
}

export function DateFieldConfig({
  config,
  onChange
}: DateFieldConfigProps) {
  const dateFormats = [
    { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY', description: 'US format (12/31/2024)' },
    { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY', description: 'European format (31/12/2024)' },
    { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD', description: 'ISO format (2024-12-31)' }
  ]

  const timeFormats = [
    { value: '12h', label: '12-hour (AM/PM)', description: '2:30 PM' },
    { value: '24h', label: '24-hour', description: '14:30' }
  ]

  const fieldModes = [
    { value: 'date', label: 'Date Only', description: 'Traditional date/time picker' },
    { value: 'duration', label: 'Duration Only', description: 'Time periods like "2 weeks", "3 months"' },
    { value: 'both', label: 'Date or Duration', description: 'Allow users to choose between date or duration' }
  ]

  const durationUnits = [
    { value: 'minutes', label: 'Minutes' },
    { value: 'hours', label: 'Hours' },
    { value: 'days', label: 'Days' },
    { value: 'weeks', label: 'Weeks' },
    { value: 'months', label: 'Months' },
    { value: 'years', label: 'Years' }
  ]

  const durationDisplayFormats = [
    { value: 'full', label: 'Full', description: '2 weeks, 3 months' },
    { value: 'short', label: 'Short', description: '2w, 3m' },
    { value: 'numeric', label: 'Numeric', description: '14 days, 90 days' }
  ]

  const defaultDurationPresets = [
    { label: '1 day', value: 1, unit: 'days' },
    { label: '3 days', value: 3, unit: 'days' },
    { label: '1 week', value: 1, unit: 'weeks' },
    { label: '2 weeks', value: 2, unit: 'weeks' },
    { label: '1 month', value: 1, unit: 'months' },
    { label: '3 months', value: 3, unit: 'months' },
    { label: '6 months', value: 6, unit: 'months' },
    { label: '1 year', value: 1, unit: 'years' }
  ]

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">Date Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Date and time input with customizable formatting and duration support
        </p>
      </div>

      {/* Field Mode Selection */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Field Mode</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Choose whether this field accepts dates, durations, or both">
            <Label>Input Type</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={config.field_mode || 'date'}
            onValueChange={(value) => onChange('field_mode', value)}
            className="space-y-2"
          >
            {fieldModes.map((mode) => (
              <div key={mode.value} className="flex items-start space-x-3">
                <RadioGroupItem value={mode.value} id={`field-mode-${mode.value}`} className="mt-1" />
                <div className="space-y-1">
                  <Label htmlFor={`field-mode-${mode.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                    {mode.label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{mode.description}</p>
                </div>
              </div>
            ))}
          </RadioGroup>
        </div>
      </div>

      {/* Duration Configuration */}
      {(config.field_mode === 'duration' || config.field_mode === 'both') && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Duration Settings</Label>

            {/* Available Duration Units */}
            <div className="space-y-3">
              <HelpTooltipWrapper helpText="Select which time units users can choose from">
                <Label>Available Time Units</Label>
              </HelpTooltipWrapper>
              
              <div className="grid grid-cols-3 gap-3">
                {durationUnits.map((unit) => (
                  <div key={unit.value} className="flex items-center space-x-2">
                    <Checkbox
                      id={`duration-unit-${unit.value}`}
                      checked={(config.duration_units || ['days', 'weeks', 'months', 'years']).includes(unit.value)}
                      onCheckedChange={(checked) => {
                        const currentUnits = config.duration_units || ['days', 'weeks', 'months', 'years']
                        const newUnits = checked
                          ? [...currentUnits, unit.value]
                          : currentUnits.filter((u: string) => u !== unit.value)
                        onChange('duration_units', newUnits)
                      }}
                    />
                    <Label htmlFor={`duration-unit-${unit.value}`} className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      {unit.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            {/* Duration Display Format */}
            <div className="space-y-3">
              <HelpTooltipWrapper helpText="Choose how durations are displayed once saved">
                <Label>Duration Display Format</Label>
              </HelpTooltipWrapper>
              
              <RadioGroup
                value={config.duration_display_format || 'full'}
                onValueChange={(value) => onChange('duration_display_format', value)}
                className="space-y-2"
              >
                {durationDisplayFormats.map((format) => (
                  <div key={format.value} className="flex items-start space-x-3">
                    <RadioGroupItem value={format.value} id={`duration-format-${format.value}`} className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor={`duration-format-${format.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                        {format.label}
                      </Label>
                      <p className="text-xs text-muted-foreground">{format.description}</p>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            </div>

            {/* Custom Duration Input */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="allow-custom-duration"
                checked={config.allow_custom_duration !== false}
                onCheckedChange={(checked) => onChange('allow_custom_duration', checked)}
              />
              <HelpTooltipWrapper helpText="Allow users to enter custom durations beyond the presets">
                <Label htmlFor="allow-custom-duration" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                  Allow custom duration input
                </Label>
              </HelpTooltipWrapper>
            </div>

            {/* Duration Constraints */}
            <div className="grid grid-cols-2 gap-4">
              <FieldOption
                label="Minimum Duration (days)"
                description="Minimum allowed duration in days"
                type="number"
                value={config.min_duration_days || ''}
                onChange={(value) => onChange('min_duration_days', value)}
                placeholder="1"
              />

              <FieldOption
                label="Maximum Duration (days)"
                description="Maximum allowed duration in days"
                type="number"
                value={config.max_duration_days || ''}
                onChange={(value) => onChange('max_duration_days', value)}
                placeholder="365"
              />
            </div>
          </div>
        </>
      )}

      {/* Date/Time Configuration - only show if not duration-only */}
      {config.field_mode !== 'duration' && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Date/Time Settings</Label>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="include-time"
                checked={config.include_time || false}
                onCheckedChange={(checked) => onChange('include_time', checked)}
              />
              <HelpTooltipWrapper helpText="Include time picker in addition to date selection">
                <Label htmlFor="include-time" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                  Include time selection (datetime field)
                </Label>
              </HelpTooltipWrapper>
            </div>

            {config.include_time && (
              <FieldOption
                label="Default Time"
                description="Default time when only date is selected (e.g., 09:00)"
                type="text"
                value={config.default_time || ''}
                onChange={(value) => onChange('default_time', value)}
                placeholder="09:00"
              />
            )}
          </div>
        </>
      )}

      {/* Date Format Configuration - only show if not duration-only */}
      {config.field_mode !== 'duration' && (
        <>
          <Separator />

          {/* Date Format Configuration */}
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Date Format</Label>

            <div className="space-y-3">
              <HelpTooltipWrapper helpText="Choose how dates are displayed in the input field">
                <Label>Date Display Format</Label>
              </HelpTooltipWrapper>
              
              <RadioGroup
                value={config.date_format || 'MM/DD/YYYY'}
                onValueChange={(value) => onChange('date_format', value)}
                className="space-y-2"
              >
                {dateFormats.map((format) => (
                  <div key={format.value} className="flex items-start space-x-3">
                    <RadioGroupItem value={format.value} id={`date-format-${format.value}`} className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor={`date-format-${format.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                        {format.label}
                      </Label>
                      <p className="text-xs text-muted-foreground">{format.description}</p>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            </div>
          </div>

      {/* Time Format Configuration */}
      {config.include_time && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Time Format</Label>

            <div className="space-y-3">
              <HelpTooltipWrapper helpText="Choose between 12-hour (AM/PM) or 24-hour time format">
                <Label>Time Display Format</Label>
              </HelpTooltipWrapper>
              
              <RadioGroup
                value={config.time_format || '12h'}
                onValueChange={(value) => onChange('time_format', value)}
                className="space-y-2"
              >
                {timeFormats.map((format) => (
                  <div key={format.value} className="flex items-start space-x-3">
                    <RadioGroupItem value={format.value} id={`time-format-${format.value}`} className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor={`time-format-${format.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                        {format.label}
                      </Label>
                      <p className="text-xs text-muted-foreground">{format.description}</p>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            </div>
          </div>
        </>
      )}

          <Separator />

          {/* Date Range Validation */}
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Date Validation</Label>

            <div className="grid grid-cols-2 gap-4">
              <FieldOption
                label="Minimum Date"
                description="Earliest allowed date (YYYY-MM-DD format)"
                type="text"
                value={config.min_date || ''}
                onChange={(value) => onChange('min_date', value)}
                placeholder="2024-01-01"
              />

              <FieldOption
                label="Maximum Date"
                description="Latest allowed date (YYYY-MM-DD format)"
                type="text"
                value={config.max_date || ''}
                onChange={(value) => onChange('max_date', value)}
                placeholder="2025-12-31"
              />
            </div>
          </div>
        </>
      )}

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Date Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• Mode: {fieldModes.find(m => m.value === (config.field_mode || 'date'))?.label}</div>
            {config.field_mode !== 'duration' && (
              <>
                <div>• Type: {config.include_time ? 'Date & Time' : 'Date Only'}</div>
                <div>• Date format: {config.date_format || 'MM/DD/YYYY'}</div>
                {config.include_time && <div>• Time format: {timeFormats.find(t => t.value === (config.time_format || '12h'))?.label}</div>}
                {config.default_time && <div>• Default time: {config.default_time}</div>}
                {config.min_date && <div>• Minimum date: {config.min_date}</div>}
                {config.max_date && <div>• Maximum date: {config.max_date}</div>}
              </>
            )}
            {(config.field_mode === 'duration' || config.field_mode === 'both') && (
              <>
                <div>• Duration units: {(config.duration_units || ['days', 'weeks', 'months', 'years']).join(', ')}</div>
                <div>• Duration display: {durationDisplayFormats.find(f => f.value === (config.duration_display_format || 'full'))?.label}</div>
                {config.allow_custom_duration === false && <div>• Custom input: Disabled</div>}
                {config.min_duration_days && <div>• Min duration: {config.min_duration_days} days</div>}
                {config.max_duration_days && <div>• Max duration: {config.max_duration_days} days</div>}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}