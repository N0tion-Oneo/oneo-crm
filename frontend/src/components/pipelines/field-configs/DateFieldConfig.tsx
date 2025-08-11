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

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">Date Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Date and time input with customizable formatting
        </p>
      </div>

      {/* Include Time Configuration */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Date/Time Type</Label>

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

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Date Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• Type: {config.include_time ? 'Date & Time' : 'Date Only'}</div>
            <div>• Date format: {config.date_format || 'MM/DD/YYYY'}</div>
            {config.include_time && <div>• Time format: {timeFormats.find(t => t.value === (config.time_format || '12h'))?.label}</div>}
            {config.default_time && <div>• Default time: {config.default_time}</div>}
            {config.min_date && <div>• Minimum date: {config.min_date}</div>}
            {config.max_date && <div>• Maximum date: {config.max_date}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}