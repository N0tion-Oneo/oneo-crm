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

interface BooleanFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
}

export function BooleanFieldConfig({
  config,
  onChange
}: BooleanFieldConfigProps) {
  const displayOptions = [
    { value: 'checkbox', label: 'Checkbox', description: 'Traditional checkbox input' },
    { value: 'toggle', label: 'Toggle Switch', description: 'Modern toggle switch' },
    { value: 'radio', label: 'Radio Buttons', description: 'Yes/No radio button pair' },
    { value: 'select', label: 'Dropdown', description: 'Yes/No dropdown selection' }
  ]

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">Boolean Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          True/false value with customizable display options
        </p>
      </div>

      {/* Display Configuration */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Display Options</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Choose how the boolean field should be displayed to users">
            <Label>Display As</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={config.display_as || 'checkbox'}
            onValueChange={(value) => onChange('display_as', value)}
            className="space-y-2"
          >
            {displayOptions.map((option) => (
              <div key={option.value} className="flex items-start space-x-3">
                <RadioGroupItem value={option.value} id={option.value} className="mt-1" />
                <div className="space-y-1">
                  <Label htmlFor={option.value} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                    {option.label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{option.description}</p>
                </div>
              </div>
            ))}
          </RadioGroup>
        </div>
      </div>

      <Separator />

      {/* Default Value */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Default Value</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="The default value for new records">
            <Label>Default State</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={config.default_value?.toString() || 'false'}
            onValueChange={(value) => onChange('default_value', value === 'true')}
            className="flex space-x-6"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="false" id="default-false" />
              <Label htmlFor="default-false" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                False (unchecked)
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="true" id="default-true" />
              <Label htmlFor="default-true" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                True (checked)
              </Label>
            </div>
          </RadioGroup>
        </div>
      </div>

      <Separator />

      {/* Custom Labels */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Custom Labels</Label>

        <div className="grid grid-cols-2 gap-4">
          <FieldOption
            label="True Label"
            description="Custom label for true/checked state"
            type="text"
            value={config.true_label || ''}
            onChange={(value) => onChange('true_label', value)}
            placeholder="Yes, True, Enabled..."
          />

          <FieldOption
            label="False Label"
            description="Custom label for false/unchecked state"
            type="text"
            value={config.false_label || ''}
            onChange={(value) => onChange('false_label', value)}
            placeholder="No, False, Disabled..."
          />
        </div>

        <p className="text-xs text-muted-foreground">
          Leave empty to use default labels (True/False)
        </p>
      </div>

      <Separator />

      {/* Advanced Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Advanced Options</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="show-label"
              checked={config.show_label !== false}
              onCheckedChange={(checked) => onChange('show_label', checked)}
            />
            <HelpTooltipWrapper helpText="Show the field label next to the input">
              <Label htmlFor="show-label" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Show field label
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="inline-display"
              checked={config.inline_display || false}
              onCheckedChange={(checked) => onChange('inline_display', checked)}
            />
            <HelpTooltipWrapper helpText="Display the field inline with other form elements">
              <Label htmlFor="inline-display" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Inline display
              </Label>
            </HelpTooltipWrapper>
          </div>

          {(config.display_as === 'radio' || config.display_as === 'select') && (
            <div className="flex items-center space-x-2">
              <Checkbox
                id="allow-null"
                checked={config.allow_null || false}
                onCheckedChange={(checked) => onChange('allow_null', checked)}
              />
              <HelpTooltipWrapper helpText="Allow empty/unselected state (third option)">
                <Label htmlFor="allow-null" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                  Allow empty state
                </Label>
              </HelpTooltipWrapper>
            </div>
          )}
        </div>
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Boolean Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• Display as: {displayOptions.find(opt => opt.value === (config.display_as || 'checkbox'))?.label}</div>
            <div>• Default value: {config.default_value ? 'True' : 'False'}</div>
            {config.true_label && <div>• True label: "{config.true_label}"</div>}
            {config.false_label && <div>• False label: "{config.false_label}"</div>}
            {config.allow_null && <div>• Empty state allowed</div>}
          </div>
        </div>
      </div>
    </div>
  )
}