/**
 * DependencyWarning Component
 * 
 * Displays warnings when a user type lacks required static permissions
 * for dynamic resource access, with quick action buttons to grant them.
 */

import React from 'react'
import { AlertTriangle } from 'lucide-react'
import { UserType, getDependencyWarning } from '@/utils/permission-dependencies'

interface DependencyWarningProps {
  userType: UserType
  resourceType: string
}

export const DependencyWarning: React.FC<DependencyWarningProps> = ({
  userType,
  resourceType
}) => {
  const warningMessage = getDependencyWarning(userType, resourceType)
  
  if (!warningMessage) {
    return null
  }

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
      <div className="flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <div className="text-yellow-800 text-sm">
            {warningMessage}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DependencyWarning