'use client'

import React, { useState } from 'react'
import { X, AlertTriangle, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'

interface UserType {
  id: number
  name: string
  slug: string
  description: string
  is_system_default: boolean
  is_custom: boolean
  user_count?: number
}

interface DeleteUserTypeModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  userType: UserType | null
}

export default function DeleteUserTypeModal({ isOpen, onClose, onSuccess, userType }: DeleteUserTypeModalProps) {
  const [loading, setLoading] = useState(false)
  const [confirmText, setConfirmText] = useState('')

  if (!isOpen || !userType) return null

  const canDelete = userType.is_custom && !userType.is_system_default
  const hasUsers = (userType.user_count || 0) > 0
  const expectedConfirmText = 'DELETE'

  const handleDelete = async () => {
    if (!canDelete || confirmText !== expectedConfirmText) {
      return
    }

    setLoading(true)
    try {
      await api.delete(`/auth/user-types/${userType.id}/`)
      onSuccess()
      onClose()
    } catch (error: any) {
      console.error('Failed to delete user type:', error)
      
      let errorMessage = 'Failed to delete user type. Please try again.'
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (error.response?.status === 400) {
        errorMessage = 'Cannot delete user type that is assigned to users or is a system default.'
      } else if (error.response?.status === 403) {
        errorMessage = 'You do not have permission to delete user types.'
      }
      
      alert(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setConfirmText('')
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <div className="flex items-center justify-center w-10 h-10 bg-red-100 dark:bg-red-900/20 rounded-full mr-3">
              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Delete User Type
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                This action cannot be undone
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {!canDelete ? (
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Cannot Delete System User Type
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    <strong>{userType.name}</strong> is a system default user type and cannot be deleted. 
                    System user types are required for proper system operation.
                  </p>
                </div>
              </div>
            </div>
          ) : hasUsers ? (
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                    User Type Has Assigned Users
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    <strong>{userType.name}</strong> is currently assigned to <strong>{userType.user_count} user(s)</strong>. 
                    You must reassign these users to another user type before deleting this one.
                  </p>
                </div>
              </div>
              
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md p-3">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  <strong>Tip:</strong> Go to the Users page to reassign users, or use the bulk assignment feature 
                  to quickly move all users to another user type.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Confirm Deletion
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    You are about to permanently delete the user type <strong>{userType.name}</strong>. 
                    This action cannot be undone.
                  </p>
                  
                  <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3 mb-4">
                    <h4 className="text-sm font-medium text-red-800 dark:text-red-200 mb-1">
                      What will be deleted:
                    </h4>
                    <ul className="text-sm text-red-700 dark:text-red-300 space-y-1 ml-4">
                      <li>• User type configuration and permissions</li>
                      <li>• All associated metadata</li>
                      <li>• Custom permission overrides</li>
                    </ul>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Type <strong>DELETE</strong> to confirm:
                    </label>
                    <input
                      type="text"
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 dark:bg-gray-700 dark:text-white"
                      placeholder="Type DELETE to confirm"
                      autoComplete="off"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
          <button
            type="button"
            onClick={handleClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-md hover:bg-gray-50 dark:hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          
          {canDelete && !hasUsers && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={loading || confirmText !== expectedConfirmText}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete User Type
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}