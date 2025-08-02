'use client'

import React, { use } from 'react'
import { DynamicFormRenderer } from '@/components/forms/DynamicFormRenderer'
import { notFound } from 'next/navigation'

interface SharedRecordFormPageProps {
  params: Promise<{
    'pipeline-slug': string
    'record-id': string
  }>
  searchParams: Promise<{
    token?: string
  }>
}

export default function SharedRecordFormPage({ 
  params, 
  searchParams 
}: SharedRecordFormPageProps) {
  const resolvedParams = use(params)
  const resolvedSearchParams = use(searchParams)
  const { 'pipeline-slug': pipelineSlug, 'record-id': recordId } = resolvedParams
  const { token } = resolvedSearchParams

  // TODO: Validate token when implemented in Phase 6
  if (!token) {
    notFound()
  }

  const handleFormSubmit = (data: Record<string, any>) => {
    // Show success message
    console.log('Shared record updated:', { recordId, data })
  }

  const handleFormError = (error: string) => {
    console.error('Shared record form error:', error)
    // Could show toast notification here
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Update Shared Record</h1>
          <p className="mt-2 text-gray-600">
            Review and update the information below
          </p>
        </div>
        
        <DynamicFormRenderer
          pipelineSlug={pipelineSlug}
          formType="shared_record"
          recordId={recordId}
          onSubmit={handleFormSubmit}
          onError={handleFormError}
          className="max-w-none"
        />
        
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Shared via Oneo CRM</p>
        </div>
      </div>
    </div>
  )
}