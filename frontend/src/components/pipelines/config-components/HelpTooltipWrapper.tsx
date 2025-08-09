'use client'

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui'
import { HelpCircle } from 'lucide-react'

interface HelpTooltipWrapperProps {
  children: React.ReactNode
  helpText: string
  side?: 'top' | 'bottom' | 'left' | 'right'
}

export function HelpTooltipWrapper({
  children,
  helpText,
  side = 'top'
}: HelpTooltipWrapperProps) {
  return (
    <TooltipProvider>
      <div className="flex items-center gap-2">
        {children}
        <Tooltip>
          <TooltipTrigger asChild>
            <HelpCircle className="h-4 w-4 text-muted-foreground hover:text-foreground transition-colors cursor-help" />
          </TooltipTrigger>
          <TooltipContent side={side}>
            <p className="max-w-xs">{helpText}</p>
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  )
}