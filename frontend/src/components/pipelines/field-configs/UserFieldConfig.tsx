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

interface UserFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
}

const availableRoles = [
  { value: 'assigned', label: 'Assigned' },
  { value: 'owner', label: 'Owner' },
  { value: 'collaborator', label: 'Collaborator' },
  { value: 'reviewer', label: 'Reviewer' }
]

export function UserFieldConfig({
  config,
  onChange
}: UserFieldConfigProps) {
  const handleRoleToggle = (role: string, checked: boolean) => {
    const currentRoles = config.allowed_roles || ['assigned', 'owner', 'collaborator', 'reviewer']
    const newRoles = checked
      ? [...currentRoles, role]
      : currentRoles.filter((r: string) => r !== role)
    onChange('allowed_roles', newRoles)
  }

  return (
    <div className="space-y-6">
      {/* Assignment Configuration */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Assignment Configuration</Label>
        
        <div className="flex items-center space-x-2">
          <Checkbox
            id="allow-multiple"
            checked={config.allow_multiple !== false}
            onCheckedChange={(checked) => onChange('allow_multiple', checked)}
          />
          <HelpTooltipWrapper helpText="Allow multiple users to be assigned to this field simultaneously">
            <Label htmlFor="allow-multiple" className="text-sm font-normal text-gray-700 dark:text-gray-300">
              Allow Multiple Users
            </Label>
          </HelpTooltipWrapper>
        </div>

        <FieldOption
          label="Maximum Users"
          description="Maximum number of users that can be assigned (leave empty for unlimited)"
          helpText="Set a limit on how many users can be assigned to this field. Leave empty for no limit."
          type="number"
          value={config.max_users || ''}
          onChange={(value) => onChange('max_users', value ? parseInt(value.toString()) : null)}
          placeholder="No limit"
        />
      </div>

      <Separator />

      {/* Role Configuration */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Role Configuration</Label>

        <div className="space-y-2">
          <HelpTooltipWrapper helpText="The default role assigned when no specific role is selected">
            <Label htmlFor="default-role">Default Role</Label>
          </HelpTooltipWrapper>
          <Select
            value={config.default_role || 'assigned'}
            onValueChange={(value) => onChange('default_role', value)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {availableRoles.map((role) => (
                <SelectItem key={role.value} value={role.value}>
                  {role.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Default role assigned to users when no role is specified
          </p>
        </div>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Select which roles users can be assigned in this field">
            <Label>Allowed Roles</Label>
          </HelpTooltipWrapper>
          
          <div className="space-y-2">
            {availableRoles.map((role) => (
              <div key={role.value} className="flex items-center space-x-2">
                <Checkbox
                  id={`role-${role.value}`}
                  checked={(config.allowed_roles || ['assigned', 'owner', 'collaborator', 'reviewer']).includes(role.value)}
                  onCheckedChange={(checked) => handleRoleToggle(role.value, !!checked)}
                />
                <Label htmlFor={`role-${role.value}`} className="text-sm font-normal capitalize">
                  {role.label}
                </Label>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Roles that can be assigned to users for this field
          </p>
        </div>
      </div>

      <Separator />

      {/* Display Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Display Options</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="show-role-selector"
              checked={config.show_role_selector !== false}
              onCheckedChange={(checked) => onChange('show_role_selector', checked)}
            />
            <HelpTooltipWrapper helpText="Display a role selector when assigning users to this field">
              <Label htmlFor="show-role-selector" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Show Role Selector
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="require-role-selection"
              checked={config.require_role_selection || false}
              onCheckedChange={(checked) => onChange('require_role_selection', checked)}
            />
            <HelpTooltipWrapper helpText="Require users to select a role when assigning users (only applies if role selector is shown)">
              <Label htmlFor="require-role-selection" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Require Role Selection
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="show-user-avatars"
              checked={config.show_user_avatars !== false}
              onCheckedChange={(checked) => onChange('show_user_avatars', checked)}
            />
            <HelpTooltipWrapper helpText="Display user profile pictures in the assignment display">
              <Label htmlFor="show-user-avatars" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Show User Avatars
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">User Assignment Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• {config.allow_multiple !== false ? 'Multiple users allowed' : 'Single user only'}</div>
            {config.max_users && <div>• Maximum: {config.max_users} users</div>}
            <div>• Default role: {availableRoles.find(r => r.value === (config.default_role || 'assigned'))?.label}</div>
            <div>• Available roles: {(config.allowed_roles || ['assigned', 'owner', 'collaborator', 'reviewer']).length}</div>
          </div>
        </div>
      </div>
    </div>
  )
}