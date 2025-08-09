'use client'

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui'

interface ConfigSectionProps {
  title: string
  description?: string
  children: React.ReactNode
  defaultOpen?: boolean
  value?: string
}

export function ConfigSection({
  title,
  description,
  children,
  defaultOpen = false,
  value = 'section'
}: ConfigSectionProps) {
  return (
    <Accordion type="single" collapsible defaultValue={defaultOpen ? value : undefined}>
      <AccordionItem value={value} className="border rounded-md">
        <AccordionTrigger className="px-4 py-3 hover:no-underline">
          <div className="text-left">
            <div className="font-medium text-gray-900 dark:text-white">{title}</div>
            {description && (
              <div className="text-sm text-muted-foreground mt-1">{description}</div>
            )}
          </div>
        </AccordionTrigger>
        <AccordionContent className="px-4 pb-4">
          {children}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}