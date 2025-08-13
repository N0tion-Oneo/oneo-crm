'use client'

import { useState } from 'react'
import { Shield, User, Mail, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface AccessorInfoGateProps {
  onSubmit: (name: string, email: string) => void
  loading?: boolean
  error?: string | null
}

interface AccessorInfo {
  name: string
  email: string
}

export function AccessorInfoGate({ onSubmit, loading = false, error }: AccessorInfoGateProps) {
  const [formData, setFormData] = useState<AccessorInfo>({
    name: '',
    email: ''
  })
  const [formErrors, setFormErrors] = useState<Partial<AccessorInfo>>({})

  const validateForm = (): boolean => {
    const errors: Partial<AccessorInfo> = {}
    
    // Validate name
    if (!formData.name.trim()) {
      errors.name = 'Name is required'
    } else if (formData.name.trim().length < 2) {
      errors.name = 'Name must be at least 2 characters'
    }
    
    // Validate email
    if (!formData.email.trim()) {
      errors.email = 'Email is required'
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(formData.email.trim())) {
        errors.email = 'Please enter a valid email address'
      }
    }
    
    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (validateForm()) {
      onSubmit(formData.name.trim(), formData.email.trim().toLowerCase())
    }
  }

  const handleInputChange = (field: keyof AccessorInfo, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Clear field error when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Header Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
              <Shield className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            </div>
            
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Access Shared Record
            </h1>
            
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              Please provide your information to access this secure shared record.
            </p>
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Error Alert */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div className="flex items-start">
                  <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 mr-3 flex-shrink-0" />
                  <div>
                    <h3 className="font-medium text-red-900 dark:text-red-200 mb-1">
                      Access Error
                    </h3>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      {error}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Name Field */}
            <div className="space-y-2">
              <Label htmlFor="name" className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center">
                <User className="w-4 h-4 mr-2" />
                Your Name
              </Label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="Enter your full name"
                className={`${formErrors.name ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}`}
                disabled={loading}
                autoComplete="name"
                required
              />
              {formErrors.name && (
                <p className="text-sm text-red-600 dark:text-red-400">{formErrors.name}</p>
              )}
            </div>

            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center">
                <Mail className="w-4 h-4 mr-2" />
                Your Email
              </Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                placeholder="Enter your email address"
                className={`${formErrors.email ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}`}
                disabled={loading}
                autoComplete="email"
                required
              />
              {formErrors.email && (
                <p className="text-sm text-red-600 dark:text-red-400">{formErrors.email}</p>
              )}
            </div>

            {/* Privacy Notice */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex items-start">
                <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <h3 className="font-medium text-blue-900 dark:text-blue-200 text-sm mb-1">
                    Privacy & Security
                  </h3>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    Your information is collected to track access for security purposes. 
                    We respect your privacy and only use this data for record access logging.
                  </p>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full"
              disabled={loading || !formData.name.trim() || !formData.email.trim()}
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Accessing Record...
                </>
              ) : (
                <>
                  <Shield className="w-4 h-4 mr-2" />
                  Access Shared Record
                </>
              )}
            </Button>
          </form>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Powered by{' '}
            <span className="font-medium text-blue-600 dark:text-blue-400">
              Oneo CRM
            </span>
            {' '}- Secure Record Sharing
          </p>
        </div>
      </div>
    </div>
  )
}