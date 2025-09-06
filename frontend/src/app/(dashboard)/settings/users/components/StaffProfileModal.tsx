'use client'

import { useState, useEffect } from 'react'
import { X, User, Briefcase, Globe, Phone, AlertTriangle, Shield, Building, Users, FileText, Calendar, Mail, MapPin, Award, BookOpen, Link2, Clock, UserCheck, Github, Twitter, Linkedin } from 'lucide-react'
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
              <div className="space-y-6">
                {/* Profile Header Card */}
                <div className="bg-gradient-to-r from-primary/10 to-primary/5 dark:from-primary/20 dark:to-primary/10 rounded-xl p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="w-16 h-16 bg-primary/20 dark:bg-primary/30 rounded-full flex items-center justify-center">
                        <User className="w-8 h-8 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                          {profile?.job_title || <span className="text-gray-400 italic">No Job Title</span>}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          <span className={!profile?.department ? "italic" : ""}>{profile?.department || 'No Department'}</span>
                          {(profile?.department || profile?.employee_id) && ' • '}
                          <span className={!profile?.employee_id ? "italic" : ""}>{profile?.employee_id || 'No Employee ID'}</span>
                        </p>
                        <div className="flex items-center gap-3 mt-2">
                          {profile?.employment_status && (
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              profile.employment_status === 'active' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                              profile.employment_status === 'on_leave' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                              'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                            }`}>
                              {profile.employment_status.replace('_', ' ').charAt(0).toUpperCase() + profile.employment_status.replace('_', ' ').slice(1)}
                            </span>
                          )}
                          {profile?.employment_type && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                              {profile.employment_type.replace('_', ' ').charAt(0).toUpperCase() + profile.employment_type.replace('_', ' ').slice(1)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    {canEdit && (
                      <button
                        onClick={() => setActiveTab('edit')}
                        className="inline-flex items-center px-3 py-1.5 border border-primary/20 text-sm font-medium rounded-md shadow-sm text-primary bg-white dark:bg-gray-800 hover:bg-primary/5 dark:hover:bg-primary/10 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                      >
                        Edit Profile
                      </button>
                    )}
                  </div>
                </div>

                {/* Quick Info Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <div className="flex items-center space-x-3">
                      <MapPin className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Work Location</p>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {profile?.work_location ? 
                            profile.work_location.replace('_', ' ').charAt(0).toUpperCase() + profile.work_location.replace('_', ' ').slice(1) : 
                            <span className="text-gray-400 italic">Not specified</span>
                          }
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <div className="flex items-center space-x-3">
                      <Calendar className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Started</p>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {profile?.start_date ? 
                            new Date(profile.start_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 
                            <span className="text-gray-400 italic">Not specified</span>
                          }
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <div className="flex items-center space-x-3">
                      <UserCheck className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Reports To</p>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {profile?.reporting_manager_name || <span className="text-gray-400 italic">Not specified</span>}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <Tabs defaultValue="overview" className="w-full">
                  <TabsList className="grid w-full grid-cols-4 lg:grid-cols-5">
                    <TabsTrigger value="overview" className="text-xs">
                      <User className="w-4 h-4 mr-1" />
                      Overview
                    </TabsTrigger>
                    <TabsTrigger value="employment" className="text-xs">
                      <Briefcase className="w-4 h-4 mr-1" />
                      Employment
                    </TabsTrigger>
                    <TabsTrigger value="education" className="text-xs">
                      <BookOpen className="w-4 h-4 mr-1" />
                      Education
                    </TabsTrigger>
                    <TabsTrigger value="personal" className="text-xs">
                      <Shield className="w-4 h-4 mr-1" />
                      Personal
                    </TabsTrigger>
                    {canViewAdmin && (
                      <TabsTrigger value="admin" className="text-xs">
                        <FileText className="w-4 h-4 mr-1" />
                        Admin
                      </TabsTrigger>
                    )}
                  </TabsList>

                  {/* Overview Tab */}
                  <TabsContent value="overview" className="mt-6 space-y-6">
                    {/* Professional Information */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                      <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                        <Briefcase className="w-5 h-5 mr-2 text-primary" />
                        Professional Information
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        <ProfileField 
                          label="Employee ID" 
                          value={profile?.employee_id}
                          icon={<UserCheck className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Job Title" 
                          value={profile?.job_title}
                          icon={<Briefcase className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Department" 
                          value={profile?.department}
                          icon={<Building className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Work Location" 
                          value={profile?.work_location ? profile.work_location.replace('_', ' ').charAt(0).toUpperCase() + profile.work_location.replace('_', ' ').slice(1) : ''}
                          icon={<MapPin className="w-4 h-4" />}
                        />
                      </div>
                    </div>

                    {/* Work Contact Details */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                      <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                        <Phone className="w-5 h-5 mr-2 text-primary" />
                        Work Contact
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        <ProfileField 
                          label="Work Email" 
                          value={user.email} 
                          icon={<Mail className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Extension" 
                          value={profile?.work_phone_extension}
                          icon={<Phone className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Office Location" 
                          value={profile?.office_location}
                          icon={<Building className="w-4 h-4" />}
                        />
                      </div>
                    </div>

                    {/* Bio Section */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                      <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                        <User className="w-5 h-5 mr-2 text-primary" />
                        Biography
                      </h4>
                      {profile?.bio ? (
                        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                          {profile.bio}
                        </p>
                      ) : (
                        <p className="text-sm text-gray-400 dark:text-gray-500 italic">No biography provided</p>
                      )}
                    </div>

                    {/* Professional Links Section */}
                    {(profile?.professional_links && Object.keys(profile.professional_links).length > 0) || profile?.linkedin_profile ? (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                          <Globe className="w-5 h-5 mr-2 text-primary" />
                          Professional Links
                        </h4>
                        <div className="space-y-3">
                          {(profile?.linkedin_profile || profile?.professional_links?.linkedin) && (
                            <a
                              href={(profile?.professional_links?.linkedin || profile?.linkedin_profile || '').startsWith('http') 
                                ? (profile?.professional_links?.linkedin || profile?.linkedin_profile) 
                                : `https://${profile?.professional_links?.linkedin || profile?.linkedin_profile}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                            >
                              <Linkedin className="w-4 h-4" />
                              <span>LinkedIn</span>
                            </a>
                          )}
                          {profile?.professional_links?.github && (
                            <a
                              href={profile.professional_links.github.startsWith('http') ? profile.professional_links.github : `https://${profile.professional_links.github}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                            >
                              <Github className="w-4 h-4" />
                              <span>GitHub</span>
                            </a>
                          )}
                          {profile?.professional_links?.twitter && (
                            <a
                              href={profile.professional_links.twitter.startsWith('http') ? profile.professional_links.twitter : `https://${profile.professional_links.twitter}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                            >
                              <Twitter className="w-4 h-4" />
                              <span>Twitter/X</span>
                            </a>
                          )}
                          {profile?.professional_links?.portfolio && (
                            <a
                              href={profile.professional_links.portfolio.startsWith('http') ? profile.professional_links.portfolio : `https://${profile.professional_links.portfolio}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                            >
                              <Globe className="w-4 h-4" />
                              <span>Portfolio/Website</span>
                            </a>
                          )}
                          {profile?.professional_links && Object.entries(profile.professional_links)
                            .filter(([key]) => !['linkedin', 'github', 'twitter', 'portfolio'].includes(key))
                            .map(([platform, url]) => (
                              <a
                                key={platform}
                                href={url.startsWith('http') ? url : `https://${url}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                              >
                                <Link2 className="w-4 h-4" />
                                <span>{platform.charAt(0).toUpperCase() + platform.slice(1).replace(/_/g, ' ').replace(/custom /i, '')}</span>
                              </a>
                            ))}
                        </div>
                      </div>
                    ) : null}
                  </TabsContent>

                  {/* Employment Tab */}
                  <TabsContent value="employment" className="mt-6">
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                      <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
                        <Briefcase className="w-5 h-5 mr-2 text-primary" />
                        Employment Details
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        <ProfileField 
                          label="Employee ID" 
                          value={profile?.employee_id}
                          icon={<UserCheck className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Job Title" 
                          value={profile?.job_title}
                          icon={<Briefcase className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Department" 
                          value={profile?.department}
                          icon={<Building className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Employment Type" 
                          value={profile?.employment_type ? profile.employment_type.replace('_', ' ').charAt(0).toUpperCase() + profile.employment_type.replace('_', ' ').slice(1) : ''}
                          icon={<Clock className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="Start Date" 
                          value={profile?.start_date} 
                          type="date"
                          icon={<Calendar className="w-4 h-4" />}
                        />
                        <ProfileField 
                          label="End Date" 
                          value={profile?.end_date} 
                          type="date"
                          icon={<Calendar className="w-4 h-4" />}
                        />
                      </div>

                      {/* Manager Information */}
                      {(profile?.reporting_manager_name || profile?.direct_reports_count) && (
                        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                          <h5 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                            <Users className="w-5 h-5 mr-2 text-gray-400" />
                            Reporting Structure
                          </h5>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <ProfileField 
                              label="Reports To" 
                              value={profile?.reporting_manager_name}
                              icon={<UserCheck className="w-4 h-4" />}
                            />
                            {profile?.direct_reports_count !== undefined && profile.direct_reports_count > 0 && (
                              <ProfileField 
                                label="Direct Reports" 
                                value={`${profile.direct_reports_count} ${profile.direct_reports_count === 1 ? 'person' : 'people'}`}
                                icon={<Users className="w-4 h-4" />}
                              />
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  {/* Education Tab */}
                  <TabsContent value="education" className="mt-6">
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                      <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
                        <BookOpen className="w-5 h-5 mr-2 text-primary" />
                        Education & Qualifications
                      </h4>
                      {profile?.education && Object.keys(profile.education).length > 0 ? (
                        <div className="space-y-4">
                          {(Array.isArray(profile.education) ? profile.education : Object.values(profile.education)).map((edu: any, index) => (
                            <div key={index} className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                              <div className="flex items-start space-x-3">
                                <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                                  <BookOpen className="w-4 h-4 text-primary" />
                                </div>
                                <div className="flex-1">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                                    {edu.degree || 'Degree'}
                                    {edu.field_of_study && ` in ${edu.field_of_study}`}
                                  </p>
                                  <p className="text-sm text-gray-600 dark:text-gray-400">
                                    {edu.institution || 'Institution'}
                                    {edu.year && ` • ${edu.year}`}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <BookOpen className="w-12 h-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
                          <p className="text-sm text-gray-500 dark:text-gray-400">No education records added</p>
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  {/* Personal Tab */}
                  <TabsContent value="personal" className="mt-6">
                    {canViewSensitive ? (
                      <div className="space-y-6">
                        {/* Personal Details */}
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                          <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
                            <User className="w-5 h-5 mr-2 text-primary" />
                            Personal Information
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <ProfileField 
                              label="Date of Birth" 
                              value={profile?.date_of_birth} 
                              type="date"
                              icon={<Calendar className="w-4 h-4" />}
                            />
                            <ProfileField 
                              label="Nationality" 
                              value={profile?.nationality}
                              icon={<Globe className="w-4 h-4" />}
                            />
                            <ProfileField 
                              label="Personal Email" 
                              value={profile?.personal_email}
                              icon={<Mail className="w-4 h-4" />}
                            />
                          </div>

                          {/* Home Address */}
                          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                            <h5 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                              <MapPin className="w-5 h-5 mr-2 text-gray-400" />
                              Home Address
                            </h5>
                            <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                              {profile?.home_address && typeof profile.home_address === 'object' && Object.keys(profile.home_address).length > 0 ? (
                                <p className="text-sm text-gray-700 dark:text-gray-300">
                                  {[profile.home_address.street, profile.home_address.city, profile.home_address.state, profile.home_address.postal_code, profile.home_address.country]
                                    .filter(Boolean)
                                    .join(', ') || <span className="text-gray-400 italic">No address provided</span>}
                                </p>
                              ) : (
                                <p className="text-sm text-gray-400 dark:text-gray-500 italic">No address provided</p>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Emergency Contact */}
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                          <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
                            <Phone className="w-5 h-5 mr-2 text-primary" />
                            Emergency Contact
                          </h4>
                          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                              <ProfileField 
                                label="Contact Name" 
                                value={profile?.emergency_contact_name}
                                icon={<User className="w-4 h-4" />}
                              />
                              <ProfileField 
                                label="Contact Phone" 
                                value={profile?.emergency_contact_phone}
                                icon={<Phone className="w-4 h-4" />}
                              />
                              <ProfileField 
                                label="Relationship" 
                                value={profile?.emergency_contact_relationship}
                                icon={<Users className="w-4 h-4" />}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-12 text-center">
                        <Shield className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Restricted Access</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">You don't have permission to view personal information.</p>
                      </div>
                    )}
                  </TabsContent>

                  {/* Admin Tab */}
                  {canViewAdmin && (
                    <TabsContent value="admin" className="mt-6">
                      <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-lg p-6">
                        <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                          <FileText className="w-5 h-5 mr-2 text-amber-600 dark:text-amber-400" />
                          Internal Notes
                          <span className="ml-auto text-xs text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/50 px-2 py-1 rounded-full">
                            Admin Only
                          </span>
                        </h4>
                        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-amber-200 dark:border-amber-700">
                          {profile?.internal_notes ? (
                            <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                              {profile.internal_notes}
                            </p>
                          ) : (
                            <p className="text-sm text-gray-400 dark:text-gray-500 italic">
                              No internal notes added
                            </p>
                          )}
                        </div>
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
  icon?: React.ReactNode
}

function ProfileField({ label, value, type = 'text', icon }: ProfileFieldProps) {
  const formatValue = () => {
    if (!value || value === '') {
      return <span className="text-gray-400 dark:text-gray-500 italic">Not provided</span>
    }
    
    if (type === 'date') {
      return new Date(value).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      })
    }
    if (type === 'link') {
      return (
        <a 
          href={value.startsWith('http') ? value : `https://${value}`} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
        >
          {value}
        </a>
      )
    }
    return value
  }

  return (
    <div className="group">
      <div className="flex items-center space-x-2 mb-1">
        {icon && (
          <span className="text-gray-400 dark:text-gray-500">
            {icon}
          </span>
        )}
        <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {label}
        </label>
      </div>
      <div className="text-sm text-gray-900 dark:text-white font-medium pl-6">
        {formatValue()}
      </div>
    </div>
  )
}