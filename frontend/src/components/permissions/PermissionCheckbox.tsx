/**
 * PermissionCheckbox Component
 * 
 * Enhanced checkbox component that handles different permission states
 * with visual feedback and tooltips for permission dependencies.
 */

import React from 'react'
import { Check, Lock } from 'lucide-react'
import { 
  PermissionState, 
  getPermissionStateClasses, 
  getPermissionTooltip,
  UserType 
} from '@/utils/permission-dependencies'

interface PermissionCheckboxProps {
  userType: UserType
  resourceType: string
  resourceName: string
  resourceId: string | number
  state: PermissionState
  onChange?: (granted: boolean) => Promise<void>
  isChanging?: boolean
  className?: string
}

export const PermissionCheckbox: React.FC<PermissionCheckboxProps> = ({
  userType,
  resourceType,
  resourceName,
  resourceId,
  state,
  onChange,
  isChanging = false,
  className = ''
}) => {
  const handleClick = async () => {
    if (state === 'disabled' || isChanging || !onChange) return
    
    const newGranted = state === 'available'
    await onChange(newGranted)
  }

  const tooltipMessage = getPermissionTooltip(state, userType, resourceType, resourceName)
  const stateClasses = getPermissionStateClasses(state)
  
  const renderCheckboxContent = () => {
    if (isChanging) {
      return (
        <div className="w-4 h-4 border-2 border-blue-600 rounded-sm animate-spin" 
             style={{ borderTopColor: 'transparent' }} />
      )
    }
    
    switch (state) {
      case 'enabled':
        return <Check className="w-4 h-4" />
      case 'disabled':
        return <Lock className="w-3 h-3 text-gray-400" />
      case 'available':
        return null
      default:
        return null
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={state === 'disabled' || isChanging}
      className={`
        w-6 h-6 rounded-sm border-2 flex items-center justify-center transition-all duration-200
        ${stateClasses}
        ${className}
      `}
      title={tooltipMessage}
    >
      {renderCheckboxContent()}
    </button>
  )
}

export default PermissionCheckbox