/**
 * Utility functions for handling shared access modes consistently across components
 */

export type SharedAccessMode = 'view_only' | 'filtered_edit' | 'comment' | 'export'

export interface AccessPermissions {
  canView: boolean
  canEdit: boolean
  canCreate: boolean
  canDelete: boolean
  canComment: boolean
  canExport: boolean
  isReadOnly: boolean
}

/**
 * Convert access mode to granular permissions
 */
export function getAccessPermissions(accessMode: SharedAccessMode): AccessPermissions {
  switch (accessMode) {
    case 'view_only':
      return {
        canView: true,
        canEdit: false,
        canCreate: false,
        canDelete: false,
        canComment: false,
        canExport: false,
        isReadOnly: true
      }
    
    case 'filtered_edit':
      return {
        canView: true,
        canEdit: true,
        canCreate: true,
        canDelete: false, // Usually no delete in filtered edit
        canComment: true,
        canExport: true,
        isReadOnly: false
      }
    
    case 'comment':
      return {
        canView: true,
        canEdit: false,
        canCreate: false,
        canDelete: false,
        canComment: true,
        canExport: false,
        isReadOnly: true
      }
    
    case 'export':
      return {
        canView: true,
        canEdit: false,
        canCreate: false,
        canDelete: false,
        canComment: false,
        canExport: true,
        isReadOnly: true
      }
    
    default:
      // Fallback to most restrictive
      return {
        canView: true,
        canEdit: false,
        canCreate: false,
        canDelete: false,
        canComment: false,
        canExport: false,
        isReadOnly: true
      }
  }
}

/**
 * Get user-friendly access mode display name
 */
export function getAccessModeDisplayName(accessMode: SharedAccessMode): string {
  switch (accessMode) {
    case 'view_only':
      return 'View Only'
    case 'filtered_edit':
      return 'Filtered Edit'
    case 'comment':
      return 'View + Comment'
    case 'export':
      return 'View + Export'
    default:
      return accessMode
  }
}

/**
 * Get user-friendly access mode description
 */
export function getAccessModeDescription(accessMode: SharedAccessMode): string {
  switch (accessMode) {
    case 'view_only':
      return 'You can view all records but cannot make changes.'
    case 'filtered_edit':
      return 'You can view and edit records within the filter constraints.'
    case 'comment':
      return 'You can view records and add comments.'
    case 'export':
      return 'You can view records and export the filtered data.'
    default:
      return 'You have limited access to this data.'
  }
}

/**
 * Get appropriate error message for restricted actions
 */
export function getAccessDeniedMessage(accessMode: SharedAccessMode, action: 'create' | 'edit' | 'delete' | 'comment' | 'export'): string {
  const modeName = getAccessModeDisplayName(accessMode)
  
  switch (action) {
    case 'create':
      return `Your ${modeName} access doesn't allow creating new records.`
    case 'edit':
      return `Your ${modeName} access doesn't allow editing records.`
    case 'delete':
      return `Your ${modeName} access doesn't allow deleting records.`
    case 'comment':
      return `Your ${modeName} access doesn't allow commenting.`
    case 'export':
      return `Your ${modeName} access doesn't allow exporting data.`
    default:
      return `This action is not allowed with ${modeName} access.`
  }
}