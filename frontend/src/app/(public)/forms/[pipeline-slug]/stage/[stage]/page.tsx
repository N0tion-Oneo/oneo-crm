'use client'

import React, { use } from 'react'
import { DynamicFormRenderer } from '@/components/forms/DynamicFormRenderer'
import { notFound } from 'next/navigation'

interface PublicStageFormPageProps {
  params: Promise<{
    'pipeline-slug': string
    stage: string
  }>
}

export default function PublicStageFormPage({ params }: PublicStageFormPageProps) {
  const resolvedParams = use(params)
  const { 'pipeline-slug': pipelineSlug, stage } = resolvedParams

  const handleFormSubmit = (data: Record<string, any>) => {
    // Show success message or redirect
    console.log('Stage form submitted:', { stage, data })
  }

  const handleFormError = (error: string) => {
    console.error('Stage form error:', error)
    // Could show toast notification here
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            {stage.charAt(0).toUpperCase() + stage.slice(1)} Stage Form
          </h1>
          <p className="mt-2 text-gray-600">
            Complete the required fields for the {stage} stage
          </p>
        </div>
        
        <DynamicFormRenderer
          pipelineSlug={pipelineSlug}
          formType="stage_public"
          stage={stage}
          onSubmit={handleFormSubmit}
          onError={handleFormError}
          className="max-w-none"
        />
        
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Powered by Oneo CRM</p>
        </div>
      </div>
    </div>
  )
}