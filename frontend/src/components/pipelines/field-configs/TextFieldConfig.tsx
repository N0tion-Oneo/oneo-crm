'use client'

import {
  Checkbox,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Separator
} from '@/components/ui'
import { FieldOption } from '../config-components/FieldOption'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'

interface TextFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
  fieldType: 'text' | 'textarea' | 'email' | 'url'
}

export function TextFieldConfig({
  config,
  onChange,
  fieldType
}: TextFieldConfigProps) {
  const getFieldTypeInfo = () => {
    switch (fieldType) {
      case 'text':
        return {
          title: 'Text Field',
          description: 'Single-line text input',
          showTextSettings: true,
          showLengthSettings: true
        }
      case 'textarea':
        return {
          title: 'Textarea Field',
          description: 'Multi-line text input',
          showTextSettings: true,
          showLengthSettings: true,
          showRowSettings: true
        }
      case 'email':
        return {
          title: 'Email Field',
          description: 'Email address input with validation',
          showTextSettings: false,
          showLengthSettings: true,
          showEmailSettings: true
        }
      case 'url':
        return {
          title: 'URL Field',
          description: 'Website URL input with validation',
          showTextSettings: false,
          showLengthSettings: true,
          showUrlSettings: true
        }
      default:
        return {
          title: 'Text Field',
          description: 'Text input field',
          showTextSettings: true,
          showLengthSettings: true
        }
    }
  }

  const fieldInfo = getFieldTypeInfo()

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">{fieldInfo.title}</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {fieldInfo.description}
        </p>
      </div>

      {/* Basic Configuration */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Basic Settings</Label>

        <FieldOption
          label="Default Value"
          description="Default value when creating new records"
          type="text"
          value={config.default_value || ''}
          onChange={(value) => onChange('default_value', value)}
          placeholder="Enter default value..."
        />

        <FieldOption
          label="Placeholder Text"
          description="Hint text shown when the field is empty"
          type="text"
          value={config.placeholder || ''}
          onChange={(value) => onChange('placeholder', value)}
          placeholder="Enter placeholder text..."
        />
      </div>

      {/* Length Settings */}
      {fieldInfo.showLengthSettings && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Length Constraints</Label>

            <div className="grid grid-cols-2 gap-4">
              <FieldOption
                label="Minimum Length"
                description="Minimum number of characters"
                type="number"
                value={config.min_length || ''}
                onChange={(value) => onChange('min_length', value)}
              />

              <FieldOption
                label="Maximum Length"
                description="Maximum number of characters"
                type="number"
                value={config.max_length || ''}
                onChange={(value) => onChange('max_length', value)}
              />
            </div>
          </div>
        </>
      )}

      {/* Text-specific Settings */}
      {fieldInfo.showTextSettings && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Text Options</Label>

            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="case-sensitive"
                  checked={config.case_sensitive !== false}
                  onCheckedChange={(checked) => onChange('case_sensitive', checked)}
                />
                <HelpTooltipWrapper helpText="Whether text comparison should be case-sensitive">
                  <Label htmlFor="case-sensitive" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Case sensitive
                  </Label>
                </HelpTooltipWrapper>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="auto-format"
                  checked={config.auto_format || false}
                  onCheckedChange={(checked) => onChange('auto_format', checked)}
                />
                <HelpTooltipWrapper helpText="Automatically format text as user types (capitalize, trim spaces, etc.)">
                  <Label htmlFor="auto-format" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Auto-format text
                  </Label>
                </HelpTooltipWrapper>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="trim-whitespace"
                  checked={config.trim_whitespace !== false}
                  onCheckedChange={(checked) => onChange('trim_whitespace', checked)}
                />
                <HelpTooltipWrapper helpText="Remove leading and trailing spaces when saving">
                  <Label htmlFor="trim-whitespace" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Trim whitespace
                  </Label>
                </HelpTooltipWrapper>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Textarea-specific Settings */}
      {fieldInfo.showRowSettings && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Textarea Display</Label>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="enable-rich-text"
                checked={config.enable_rich_text || false}
                onCheckedChange={(checked) => onChange('enable_rich_text', checked)}
              />
              <HelpTooltipWrapper helpText="Enable rich text editor with formatting options">
                <Label htmlFor="enable-rich-text" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                  Enable rich text editor
                </Label>
              </HelpTooltipWrapper>
            </div>
          </div>
        </>
      )}

      {/* Email-specific Settings */}
      {fieldInfo.showEmailSettings && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Email Validation</Label>

            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="auto-lowercase"
                  checked={config.auto_lowercase !== false}
                  onCheckedChange={(checked) => onChange('auto_lowercase', checked)}
                />
                <HelpTooltipWrapper helpText="Automatically convert email addresses to lowercase">
                  <Label htmlFor="auto-lowercase" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Convert to lowercase
                  </Label>
                </HelpTooltipWrapper>
              </div>
            </div>
          </div>
        </>
      )}

      {/* URL-specific Settings */}
      {fieldInfo.showUrlSettings && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">URL Display & Behavior</Label>

            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="open-in-new-tab"
                  checked={config.open_in_new_tab !== false}
                  onCheckedChange={(checked) => onChange('open_in_new_tab', checked)}
                />
                <HelpTooltipWrapper helpText="Open URLs in new tab/window when clicked">
                  <Label htmlFor="open-in-new-tab" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Open in new tab
                  </Label>
                </HelpTooltipWrapper>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="show-favicon"
                  checked={config.show_favicon || false}
                  onCheckedChange={(checked) => onChange('show_favicon', checked)}
                />
                <HelpTooltipWrapper helpText="Display the website favicon next to the URL">
                  <Label htmlFor="show-favicon" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Show favicon
                  </Label>
                </HelpTooltipWrapper>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="preview-on-hover"
                  checked={config.preview_on_hover || false}
                  onCheckedChange={(checked) => onChange('preview_on_hover', checked)}
                />
                <HelpTooltipWrapper helpText="Show URL preview tooltip when hovering">
                  <Label htmlFor="preview-on-hover" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Preview on hover
                  </Label>
                </HelpTooltipWrapper>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="auto-add-protocol"
                  checked={config.auto_add_protocol !== false}
                  onCheckedChange={(checked) => onChange('auto_add_protocol', checked)}
                />
                <HelpTooltipWrapper helpText="Automatically add http:// to URLs without protocol">
                  <Label htmlFor="auto-add-protocol" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Auto-add protocol
                  </Label>
                </HelpTooltipWrapper>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">{fieldInfo.title} Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            {config.min_length && <div>• Minimum length: {config.min_length} characters</div>}
            {config.max_length && <div>• Maximum length: {config.max_length} characters</div>}
            {fieldType === 'textarea' && <div>• Rows: {config.rows || 4}</div>}
            {config.default_value && <div>• Default value: "{config.default_value}"</div>}
            {fieldType === 'email' && config.strict_validation !== false && <div>• Strict email validation enabled</div>}
            {fieldType === 'url' && config.require_protocol !== false && <div>• Protocol required</div>}
          </div>
        </div>
      </div>
    </div>
  )
}