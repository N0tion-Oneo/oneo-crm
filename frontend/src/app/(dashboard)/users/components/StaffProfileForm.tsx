'use client'

import { useState, useEffect } from 'react'
import { createStaffProfile, updateStaffProfile } from '@/lib/staff-profiles'
import { StaffProfile, StaffProfileFormData, EmploymentType, EmploymentStatus, WorkLocation, Address } from '@/types/staff-profile'
import { useAuth } from '@/features/auth/context'
import { AlertTriangle, Award, BookOpen, Briefcase, Building, Calendar, Clock, FileText, Github, Globe, Link2, Linkedin, Mail, MapPin, Phone, Plus, Shield, Trash2, Twitter, User, UserCheck, Users } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface StaffProfileFormProps {
  userId: number
  profile: StaffProfile | null
  onSave: () => void
  onCancel: () => void
}

export default function StaffProfileForm({ userId, profile, onSave, onCancel }: StaffProfileFormProps) {
  const { hasPermission } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const canEditSensitive = hasPermission('staff_profiles', 'update_sensitive')
  const canEditAdmin = hasPermission('staff_profiles', 'update_admin')

  const [formData, setFormData] = useState<Partial<StaffProfileFormData>>({
    employee_id: '',
    job_title: '',
    department: '',
    employment_type: 'full_time' as EmploymentType,
    employment_status: 'active' as EmploymentStatus,
    start_date: '',
    end_date: '',
    work_location: 'office' as WorkLocation,
    office_location: '',
    work_phone_extension: '',
    reporting_manager: null,
    education: [],
    bio: '',
    linkedin_profile: '',
    professional_links: {},
    emergency_contact_name: '',
    emergency_contact_phone: '',
    emergency_contact_relationship: '',
    date_of_birth: '',
    nationality: '',
    personal_email: '',
    home_address: {
      street: '',
      city: '',
      state: '',
      postal_code: '',
      country: ''
    },
    internal_notes: ''
  })

  useEffect(() => {
    if (profile) {
      setFormData({
        employee_id: profile.employee_id || '',
        job_title: profile.job_title || '',
        department: profile.department || '',
        employment_type: profile.employment_type || 'full_time',
        employment_status: profile.employment_status || 'active',
        start_date: profile.start_date || '',
        end_date: profile.end_date || '',
        work_location: profile.work_location || 'office',
        office_location: profile.office_location || '',
        work_phone_extension: profile.work_phone_extension || '',
        reporting_manager: profile.reporting_manager || null,
        education: Array.isArray(profile.education) ? profile.education : [],
        bio: profile.bio || '',
        linkedin_profile: profile.linkedin_profile || '',
        professional_links: profile.professional_links || {},
        emergency_contact_name: profile.emergency_contact_name || '',
        emergency_contact_phone: profile.emergency_contact_phone || '',
        emergency_contact_relationship: profile.emergency_contact_relationship || '',
        date_of_birth: profile.date_of_birth || '',
        nationality: profile.nationality || '',
        personal_email: profile.personal_email || '',
        home_address: (typeof profile.home_address === 'object' && profile.home_address !== null && 
                       'street' in profile.home_address && 
                       'city' in profile.home_address && 
                       'state' in profile.home_address && 
                       'postal_code' in profile.home_address && 
                       'country' in profile.home_address) 
                      ? profile.home_address as Address
                      : {
                          street: '',
                          city: '',
                          state: '',
                          postal_code: '',
                          country: ''
                        },
        internal_notes: profile.internal_notes || ''
      })
    }
  }, [profile])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (profile) {
        await updateStaffProfile(profile.id, formData)
      } else {
        await createStaffProfile(userId, formData)
      }
      onSave()
    } catch (err: any) {
      console.error('Failed to save staff profile:', err)
      console.error('Error response data:', err.response?.data)
      console.error('Form data being sent:', formData)
      
      // Extract error message from response
      let errorMessage = 'Failed to save profile'
      if (err.response?.data) {
        // Handle Django validation errors
        if (typeof err.response.data === 'object') {
          const errors = Object.entries(err.response.data)
            .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
            .join('; ')
          errorMessage = errors || errorMessage
        } else if (err.response.data.detail) {
          errorMessage = err.response.data.detail
        } else if (err.response.data.message) {
          errorMessage = err.response.data.message
        }
      } else if (err.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }


  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md mb-4">
          <div className="flex">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        </div>
      )}

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
          {canEditAdmin && (
            <TabsTrigger value="admin" className="text-xs">
              <FileText className="w-4 h-4 mr-1" />
              Admin
            </TabsTrigger>
          )}
        </TabsList>

        {/* Overview Tab - Professional Information, Work Contact, Bio */}
        <TabsContent value="overview" className="mt-4 space-y-6">
          {/* Professional Information Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <Briefcase className="w-5 h-5 mr-2 text-primary" />
              Professional Information
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="employee_id">Employee ID</Label>
                <Input
                  id="employee_id"
                  type="text"
                  value={formData.employee_id}
                  onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                  placeholder="EMP001"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="job_title">Job Title</Label>
                <Input
                  id="job_title"
                  type="text"
                  value={formData.job_title}
                  onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                  placeholder="Software Engineer"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="department">Department</Label>
                <Input
                  id="department"
                  type="text"
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  placeholder="Engineering"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="work_location">Work Location</Label>
                <Select
                  value={formData.work_location}
                  onValueChange={(value) => setFormData({ ...formData, work_location: value as WorkLocation })}
                >
                  <SelectTrigger id="work_location">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="office">Office</SelectItem>
                    <SelectItem value="remote">Remote</SelectItem>
                    <SelectItem value="hybrid">Hybrid</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Work Contact Details Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <Phone className="w-5 h-5 mr-2 text-primary" />
              Work Contact
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="work_phone_extension">Work Phone Extension</Label>
                <Input
                  id="work_phone_extension"
                  type="text"
                  value={formData.work_phone_extension}
                  onChange={(e) => setFormData({ ...formData, work_phone_extension: e.target.value })}
                  placeholder="1234"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="office_location">Office Location</Label>
                <Input
                  id="office_location"
                  type="text"
                  value={formData.office_location}
                  onChange={(e) => setFormData({ ...formData, office_location: e.target.value })}
                  placeholder="New York Office, Floor 3"
                />
              </div>
            </div>
          </div>

          {/* Biography Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <User className="w-5 h-5 mr-2 text-primary" />
              Biography
            </h4>
            <div className="space-y-2">
              <Textarea
                id="bio"
                value={formData.bio}
                onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                rows={4}
                placeholder="Tell us about yourself..."
                className="w-full"
              />
            </div>
          </div>

          {/* Professional Links Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <Globe className="w-5 h-5 mr-2 text-primary" />
              Professional Links
            </h4>
            <div className="space-y-4">
              {/* LinkedIn */}
              <div className="space-y-2">
                <Label htmlFor="linkedin" className="flex items-center gap-2">
                  <Linkedin className="w-4 h-4" />
                  LinkedIn
                </Label>
                <Input
                  id="linkedin"
                  type="url"
                  value={formData.professional_links?.linkedin || formData.linkedin_profile || ''}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    linkedin_profile: e.target.value,
                    professional_links: { 
                      ...formData.professional_links, 
                      linkedin: e.target.value 
                    }
                  })}
                  placeholder="https://linkedin.com/in/username"
                />
              </div>

              {/* GitHub */}
              <div className="space-y-2">
                <Label htmlFor="github" className="flex items-center gap-2">
                  <Github className="w-4 h-4" />
                  GitHub
                </Label>
                <Input
                  id="github"
                  type="url"
                  value={formData.professional_links?.github || ''}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    professional_links: { 
                      ...formData.professional_links, 
                      github: e.target.value 
                    }
                  })}
                  placeholder="https://github.com/username"
                />
              </div>

              {/* Twitter/X */}
              <div className="space-y-2">
                <Label htmlFor="twitter" className="flex items-center gap-2">
                  <Twitter className="w-4 h-4" />
                  Twitter/X
                </Label>
                <Input
                  id="twitter"
                  type="url"
                  value={formData.professional_links?.twitter || ''}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    professional_links: { 
                      ...formData.professional_links, 
                      twitter: e.target.value 
                    }
                  })}
                  placeholder="https://twitter.com/username or https://x.com/username"
                />
              </div>

              {/* Portfolio/Website */}
              <div className="space-y-2">
                <Label htmlFor="portfolio" className="flex items-center gap-2">
                  <Globe className="w-4 h-4" />
                  Portfolio/Website
                </Label>
                <Input
                  id="portfolio"
                  type="url"
                  value={formData.professional_links?.portfolio || ''}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    professional_links: { 
                      ...formData.professional_links, 
                      portfolio: e.target.value 
                    }
                  })}
                  placeholder="https://yourwebsite.com"
                />
              </div>

              {/* Custom Links */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Link2 className="w-4 h-4" />
                  Custom Links
                </Label>
                <div className="space-y-2">
                  {Object.entries(formData.professional_links || {})
                    .filter(([key]) => !['linkedin', 'github', 'twitter', 'portfolio'].includes(key))
                    .map(([key, value], index) => (
                      <div key={key} className="flex gap-2">
                        <Input
                          type="text"
                          value={key}
                          onChange={(e) => {
                            const newLinks = { ...formData.professional_links }
                            delete newLinks[key]
                            newLinks[e.target.value] = value
                            setFormData({ ...formData, professional_links: newLinks })
                          }}
                          placeholder="Platform name"
                          className="w-1/3"
                        />
                        <Input
                          type="url"
                          value={value}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            professional_links: { 
                              ...formData.professional_links, 
                              [key]: e.target.value 
                            }
                          })}
                          placeholder="https://example.com/profile"
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            const newLinks = { ...formData.professional_links }
                            delete newLinks[key]
                            setFormData({ ...formData, professional_links: newLinks })
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const newKey = `custom_${Date.now()}`
                      setFormData({ 
                        ...formData, 
                        professional_links: { 
                          ...formData.professional_links, 
                          [newKey]: '' 
                        }
                      })
                    }}
                    className="w-full"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Custom Link
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Employment Tab - Employment Details */}
        <TabsContent value="employment" className="mt-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
              <Briefcase className="w-5 h-5 mr-2 text-primary" />
              Employment Details
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="emp_employee_id">Employee ID</Label>
                <Input
                  id="emp_employee_id"
                  type="text"
                  value={formData.employee_id}
                  onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                  placeholder="EMP001"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="emp_job_title">Job Title</Label>
                <Input
                  id="emp_job_title"
                  type="text"
                  value={formData.job_title}
                  onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                  placeholder="Software Engineer"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="emp_department">Department</Label>
                <Input
                  id="emp_department"
                  type="text"
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  placeholder="Engineering"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="employment_type">Employment Type</Label>
                <Select
                  value={formData.employment_type}
                  onValueChange={(value) => setFormData({ ...formData, employment_type: value as EmploymentType })}
                >
                  <SelectTrigger id="employment_type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="full_time">Full Time</SelectItem>
                    <SelectItem value="part_time">Part Time</SelectItem>
                    <SelectItem value="contractor">Contractor</SelectItem>
                    <SelectItem value="intern">Intern</SelectItem>
                    <SelectItem value="consultant">Consultant</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="employment_status">Employment Status</Label>
                <Select
                  value={formData.employment_status}
                  onValueChange={(value) => setFormData({ ...formData, employment_status: value as EmploymentStatus })}
                >
                  <SelectTrigger id="employment_status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="on_leave">On Leave</SelectItem>
                    <SelectItem value="terminated">Terminated</SelectItem>
                    <SelectItem value="resigned">Resigned</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="start_date">Start Date</Label>
                <Input
                  id="start_date"
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end_date">End Date</Label>
                <Input
                  id="end_date"
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                />
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Education Tab */}
        <TabsContent value="education" className="mt-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
              <BookOpen className="w-5 h-5 mr-2 text-primary" />
              Education & Qualifications
            </h4>
            <div className="space-y-4">
              {formData.education && formData.education.length > 0 ? (
                formData.education.map((edu, index) => (
                  <div key={index} className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <Input
                          type="text"
                          value={edu.degree || ''}
                          onChange={(e) => {
                            const newEducation = [...(formData.education || [])]
                            newEducation[index] = { ...edu, degree: e.target.value }
                            setFormData({ ...formData, education: newEducation })
                          }}
                          placeholder="Degree (e.g., Bachelor of Science)"
                        />
                        <Input
                          type="text"
                          value={edu.field_of_study || ''}
                          onChange={(e) => {
                            const newEducation = [...(formData.education || [])]
                            newEducation[index] = { ...edu, field_of_study: e.target.value }
                            setFormData({ ...formData, education: newEducation })
                          }}
                          placeholder="Field of Study (e.g., Computer Science)"
                        />
                        <Input
                          type="text"
                          value={edu.institution || ''}
                          onChange={(e) => {
                            const newEducation = [...(formData.education || [])]
                            newEducation[index] = { ...edu, institution: e.target.value }
                            setFormData({ ...formData, education: newEducation })
                          }}
                          placeholder="Institution (e.g., MIT)"
                        />
                        <Input
                          type="text"
                          value={edu.year || ''}
                          onChange={(e) => {
                            const newEducation = [...(formData.education || [])]
                            newEducation[index] = { ...edu, year: e.target.value }
                            setFormData({ ...formData, education: newEducation })
                          }}
                          placeholder="Year (e.g., 2020)"
                        />
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          const newEducation = (formData.education || []).filter((_, i) => i !== index)
                          setFormData({ ...formData, education: newEducation })
                        }}
                        className="ml-2"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  No education records added yet
                </p>
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setFormData({
                    ...formData,
                    education: [...(formData.education || []), { degree: '', institution: '', year: '', field_of_study: '' }]
                  })
                }}
                className="w-full"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Education Record
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* Personal Tab */}
        <TabsContent value="personal" className="mt-4">
          {canEditSensitive ? (
            <div className="space-y-6">
              {/* Personal Details Section */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
                  <User className="w-5 h-5 mr-2 text-primary" />
                  Personal Information
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="date_of_birth">Date of Birth</Label>
                    <Input
                      id="date_of_birth"
                      type="date"
                      value={formData.date_of_birth}
                      onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nationality">Nationality</Label>
                    <Input
                      id="nationality"
                      type="text"
                      value={formData.nationality}
                      onChange={(e) => setFormData({ ...formData, nationality: e.target.value })}
                      placeholder="e.g., American"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="personal_email">Personal Email</Label>
                    <Input
                      id="personal_email"
                      type="email"
                      value={formData.personal_email}
                      onChange={(e) => setFormData({ ...formData, personal_email: e.target.value })}
                      placeholder="personal@email.com"
                    />
                  </div>
                </div>

                {/* Home Address Subsection */}
                <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                  <h5 className="text-base font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                    <MapPin className="w-5 h-5 mr-2 text-gray-400" />
                    Home Address
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="street">Street Address</Label>
                      <Input
                        id="street"
                        type="text"
                        value={formData.home_address?.street || ''}
                        onChange={(e) => setFormData({ 
                          ...formData, 
                          home_address: { 
                            street: e.target.value,
                            city: formData.home_address?.city || '',
                            state: formData.home_address?.state || '',
                            postal_code: formData.home_address?.postal_code || '',
                            country: formData.home_address?.country || ''
                          }
                        })}
                        placeholder="123 Main St"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="city">City</Label>
                      <Input
                        id="city"
                        type="text"
                        value={formData.home_address?.city || ''}
                        onChange={(e) => setFormData({ 
                          ...formData, 
                          home_address: { 
                            street: formData.home_address?.street || '',
                            city: e.target.value,
                            state: formData.home_address?.state || '',
                            postal_code: formData.home_address?.postal_code || '',
                            country: formData.home_address?.country || ''
                          }
                        })}
                        placeholder="New York"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="state">State/Province</Label>
                      <Input
                        id="state"
                        type="text"
                        value={formData.home_address?.state || ''}
                        onChange={(e) => setFormData({ 
                          ...formData, 
                          home_address: { 
                            street: formData.home_address?.street || '',
                            city: formData.home_address?.city || '',
                            state: e.target.value,
                            postal_code: formData.home_address?.postal_code || '',
                            country: formData.home_address?.country || ''
                          }
                        })}
                        placeholder="NY"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="postal_code">Postal Code</Label>
                      <Input
                        id="postal_code"
                        type="text"
                        value={formData.home_address?.postal_code || ''}
                        onChange={(e) => setFormData({ 
                          ...formData, 
                          home_address: { 
                            street: formData.home_address?.street || '',
                            city: formData.home_address?.city || '',
                            state: formData.home_address?.state || '',
                            postal_code: e.target.value,
                            country: formData.home_address?.country || ''
                          }
                        })}
                        placeholder="10001"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="country">Country</Label>
                      <Input
                        id="country"
                        type="text"
                        value={formData.home_address?.country || ''}
                        onChange={(e) => setFormData({ 
                          ...formData, 
                          home_address: { 
                            street: formData.home_address?.street || '',
                            city: formData.home_address?.city || '',
                            state: formData.home_address?.state || '',
                            postal_code: formData.home_address?.postal_code || '',
                            country: e.target.value
                          }
                        })}
                        placeholder="United States"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Emergency Contact Section */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center">
                  <Phone className="w-5 h-5 mr-2 text-primary" />
                  Emergency Contact
                </h4>
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="emergency_contact_name">Contact Name</Label>
                      <Input
                        id="emergency_contact_name"
                        type="text"
                        value={formData.emergency_contact_name}
                        onChange={(e) => setFormData({ ...formData, emergency_contact_name: e.target.value })}
                        placeholder="John Doe"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="emergency_contact_phone">Contact Phone</Label>
                      <Input
                        id="emergency_contact_phone"
                        type="tel"
                        value={formData.emergency_contact_phone}
                        onChange={(e) => setFormData({ ...formData, emergency_contact_phone: e.target.value })}
                        placeholder="+1 (555) 123-4567"
                      />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="emergency_contact_relationship">Relationship</Label>
                      <Input
                        id="emergency_contact_relationship"
                        type="text"
                        value={formData.emergency_contact_relationship}
                        onChange={(e) => setFormData({ ...formData, emergency_contact_relationship: e.target.value })}
                        placeholder="Spouse, Parent, Friend, etc."
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-12 text-center">
              <Shield className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Restricted Access</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">You don't have permission to edit personal information.</p>
            </div>
          )}
        </TabsContent>

        {/* Admin Tab */}
        {canEditAdmin && (
          <TabsContent value="admin" className="mt-4">
            <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-lg p-6">
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <FileText className="w-5 h-5 mr-2 text-amber-600 dark:text-amber-400" />
                Internal Notes
                <span className="ml-auto text-xs text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/50 px-2 py-1 rounded-full">
                  Admin Only
                </span>
              </h4>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-amber-200 dark:border-amber-700">
                <Textarea
                  id="internal_notes"
                  value={formData.internal_notes}
                  onChange={(e) => setFormData({ ...formData, internal_notes: e.target.value })}
                  rows={6}
                  className="min-h-[200px] w-full"
                  placeholder="Add internal notes about this staff member (only visible to admins)..."
                />
              </div>
            </div>
          </TabsContent>
        )}
  </Tabs>

  {/* Form Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={loading}
        >
          {loading ? 'Saving...' : profile ? 'Update Profile' : 'Create Profile'}
        </Button>
      </div>
    </form>
  )
}