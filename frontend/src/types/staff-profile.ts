/**
 * Staff Profile types for comprehensive employee information
 */

export interface EducationRecord {
  degree: string
  institution: string
  year: string
  field_of_study?: string
}

export interface Address {
  street: string
  city: string
  state: string
  postal_code: string
  country: string
}

export type EmploymentType = 'full_time' | 'part_time' | 'contractor' | 'intern' | 'consultant'
export type EmploymentStatus = 'active' | 'on_leave' | 'terminated' | 'resigned'
export type WorkLocation = 'office' | 'remote' | 'hybrid'

export interface StaffProfile {
  id: number
  user: number
  user_email?: string
  user_full_name?: string
  user_phone?: string
  user_type?: string
  
  // Professional Information
  employee_id: string
  job_title: string
  department: string
  employment_type: EmploymentType
  employment_status: EmploymentStatus
  start_date: string
  end_date?: string | null
  
  // Work Details
  work_location: WorkLocation
  office_location: string
  work_phone_extension: string
  reporting_manager?: number | null
  reporting_manager_email?: string
  reporting_manager_name?: string
  
  // Professional Details
  certifications: string[]
  education: EducationRecord[] | Record<string, any>
  bio: string
  linkedin_profile: string
  professional_links: Record<string, string>
  
  // Emergency & Personal (permission-based visibility)
  emergency_contact_name?: string
  emergency_contact_phone?: string
  emergency_contact_relationship?: string
  date_of_birth?: string | null
  nationality?: string
  personal_email?: string
  home_address?: Address | Record<string, any>
  
  // Administrative (restricted access)
  internal_notes?: string
  
  // Metadata
  is_manager?: boolean
  direct_reports_count?: number
  created_at?: string
  updated_at?: string
  created_by?: number
}

export interface StaffProfileFormData {
  // Professional Information
  employee_id: string
  job_title: string
  department: string
  employment_type: EmploymentType
  employment_status: EmploymentStatus
  start_date: string
  end_date?: string
  
  // Work Details
  work_location: WorkLocation
  office_location: string
  work_phone_extension: string
  reporting_manager?: number | null
  
  // Professional Details
  certifications: string[]
  education: EducationRecord[]
  bio: string
  linkedin_profile: string
  professional_links: Record<string, string>
  
  // Emergency & Personal
  emergency_contact_name: string
  emergency_contact_phone: string
  emergency_contact_relationship: string
  date_of_birth?: string
  nationality: string
  personal_email: string
  home_address: Address
  
  // Administrative
  internal_notes?: string
}

export interface StaffProfileSummary {
  id: number
  employee_id: string
  user_email: string
  user_full_name: string
  job_title: string
  department: string
  employment_status: EmploymentStatus
}

// Permission-based field groups
export const PUBLIC_FIELDS = [
  'id', 'user_email', 'user_full_name', 'user_type',
  'job_title', 'department', 'work_location', 'office_location',
  'bio', 'linkedin_profile', 'reporting_manager_name'
]

export const SENSITIVE_FIELDS = [
  'date_of_birth', 'nationality', 'personal_email', 'home_address',
  'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship'
]

export const ADMIN_FIELDS = ['internal_notes']

// Field labels for display
export const FIELD_LABELS: Record<string, string> = {
  employee_id: 'Employee ID',
  job_title: 'Job Title',
  department: 'Department',
  employment_type: 'Employment Type',
  employment_status: 'Employment Status',
  start_date: 'Start Date',
  end_date: 'End Date',
  work_location: 'Work Location',
  office_location: 'Office Location',
  work_phone_extension: 'Extension',
  reporting_manager: 'Reporting Manager',
  certifications: 'Certifications',
  languages_spoken: 'Languages',
  education: 'Education',
  bio: 'Biography',
  linkedin_profile: 'LinkedIn Profile',
  professional_links: 'Professional Links',
  emergency_contact_name: 'Emergency Contact Name',
  emergency_contact_phone: 'Emergency Contact Phone',
  emergency_contact_relationship: 'Emergency Contact Relationship',
  date_of_birth: 'Date of Birth',
  nationality: 'Nationality',
  personal_email: 'Personal Email',
  home_address: 'Home Address',
  internal_notes: 'Internal Notes'
}

// Employment type display values
export const EMPLOYMENT_TYPE_LABELS: Record<EmploymentType, string> = {
  full_time: 'Full Time',
  part_time: 'Part Time',
  contractor: 'Contractor',
  intern: 'Intern',
  consultant: 'Consultant'
}

// Employment status display values
export const EMPLOYMENT_STATUS_LABELS: Record<EmploymentStatus, string> = {
  active: 'Active',
  on_leave: 'On Leave',
  terminated: 'Terminated',
  resigned: 'Resigned'
}

// Work location display values
export const WORK_LOCATION_LABELS: Record<WorkLocation, string> = {
  office: 'Office',
  remote: 'Remote',
  hybrid: 'Hybrid'
}