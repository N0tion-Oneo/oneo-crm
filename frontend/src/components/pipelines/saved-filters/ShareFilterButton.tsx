'use client'

import { useState } from 'react'
import { Share2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'
import { SavedFilter } from './SavedFiltersList'
import { ShareFilterModal } from './ShareFilterModal'

interface ShareFilterButtonProps {
  filter: SavedFilter
  className?: string
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'default' | 'sm' | 'lg'
}

export function ShareFilterButton({
  filter,
  className = '',
  variant = 'outline',
  size = 'default'
}: ShareFilterButtonProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <PermissionGuard
        category="sharing"
        action="create_shared_views"
        fallback={
          <Button
            variant={variant}
            size={size}
            className={`${className} opacity-50 cursor-not-allowed`}
            disabled={true}
            title="You don't have permission to share filters"
          >
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </Button>
        }
      >
        <Button
          variant={variant}
          size={size}
          className={className}
          onClick={() => setIsOpen(true)}
        >
          <Share2 className="w-4 h-4 mr-2" />
          Share
        </Button>
      </PermissionGuard>

      <ShareFilterModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        filter={filter}
        onShared={(sharedFilter) => {
          console.log('Filter shared:', sharedFilter)
          // Handle successful share if needed
        }}
      />
    </>
  )
}