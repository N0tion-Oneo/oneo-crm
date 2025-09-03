'use client'

import { useState, useEffect } from 'react'
import { X, User, Briefcase, Globe, Phone, AlertTriangle, Shield, Building, Users, FileText } from 'lucide-react'
import { getStaffProfile, hasStaffProfile } from '@/lib/staff-profiles'
import { StaffProfile } from '@/types/staff-profile'
import { useAuth } from '@/features/auth/context'
import StaffProfileForm from './StaffProfileForm'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface StaffProfileModalProps {
  user: {
    id: number
    first_name: string
    last_name: string
    full_name: string
    email: string
  } | null
  isOpen: boolean
  onClose: () => void
  onProfileUpdated?: () => void
}

export default function StaffProfileModal({ 
  user, 
  isOpen, 
  onClose,
  onProfileUpdated 
}: StaffProfileModalProps) {
  const { hasPermission } = useAuth()
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<StaffProfile | null>(null)
  const [hasProfile, setHasProfile] = useState(false)
  const [activeTab, setActiveTab] = useState<'view' | 'edit'>('view')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && user) {
      loadProfile()
    }
  }, [isOpen, user])

  const loadProfile = async () => {
    if (!user) return
    
    setLoading(true)
    setError(null)
    
    try {
      const profileExists = await hasStaffProfile(user.id)
      setHasProfile(profileExists)
      
      if (profileExists) {
        const profileData = await getStaffProfile(user.id)
        setProfile(profileData)
      }
    } catch (err: any) {
      console.error('Failed to load staff profile:', err)
      setError(err.message || 'Failed to load staff profile')
    } finally {
      setLoading(false)
    }
  }

  const handleProfileSaved = () => {
    loadProfile()
    onProfileUpdated?.()
    setActiveTab('view')
  }

  if (!isOpen || !user) return null

  const canEdit = hasPermission('staff_profiles', 'update') || 
                 hasPermission('staff_profiles', 'update_all')
  const canViewSensitive = hasPermission('staff_profiles', 'read_sensitive')
  const canEditSensitive = hasPermission('staff_profiles', 'update_sensitive')
  const canViewAdmin = hasPermission('staff_profiles', 'read_admin')
  const canEditAdmin = hasPermission('staff_profiles', 'update_admin')

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Staff Profile
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {user.full_name} - {user.email}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded-md p-4 mb-6">
              <div className="flex">
                <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          ) : !hasProfile && activeTab === 'view' ? (
            <div className="text-center py-12 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <Briefcase className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
              <h3 className="mt-2 text-lg font-medium text-gray-900 dark:text-white">
                No Staff Profile
              </h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                This user doesn't have a staff profile yet.
              </p>
              {canEdit && (
                <div className="mt-6">
                  <button
                    onClick={() => setActiveTab('edit')}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                  >
                    Create Staff Profile
                  </button>
                </div>
              )}
            </div>
            ) : activeTab === 'edit' ? (
              <StaffProfileForm
                userId={user.id}
                profile={profile}
                onSave={handleProfileSaved}
                onCancel={() => setActiveTab('view')}
              />
            ) : (
              <div>
                {canEdit && (
                  <div className="flex justify-end mb-4">
                    <button
                      onClick={() => setActiveTab('edit')}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    >
                      Edit Profile
                    </button>
                  </div>
                )}

                <Tabs defaultValue="employment" className="w-full">
                  <TabsList className="grid w-full grid-cols-5">
                    <TabsTrigger value="employment" className="text-xs">
                      <Briefcase className="w-4 h-4 mr-1" />
                      Employment
                    </TabsTrigger>
                    <TabsTrigger value="work" className="text-xs">
                      <Building className="w-4 h-4 mr-1" />
                      Work
                    </TabsTrigger>
                    <TabsTrigger value="qualifications" className="text-xs">
                      <FileText className="w-4 h-4 mr-1" />
                      Skills
                    </TabsTrigger>
                    <TabsTrigger value="personal" className="text-xs">
                      <User className="w-4 h-4 mr-1" />
                      Personal
                    </TabsTrigger>
                    {canViewAdmin && profile?.internal_notes && (
                      <TabsTrigger value="admin" className="text-xs">
                        <Shield className="w-4 h-4 mr-1" />
                        Admin
                      </TabsTrigger>
                    )}
                  </TabsList>

                  <TabsContent value="employment" className="mt-4">
                    <div>
                      <h4 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                        <Briefcase className="w-5 h-5 mr-2" />
                        Employment Information
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <ProfileField label="Employee ID" value={profile?.employee_id} />
                        <ProfileField label="Job Title" value={profile?.job_title} />
                        <ProfileField label="Department" value={profile?.department} />
                        <ProfileField label="Employment Type" value={profile?.employment_type} />
                        <ProfileField label="Employment Status" value={profile?.employment_status} />
                        <ProfileField label="Start Date" value={profile?.start_date} type="date" />
                        {profile?.end_date && (
                          <ProfileField label="End Date" value={profile.end_date} type="date" />
                        )}
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="work" className="mt-4">
                    <div>
                      <h4 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                        <Building className="w-5 h-5 mr-2" />
                        Work Details
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <ProfileField label="Work Location" value={profile?.work_location} />
                        <ProfileField label="Office Location" value={profile?.office_location} />
                        <ProfileField label="Extension" value={profile?.work_phone_extension} />
                        <ProfileField label="Reports To" value={profile?.reporting_manager_name} />
                        <ProfileField label="Direct Reports" value={profile?.direct_reports_count?.toString()} />
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="qualifications" className="mt-4">
                    <div>
                      <h4 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                        <FileText className="w-5 h-5 mr-2" />
                        Qualifications & Skills
                      </h4>
                      <div className="space-y-4">
                        {profile?.bio && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                              Biography
                            </label>
                            <p className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
                              {profile.bio}
                            </p>
                          </div>
                        )}
                        {profile?.certifications && profile.certifications.length > 0 && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                              Certifications
                            </label>
                            <div className="flex flex-wrap gap-2">
                              {profile.certifications.map((cert, index) => (
                                <span
                                  key={index}
                                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                                >
                                  {cert}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {profile?.linkedin_profile && (
                          <ProfileField 
                            label="LinkedIn Profile" 
                            value={profile.linkedin_profile} 
                            type="link"
                          />
                        )}
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="personal" className="mt-4">
                    {canViewSensitive ? (
                      <div className="space-y-6">
                        <div>
                          <h4 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                            <User className="w-5 h-5 mr-2" />
                            Personal Details
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <ProfileField label="Date of Birth" value={profile?.date_of_birth} type="date" />
                            <ProfileField label="Nationality" value={profile?.nationality} />
                            <ProfileField label="Personal Email" value={profile?.personal_email} />
                          </div>
                        </div>

                        <div>
                          <h4 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                            <Phone className="w-5 h-5 mr-2" />
                            Emergency Contact
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <ProfileField label="Contact Name" value={profile?.emergency_contact_name} />
                            <ProfileField label="Contact Phone" value={profile?.emergency_contact_phone} />
                            <ProfileField label="Relationship" value={profile?.emergency_contact_relationship} />
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                        <Shield className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>You don't have permission to view personal information.</p>
                      </div>
                    )}
                  </TabsContent>

                  {canViewAdmin && profile?.internal_notes && (
                    <TabsContent value="admin" className="mt-4">
                      <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-6">
                        <h4 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                          <Shield className="w-5 h-5 mr-2" />
                          Internal Notes
                          <span className="ml-2 text-xs text-yellow-600 dark:text-yellow-400">
                            (Admin Only)
                          </span>
                        </h4>
                        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                          {profile.internal_notes}
                        </p>
                      </div>
                    </TabsContent>
                  )}
                </Tabs>
              </div>
            )}
        </div>
      </div>
    </div>
  )
}

interface ProfileFieldProps {
  label: string
  value?: string | null
  type?: 'text' | 'date' | 'link'
}

function ProfileField({ label, value, type = 'text' }: ProfileFieldProps) {
  if (!value) return null

  const formatValue = () => {
    if (type === 'date') {
      return new Date(value).toLocaleDateString()
    }
    if (type === 'link') {
      return (
        <a 
          href={value.startsWith('http') ? value : `https://${value}`} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
        >
          {value}
        </a>
      )
    }
    return value
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      <div className="mt-1 text-sm text-gray-900 dark:text-white">
        {formatValue()}
      </div>
    </div>
  )
}