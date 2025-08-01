'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Loader2, Check, X, AlertCircle } from 'lucide-react'
import { useRegister, useCheckSubdomain } from '@/hooks/auth'
import { useToast } from '@/hooks/use-toast'
import { extractErrorMessage } from '@/lib/utils'

const registerSchema = z.object({
  organization_name: z.string()
    .min(1, 'Organization name is required')
    .max(100, 'Organization name must be less than 100 characters'),
  subdomain: z.string()
    .min(2, 'Subdomain must be at least 2 characters')
    .max(63, 'Subdomain must be less than 64 characters')
    .regex(/^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/, 'Subdomain must contain only lowercase letters, numbers, and hyphens'),
  first_name: z.string()
    .min(1, 'First name is required')
    .max(30, 'First name must be less than 30 characters')
    .regex(/^[a-zA-Z\s'-]+$/, 'First name can only contain letters, spaces, hyphens, and apostrophes'),
  last_name: z.string()
    .min(1, 'Last name is required')
    .max(30, 'Last name must be less than 30 characters')
    .regex(/^[a-zA-Z\s'-]+$/, 'Last name can only contain letters, spaces, hyphens, and apostrophes'),
  email: z.string()
    .email('Please enter a valid email address')
    .max(254, 'Email address is too long')
    .refine(email => {
      // Basic business email validation - exclude common personal email domains
      const personalDomains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com']
      const domain = email.split('@')[1]?.toLowerCase()
      return !personalDomains.includes(domain)
    }, 'Please use a business email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .max(128, 'Password must be less than 128 characters')
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/, 
      'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character'),
  confirm_password: z.string(),
}).refine(data => data.password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
})

type RegisterFormData = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [subdomainStatus, setSubdomainStatus] = useState<'idle' | 'checking' | 'available' | 'taken' | 'error'>('idle')
  const [subdomainMessage, setSubdomainMessage] = useState('')
  const [subdomainCheckTimeout, setSubdomainCheckTimeout] = useState<NodeJS.Timeout | null>(null)
  const [passwordStrength, setPasswordStrength] = useState<{
    score: number
    feedback: string[]
    hasMinLength: boolean
    hasUppercase: boolean
    hasLowercase: boolean
    hasNumber: boolean
    hasSpecialChar: boolean
  }>({
    score: 0,
    feedback: [],
    hasMinLength: false,
    hasUppercase: false,
    hasLowercase: false,
    hasNumber: false,
    hasSpecialChar: false
  })
  const router = useRouter()
  const { toast } = useToast()
  const register = useRegister()
  const checkSubdomain = useCheckSubdomain()

  const {
    register: formRegister,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  const passwordValue = watch('password')
  const confirmPasswordValue = watch('confirm_password')

  // Handle subdomain input with debounced checking
  const handleSubdomainChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toLowerCase()
    
    // Clear existing timeout
    if (subdomainCheckTimeout) {
      clearTimeout(subdomainCheckTimeout)
    }

    // Reset state for short inputs
    if (!value || value.length < 2) {
      setSubdomainStatus('idle')
      setSubdomainMessage('')
      return
    }

    // Validate format first
    const validFormat = /^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/.test(value)
    if (!validFormat) {
      setSubdomainStatus('error')
      setSubdomainMessage('Must contain only lowercase letters, numbers, and hyphens')
      return
    }

    // Set debounced check
    const timeoutId = setTimeout(async () => {
      setSubdomainStatus('checking')
      setSubdomainMessage('Checking availability...')
      
      try {
        const result = await checkSubdomain.mutateAsync(value)
        if (result.available) {
          setSubdomainStatus('available')
          setSubdomainMessage('Great! This subdomain is available')
        } else {
          setSubdomainStatus('taken')
          setSubdomainMessage('This subdomain is already taken')
        }
      } catch (error) {
        setSubdomainStatus('error')
        setSubdomainMessage('Error checking availability')
      }
    }, 800)

    setSubdomainCheckTimeout(timeoutId)
  }

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (subdomainCheckTimeout) {
        clearTimeout(subdomainCheckTimeout)
      }
    }
  }, [subdomainCheckTimeout])

  // Check password strength in real-time
  useEffect(() => {
    if (!passwordValue) {
      setPasswordStrength({
        score: 0,
        feedback: [],
        hasMinLength: false,
        hasUppercase: false,
        hasLowercase: false,
        hasNumber: false,
        hasSpecialChar: false
      })
      return
    }

    const hasMinLength = passwordValue.length >= 8
    const hasUppercase = /[A-Z]/.test(passwordValue)
    const hasLowercase = /[a-z]/.test(passwordValue)
    const hasNumber = /\d/.test(passwordValue)
    const hasSpecialChar = /[@$!%*?&]/.test(passwordValue)

    const criteria = [hasMinLength, hasUppercase, hasLowercase, hasNumber, hasSpecialChar]
    const score = criteria.filter(Boolean).length

    const feedback: string[] = []
    if (!hasMinLength) feedback.push('At least 8 characters')
    if (!hasUppercase) feedback.push('One uppercase letter')
    if (!hasLowercase) feedback.push('One lowercase letter') 
    if (!hasNumber) feedback.push('One number')
    if (!hasSpecialChar) feedback.push('One special character (@$!%*?&)')

    setPasswordStrength({
      score,
      feedback,
      hasMinLength,
      hasUppercase,
      hasLowercase,
      hasNumber,
      hasSpecialChar
    })
  }, [passwordValue])

  const getPasswordStrengthColor = () => {
    if (passwordStrength.score <= 2) return 'bg-red-500'
    if (passwordStrength.score <= 3) return 'bg-yellow-500'
    if (passwordStrength.score <= 4) return 'bg-blue-500'
    return 'bg-green-500'
  }

  const getPasswordStrengthText = () => {
    if (passwordStrength.score <= 2) return 'Weak'
    if (passwordStrength.score <= 3) return 'Fair'
    if (passwordStrength.score <= 4) return 'Good'
    return 'Strong'
  }

  const onSubmit = async (data: RegisterFormData) => {
    // Check if subdomain is available before submitting
    if (subdomainStatus !== 'available') {
      toast({
        title: 'Subdomain unavailable',
        description: 'Please choose an available subdomain before continuing.',
        variant: 'destructive',
      })
      return
    }

    try {
      const { confirm_password, ...registerData } = data
      const response = await register.mutateAsync(registerData)
      
      // Handle redirect to tenant subdomain
      if (response.data?.redirect_url) {
        window.location.href = response.data.redirect_url
      } else {
        router.push('/dashboard')
      }
      
      toast({
        title: 'Welcome to Oneo CRM!',
        description: `Your organization "${registerData.organization_name}" has been created successfully.`,
      })
    } catch (error) {
      toast({
        title: 'Registration failed',
        description: extractErrorMessage(error),
        variant: 'destructive',
      })
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-primary rounded-xl mb-4">
            <span className="text-primary-foreground font-bold text-xl">O</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Create your account
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Join Oneo CRM and start managing your workflows
          </p>
        </div>

        {/* Registration Form */}
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Organization Details */}
            <div>
              <label htmlFor="organization_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Organization Name
              </label>
              <input
                {...formRegister('organization_name')}
                type="text"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent dark:bg-slate-700 dark:text-white"
                placeholder="Acme Corporation"
                disabled={register.isPending}
              />
              {errors.organization_name && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.organization_name.message}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="subdomain" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Subdomain
              </label>
              <div className="flex">
                <div className="flex-1 relative">
                  <input
                    {...formRegister('subdomain', {
                      onChange: handleSubdomainChange
                    })}
                    type="text"
                    className={`w-full px-3 py-2 pr-10 border rounded-l-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent dark:bg-slate-700 dark:text-white ${
                      subdomainStatus === 'available' ? 'border-green-300 dark:border-green-600' :
                      subdomainStatus === 'taken' || subdomainStatus === 'error' ? 'border-red-300 dark:border-red-600' :
                      'border-gray-300 dark:border-gray-600'
                    }`}
                    placeholder="acme"
                    disabled={register.isPending}
                  />
                  <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                    {subdomainStatus === 'checking' && (
                      <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                    )}
                    {subdomainStatus === 'available' && (
                      <Check className="h-4 w-4 text-green-500" />
                    )}
                    {(subdomainStatus === 'taken' || subdomainStatus === 'error') && (
                      <X className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                </div>
                <span className="inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-slate-600 text-gray-500 dark:text-gray-400 text-sm rounded-r-md">
                  .localhost
                </span>
              </div>
              {errors.subdomain && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.subdomain.message}
                </p>
              )}
              {subdomainMessage && !errors.subdomain && (
                <p className={`mt-1 text-sm ${
                  subdomainStatus === 'available' ? 'text-green-600 dark:text-green-400' :
                  subdomainStatus === 'taken' || subdomainStatus === 'error' ? 'text-red-600 dark:text-red-400' :
                  'text-gray-500 dark:text-gray-400'
                }`}>
                  {subdomainMessage}
                </p>
              )}
            </div>

            {/* Name Fields */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="first_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  First Name
                </label>
                <input
                  {...formRegister('first_name')}
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent dark:bg-slate-700 dark:text-white"
                  placeholder="John"
                  disabled={register.isPending}
                />
                {errors.first_name && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.first_name.message}
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="last_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Last Name
                </label>
                <input
                  {...formRegister('last_name')}
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent dark:bg-slate-700 dark:text-white"
                  placeholder="Doe"
                  disabled={register.isPending}
                />
                {errors.last_name && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.last_name.message}
                  </p>
                )}
              </div>
            </div>

            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Business Email Address
              </label>
              <input
                {...formRegister('email')}
                type="email"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent dark:bg-slate-700 dark:text-white"
                placeholder="john@company.com"
                disabled={register.isPending}
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.email.message}
                </p>
              )}
              {!errors.email && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Please use your business email address
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  {...formRegister('password')}
                  type={showPassword ? 'text' : 'password'}
                  className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent dark:bg-slate-700 dark:text-white"
                  placeholder="Create a strong password"
                  disabled={register.isPending}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 flex items-center pr-3"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={register.isPending}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4 text-gray-400" />
                  ) : (
                    <Eye className="h-4 w-4 text-gray-400" />
                  )}
                </button>
              </div>
              
              {/* Password Strength Indicator */}
              {passwordValue && (
                <div className="mt-2">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Password strength:</span>
                    <span className={`text-sm font-medium ${
                      passwordStrength.score <= 2 ? 'text-red-600 dark:text-red-400' :
                      passwordStrength.score <= 3 ? 'text-yellow-600 dark:text-yellow-400' :
                      passwordStrength.score <= 4 ? 'text-blue-600 dark:text-blue-400' :
                      'text-green-600 dark:text-green-400'
                    }`}>
                      {getPasswordStrengthText()}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-300 ${getPasswordStrengthColor()}`}
                      style={{ width: `${(passwordStrength.score / 5) * 100}%` }}
                    />
                  </div>
                  {passwordStrength.feedback.length > 0 && (
                    <div className="mt-2">
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Required:</p>
                      <ul className="text-sm space-y-1">
                        {passwordStrength.feedback.map((item, index) => (
                          <li key={index} className="flex items-center text-gray-500 dark:text-gray-400">
                            <X className="h-3 w-3 mr-2 text-red-500" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              
              {errors.password && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Confirm Password
              </label>
              <div className="relative">
                <input
                  {...formRegister('confirm_password')}
                  type={showConfirmPassword ? 'text' : 'password'}
                  className={`w-full px-3 py-2 pr-10 border rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent dark:bg-slate-700 dark:text-white ${
                    confirmPasswordValue && passwordValue ? (
                      confirmPasswordValue === passwordValue ? 
                        'border-green-300 dark:border-green-600' : 
                        'border-red-300 dark:border-red-600'
                    ) : 'border-gray-300 dark:border-gray-600'
                  }`}
                  placeholder="Confirm your password"
                  disabled={register.isPending}
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-10">
                  {confirmPasswordValue && passwordValue && (
                    confirmPasswordValue === passwordValue ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <X className="h-4 w-4 text-red-500" />
                    )
                  )}
                </div>
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 flex items-center pr-3"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  disabled={register.isPending}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4 text-gray-400" />
                  ) : (
                    <Eye className="h-4 w-4 text-gray-400" />
                  )}
                </button>
              </div>
              
              {/* Password Match Feedback */}
              {confirmPasswordValue && passwordValue && !errors.confirm_password && (
                <p className={`mt-1 text-sm ${
                  confirmPasswordValue === passwordValue ? 
                    'text-green-600 dark:text-green-400' : 
                    'text-red-600 dark:text-red-400'
                }`}>
                  {confirmPasswordValue === passwordValue ? 
                    'Passwords match' : 
                    'Passwords do not match'
                  }
                </p>
              )}
              
              {errors.confirm_password && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.confirm_password.message}
                </p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={register.isPending || subdomainStatus !== 'available'}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {register.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          {/* Footer Links */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Already have an account?{' '}
              <Link href="/login" className="font-medium text-primary hover:text-primary/80">
                Sign in
              </Link>
            </p>
          </div>
        </div>

        {/* Terms Notice */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            By creating an account, you agree to our{' '}
            <Link href="/terms" className="underline hover:text-gray-700 dark:hover:text-gray-300">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link href="/privacy" className="underline hover:text-gray-700 dark:hover:text-gray-300">
              Privacy Policy
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}