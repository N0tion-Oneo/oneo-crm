'use client'

import React, { useState, useEffect } from 'react'
import { formsApi, pipelinesApi } from '@/lib/api'
import { FormTemplate } from '@/types/forms'
import FormBuilder from './FormBuilder'

export default function FormsManager() {
  const [activeTab, setActiveTab] = useState<'dynamic' | 'custom'>('dynamic')
  const [customForms, setCustomForms] = useState<FormTemplate[]>([])
  const [pipelines, setPipelines] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form builder state
  const [showFormBuilder, setShowFormBuilder] = useState(false)
  const [editingForm, setEditingForm] = useState<FormTemplate | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [formsRes, pipelinesRes] = await Promise.all([
        formsApi.getForms(),
        pipelinesApi.list()
      ])

      setCustomForms(formsRes.data.results || [])
      setPipelines(pipelinesRes.data.results || [])
    } catch (err: any) {
      console.error('Error loading forms data:', err)
      setError(`Failed to load forms data: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateForm = () => {
    setEditingForm(null)
    setShowFormBuilder(true)
  }

  const handleEditForm = (form: FormTemplate) => {
    setEditingForm(form)
    setShowFormBuilder(true)
  }

  const handleFormSaved = async (savedForm: FormTemplate) => {
    if (editingForm) {
      setCustomForms(prev => prev.map(f => f.id === savedForm.id ? savedForm : f))
    } else {
      setCustomForms(prev => [...prev, savedForm])
    }
    setShowFormBuilder(false)
    setEditingForm(null)
  }

  const handleDeleteForm = async (id: number) => {
    try {
      await formsApi.deleteForm(id.toString())
      setCustomForms(prev => prev.filter(f => f.id !== id))
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to delete form')
    }
  }

  const handleGenerateDynamicForm = async (pipeline: any) => {
    try {
      // Create a dynamic form with all visible fields
      const formData = {
        name: `${pipeline.name} - Dynamic Form`,
        description: `Auto-generated form for ${pipeline.name} pipeline`,
        pipeline: pipeline.slug, // Use slug for API
        form_type: 'dynamic',
        dynamic_mode: 'visible',
        success_message: 'Thank you for your submission!',
        is_active: true
      }

      const response = await formsApi.createForm(formData)
      const newForm = response.data

      // Add all visible fields automatically
      if (pipeline.fields && pipeline.fields.length > 0) {
        const visibleFields = pipeline.fields.filter((field: any) => field.is_visible_in_detail)
        
        const fieldPromises = visibleFields.map((field: any, index: number) => {
          return formsApi.createFormField({
            form_template: newForm.id,
            pipeline_field: field.slug, // Use slug instead of ID
            display_order: index,
            is_visible: true,
            is_readonly: false,
            custom_label: '',
            custom_placeholder: '',
            custom_help_text: '',
            conditional_logic: field.is_required ? { required: true } : {},
            default_value: null,
            field_width: 'full',
            is_active: true
          })
        })

        await Promise.all(fieldPromises)
      }

      // Add to forms list and show success
      setCustomForms(prev => [...prev, newForm])
      alert(`Dynamic form "${newForm.name}" created successfully with ${pipeline.fields?.filter((f: any) => f.is_visible_in_detail).length || 0} fields!`)
      
    } catch (err: any) {
      console.error('Error creating dynamic form:', err)
      setError(err.response?.data?.message || 'Failed to create dynamic form')
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center min-h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading forms...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-medium">Error Loading Forms</h3>
          <p className="text-red-600 mt-1">{error}</p>
          <button 
            onClick={loadData}
            className="mt-3 px-4 py-2 bg-red-100 text-red-800 rounded hover:bg-red-200"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Show form builder
  if (showFormBuilder) {
    return (
      <FormBuilder
        form={editingForm}
        pipelines={pipelines}
        onSave={handleFormSaved}
        onCancel={() => {
          setShowFormBuilder(false)
          setEditingForm(null)
        }}
      />
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Forms</h1>
          <p className="text-gray-600 mt-1">Create forms to collect data into your pipelines</p>
        </div>
        <button 
          onClick={loadData}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          Refresh
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { key: 'dynamic', label: 'Dynamic Forms', count: pipelines.length },
            { key: 'custom', label: 'Custom Forms', count: customForms.length }
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
              <span className="ml-2 px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full">
                {tab.count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'dynamic' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Dynamic Forms</h2>
              <p className="text-gray-600 text-sm">Auto-generated forms from your pipelines</p>
            </div>
          </div>

          {pipelines.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {pipelines.map(pipeline => (
                <div key={pipeline.id} className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                  <div className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 text-lg">{pipeline.name}</h3>
                        {pipeline.description && (
                          <p className="text-gray-600 text-sm mt-1">{pipeline.description}</p>
                        )}
                      </div>
                      <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                        Pipeline
                      </span>
                    </div>
                    
                    <div className="space-y-2 mb-4">
                      <div className="flex items-center text-sm text-gray-600">
                        <span className="w-16">Fields:</span>
                        <span className="font-medium">{pipeline.fields?.length || 0}</span>
                      </div>
                      <div className="flex items-center text-sm text-gray-600">
                        <span className="w-16">Type:</span>
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                          {pipeline.pipeline_type}
                        </span>
                      </div>
                    </div>

                    <div className="pt-4 border-t border-gray-100">
                      <p className="text-xs text-gray-500 mb-3">
                        Dynamic forms automatically include all visible fields from this pipeline
                      </p>
                      <button 
                        onClick={() => handleGenerateDynamicForm(pipeline)}
                        className="w-full px-3 py-2 text-blue-600 hover:bg-blue-50 rounded text-sm border border-blue-200"
                      >
                        Generate Dynamic Form
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM21 17a2 2 0 11-4 0 2 2 0 014 0zM7 13h10l4-8H5.4l-.8-2H1" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No pipelines available</h3>
              <p className="mt-1 text-sm text-gray-500">Create a pipeline first to generate dynamic forms.</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'custom' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Custom Forms</h2>
              <p className="text-gray-600 text-sm">Create custom forms with selected pipeline fields</p>
            </div>
            <button 
              onClick={handleCreateForm}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Create Form
            </button>
          </div>

          {customForms.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {customForms.map(form => (
                <div key={form.id} className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                  <div className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 text-lg">{form.name}</h3>
                        {form.description && (
                          <p className="text-gray-600 text-sm mt-1">{form.description}</p>
                        )}
                      </div>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        form.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {form.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    
                    <div className="space-y-2 mb-4">
                      <div className="flex items-center text-sm text-gray-600">
                        <span className="w-16">Type:</span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                          {form.form_type}
                        </span>
                      </div>
                      <div className="flex items-center text-sm text-gray-600">
                        <span className="w-16">Pipeline:</span>
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">
                          {pipelines.find(p => p.id == form.pipeline)?.name || 'Unknown'}
                        </span>
                      </div>
                    </div>

                    <div className="flex justify-between items-center pt-4 border-t border-gray-100">
                      <span className="text-xs text-gray-500">
                        {form.field_configs?.length || 0} fields
                      </span>
                      <div className="flex space-x-2">
                        <button 
                          onClick={() => handleEditForm(form)}
                          className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded text-sm"
                        >
                          Edit
                        </button>
                        <button 
                          onClick={() => handleDeleteForm(form.id)}
                          className="px-3 py-1 text-red-600 hover:bg-red-50 rounded text-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No custom forms</h3>
              <p className="mt-1 text-sm text-gray-500">Get started by creating your first custom form.</p>
              <div className="mt-6">
                <button 
                  onClick={handleCreateForm}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Create Form
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}