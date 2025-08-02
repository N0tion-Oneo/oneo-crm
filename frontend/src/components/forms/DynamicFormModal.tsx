'use client'

import React, { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X } from 'lucide-react'
import { DynamicFormRenderer } from './DynamicFormRenderer'

interface DynamicFormModalProps {
  isOpen: boolean
  onClose: () => void
  pipelineId: string
  formType: 'internal_full' | 'public_filtered' | 'stage_internal' | 'stage_public' | 'shared_record'
  stage?: string
  recordId?: string
  recordData?: Record<string, any>
  title?: string
  onSubmit?: (data: Record<string, any>) => void
}

export function DynamicFormModal({
  isOpen,
  onClose,
  pipelineId,
  formType,
  stage,
  recordId,
  recordData,
  title,
  onSubmit
}: DynamicFormModalProps) {
  const handleFormSubmit = (data: Record<string, any>) => {
    if (onSubmit) {
      onSubmit(data)
    }
    onClose()
  }

  const handleFormError = (error: string) => {
    console.error('Form modal error:', error)
    // Keep modal open on error so user can fix issues
  }

  const getDefaultTitle = () => {
    if (recordId) return 'Edit Record'
    if (stage) return `Create Record - ${stage.charAt(0).toUpperCase() + stage.slice(1)} Stage`
    return 'Create New Record'
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-lg bg-white text-left align-middle shadow-xl transition-all">
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                  <Dialog.Title
                    as="h3"
                    className="text-lg font-medium leading-6 text-gray-900"
                  >
                    {title || getDefaultTitle()}
                  </Dialog.Title>
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <div className="p-0">
                  <DynamicFormRenderer
                    pipelineId={pipelineId}
                    formType={formType}
                    stage={stage}
                    recordId={recordId}
                    recordData={recordData}
                    onSubmit={handleFormSubmit}
                    onError={handleFormError}
                    embedMode={true}
                    className="border-0 shadow-none rounded-none"
                  />
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}