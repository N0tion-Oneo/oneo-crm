'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { User, AlertTriangle, Search, CheckCircle, Building, Mail } from 'lucide-react'

interface ContactRecord {
  id: string
  title: string
  pipeline_id: string
  pipeline_name: string
  data: Record<string, any>
}

interface ContactResolutionBadgeProps {
  contactRecord?: ContactRecord | null
  needsResolution?: boolean
  domainValidated?: boolean
  needsDomainReview?: boolean
  unmatchedData?: {
    email?: string
    phone?: string
    name?: string
    [key: string]: any
  }
  className?: string
  onClick?: () => void
}

export function ContactResolutionBadge({
  contactRecord,
  needsResolution = false,
  domainValidated = true,
  needsDomainReview = false,
  unmatchedData,
  className = '',
  onClick
}: ContactResolutionBadgeProps) {
  const [isHovered, setIsHovered] = useState(false)

  // Determine badge state and appearance
  const getBadgeConfig = () => {
    // Matched contact with valid domain
    if (contactRecord && domainValidated && !needsDomainReview) {
      return {
        variant: 'default' as const,
        icon: <User className="w-3 h-3" />,
        text: contactRecord.title || 'Contact',
        subtext: contactRecord.pipeline_name,
        bgColor: 'bg-green-100 text-green-800 border-green-200',
        tooltip: `Matched to ${contactRecord.title} in ${contactRecord.pipeline_name}`,
        status: 'matched'
      }
    }

    // Matched contact but domain validation warning
    if (contactRecord && (!domainValidated || needsDomainReview)) {
      return {
        variant: 'secondary' as const,
        icon: <AlertTriangle className="w-3 h-3" />,
        text: contactRecord.title || 'Contact',
        subtext: 'Domain Warning',
        bgColor: 'bg-yellow-100 text-yellow-800 border-yellow-200',
        tooltip: `Contact matched but domain validation needs review`,
        status: 'domain-warning'
      }
    }

    // Unmatched contact needing resolution
    if (needsResolution || (!contactRecord && unmatchedData)) {
      return {
        variant: 'destructive' as const,
        icon: <Search className="w-3 h-3" />,
        text: 'Unmatched',
        subtext: unmatchedData?.name || unmatchedData?.email || 'Unknown',
        bgColor: 'bg-red-100 text-red-800 border-red-200',
        tooltip: `No contact matched - needs manual resolution`,
        status: 'unmatched'
      }
    }

    // No contact info available (shouldn't happen normally)
    return {
      variant: 'outline' as const,
      icon: <Mail className="w-3 h-3" />,
      text: 'No Contact',
      subtext: '',
      bgColor: 'bg-gray-100 text-gray-600 border-gray-200',
      tooltip: 'No contact information available',
      status: 'none'
    }
  }

  const config = getBadgeConfig()

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent triggering parent click handlers
    onClick?.()
  }

  const badgeContent = (
    <Badge 
      variant={config.variant}
      className={`
        ${config.bgColor} 
        ${onClick ? 'cursor-pointer hover:opacity-80 transition-opacity' : ''}
        ${className}
        flex items-center gap-1.5 max-w-48
      `}
      onClick={onClick ? handleClick : undefined}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {config.icon}
      <div className="flex flex-col items-start min-w-0">
        <span className="text-xs font-medium truncate">
          {config.text}
        </span>
        {config.subtext && (
          <span className="text-xs opacity-75 truncate">
            {config.subtext}
          </span>
        )}
      </div>
      {onClick && isHovered && (
        <span className="text-xs opacity-75 ml-1">→</span>
      )}
    </Badge>
  )

  if (onClick) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            {badgeContent}
          </TooltipTrigger>
          <TooltipContent>
            <p>{config.tooltip}</p>
            <p className="text-xs opacity-75 mt-1">Click to {config.status === 'matched' ? 'view contact' : config.status === 'unmatched' ? 'resolve contact' : 'review validation'}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {badgeContent}
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

// Compact version for use in conversation lists
export function ContactResolutionIndicator({
  contactRecord,
  needsResolution = false,
  domainValidated = true,
  needsDomainReview = false,
  onClick
}: Pick<ContactResolutionBadgeProps, 'contactRecord' | 'needsResolution' | 'domainValidated' | 'needsDomainReview' | 'onClick'>) {
  const getIndicatorConfig = () => {
    if (contactRecord && domainValidated && !needsDomainReview) {
      return {
        icon: <CheckCircle className="w-4 h-4 text-green-600" />,
        tooltip: `Matched to ${contactRecord.title}`,
        status: 'matched'
      }
    }

    if (contactRecord && (!domainValidated || needsDomainReview)) {
      return {
        icon: <AlertTriangle className="w-4 h-4 text-yellow-600" />,
        tooltip: 'Contact matched but needs domain review',
        status: 'warning'
      }
    }

    if (needsResolution) {
      return {
        icon: <Search className="w-4 h-4 text-red-600" />,
        tooltip: 'Unmatched contact - needs resolution',
        status: 'unmatched'
      }
    }

    return null
  }

  const config = getIndicatorConfig()
  if (!config) return null

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onClick?.()
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 hover:bg-transparent"
            onClick={onClick ? handleClick : undefined}
          >
            {config.icon}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.tooltip}</p>
          {onClick && (
            <p className="text-xs opacity-75 mt-1">Click to {config.status === 'matched' ? 'view' : 'resolve'}</p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}