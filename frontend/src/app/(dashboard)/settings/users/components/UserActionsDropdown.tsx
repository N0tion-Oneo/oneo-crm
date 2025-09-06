'use client'

import { useState, useRef, useEffect } from 'react'
import { MoreHorizontal, Edit, Shield, Mail, Trash2, UserCheck, UserX, Key, Briefcase } from 'lucide-react'
import { api } from '@/lib/api'
import UserPermissionModal from './UserPermissionModal'

interface User {
  id: number
  first_name: string
  last_name: string
  full_name: string
  email: string
  user_type_name: string
  is_active: boolean
  last_login: string | null
  date_joined: string
}

interface UserActionsDropdownProps {
  user: User
  onUserUpdated: () => void
  onEditUser: (user: User) => void
  onViewStaffProfile: (user: User) => void
  canEdit?: boolean  // Whether user has permission to edit/manage users
  canUpdate?: boolean  // Specific update permission
  canDelete?: boolean  // Specific delete permission
  canAssignRoles?: boolean  // Can assign roles to users
  canImpersonate?: boolean  // Can impersonate users
  isOwnUser?: boolean  // Is this the current user's own account
}

export default function UserActionsDropdown({ 
  user, 
  onUserUpdated, 
  onEditUser, 
  onViewStaffProfile, 
  canEdit = true, 
  canUpdate = canEdit, 
  canDelete = canEdit,
  canAssignRoles = false,
  canImpersonate = false,
  isOwnUser = false
}: UserActionsDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [showPermissionModal, setShowPermissionModal] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleActivateUser = async () => {
    setLoading(true)
    try {
      console.log('🔄 Attempting to activate user:', user.id)
      console.log('🔄 API endpoint:', `/auth/users/${user.id}/activate/`)
      
      const response = await api.post(`/auth/users/${user.id}/activate/`)
      console.log('✅ Activate response:', response.data)
      console.log('✅ User is now active:', response.data.is_active)
      
      onUserUpdated()
      setIsOpen(false)
      alert('User activated successfully')
    } catch (error: any) {
      console.error('❌ Failed to activate user:', error)
      console.error('❌ Error details:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
        config: error.config
      })
      
      let errorMessage = 'Failed to activate user'
      if (error.response?.status === 401) {
        errorMessage = 'Authentication failed. Please log in again.'
      } else if (error.response?.status === 403) {
        errorMessage = 'Permission denied. You do not have permission to activate users.'
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      }
      
      alert(`${errorMessage}\n\nCheck the browser console for detailed error information.`)
    } finally {
      setLoading(false)
    }
  }

  const handleDeactivateUser = async () => {
    if (!window.confirm('Are you sure you want to deactivate this user? They will not be able to login.')) {
      return
    }

    setLoading(true)
    try {
      console.log('🔄 Attempting to deactivate user:', user.id)
      console.log('🔄 API endpoint:', `/auth/users/${user.id}/deactivate/`)
      
      const response = await api.post(`/auth/users/${user.id}/deactivate/`)
      console.log('✅ Deactivate response:', response.data)
      console.log('✅ User is now active:', response.data.is_active)
      
      onUserUpdated()
      setIsOpen(false)
      alert('User deactivated successfully')
    } catch (error: any) {
      console.error('❌ Failed to deactivate user:', error)
      console.error('❌ Error details:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
        config: error.config
      })
      
      let errorMessage = 'Failed to deactivate user'
      if (error.response?.status === 401) {
        errorMessage = 'Authentication failed. Please log in again.'
      } else if (error.response?.status === 403) {
        errorMessage = 'Permission denied. You do not have permission to deactivate users.'
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      }
      
      alert(`${errorMessage}\n\nCheck the browser console for detailed error information.`)
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async () => {
    const newPassword = window.prompt('Enter new password for this user:')
    if (!newPassword) {
      return
    }

    if (newPassword.length < 8) {
      alert('Password must be at least 8 characters long')
      return
    }

    setLoading(true)
    try {
      await api.post(`/auth/users/${user.id}/reset_password/`, {
        new_password: newPassword
      })
      alert('Password reset successfully')
      setIsOpen(false)
    } catch (error) {
      console.error('Failed to reset password:', error)
      alert('Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteUser = async () => {
    const confirmation = window.prompt(
      `Are you sure you want to delete ${user.full_name}? This will deactivate the user account. Type "DELETE" to confirm:`
    )
    
    if (confirmation !== 'DELETE') {
      return
    }

    setLoading(true)
    try {
      await api.delete(`/auth/users/${user.id}/`)
      onUserUpdated()
      setIsOpen(false)
    } catch (error) {
      console.error('Failed to delete user:', error)
      alert('Failed to delete user')
    } finally {
      setLoading(false)
    }
  }

  const handleViewPermissions = () => {
    setShowPermissionModal(true)
    setIsOpen(false)
  }

  const handleSendEmail = () => {
    // Open email client with user's email
    window.location.href = `mailto:${user.email}`
  }

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          disabled={loading}
          className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          <MoreHorizontal className="w-4 h-4" />
        </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 z-10">
          <div className="py-1">
            {/* Edit User - only show if user has update permission */}
            {canUpdate && (
              <button
                onClick={() => {
                  onEditUser(user)
                  setIsOpen(false)
                }}
                className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <Edit className="w-4 h-4 mr-3" />
                Edit User
              </button>
            )}

            {/* Staff Profile */}
            <button
              onClick={() => {
                onViewStaffProfile(user)
                setIsOpen(false)
              }}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <Briefcase className="w-4 h-4 mr-3" />
              Staff Profile
            </button>

            {/* View Permissions */}
            <button
              onClick={handleViewPermissions}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <Shield className="w-4 h-4 mr-3" />
              View Permissions
            </button>

            {/* Send Email */}
            <button
              onClick={handleSendEmail}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <Mail className="w-4 h-4 mr-3" />
              Send Email
            </button>

            {/* Reset Password - only show if user has update permission */}
            {canUpdate && (
              <button
                onClick={handleResetPassword}
                disabled={loading}
                className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                <Key className="w-4 h-4 mr-3" />
                Reset Password
              </button>
            )}

            {(canUpdate || canDelete) && <div className="border-t border-gray-200 dark:border-gray-700 my-1" />}

            {/* Activate/Deactivate - only show if user has update permission */}
            {canUpdate && (
              user.is_active ? (
                <button
                  onClick={handleDeactivateUser}
                  disabled={loading}
                  className="flex items-center w-full px-4 py-2 text-sm text-orange-600 dark:text-orange-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
                >
                  <UserX className="w-4 h-4 mr-3" />
                  Deactivate User
                </button>
              ) : (
                <button
                  onClick={handleActivateUser}
                  disabled={loading}
                  className="flex items-center w-full px-4 py-2 text-sm text-green-600 dark:text-green-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
                >
                  <UserCheck className="w-4 h-4 mr-3" />
                  Activate User
                </button>
              )
            )}

            {/* Delete User - only show if user has delete permission */}
            {canDelete && (
              <button
                onClick={handleDeleteUser}
                disabled={loading}
                className="flex items-center w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4 mr-3" />
                Delete User
              </button>
            )}
          </div>
        </div>
      )}
      </div>

      {/* Permission Modal */}
      <UserPermissionModal
        user={showPermissionModal ? user : null}
        isOpen={showPermissionModal}
        onClose={() => setShowPermissionModal(false)}
        onUserUpdated={onUserUpdated}
      />
    </>
  )
}