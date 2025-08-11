'use client'

import {
  Checkbox,
  Label,
  RadioGroup,
  RadioGroupItem,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Separator
} from '@/components/ui'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'

interface RecordDataFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
}

export function RecordDataFieldConfig({
  config,
  onChange
}: RecordDataFieldConfigProps) {
  const dataTypes = [
    { value: 'timestamp', label: 'Timestamp', description: 'Date and time values (created, updated, etc.)' },
    { value: 'user', label: 'User', description: 'User references (created by, updated by, etc.)' },
    { value: 'count', label: 'Count', description: 'Numeric counts (communications, days in pipeline, etc.)' },
    { value: 'duration', label: 'Duration', description: 'Time durations (response time, stage duration, etc.)' },
    { value: 'status', label: 'Status', description: 'System status indicators (engagement, response, etc.)' }
  ]

  const timestampTypes = [
    { value: 'created_at', label: 'Created At', description: 'When the record was created' },
    { value: 'updated_at', label: 'Updated At', description: 'When the record was last updated' },
    { value: 'last_engaged_at', label: 'Last Engaged At', description: 'Last engagement timestamp' },
    { value: 'first_contacted_at', label: 'First Contacted At', description: 'First contact timestamp' },
    { value: 'last_contacted_at', label: 'Last Contacted At', description: 'Last contact timestamp' },
    { value: 'first_response_at', label: 'First Response At', description: 'First response timestamp' },
    { value: 'last_response_at', label: 'Last Response At', description: 'Last response timestamp' }
  ]

  const userTypes = [
    { value: 'created_by', label: 'Created By', description: 'User who created the record' },
    { value: 'updated_by', label: 'Updated By', description: 'User who last updated the record' },
    { value: 'assigned_to', label: 'Assigned To', description: 'User assigned to the record' },
    { value: 'first_contacted_by', label: 'First Contacted By', description: 'User who made first contact' },
    { value: 'last_contacted_by', label: 'Last Contacted By', description: 'User who made last contact' },
    { value: 'owner', label: 'Owner', description: 'Record owner' }
  ]

  const countTypes = [
    { value: 'total_communications', label: 'Total Communications', description: 'Total number of communications' },
    { value: 'days_in_pipeline', label: 'Days in Pipeline', description: 'Number of days in current pipeline' },
    { value: 'days_in_stage', label: 'Days in Stage', description: 'Number of days in current stage' },
    { value: 'total_tasks', label: 'Total Tasks', description: 'Total number of tasks' },
    { value: 'completed_tasks', label: 'Completed Tasks', description: 'Number of completed tasks' },
    { value: 'pending_tasks', label: 'Pending Tasks', description: 'Number of pending tasks' }
  ]

  const durationTypes = [
    { value: 'time_to_first_response', label: 'Time to First Response', description: 'Duration from first contact to first response' },
    { value: 'time_to_last_response', label: 'Time to Last Response', description: 'Duration from last contact to last response' },
    { value: 'average_response_time', label: 'Average Response Time', description: 'Average time between contacts and responses' },
    { value: 'stage_duration', label: 'Stage Duration', description: 'Time spent in current stage' },
    { value: 'pipeline_duration', label: 'Pipeline Duration', description: 'Total time in pipeline' },
    { value: 'time_since_last_contact', label: 'Time Since Last Contact', description: 'Duration since last contact' }
  ]

  const statusTypes = [
    { value: 'engagement_status', label: 'Engagement Status', description: 'Level of engagement (high, medium, low)' },
    { value: 'response_status', label: 'Response Status', description: 'Response behavior (responsive, slow, non-responsive)' },
    { value: 'communication_status', label: 'Communication Status', description: 'Communication health status' },
    { value: 'pipeline_status', label: 'Pipeline Status', description: 'Overall pipeline health' },
    { value: 'activity_status', label: 'Activity Status', description: 'Activity level indicator' }
  ]

  const formatOptions = [
    { value: 'relative', label: 'Relative', description: '"2 days ago", "3 hours ago"' },
    { value: 'absolute', label: 'Absolute', description: '"Jan 15, 2024", "14:30"' }
  ]

  const selectedDataType = config.data_type || 'timestamp'

  const getTypeOptions = () => {
    switch (selectedDataType) {
      case 'timestamp': return timestampTypes
      case 'user': return userTypes
      case 'count': return countTypes
      case 'duration': return durationTypes
      case 'status': return statusTypes
      default: return []
    }
  }

  const getTypeConfigKey = () => {
    switch (selectedDataType) {
      case 'timestamp': return 'timestamp_type'
      case 'user': return 'user_type'
      case 'count': return 'count_type'
      case 'duration': return 'duration_type'
      case 'status': return 'status_type'
      default: return ''
    }
  }

  const typeOptions = getTypeOptions()
  const typeConfigKey = getTypeConfigKey()

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">Record Data Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          System-generated field that displays predefined record metadata
        </p>
      </div>

      {/* Data Type Selection */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Data Type</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Choose what type of record data this field will display">
            <Label>Record Data Type</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={selectedDataType}
            onValueChange={(value) => {
              onChange('data_type', value)
              // Clear the specific type when data type changes
              const newTypeKey = value === 'timestamp' ? 'timestamp_type' :
                                value === 'user' ? 'user_type' :
                                value === 'count' ? 'count_type' :
                                value === 'duration' ? 'duration_type' :
                                value === 'status' ? 'status_type' : ''
              if (newTypeKey) {
                onChange(newTypeKey, '')
              }
            }}
            className="space-y-2"
          >
            {dataTypes.map((type) => (
              <div key={type.value} className="flex items-start space-x-3">
                <RadioGroupItem value={type.value} id={`data-type-${type.value}`} className="mt-1" />
                <div className="space-y-1">
                  <Label htmlFor={`data-type-${type.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                    {type.label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{type.description}</p>
                </div>
              </div>
            ))}
          </RadioGroup>
        </div>
      </div>

      {/* Specific Type Configuration */}
      {typeOptions.length > 0 && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">
              {dataTypes.find(t => t.value === selectedDataType)?.label} Type
            </Label>

            <div className="space-y-2">
              <HelpTooltipWrapper helpText={`Select the specific ${selectedDataType} data to display`}>
                <Label>Specific Data</Label>
              </HelpTooltipWrapper>
              
              <Select
                value={config[typeConfigKey] || undefined}
                onValueChange={(value) => onChange(typeConfigKey, value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder={`Select ${selectedDataType} type`} />
                </SelectTrigger>
                <SelectContent>
                  {typeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {config[typeConfigKey] && (
                <p className="text-xs text-muted-foreground">
                  {typeOptions.find(opt => opt.value === config[typeConfigKey])?.description}
                </p>
              )}
            </div>
          </div>
        </>
      )}

      <Separator />

      {/* Display Format */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Display Format</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Choose how the data should be formatted for display">
            <Label>Format Style</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={config.format || 'relative'}
            onValueChange={(value) => onChange('format', value)}
            className="space-y-2"
          >
            {formatOptions.map((format) => (
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

      {/* Time Display (for timestamp and duration types) */}
      {(selectedDataType === 'timestamp' || selectedDataType === 'duration') && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Time Display</Label>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="include-time"
                checked={config.include_time || false}
                onCheckedChange={(checked) => onChange('include_time', checked)}
              />
              <HelpTooltipWrapper helpText="Include time component in addition to date">
                <Label htmlFor="include-time" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                  Include time in display
                </Label>
              </HelpTooltipWrapper>
            </div>
          </div>
        </>
      )}

      {/* Read-only Notice */}
      <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
        <div className="flex items-start gap-2">
          <div className="w-4 h-4 bg-yellow-500 rounded-full flex-shrink-0 mt-0.5"></div>
          <div>
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              System Generated Field
            </p>
            <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
              This field is automatically populated by the system and cannot be edited by users. The data is calculated and updated in real-time based on record activity.
            </p>
          </div>
        </div>
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Record Data Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• Data type: {dataTypes.find(t => t.value === selectedDataType)?.label}</div>
            {config[typeConfigKey] && (
              <div>• Specific data: {typeOptions.find(opt => opt.value === config[typeConfigKey])?.label}</div>
            )}
            <div>• Display format: {formatOptions.find(f => f.value === (config.format || 'relative'))?.label}</div>
            {config.include_time && <div>• Time component included</div>}
            <div>• Read-only system field</div>
          </div>
        </div>
      </div>
    </div>
  )
}