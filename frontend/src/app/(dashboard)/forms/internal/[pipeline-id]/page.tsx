'use client'

import React, { use } from 'react'
import { DynamicFormRenderer } from '@/components/forms/DynamicFormRenderer'
import { useRouter } from 'next/navigation'

interface InternalFormPageProps {
  params: Promise<{
    'pipeline-id': string
  }>
  searchParams: Promise<{
    stage?: string
    recordId?: string
    embed?: string
  }>
}

export default function InternalFormPage({ 
  params, 
  searchParams 
}: InternalFormPageProps) {
  const router = useRouter()
  const resolvedParams = use(params)
  const resolvedSearchParams = use(searchParams)
  const { 'pipeline-id': pipelineId } = resolvedParams
  const { stage, recordId, embed } = resolvedSearchParams

  // Determine form type based on parameters
  const formType = stage ? 'stage_internal' : 'internal_full'
  const isEmbed = embed === 'true'

  const handleFormSubmit = (data: Record<string, any>) => {
    if (recordId) {
      // Record updated, could redirect back to record detail
      router.push(`/pipelines/${pipelineId}/records/${recordId}`)
    } else {
      // New record created, could redirect to record list or detail
      router.push(`/pipelines/${pipelineId}`)
    }
  }

  const handleFormError = (error: string) => {
    console.error('Internal form error:', error)
    // Could show toast notification here
  }

  const containerClass = isEmbed 
    ? 'w-full' 
    : 'min-h-screen bg-gray-50 dark:bg-gray-900 py-8'

  const contentClass = isEmbed
    ? 'w-full'
    : 'max-w-2xl mx-auto px-4 sm:px-6 lg:px-8'

  return (
    <div className={containerClass}>
      <div className={contentClass}>
        {!isEmbed && (
          <div className="mb-8">
            <button
              onClick={() => router.back()}
              className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm font-medium"
            >
              ← Back
            </button>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {recordId ? 'Edit Record' : 'Create New Record'}
              {stage && ` - ${stage.charAt(0).toUpperCase() + stage.slice(1)} Stage`}
            </h1>
          </div>
        )}
        
        <DynamicFormRenderer
          pipelineId={pipelineId}
          formType={formType}
          stage={stage}
          recordId={recordId}
          onSubmit={handleFormSubmit}
          onError={handleFormError}
          embedMode={isEmbed}
          className="max-w-none"
        />
      </div>
    </div>
  )
}