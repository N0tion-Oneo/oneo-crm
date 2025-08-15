import React, { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'
import { api } from '@/lib/api'
import { useAuth } from '@/features/auth/context'

interface UserAssignment {
  user_id: number
  role?: string
  name?: string
  email?: string
  avatar?: string
  assigned_at?: string
  first_name?: string
  last_name?: string
  user_type?: string
  display_name?: string
  display_email?: string
  avatar_url?: string
}

// USER fields store assignments directly as UserAssignment[]

export const UserFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, className, disabled, pipeline_id, record_id, error, context } = props
    const { user } = useAuth() // Use centralized auth system
    
    // Debug logging
    console.log('🧑‍💼 USER FIELD RENDER:', {
      fieldName: field.name,
      pipeline_id,
      record_id,
      hasValue: !!value,
      currentValue: value
    })
    
    const [availableUsers, setAvailableUsers] = useState<any[]>([])
    const [loading, setLoading] = useState(false)
    const [searchTerm, setSearchTerm] = useState('')
    const [showDropdown, setShowDropdown] = useState(false)
    const [filteredUsers, setFilteredUsers] = useState<any[]>([])
    const dropdownRef = useRef<HTMLDivElement>(null)
    
    // Field configuration - streamlined essential options
    const allow_multiple = getFieldConfig(field, 'allow_multiple', true)
    const max_users = getFieldConfig(field, 'max_users', null)
    const default_role = getFieldConfig(field, 'default_role', 'assigned')
    const allowed_roles = getFieldConfig(field, 'allowed_roles', ['assigned', 'owner', 'collaborator', 'reviewer'])
    const show_role_selector = getFieldConfig(field, 'show_role_selector', true)
    const require_role_selection = getFieldConfig(field, 'require_role_selection', false)
    const restrict_to_user_types = getFieldConfig(field, 'restrict_to_user_types', [])
    const display_format = getFieldConfig(field, 'display_format', 'name_with_role')
    const show_user_avatars = getFieldConfig(field, 'show_user_avatars', true)
    const avatar_size = getFieldConfig(field, 'avatar_size', 'small')
    const preserve_assignment_order = getFieldConfig(field, 'preserve_assignment_order', true)
    
    // Parse current value - USER fields store assignments as direct array
    const assignments: UserAssignment[] = Array.isArray(value) ? value : []
    
    // Fetch available users using new pipeline-permission-aware API
    // Load all available users once when component mounts
    const loadAllUsers = async () => {
      console.log('🔧 USER FIELD: loadAllUsers called with pipeline_id:', pipeline_id)
      if (!pipeline_id) {
        console.warn('🧑‍💼 USER FIELD: No pipeline_id provided, loading all users without permission filtering')
        console.log('🧑‍💼 USER FIELD: Props received:', { field: field.name, pipeline_id, record_id })
        // Fall back to loading all users without pipeline permission filtering
        await loadAllUsersWithoutPipelineFilter()
        return
      }
      
      setLoading(true)
      try {
        const params = {
          pipeline_id: pipeline_id.toString(),
          limit: 100, // Load more users initially for better UX
          // Add user type filtering if configured
          ...(restrict_to_user_types.length > 0 && {
            restrict_to_user_types: restrict_to_user_types
          })
        }
        
        console.log('🧑‍💼 USER FIELD: Loading all available users:', {
          pipeline_id,
          params
        })
        
        const response = await api.get('/api/v1/users/autocomplete/', { params })
        
        console.log('✅ USER FIELD: API Response received:', response.data)
        console.log('✅ USER FIELD: Loaded users:', response.data.results?.length || 0, 'users')
        console.log('✅ USER FIELD: Full user list:', response.data.results)
        
        const users = response.data.results || []
        setAvailableUsers(users)
        setFilteredUsers(users) // Initially show all users
        
        console.log('✅ USER FIELD: State updated - availableUsers length:', users.length)
        console.log('✅ USER FIELD: State updated - filteredUsers length:', users.length)
      } catch (error) {
        console.error('❌ USER FIELD: Failed to load users:', error)
        if ((error as any).response) {
          console.error('Error response:', (error as any).response.status, (error as any).response.data)
        }
        setAvailableUsers([])
        setFilteredUsers([])
      } finally {
        setLoading(false)
      }
    }
    
    // Fallback: Load all users without pipeline permission filtering
    const loadAllUsersWithoutPipelineFilter = async () => {
      setLoading(true)
      try {
        // Try the auth endpoint first for all users
        const response = await api.get('/auth/users/')
        console.log('✅ USER FIELD: Loaded all users (no pipeline filter):', response.data?.length || 0, 'users')
        
        const users = (response.data || []).map((user: any) => ({
          user_id: user.id,
          name: user.name || `${user.first_name} ${user.last_name}`.trim(),
          email: user.email,
          first_name: user.first_name,
          last_name: user.last_name,
          user_type: user.user_type || 'Unknown',
          is_active: user.is_active,
          display_name: user.name || `${user.first_name} ${user.last_name}`.trim(),
          display_email: user.email,
          avatar_url: user.avatar_url || null
        }))
        
        setAvailableUsers(users)
        setFilteredUsers(users)
      } catch (error) {
        console.error('❌ USER FIELD: Failed to load all users:', error)
        setAvailableUsers([])
        setFilteredUsers([])
      } finally {
        setLoading(false)
      }
    }
    
    // Filter users based on search term
    const filterUsers = (searchTerm: string) => {
      if (!searchTerm.trim()) {
        setFilteredUsers(availableUsers)
        return
      }
      
      const filtered = availableUsers.filter(user => {
        const searchLower = searchTerm.toLowerCase()
        const name = (user.display_name || user.name || '').toLowerCase()
        const email = (user.display_email || user.email || '').toLowerCase()
        const firstName = (user.first_name || '').toLowerCase()
        const lastName = (user.last_name || '').toLowerCase()
        
        return name.includes(searchLower) || 
               email.includes(searchLower) ||
               firstName.includes(searchLower) ||
               lastName.includes(searchLower)
      })
      
      setFilteredUsers(filtered)
    }
    
    // Load all users when component mounts or pipeline changes
    useEffect(() => {
      // Only load users if authenticated and not in public context
      if (user && context !== 'public') {
        loadAllUsers()
      }
    }, [pipeline_id, user, context])
    
    // Filter users when search term changes
    useEffect(() => {
      filterUsers(searchTerm)
    }, [searchTerm, availableUsers])
    
    // Click outside to close dropdown
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
          setShowDropdown(false)
          setSearchTerm('') // Clear search when closing
        }
      }
      
      if (showDropdown) {
        document.addEventListener('mousedown', handleClickOutside)
        return () => {
          document.removeEventListener('mousedown', handleClickOutside)
        }
      }
    }, [showDropdown])
    
    const handleAddUser = (user: any) => {
      // Check max_users limit
      if (max_users && assignments.length >= max_users && (allow_multiple || assignments.length === 0)) {
        console.warn(`🧑‍💼 USER FIELD: Cannot add user - maximum of ${max_users} users allowed`)
        return
      }

      if (!allow_multiple && assignments.length > 0) {
        // Replace existing user for single selection
        const newAssignment: UserAssignment = {
          user_id: user.user_id,
          role: require_role_selection ? '' : default_role, // Empty role if selection required
          name: user.display_name || user.name,
          email: user.display_email || user.email,
          avatar: user.avatar_url,
          first_name: user.first_name,
          last_name: user.last_name,
          user_type: user.user_type,
          display_name: user.display_name,
          display_email: user.display_email,
          avatar_url: user.avatar_url,
          assigned_at: new Date().toISOString()
        }
        console.log('🟢 USER FIELD: Calling onChange with single assignment:', [newAssignment])
        onChange([newAssignment])
      } else {
        // Add user for multiple selection
        const isAlreadyAssigned = assignments.some(a => a.user_id === user.user_id)
        if (!isAlreadyAssigned) {
          const newAssignment: UserAssignment = {
            user_id: user.user_id,
            role: require_role_selection ? '' : default_role, // Empty role if selection required
            name: user.display_name || user.name,
            email: user.display_email || user.email,
            avatar: user.avatar_url,
            first_name: user.first_name,
            last_name: user.last_name,
            user_type: user.user_type,
            display_name: user.display_name,
            display_email: user.display_email,
            avatar_url: user.avatar_url,
            assigned_at: new Date().toISOString()
          }
          
          let updatedAssignments = [...assignments, newAssignment]
          
          // Apply assignment ordering if preserve_assignment_order is enabled
          if (preserve_assignment_order) {
            updatedAssignments = updatedAssignments.sort((a, b) => {
              const aTime = new Date(a.assigned_at || '').getTime()
              const bTime = new Date(b.assigned_at || '').getTime()
              return bTime - aTime // Most recent first
            })
          }
          
          console.log('🟢 USER FIELD: Calling onChange with multiple assignments:', updatedAssignments)
          onChange(updatedAssignments)
        }
      }
      setSearchTerm('')
      setShowDropdown(false)
    }
    
    const handleRemoveUser = (userId: number) => {
      const updatedAssignments = assignments.filter(a => a.user_id !== userId)
      console.log('🟢 USER FIELD: Calling onChange with removed user:', updatedAssignments)
      onChange(updatedAssignments)
    }
    
    const handleRoleChange = (userId: number, newRole: string) => {
      const updatedAssignments = assignments.map(a => 
        a.user_id === userId ? { ...a, role: newRole as any } : a
      )
      console.log('🟢 USER FIELD: Calling onChange with role change:', updatedAssignments)
      onChange(updatedAssignments)
    }
    
    const getAvatarSizeClass = () => {
      switch (avatar_size) {
        case 'small': return 'w-8 h-8'
        case 'medium': return 'w-10 h-10'
        case 'large': return 'w-12 h-12'
        default: return 'w-8 h-8'
      }
    }

    const renderUserAssignment = (assignment: UserAssignment) => {
      const displayName = assignment.display_name || assignment.name || assignment.email || `User ${assignment.user_id}`
      const hasRequiredRole = !require_role_selection || (assignment.role && assignment.role.trim() !== '')
      
      return (
        <div key={assignment.user_id} className={`flex items-center gap-2 p-2 rounded-lg ${
          hasRequiredRole 
            ? 'bg-blue-50 dark:bg-blue-900/20' 
            : 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800'
        }`}>
          {show_user_avatars && (assignment.avatar_url || assignment.avatar) && (
            <img 
              src={assignment.avatar_url || assignment.avatar} 
              alt={displayName}
              className={`${getAvatarSizeClass()} rounded-full object-cover`}
            />
          )}
          
          <div className="flex-1">
            <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
              {display_format === 'avatar_with_name' && show_user_avatars ? (
                <span className="flex items-center gap-2">
                  {assignment.avatar_url && (
                    <img 
                      src={assignment.avatar_url}
                      alt={displayName}
                      className="w-5 h-5 rounded-full object-cover inline"
                    />
                  )}
                  {displayName}
                </span>
              ) : (
                displayName
              )}
            </div>
            {display_format === 'name_with_role' && assignment.role && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {assignment.role.charAt(0).toUpperCase() + assignment.role.slice(1)}
              </div>
            )}
            {!hasRequiredRole && (
              <div className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                Role selection required
              </div>
            )}
          </div>
          
          {show_role_selector && !disabled && (
            <Select
              value={assignment.role || undefined}
              onValueChange={(value) => handleRoleChange(assignment.user_id, value)}
            >
              <SelectTrigger className={`w-28 text-xs h-7 ${
                require_role_selection && (!assignment.role || assignment.role.trim() === '')
                  ? 'border-amber-300 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 focus:border-amber-500 focus:ring-amber-500'
                  : ''
              }`}>
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                {allowed_roles.map((role: string) => (
                  <SelectItem key={role} value={role}>
                    {role.charAt(0).toUpperCase() + role.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
          {!disabled && (
            <Button
              onClick={() => handleRemoveUser(assignment.user_id)}
              variant="ghost"
              size="sm"
              className="text-red-500 hover:text-red-700 h-6 w-6 p-0"
              type="button"
              title="Remove user"
            >
              ×
            </Button>
          )}
        </div>
      )
    }
    
    return (
      <div className={className}>
        {/* Current assignments */}
        <div className="space-y-2 mb-3">
          {assignments.map(renderUserAssignment)}
          {assignments.length === 0 && (
            <div className="text-gray-500 dark:text-gray-400 text-sm italic">
              No users assigned
            </div>
          )}
        </div>
        
        {/* Add user interface */}
        {!disabled && (allow_multiple || assignments.length === 0) && (!max_users || assignments.length < max_users) && (
          <div className="space-y-2">
            {max_users && assignments.length > 0 && (
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                {assignments.length} of {max_users} users assigned
              </div>
            )}
            <div className="relative" ref={dropdownRef}>
              <Button
                type="button"
                onClick={() => setShowDropdown(!showDropdown)}
                disabled={disabled}
                variant="outline"
                className={`w-full justify-between ${error ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' : ''}`}
              >
                <span className="text-gray-500 dark:text-gray-400">
                  {loading ? 'Loading users...' : `Select user to assign... (${availableUsers.length} available)`}
                </span>
                <svg className={`w-4 h-4 transition-transform ${showDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </Button>
              
              {/* User dropdown */}
              {showDropdown && (
                <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-64 overflow-hidden">
                  {/* Search input inside dropdown */}
                  <div className="p-2 border-b border-gray-200 dark:border-gray-700">
                    <Input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Type to filter users..."
                      className="text-sm"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') {
                          setShowDropdown(false)
                          setSearchTerm('')
                        }
                      }}
                    />
                  </div>
                  
                  {/* User list */}
                  <div className="max-h-48 overflow-y-auto">
                    {loading && (
                      <div className="p-3 text-center text-gray-500">Loading...</div>
                    )}
                    {!loading && filteredUsers.length === 0 && (
                      <div className="p-3 text-center text-gray-500">
                        {searchTerm ? `No users found matching "${searchTerm}"` : 'No users available'}
                        <div className="text-xs mt-1">
                          Available: {availableUsers.length}, Filtered: {filteredUsers.length}
                        </div>
                      </div>
                    )}
                    {!loading && filteredUsers.map((user) => {
                      // Don't show already assigned users
                      const isAlreadyAssigned = assignments.some(a => a.user_id === user.user_id)
                      if (isAlreadyAssigned) return null
                      
                      return (
                        <div
                          key={user.user_id}
                          onClick={(e) => {
                            console.log('🔵 USER OPTION CLICKED:', user.display_name || user.name)
                            e.preventDefault()
                            e.stopPropagation()
                            handleAddUser(user)
                          }}
                          onMouseDown={(e) => {
                            console.log('🟡 USER OPTION MOUSE DOWN:', user.display_name || user.name)
                          }}
                          className="w-full text-left px-3 py-2 hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-2 transition-colors cursor-pointer"
                        >
                          {show_user_avatars && user.avatar_url && (
                            <img 
                              src={user.avatar_url} 
                              alt={user.display_name || user.name}
                              className="w-6 h-6 rounded-full"
                            />
                          )}
                          <div className="flex-1">
                            <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
                              {user.display_name || user.name}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              {user.display_email || user.email}
                              {user.user_type && (
                                <span className="ml-1 text-blue-600 dark:text-blue-400">({user.user_type})</span>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Error display - consistent with other field types */}
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    const assignments: UserAssignment[] = Array.isArray(value) ? value : []
    
    if (assignments.length === 0) {
      if (context === 'table') {
        return <span className="text-gray-400 italic">—</span>
      }
      return 'No users assigned'
    }
    const display_format = getFieldConfig(field, 'display_format', 'name_with_role')
    const max_displayed_users = getFieldConfig(field, 'max_displayed_users', 5)
    
    const visibleAssignments = assignments.slice(0, max_displayed_users)
    const remainingCount = assignments.length - max_displayed_users
    
    if (context === 'table') {
      return (
        <div className="flex items-center gap-1 flex-wrap">
          {visibleAssignments.map((assignment: UserAssignment, index: number) => {
            const displayName = assignment.name || assignment.email || `User ${assignment.user_id}`
            const roleText = display_format === 'name_with_role' && assignment.role 
              ? ` (${assignment.role})` 
              : ''
            
            return (
              <span 
                key={assignment.user_id}
                className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
              >
                {displayName}{roleText}
              </span>
            )
          })}
          {remainingCount > 0 && (
            <span className="text-xs text-gray-500">
              +{remainingCount} more
            </span>
          )}
        </div>
      )
    }
    
    // Detail view format
    return visibleAssignments.map((assignment: UserAssignment) => {
      const displayName = assignment.name || assignment.email || `User ${assignment.user_id}`
      const roleText = display_format === 'name_with_role' && assignment.role 
        ? ` (${assignment.role})` 
        : ''
      return displayName + roleText
    }).join(', ') + (remainingCount > 0 ? ` and ${remainingCount} more` : '')
  },

  validate: (value: any, field: Field): ValidationResult => {
    const assignments: UserAssignment[] = Array.isArray(value) ? value : []
    
    if (assignments.length === 0) {
      return { isValid: true }
    }
    const allow_multiple = getFieldConfig(field, 'allow_multiple', true)
    const max_users = getFieldConfig(field, 'max_users', null)
    const allowed_roles = getFieldConfig(field, 'allowed_roles', ['assigned', 'owner', 'collaborator', 'reviewer'])
    const require_role_selection = getFieldConfig(field, 'require_role_selection', false)
    
    // Check if single selection constraint is violated
    if (!allow_multiple && assignments.length > 1) {
      return {
        isValid: false,
        error: 'Only one user can be assigned to this field'
      }
    }
    
    // Check max users constraint
    if (max_users && assignments.length > max_users) {
      return {
        isValid: false,
        error: `Maximum of ${max_users} users allowed, but ${assignments.length} are assigned`
      }
    }
    
    // Validate each assignment
    for (const assignment of assignments) {
      if (!assignment.user_id || typeof assignment.user_id !== 'number') {
        return {
          isValid: false,
          error: 'Invalid user ID in assignment'
        }
      }
      
      // Check role requirement
      if (require_role_selection && (!assignment.role || assignment.role.trim() === '')) {
        return {
          isValid: false,
          error: 'Role selection is required for all user assignments'
        }
      }
      
      // Check allowed roles
      if (assignment.role && assignment.role.trim() !== '' && !allowed_roles.includes(assignment.role)) {
        return {
          isValid: false,
          error: `Invalid role: ${assignment.role}. Allowed roles: ${allowed_roles.join(', ')}`
        }
      }
    }
    
    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    return []
  },

  isEmpty: (value: any) => {
    return !Array.isArray(value) || value.length === 0
  }
}