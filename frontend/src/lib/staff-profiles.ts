/**
 * Staff Profile API service functions
 */

import { api } from './api'
import { 
  StaffProfile, 
  StaffProfileFormData, 
  StaffProfileSummary 
} from '@/types/staff-profile'

/**
 * Get staff profile for a specific user
 */
export async function getStaffProfile(userId: number): Promise<StaffProfile | null> {
  try {
    // Try to get the profile through the user endpoint first
    const response = await api.get(`/api/v1/users/${userId}/staff-profile/`)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 404) {
      // Profile doesn't exist
      return null
    }
    throw error
  }
}

/**
 * Get current user's staff profile
 */
export async function getMyStaffProfile(): Promise<StaffProfile | null> {
  try {
    const response = await api.get('/api/v1/staff-profiles/me/')
    return response.data
  } catch (error: any) {
    if (error.response?.status === 404) {
      return null
    }
    throw error
  }
}

/**
 * Get all staff profiles (with pagination)
 */
export async function getAllStaffProfiles(params?: {
  page?: number
  page_size?: number
  search?: string
  department?: string
  employment_status?: string
}): Promise<{
  results: StaffProfileSummary[]
  count: number
  next: string | null
  previous: string | null
}> {
  try {
    const response = await api.get('/api/v1/staff-profiles/', { params })
    return response.data
  } catch (error) {
    console.error('Failed to fetch staff profiles:', error)
    return {
      results: [],
      count: 0,
      next: null,
      previous: null
    }
  }
}

/**
 * Create a new staff profile for a user
 */
export async function createStaffProfile(
  userId: number,
  data: Partial<StaffProfileFormData>
): Promise<StaffProfile> {
  const response = await api.post('/api/v1/staff-profiles/', {
    user: userId,
    ...data
  })
  return response.data
}

/**
 * Update an existing staff profile
 */
export async function updateStaffProfile(
  profileId: number,
  data: Partial<StaffProfileFormData>
): Promise<StaffProfile> {
  const response = await api.patch(`/api/v1/staff-profiles/${profileId}/`, data)
  return response.data
}

/**
 * Delete a staff profile
 */
export async function deleteStaffProfile(profileId: number): Promise<void> {
  await api.delete(`/api/v1/staff-profiles/${profileId}/`)
}

/**
 * Get list of all departments
 */
export async function getDepartments(): Promise<string[]> {
  try {
    const response = await api.get('/api/v1/staff-profiles/departments/')
    return response.data || []
  } catch (error) {
    console.error('Failed to fetch departments:', error)
    return []
  }
}

/**
 * Get direct reports for a manager
 */
export async function getMyTeam(): Promise<StaffProfile[]> {
  try {
    const response = await api.get('/api/v1/staff-profiles/my-team/')
    return response.data || []
  } catch (error: any) {
    if (error.response?.status === 403) {
      // User is not a manager
      return []
    }
    throw error
  }
}

/**
 * Get reporting chain for a staff member
 */
export async function getReportingChain(profileId: number): Promise<StaffProfile[]> {
  try {
    const response = await api.get(`/api/v1/staff-profiles/${profileId}/reporting-chain/`)
    return response.data || []
  } catch (error) {
    console.error('Failed to fetch reporting chain:', error)
    return []
  }
}

/**
 * Export staff profiles to CSV (admin only)
 */
export async function exportStaffProfiles(): Promise<Blob> {
  const response = await api.get('/api/v1/staff-profiles/export/', {
    responseType: 'blob'
  })
  return response.data
}

/**
 * Check if a user has a staff profile
 */
export async function hasStaffProfile(userId: number): Promise<boolean> {
  try {
    await api.get(`/api/v1/users/${userId}/staff-profile/`)
    return true
  } catch (error: any) {
    if (error.response?.status === 404) {
      return false
    }
    throw error
  }
}

/**
 * Helper function to format employment type
 */
export function formatEmploymentType(type: string): string {
  const types: Record<string, string> = {
    full_time: 'Full Time',
    part_time: 'Part Time',
    contractor: 'Contractor',
    intern: 'Intern',
    consultant: 'Consultant'
  }
  return types[type] || type
}

/**
 * Helper function to format employment status
 */
export function formatEmploymentStatus(status: string): string {
  const statuses: Record<string, string> = {
    active: 'Active',
    on_leave: 'On Leave',
    terminated: 'Terminated',
    resigned: 'Resigned'
  }
  return statuses[status] || status
}

/**
 * Helper function to format work location
 */
export function formatWorkLocation(location: string): string {
  const locations: Record<string, string> = {
    office: 'Office',
    remote: 'Remote',
    hybrid: 'Hybrid'
  }
  return locations[location] || location
}

/**
 * Get employment status color for badges
 */
export function getEmploymentStatusColor(status: string): string {
  switch (status) {
    case 'active':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    case 'on_leave':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    case 'terminated':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    case 'resigned':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
  }
}