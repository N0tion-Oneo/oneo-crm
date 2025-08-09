'use client'

import {
  Checkbox,
  Label,
  RadioGroup,
  RadioGroupItem,
  Separator
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
  const dateTypes = [
    { value: 'date', label: 'Date Only', description: 'Just the date (YYYY-MM-DD)' },
    { value: 'time', label: 'Time Only', description: 'Just the time (HH:MM:SS)' },
    { value: 'timestamp', label: 'Date & Time', description: 'Full date and time' }
  ]

  const displayFormats = [
    { value: 'relative', label: 'Relative', description: '"2 days ago", "3 hours ago"' },
    { value: 'absolute', label: 'Absolute', description: '"Jan 15, 2024", "14:30"' },
    { value: 'both', label: 'Both', description: 'Show both relative and absolute' }
  ]

  const statusTypes = [
    { value: '', label: 'Regular Date' },
    { value: 'engagement_status', label: 'Engagement Status' },
    { value: 'response_status', label: 'Response Status' },
    { value: 'communication_status', label: 'Communication Status' },
    { value: 'pipeline_status', label: 'Pipeline Status' },
    { value: 'activity_status', label: 'Activity Status' }
  ]

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">Date/Time Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Date, time, or timestamp input with flexible formatting options
        </p>
      </div>

      {/* Date Type Configuration */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Date Type</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Choose what type of date/time information to store">
            <Label>Data Type</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={config.data_type || 'date'}
            onValueChange={(value) => onChange('data_type', value)}
            className="space-y-2"
          >
            {dateTypes.map((type) => (
              <div key={type.value} className="flex items-start space-x-3">
                <RadioGroupItem value={type.value} id={`type-${type.value}`} className="mt-1" />
                <div className="space-y-1">
                  <Label htmlFor={`type-${type.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                    {type.label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{type.description}</p>
                </div>
              </div>
            ))}
          </RadioGroup>
        </div>
      </div>

      <Separator />

      {/* Status Type (for special date fields) */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Status Type (Optional)</Label>

        <FieldOption
          label="Status Category"
          description="Mark this date field as tracking a specific type of status"
          type="select"
          value={config.status_type || ''}
          onChange={(value) => onChange('status_type', value)}
          options={statusTypes}
        />

        {config.status_type && (
          <div className="p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
            <p className="text-xs text-yellow-800 dark:text-yellow-200">
              This date field will be treated as a status indicator and may have special display logic.
            </p>
          </div>
        )}
      </div>

      <Separator />

      {/* Display Format */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Display Format</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="How dates should be displayed to users">
            <Label>Format Style</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={config.format || 'relative'}
            onValueChange={(value) => onChange('format', value)}
            className="space-y-2"
          >
            {displayFormats.map((format) => (
              <div key={format.value} className="flex items-start space-x-3">
                <RadioGroupItem value={format.value} id={`format-${format.value}`} className="mt-1" />
                <div className="space-y-1">
                  <Label htmlFor={`format-${format.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                    {format.label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{format.description}</p>
                </div>
              </div>
            ))}
          </RadioGroup>
        </div>
      </div>

      {/* Time Display Options */}
      {config.data_type === 'timestamp' && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Time Display</Label>

            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="include-time"
                  checked={config.include_time !== false}
                  onCheckedChange={(checked) => onChange('include_time', checked)}
                />
                <HelpTooltipWrapper helpText="Show time component in addition to date">
                  <Label htmlFor="include-time" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Include time in display
                  </Label>
                </HelpTooltipWrapper>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="show-seconds"
                  checked={config.show_seconds || false}
                  onCheckedChange={(checked) => onChange('show_seconds', checked)}
                />
                <HelpTooltipWrapper helpText="Show seconds in time display">
                  <Label htmlFor="show-seconds" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Show seconds
                  </Label>
                </HelpTooltipWrapper>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="use-24-hour"
                  checked={config.use_24_hour || false}
                  onCheckedChange={(checked) => onChange('use_24_hour', checked)}
                />
                <HelpTooltipWrapper helpText="Use 24-hour time format instead of 12-hour AM/PM">
                  <Label htmlFor="use-24-hour" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    24-hour time format
                  </Label>
                </HelpTooltipWrapper>
              </div>
            </div>
          </div>
        </>
      )}

      <Separator />

      {/* Default Value Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Default Value</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="default-now"
              checked={config.default_now || false}
              onCheckedChange={(checked) => onChange('default_now', checked)}
            />
            <HelpTooltipWrapper helpText="Set current date/time as default for new records">
              <Label htmlFor="default-now" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Default to current date/time
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="auto-update"
              checked={config.auto_update || false}
              onCheckedChange={(checked) => onChange('auto_update', checked)}
            />
            <HelpTooltipWrapper helpText="Automatically update to current date/time when record is modified">
              <Label htmlFor="auto-update" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Auto-update on changes
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      <Separator />

      {/* Validation Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Validation</Label>

        <div className="grid grid-cols-2 gap-4">
          <FieldOption
            label="Minimum Date"
            description="Earliest allowed date (YYYY-MM-DD)"
            type="text"
            value={config.min_date || ''}
            onChange={(value) => onChange('min_date', value)}
            placeholder="2024-01-01"
          />

          <FieldOption
            label="Maximum Date"
            description="Latest allowed date (YYYY-MM-DD)"
            type="text"
            value={config.max_date || ''}
            onChange={(value) => onChange('max_date', value)}
            placeholder="2025-12-31"
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="no-weekends"
              checked={config.no_weekends || false}
              onCheckedChange={(checked) => onChange('no_weekends', checked)}
            />
            <HelpTooltipWrapper helpText="Prevent selection of weekend dates">
              <Label htmlFor="no-weekends" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Exclude weekends
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="business-hours"
              checked={config.business_hours_only || false}
              onCheckedChange={(checked) => onChange('business_hours_only', checked)}
            />
            <HelpTooltipWrapper helpText="Restrict time selection to business hours (9 AM - 5 PM)">
              <Label htmlFor="business-hours" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Business hours only
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Date Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• Type: {dateTypes.find(t => t.value === (config.data_type || 'date'))?.label}</div>
            <div>• Format: {displayFormats.find(f => f.value === (config.format || 'relative'))?.label}</div>
            {config.status_type && <div>• Status type: {config.status_type.replace('_', ' ')}</div>}
            {config.default_now && <div>• Defaults to current date/time</div>}
            {config.auto_update && <div>• Auto-updates on changes</div>}
            {config.min_date && <div>• Minimum date: {config.min_date}</div>}
            {config.max_date && <div>• Maximum date: {config.max_date}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}