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

      {/* User Type Filtering */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">User Filtering</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Restrict field to specific user types. Leave empty to allow all user types.">
            <Label>Restrict to User Types (Optional)</Label>
          </HelpTooltipWrapper>
          
          <div className="p-3 border rounded-md bg-muted/20">
            <p className="text-xs text-muted-foreground mb-2">
              Select user types that can be assigned to this field. Leave empty to allow all user types.
            </p>
            
            {['admin', 'manager', 'user', 'viewer'].map((userType) => (
              <div key={userType} className="flex items-center space-x-2">
                <Checkbox
                  id={`user-type-${userType}`}
                  checked={(config.restrict_to_user_types || []).includes(userType)}
                  onCheckedChange={(checked) => {
                    const currentTypes = config.restrict_to_user_types || []
                    const newTypes = checked 
                      ? [...currentTypes, userType]
                      : currentTypes.filter((t: string) => t !== userType)
                    onChange('restrict_to_user_types', newTypes)
                  }}
                />
                <Label htmlFor={`user-type-${userType}`} className="text-sm font-normal capitalize">
                  {userType}
                </Label>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Separator />

      {/* Display Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Display Configuration</Label>

        <div className="space-y-4">
          {/* Display Format */}
          <div className="space-y-2">
            <HelpTooltipWrapper helpText="Choose how user assignments are displayed">
              <Label>Display Format</Label>
            </HelpTooltipWrapper>
            <Select
              value={config.display_format || 'name_with_role'}
              onValueChange={(value) => onChange('display_format', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="name_only">Name Only</SelectItem>
                <SelectItem value="name_with_role">Name with Role</SelectItem>
                <SelectItem value="avatar_with_name">Avatar with Name</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Avatar Settings */}
          <div className="space-y-3">
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

            {config.show_user_avatars !== false && (
              <div className="ml-6 space-y-2">
                <HelpTooltipWrapper helpText="Size of user avatar images">
                  <Label>Avatar Size</Label>
                </HelpTooltipWrapper>
                <Select
                  value={config.avatar_size || 'small'}
                  onValueChange={(value) => onChange('avatar_size', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="small">Small</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="large">Large</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          {/* Role Selector Options */}
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

            {config.show_role_selector !== false && (
              <div className="ml-6">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="require-role-selection"
                    checked={config.require_role_selection || false}
                    onCheckedChange={(checked) => onChange('require_role_selection', checked)}
                  />
                  <HelpTooltipWrapper helpText="Require users to select a role when assigning users">
                    <Label htmlFor="require-role-selection" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      Require Role Selection
                    </Label>
                  </HelpTooltipWrapper>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <Separator />

      {/* Assignment Behavior */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Assignment Behavior</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="auto-assign-creator"
              checked={config.auto_assign_creator || false}
              onCheckedChange={(checked) => onChange('auto_assign_creator', checked)}
            />
            <HelpTooltipWrapper helpText="Automatically assign the record creator when a new record is created">
              <Label htmlFor="auto-assign-creator" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Auto-assign record creator
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="preserve-assignment-order"
              checked={config.preserve_assignment_order !== false}
              onCheckedChange={(checked) => onChange('preserve_assignment_order', checked)}
            />
            <HelpTooltipWrapper helpText="Maintain the order of user assignments based on when they were added">
              <Label htmlFor="preserve-assignment-order" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Preserve assignment order
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
            {config.restrict_to_user_types?.length > 0 && <div>• Restricted to: {config.restrict_to_user_types.join(', ')} user types</div>}
            <div>• Display format: {config.display_format || 'name_with_role'}</div>
            {config.show_user_avatars !== false && <div>• Avatar size: {config.avatar_size || 'small'}</div>}
            {config.auto_assign_creator && <div>• Auto-assign creator enabled</div>}
            {config.preserve_assignment_order !== false && <div>• Assignment order preserved</div>}
          </div>
        </div>
      </div>
    </div>
  )
}