'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { User, AlertTriangle, Search, CheckCircle, Building, Mail, X } from 'lucide-react'

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
  onDisconnect?: () => void
}

export function ContactResolutionBadge({
  contactRecord,
  needsResolution = false,
  domainValidated = true,
  needsDomainReview = false,
  unmatchedData,
  className = '',
  onClick,
  onDisconnect
}: ContactResolutionBadgeProps) {
  const [isHovered, setIsHovered] = useState(false)

  // Helper function to parse title into primary and secondary parts
  const parseContactTitle = (title: string) => {
    if (!title) return { primary: '', secondary: [] }
    
    const parts = title.split('|')
    const primary = parts[0]?.trim() || ''
    
    // Process secondary parts - handle arrays by joining them inline
    const secondary = parts.slice(1)
      .map(part => part.trim())
      .filter(part => part.length > 0)
      .map(part => {
        // If this looks like an array representation, clean it up for inline display
        if (part.startsWith('[') && part.endsWith(']')) {
          // Remove brackets and split on commas, then rejoin with spaces
          return part.slice(1, -1)
            .split(',')
            .map(item => item.trim().replace(/^["']|["']$/g, '')) // Remove quotes
            .join(', ')
        }
        return part
      })
    
    return { primary, secondary }
  }

  // Determine badge state and appearance
  const getBadgeConfig = () => {
    // Matched contact with valid domain
    if (contactRecord && domainValidated && !needsDomainReview) {
      const { primary, secondary } = parseContactTitle(contactRecord.title)
      const displayTitle = primary || contactRecord.title || 'Contact'
      
      return {
        variant: 'default' as const,
        icon: <User className="w-3 h-3" />,
        text: `${displayTitle} • ${contactRecord.pipeline_name}`,
        subtext: null,
        secondary: secondary,
        bgColor: 'bg-green-100 text-green-800 border-green-200',
        tooltip: `Matched to ${displayTitle} in ${contactRecord.pipeline_name}`,
        status: 'matched'
      }
    }

    // Matched contact but domain validation warning
    if (contactRecord && (!domainValidated || needsDomainReview)) {
      const { primary, secondary } = parseContactTitle(contactRecord.title)
      const displayTitle = primary || contactRecord.title || 'Contact'
      
      return {
        variant: 'secondary' as const,
        icon: <AlertTriangle className="w-3 h-3" />,
        text: `${displayTitle} • ${contactRecord.pipeline_name}`,
        subtext: 'Domain Warning',
        secondary: secondary,
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

  const handleDisconnect = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent triggering parent click handlers
    e.preventDefault()
    onDisconnect?.()
  }

  // Determine if disconnect button should be shown
  const showDisconnect = onDisconnect && contactRecord && (config.status === 'matched' || config.status === 'domain-warning')

  const badgeContent = (
    <Badge 
      variant={config.variant}
      className={`
        ${config.bgColor} 
        ${onClick ? 'cursor-pointer hover:bg-gray-700 hover:text-white transition-all duration-200' : ''}
        ${className}
        flex items-center gap-1.5 max-w-none w-fit relative group px-2 py-1
      `}
      onClick={onClick ? handleClick : undefined}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="group-hover:text-white">
        {config.icon}
      </div>
      <div className="flex flex-col items-start flex-1">
        <span className="text-xs font-medium whitespace-nowrap group-hover:text-white">
          {config.text}
        </span>
        {config.subtext && (
          <span className="text-xs opacity-75 whitespace-nowrap group-hover:text-white group-hover:opacity-100">
            {config.subtext}
          </span>
        )}
        {config.secondary && config.secondary.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {config.secondary.map((part, index) => (
              <span 
                key={index}
                className="inline-block text-[10px] px-1.5 py-0.5 rounded bg-white/20 text-current group-hover:text-white"
              >
                {part}
              </span>
            ))}
          </div>
        )}
      </div>
      
      {/* Show disconnect button for connected contacts */}
      {showDisconnect && isHovered && (
        <Button
          variant="ghost"
          size="sm"
          className="h-4 w-4 p-0 ml-1 hover:bg-red-100 text-red-600 hover:text-red-700 transition-colors"
          onClick={handleDisconnect}
          title="Disconnect contact"
        >
          <X className="w-3 h-3" />
        </Button>
      )}
      
      {/* Show arrow for clickable badges without disconnect */}
      {onClick && isHovered && !showDisconnect && (
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
            <p className="text-xs opacity-75 mt-1">
              Click to {config.status === 'matched' ? 'view contact' : config.status === 'unmatched' ? 'resolve contact' : 'review validation'}
              {showDisconnect && <span className="block">Hover and click X to disconnect</span>}
            </p>
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