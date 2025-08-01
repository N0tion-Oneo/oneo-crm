'use client'

import { useState, useEffect } from 'react'
import { X, Shield, Check, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/features/auth/context'

interface User {
  id: number
  first_name: string
  last_name: string
  full_name: string
  email: string
  user_type_name: string
  is_active: boolean
}

interface UserPermissions {
  [category: string]: string[]
}

interface UserPermissionModalProps {
  user: User | null
  isOpen: boolean
  onClose: () => void
  onUserUpdated: () => void
}

export default function UserPermissionModal({ user, isOpen, onClose, onUserUpdated }: UserPermissionModalProps) {
  const { hasPermission } = useAuth()
  const [permissions, setPermissions] = useState<UserPermissions>({})
  const [userType, setUserType] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [pendingChanges, setPendingChanges] = useState<UserPermissions>({})

  // Permission categories with friendly names
  const permissionCategories = {
    system: 'System Administration',
    users: 'User Management',
    user_types: 'User Type Management',
    pipelines: 'Pipeline Management',
    records: 'Record Management',
    fields: 'Field Management',
    relationships: 'Relationship Management',
    workflows: 'Workflow Management',
    communications: 'Communication Management',
    settings: 'System Settings',
    monitoring: 'System Monitoring',
    ai_features: 'AI Features',
    reports: 'Reports & Analytics',
    api_access: 'API Access'
  }

  // Action display names
  const actionNames = {
    create: 'Create',
    read: 'Read',
    update: 'Update',
    delete: 'Delete',
    execute: 'Execute',
    export: 'Export',
    import: 'Import',
    clone: 'Clone',
    configure: 'Configure',
    send: 'Send',
    traverse: 'Traverse',
    bulk_edit: 'Bulk Edit',
    impersonate: 'Impersonate',
    assign_roles: 'Assign Roles',
    full_access: 'Full Access',
    read_all: 'Read All',
    write: 'Write'
  }

  // Load user permissions
  useEffect(() => {
    if (isOpen && user) {
      loadUserPermissions()
    }
  }, [isOpen, user])

  const loadUserPermissions = async () => {
    if (!user) return

    setLoading(true)
    setError(null)
    
    try {
      const response = await api.get(`/auth/users/${user.id}/permissions/`)
      setPermissions(response.data.permissions || {})
      setUserType(response.data.user_type || '')
      setPendingChanges({})
    } catch (error: any) {
      console.error('Failed to load user permissions:', error)
      setError('Failed to load user permissions')
    } finally {
      setLoading(false)
    }
  }

  const togglePermission = (category: string, action: string) => {
    if (!editMode) return

    const updatedChanges = { ...pendingChanges }
    
    if (!updatedChanges[category]) {
      updatedChanges[category] = [...(permissions[category] || [])]
    }

    const hasPermissionInChanges = updatedChanges[category].includes(action)
    
    if (hasPermissionInChanges) {
      updatedChanges[category] = updatedChanges[category].filter(a => a !== action)
    } else {
      updatedChanges[category] = [...updatedChanges[category], action]
    }

    setPendingChanges(updatedChanges)
  }

  const hasPermissionInState = (category: string, action: string): boolean => {
    if (editMode && pendingChanges[category]) {
      return pendingChanges[category].includes(action)
    }
    return permissions[category]?.includes(action) || false
  }

  const saveChanges = async () => {
    if (!user) return

    setLoading(true)
    setError(null)

    try {
      await api.post(`/auth/users/${user.id}/update_permission_overrides/`, {
        permission_overrides: pendingChanges
      })
      
      // Reload permissions to get the updated state
      await loadUserPermissions()
      setEditMode(false)
      onUserUpdated()
    } catch (error: any) {
      console.error('Failed to update permissions:', error)
      setError('Failed to update permissions')
    } finally {
      setLoading(false)
    }
  }

  const cancelChanges = () => {
    setPendingChanges({})
    setEditMode(false)
  }

  const getAllActions = (): string[] => {
    const allActions = new Set<string>()
    Object.values(permissions).forEach(actions => {
      actions.forEach(action => allActions.add(action))
    })
    return Array.from(allActions).sort()
  }

  if (!isOpen || !user) return null

  const canEditPermissions = hasPermission('users', 'update')

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-screen overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <Shield className="w-6 h-6 text-blue-500 mr-3" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                User Permissions
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {user.full_name} ({user.email}) - {userType}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {canEditPermissions && !editMode && (
              <button
                onClick={() => setEditMode(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
              >
                Edit Permissions
              </button>
            )}
            {editMode && (
              <>
                <button
                  onClick={saveChanges}
                  disabled={loading}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors text-sm disabled:opacity-50"
                >
                  Save Changes
                </button>
                <button
                  onClick={cancelChanges}
                  className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors text-sm"
                >
                  Cancel
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 max-h-96 overflow-y-auto">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600 dark:text-gray-400">Loading permissions...</span>
            </div>
          )}

          {error && (
            <div className="flex items-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg mb-6">
              <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
              <span className="text-red-700 dark:text-red-400">{error}</span>
            </div>
          )}

          {editMode && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
              <div className="flex items-center">
                <AlertCircle className="w-5 h-5 text-yellow-500 mr-2" />
                <span className="text-yellow-800 dark:text-yellow-200 text-sm">
                  You are editing permission overrides. These will be applied on top of the user's base permissions from their user type.
                </span>
              </div>
            </div>
          )}

          {!loading && !error && (
            <div className="space-y-6">
              {Object.entries(permissionCategories).map(([category, categoryName]) => {
                const categoryPermissions = permissions[category] || []
                const allActionsForCategory = getAllActions().filter(action => 
                  Object.values(permissions).some(perms => perms.includes(action))
                )

                if (categoryPermissions.length === 0 && !editMode) return null

                return (
                  <div key={category} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center">
                      <Shield className="w-4 h-4 mr-2 text-gray-500" />
                      {categoryName}
                      <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                        ({categoryPermissions.length} permissions)
                      </span>
                    </h3>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                      {allActionsForCategory.map(action => {
                        const hasPermissionValue = hasPermissionInState(category, action)
                        const isInOriginal = permissions[category]?.includes(action) || false
                        const isChanged = editMode && pendingChanges[category] && 
                          (pendingChanges[category].includes(action) !== isInOriginal)

                        return (
                          <div
                            key={action}
                            className={`flex items-center p-2 rounded border ${
                              editMode 
                                ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700' 
                                : ''
                            } ${
                              hasPermissionValue 
                                ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' 
                                : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                            } ${
                              isChanged ? 'ring-2 ring-blue-500' : ''
                            }`}
                            onClick={() => editMode && togglePermission(category, action)}
                          >
                            <div className={`w-4 h-4 rounded border-2 mr-2 flex items-center justify-center ${
                              hasPermissionValue 
                                ? 'bg-green-500 border-green-500' 
                                : 'border-gray-300 dark:border-gray-600'
                            }`}>
                              {hasPermissionValue && (
                                <Check className="w-3 h-3 text-white" />
                              )}
                            </div>
                            <span className={`text-sm ${
                              hasPermissionValue 
                                ? 'text-green-800 dark:text-green-200' 
                                : 'text-gray-600 dark:text-gray-400'
                            }`}>
                              {actionNames[action as keyof typeof actionNames] || action}
                            </span>
                            {isChanged && (
                              <span className="ml-auto text-xs text-blue-600 dark:text-blue-400">
                                Changed
                              </span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}