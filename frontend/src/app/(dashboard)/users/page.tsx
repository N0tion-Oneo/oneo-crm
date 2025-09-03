'use client'

import { useState, useEffect } from 'react'
import { Search, Plus, MoreHorizontal, Edit, Trash2, Shield, Mail, Briefcase } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'
import { PermissionGuard, PermissionButton } from '@/components/permissions/PermissionGuard'
import UserCreateModal from './components/UserCreateModal'
import UserEditModal from './components/UserEditModal'
import UserActionsDropdown from './components/UserActionsDropdown'
import StaffProfileModal from './components/StaffProfileModal'

interface User {
  id: number
  username: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  timezone: string
  language: string
  user_type: number | null
  user_type_name: string
  is_active: boolean
  is_staff: boolean
  last_login: string | null
  date_joined: string
  // Staff profile fields (if loaded)
  staff_profile?: {
    job_title?: string
    department?: string
    employment_status?: string
  }
}

interface UserType {
  id: number
  name: string
  description: string
  level: number
}

const UsersAccessDenied = () => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center max-w-md">
      <Shield className="w-12 h-12 text-red-500 mx-auto mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Access Denied
      </h2>
      <p className="text-gray-600 dark:text-gray-400 mb-4">
        You don't have permission to view user management. Please contact your administrator to request access.
      </p>
      <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3">
        <p className="text-sm text-red-700 dark:text-red-300">
          Required permission: <code className="bg-red-100 dark:bg-red-900/50 px-1 rounded">users.read</code>
        </p>
      </div>
    </div>
  </div>
)

export default function UsersPage() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [userTypes, setUserTypes] = useState<UserType[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedUserType, setSelectedUserType] = useState<string>('all')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [showStaffProfileModal, setShowStaffProfileModal] = useState(false)
  const [staffProfileUser, setStaffProfileUser] = useState<User | null>(null)

  // Load users and user types
  const loadData = async () => {
    try {
      setLoading(true)
      const [usersResponse, userTypesResponse] = await Promise.all([
        api.get('/auth/users/'), // Get all users in tenant
        api.get('/auth/user-types/') // Get all user types
      ])
      
      // Transform users data to match User interface
      const usersData = usersResponse.data.results || usersResponse.data || []
      const transformedUsers = usersData.map((userData: any) => ({
        id: userData.id,
        username: userData.username || '',
        first_name: userData.first_name || '',
        last_name: userData.last_name || '',
        full_name: userData.full_name || `${userData.first_name} ${userData.last_name}`,
        email: userData.email || '',
        phone: userData.phone || '',
        timezone: userData.timezone || 'UTC',
        language: userData.language || 'en',
        user_type: userData.user_type,
        user_type_name: userData.user_type_name || 'User',
        is_active: userData.is_active || false,
        is_staff: userData.is_staff || false,
        last_login: userData.last_login,
        date_joined: userData.date_joined || '',
        staff_profile: userData.staff_profile || null
      }))
      
      setUsers(transformedUsers)
      setUserTypes(userTypesResponse.data.results || userTypesResponse.data || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleUserCreated = () => {
    loadData() // Reload users list
  }

  const handleUserUpdated = () => {
    loadData() // Reload users list
  }

  const handleEditUser = (user: User) => {
    setSelectedUser(user)
    setShowEditModal(true)
  }

  const handleViewStaffProfile = (user: User) => {
    setStaffProfileUser(user)
    setShowStaffProfileModal(true)
  }

  // Filter users based on search and user type
  const filteredUsers = users.filter(user => {
    const matchesSearch = searchQuery === '' || 
      user.first_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.last_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesType = selectedUserType === 'all' || user.user_type_name === selectedUserType
    
    return matchesSearch && matchesType
  })

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString()
  }

  const getUserTypeColor = (userType: string) => {
    switch (userType.toLowerCase()) {
      case 'admin':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'manager':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'user':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'viewer':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-8"></div>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-300 dark:bg-gray-600 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <PermissionGuard 
      category="users" 
      action="read"
      fallback={<UsersAccessDenied />}
    >
      <div className="p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Users
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Manage users, roles, and permissions for your organization.
          </p>
        </div>

      {/* Filters and Actions */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full sm:w-64 pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
            />
          </div>

          {/* User Type Filter */}
          <select
            value={selectedUserType}
            onChange={(e) => setSelectedUserType(e.target.value)}
            className="block w-full sm:w-auto px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
          >
            <option value="all">All User Types</option>
            {userTypes.map((type) => (
              <option key={type.id} value={type.name}>
                {type.name}
              </option>
            ))}
          </select>
        </div>

        {/* Add User Button */}
        <PermissionButton
          category="users"
          action="create"
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add User
        </PermissionButton>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Job Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Department
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Last Login
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Joined
                </th>
                <th className="relative px-6 py-3">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-8 w-8">
                        <div className="h-8 w-8 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            {user.first_name.charAt(0)}{user.last_name.charAt(0)}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {user.full_name}
                          </span>
                          {user.staff_profile && (
                            <Briefcase className="w-3 h-3 text-blue-500" title="Has Staff Profile" />
                          )}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {user.email}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {user.staff_profile?.job_title || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {user.staff_profile?.department || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getUserTypeColor(user.user_type_name)}`}>
                      {user.user_type_name}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                      user.is_active 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {formatDate(user.last_login)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {formatDate(user.date_joined)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <UserActionsDropdown 
                      user={user as any}
                      onUserUpdated={handleUserUpdated}
                      onEditUser={handleEditUser as any}
                      onViewStaffProfile={handleViewStaffProfile as any}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredUsers.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-500 dark:text-gray-400">
              {searchQuery || selectedUserType !== 'all' 
                ? 'No users match your filters.' 
                : 'No users found.'}
            </div>
          </div>
        )}
      </div>

      {/* Stats Summary */}
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {users.length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Total Users
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {users.filter(u => u.is_active).length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Active Users
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {users.filter(u => u.user_type_name === 'Admin').length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Administrators
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {users.filter(u => u.last_login && new Date(u.last_login) > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)).length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Active This Week
          </div>
        </div>
      </div>

      {/* Modals */}
      <UserCreateModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onUserCreated={handleUserCreated}
      />
      
      <UserEditModal
        user={selectedUser}
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setSelectedUser(null)
        }}
        onUserUpdated={handleUserUpdated}
      />
      
      <StaffProfileModal
        user={staffProfileUser}
        isOpen={showStaffProfileModal}
        onClose={() => {
          setShowStaffProfileModal(false)
          setStaffProfileUser(null)
        }}
        onProfileUpdated={handleUserUpdated}
      />
      </div>
    </PermissionGuard>
  )
}