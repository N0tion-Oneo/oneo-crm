'use client'

import { useState, useEffect } from 'react'
import {
  Checkbox,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Separator,
  Textarea
} from '@/components/ui'
import { FieldOption } from '../config-components/FieldOption'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'
import { AlertCircle } from 'lucide-react'

interface ButtonFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
}

export function ButtonFieldConfig({
  config,
  onChange
}: ButtonFieldConfigProps) {
  const buttonStyles = [
    { value: 'primary', label: 'Primary', description: 'Prominent blue button' },
    { value: 'secondary', label: 'Secondary', description: 'Subtle gray button' },
    { value: 'success', label: 'Success', description: 'Green success button' },
    { value: 'warning', label: 'Warning', description: 'Yellow warning button' },
    { value: 'danger', label: 'Danger', description: 'Red destructive button' }
  ]

  const buttonSizes = [
    { value: 'small', label: 'Small', description: 'Compact button size' },
    { value: 'medium', label: 'Medium', description: 'Standard button size' },
    { value: 'large', label: 'Large', description: 'Larger button size' }
  ]

  const userRoles = ['admin', 'manager', 'user', 'viewer']

  const handleRoleToggle = (roleType: 'visible_to_roles' | 'clickable_by_roles', role: string, checked: boolean) => {
    const currentRoles = config[roleType] || []
    const newRoles = checked
      ? [...currentRoles, role]
      : currentRoles.filter((r: string) => r !== role)
    onChange(roleType, newRoles)
  }

  // Validation
  const buttonText = config.button_text?.trim()
  const hasButtonText = Boolean(buttonText)

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">Button Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Interactive button that can trigger workflows and custom actions
        </p>
      </div>

      {/* Button Text (Required) */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Button Configuration</Label>

        <div className="space-y-2">
          <HelpTooltipWrapper helpText="Text displayed on the button (required)">
            <Label>Button Text *</Label>
          </HelpTooltipWrapper>
          
          <Input
            type="text"
            value={config.button_text || ''}
            onChange={(e) => onChange('button_text', e.target.value)}
            placeholder="Send Email, Mark Complete, Approve..."
            className={!hasButtonText ? 'border-red-300 dark:border-red-700' : ''}
          />
          
          {!hasButtonText && (
            <div className="flex items-center gap-1 text-red-600 dark:text-red-400 text-xs">
              <AlertCircle className="h-3 w-3" />
              Button text is required
            </div>
          )}
        </div>
      </div>

      <Separator />

      {/* Button Appearance */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Appearance</Label>

        <div className="grid grid-cols-2 gap-4">
          {/* Button Style */}
          <div className="space-y-2">
            <HelpTooltipWrapper helpText="Visual style of the button">
              <Label>Button Style</Label>
            </HelpTooltipWrapper>
            
            <Select
              value={config.button_style || 'primary'}
              onValueChange={(value) => onChange('button_style', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {buttonStyles.map((style) => (
                  <SelectItem key={style.value} value={style.value}>
                    {style.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Button Size */}
          <div className="space-y-2">
            <HelpTooltipWrapper helpText="Size of the button">
              <Label>Button Size</Label>
            </HelpTooltipWrapper>
            
            <Select
              value={config.button_size || 'medium'}
              onValueChange={(value) => onChange('button_size', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {buttonSizes.map((size) => (
                  <SelectItem key={size.value} value={size.value}>
                    {size.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <Separator />

      {/* Workflow Integration */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Workflow Integration</Label>

        <div className="space-y-3">
          <FieldOption
            label="Workflow ID"
            description="ID of the workflow to trigger when button is clicked"
            type="text"
            value={config.workflow_id || ''}
            onChange={(value) => onChange('workflow_id', value)}
            placeholder="workflow-123, send-email-flow"
          />

          <div className="space-y-2">
            <HelpTooltipWrapper helpText="JSON parameters to pass to the workflow">
              <Label>Workflow Parameters (JSON)</Label>
            </HelpTooltipWrapper>
            
            <Textarea
              value={JSON.stringify(config.workflow_params || {}, null, 2)}
              onChange={(e) => {
                try {
                  const params = JSON.parse(e.target.value || '{}')
                  onChange('workflow_params', params)
                } catch (error) {
                  // Keep the invalid JSON for user to fix
                  onChange('workflow_params', e.target.value)
                }
              }}
              placeholder='{\n  "template": "email_template_1",\n  "priority": "high"\n}'
              className="min-h-[100px] font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              JSON object with parameters to pass to the workflow
            </p>
          </div>
        </div>

        {config.workflow_id && (
          <div className="p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <p className="text-xs text-blue-800 dark:text-blue-200">
              This button will trigger workflow "{config.workflow_id}" when clicked.
            </p>
          </div>
        )}
      </div>

      <Separator />

      {/* Button Behavior */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Behavior</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="require-confirmation"
              checked={config.require_confirmation || false}
              onCheckedChange={(checked) => onChange('require_confirmation', checked)}
            />
            <HelpTooltipWrapper helpText="Show a confirmation dialog before executing the button action">
              <Label htmlFor="require-confirmation" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Require confirmation before action
              </Label>
            </HelpTooltipWrapper>
          </div>

          {config.require_confirmation && (
            <div className="ml-6">
              <FieldOption
                label="Confirmation Message"
                description="Custom message shown in the confirmation dialog"
                type="text"
                value={config.confirmation_message || ''}
                onChange={(value) => onChange('confirmation_message', value)}
                placeholder="Are you sure you want to perform this action?"
              />
            </div>
          )}

          <div className="flex items-center space-x-2">
            <Checkbox
              id="disable-after-click"
              checked={config.disable_after_click || false}
              onCheckedChange={(checked) => onChange('disable_after_click', checked)}
            />
            <HelpTooltipWrapper helpText="Disable the button after it's clicked to prevent duplicate actions">
              <Label htmlFor="disable-after-click" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Disable after click (prevent duplicates)
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      <Separator />

      {/* Role-based Permissions */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Permissions</Label>

        <div className="space-y-4">
          {/* Visibility Roles */}
          <div className="space-y-3">
            <HelpTooltipWrapper helpText="User roles that can see this button. Leave empty to show to all users.">
              <Label>Visible to Roles</Label>
            </HelpTooltipWrapper>
            
            <div className="grid grid-cols-2 gap-2">
              {userRoles.map((role) => (
                <div key={role} className="flex items-center space-x-2">
                  <Checkbox
                    id={`visible-${role}`}
                    checked={(config.visible_to_roles || []).includes(role)}
                    onCheckedChange={(checked) => handleRoleToggle('visible_to_roles', role, !!checked)}
                  />
                  <Label htmlFor={`visible-${role}`} className="text-sm font-normal capitalize">
                    {role}
                  </Label>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Leave unchecked to show button to all users
            </p>
          </div>

          {/* Clickable Roles */}
          <div className="space-y-3">
            <HelpTooltipWrapper helpText="User roles that can click this button. Leave empty to allow all users who can see it.">
              <Label>Clickable by Roles</Label>
            </HelpTooltipWrapper>
            
            <div className="grid grid-cols-2 gap-2">
              {userRoles.map((role) => (
                <div key={role} className="flex items-center space-x-2">
                  <Checkbox
                    id={`clickable-${role}`}
                    checked={(config.clickable_by_roles || []).includes(role)}
                    onCheckedChange={(checked) => handleRoleToggle('clickable_by_roles', role, !!checked)}
                  />
                  <Label htmlFor={`clickable-${role}`} className="text-sm font-normal capitalize">
                    {role}
                  </Label>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Leave unchecked to allow all users who can see the button to click it
            </p>
          </div>
        </div>
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Button Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            {hasButtonText && <div>• Text: "{config.button_text}"</div>}
            <div>• Style: {buttonStyles.find(s => s.value === (config.button_style || 'primary'))?.label}</div>
            <div>• Size: {buttonSizes.find(s => s.value === (config.button_size || 'medium'))?.label}</div>
            {config.workflow_id && <div>• Triggers workflow: {config.workflow_id}</div>}
            {config.require_confirmation && <div>• Confirmation required</div>}
            {config.disable_after_click && <div>• Disables after click</div>}
            {config.visible_to_roles?.length > 0 && <div>• Visible to: {config.visible_to_roles.join(', ')}</div>}
            {config.clickable_by_roles?.length > 0 && <div>• Clickable by: {config.clickable_by_roles.join(', ')}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}