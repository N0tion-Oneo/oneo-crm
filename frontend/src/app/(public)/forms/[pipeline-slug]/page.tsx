'use client'

import React, { use } from 'react'
import { DynamicFormRenderer } from '@/components/forms/DynamicFormRenderer'
import { notFound } from 'next/navigation'

interface PublicFormPageProps {
  params: Promise<{
    'pipeline-slug': string
  }>
}

export default function PublicFormPage({ params }: PublicFormPageProps) {
  const resolvedParams = use(params)
  const pipelineSlug = resolvedParams['pipeline-slug']

  const handleFormSubmit = (data: Record<string, any>) => {
    // Show success message or redirect
    console.log('Form submitted:', data)
  }

  const handleFormError = (error: string) => {
    console.error('Form error:', error)
    // Could show toast notification here
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Public Form</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Please fill out all required fields below
          </p>
        </div>
        
        <DynamicFormRenderer
          pipelineSlug={pipelineSlug}
          formType="public_filtered"
          onSubmit={handleFormSubmit}
          onError={handleFormError}
          className="max-w-none"
        />
        
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>Powered by Oneo CRM</p>
        </div>
      </div>
    </div>
  )
}