'use client'

import { useState, useEffect } from 'react'
import { createStaffProfile, updateStaffProfile } from '@/lib/staff-profiles'
import { StaffProfile, StaffProfileFormData, EmploymentType, EmploymentStatus, WorkLocation } from '@/types/staff-profile'
import { useAuth } from '@/features/auth/context'
import { AlertTriangle } from 'lucide-react'
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
import { Briefcase, User, Shield, Building, FileText } from 'lucide-react'

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
    certifications: [],
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
        certifications: profile.certifications || [],
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
        home_address: typeof profile.home_address === 'object' ? profile.home_address : {
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
      setError(err.response?.data?.detail || err.message || 'Failed to save profile')
    } finally {
      setLoading(false)
    }
  }

  const handleArrayFieldAdd = (field: 'certifications', value: string) => {
    if (value.trim()) {
      setFormData(prev => ({
        ...prev,
        [field]: [...(prev[field] || []), value.trim()]
      }))
    }
  }

  const handleArrayFieldRemove = (field: 'certifications', index: number) => {
    setFormData(prev => ({
      ...prev,
      [field]: (prev[field] || []).filter((_, i) => i !== index)
    }))
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
          {canEditAdmin && (
            <TabsTrigger value="admin" className="text-xs">
              <Shield className="w-4 h-4 mr-1" />
              Admin
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="employment" className="mt-4">
          <div>
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Employment Information
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="employee_id">
              Employee ID <span className="text-red-500">*</span>
            </Label>
            <Input
              id="employee_id"
              type="text"
              value={formData.employee_id}
              onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="job_title">
              Job Title <span className="text-red-500">*</span>
            </Label>
            <Input
              id="job_title"
              type="text"
              value={formData.job_title}
              onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="department">Department</Label>
            <Input
              id="department"
              type="text"
              value={formData.department}
              onChange={(e) => setFormData({ ...formData, department: e.target.value })}
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
            <Label htmlFor="start_date">
              Start Date <span className="text-red-500">*</span>
            </Label>
            <Input
              id="start_date"
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              required
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

        <TabsContent value="work" className="mt-4">
          <div>
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Work Details
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

          <div className="space-y-2">
            <Label htmlFor="office_location">Office Location</Label>
            <Input
              id="office_location"
              type="text"
              value={formData.office_location}
              onChange={(e) => setFormData({ ...formData, office_location: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="work_phone_extension">Work Phone Extension</Label>
            <Input
              id="work_phone_extension"
              type="text"
              value={formData.work_phone_extension}
              onChange={(e) => setFormData({ ...formData, work_phone_extension: e.target.value })}
            />
          </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="qualifications" className="mt-4">
          <div>
            <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Professional Qualifications
            </h4>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="bio">Biography</Label>
                <Textarea
                  id="bio"
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  rows={4}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="linkedin_profile">LinkedIn Profile</Label>
                <Input
                  id="linkedin_profile"
                  type="url"
                  value={formData.linkedin_profile}
                  onChange={(e) => setFormData({ ...formData, linkedin_profile: e.target.value })}
                  placeholder="https://linkedin.com/in/username"
                />
              </div>

              <div className="space-y-2">
                <Label>Certifications</Label>
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <Input
                      type="text"
                      placeholder="Add certification"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleArrayFieldAdd('certifications', (e.target as HTMLInputElement).value)
                          ;(e.target as HTMLInputElement).value = ''
                        }
                      }}
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {formData.certifications?.map((cert, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                      >
                        {cert}
                        <button
                          type="button"
                          onClick={() => handleArrayFieldRemove('certifications', index)}
                          className="ml-1.5 inline-flex items-center justify-center w-4 h-4 text-blue-400 hover:text-blue-600"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="personal" className="mt-4">
          {canEditSensitive ? (
            <div className="space-y-6">
              <div>
                <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
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
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="personal_email">Personal Email</Label>
              <Input
                id="personal_email"
                type="email"
                value={formData.personal_email}
                onChange={(e) => setFormData({ ...formData, personal_email: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="emergency_contact_name">Emergency Contact Name</Label>
              <Input
                id="emergency_contact_name"
                type="text"
                value={formData.emergency_contact_name}
                onChange={(e) => setFormData({ ...formData, emergency_contact_name: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="emergency_contact_phone">Emergency Contact Phone</Label>
              <Input
                id="emergency_contact_phone"
                type="tel"
                value={formData.emergency_contact_phone}
                onChange={(e) => setFormData({ ...formData, emergency_contact_phone: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="emergency_contact_relationship">Emergency Contact Relationship</Label>
              <Input
                id="emergency_contact_relationship"
                type="text"
                value={formData.emergency_contact_relationship}
                onChange={(e) => setFormData({ ...formData, emergency_contact_relationship: e.target.value })}
              />
            </div>
              </div>
            </div>
          </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <User className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>You don't have permission to edit personal information.</p>
            </div>
          )}
        </TabsContent>

        {canEditAdmin && (
          <TabsContent value="admin" className="mt-4">
            <div className="space-y-2">
              <Label htmlFor="internal_notes">
                Internal Notes (Admin Only)
              </Label>
              <Textarea
                id="internal_notes"
                value={formData.internal_notes}
                onChange={(e) => setFormData({ ...formData, internal_notes: e.target.value })}
                rows={6}
                className="min-h-[200px]"
              />
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