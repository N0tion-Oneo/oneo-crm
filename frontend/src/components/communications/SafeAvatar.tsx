'use client'

import React, { useState, useEffect } from 'react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

interface SafeAvatarProps {
  src?: string | null
  fallbackText: string
  className?: string
  fallbackClassName?: string
}

/**
 * SafeAvatar component that handles problematic URL schemes gracefully
 * Specifically designed to handle WhatsApp's wapp:// URLs and other custom schemes
 * that browsers cannot load, preventing console errors and improving UX
 */
export const SafeAvatar: React.FC<SafeAvatarProps> = ({
  src,
  fallbackText,
  className = 'w-10 h-10',
  fallbackClassName = 'bg-gray-100 text-gray-700'
}) => {
  const [imageError, setImageError] = useState(false)
  
  // Check if URL is a problematic scheme that browsers can't load
  const isValidImageUrl = (url: string | undefined | null): boolean => {
    if (!url) return false
    // Block custom schemes that browsers can't load
    const invalidSchemes = ['wapp://', 'whatsapp://', 'linkedin://', 'telegram://', 'signal://']
    return !invalidSchemes.some(scheme => url.startsWith(scheme))
  }
  
  // Reset error state when src changes
  useEffect(() => {
    setImageError(false)
  }, [src])
  
  const validImageUrl = isValidImageUrl(src) && !imageError ? src : undefined
  
  return (
    <Avatar className={className}>
      <AvatarImage 
        src={validImageUrl || undefined}
        onError={() => setImageError(true)}
      />
      <AvatarFallback className={fallbackClassName}>
        {fallbackText}
      </AvatarFallback>
    </Avatar>
  )
}