import React, { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const PhoneFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Local state for editing to prevent re-render issues
    // Handle phone objects like {number: "720837293", country_code: "+27"}
    const getDisplayValue = (val: any): string => {
      if (!val) return ''
      if (typeof val === 'object' && val.number !== undefined) {
        // Format as international number: country_code + number
        return (val.country_code || '') + val.number
      }
      return val.toString()
    }
    
    const [localValue, setLocalValue] = useState(getDisplayValue(value))
    const [isEditing, setIsEditing] = useState(false)
    
    // Update local value when external value changes and not editing
    useEffect(() => {
      if (!isEditing) {
        setLocalValue(getDisplayValue(value))
      }
    }, [value, isEditing])
    
    // Get field configuration - handle ALL phone field configs
    const defaultCountry = getFieldConfig(field, 'default_country', null) // Should be null by default
    const allowedCountries = getFieldConfig(field, 'allowed_countries', []) // Empty array means all countries allowed
    const requireCountryCode = getFieldConfig(field, 'require_country_code', true)
    
    const formatDisplay = getFieldConfig(field, 'format_display', true)
    const displayFormat = getFieldConfig(field, 'display_format', 'international')
    const autoFormatInput = getFieldConfig(field, 'auto_format_input', true)

    // Local state handlers
    const handleFocus = () => {
      setIsEditing(true)
    }
    
    const handleBlur = () => {
      setIsEditing(false)
      onBlur?.()
    }
    
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        // Reset to original value on escape
        setLocalValue(value || '')
        setIsEditing(false)
      } else if (e.key === 'Enter') {
        // Trigger blur to save the field
        e.currentTarget.blur()
      }
      onKeyDown?.(e)
    }

    // Country codes mapping (helper function)
    const getCountryCode = (country: string) => {
      const codes: Record<string, string> = {
        'US': '+1', 'CA': '+1', 'GB': '+44', 'AU': '+61', 'DE': '+49',
        'FR': '+33', 'IT': '+39', 'ES': '+34', 'NL': '+31', 'BE': '+32',
        'ZA': '+27', 'NG': '+234', 'KE': '+254', 'EG': '+20', 'MA': '+212',
        'IN': '+91', 'CN': '+86', 'JP': '+81', 'KR': '+82', 'SG': '+65',
        'BR': '+55', 'MX': '+52', 'AR': '+54', 'CL': '+56', 'CO': '+57'
      }
      return codes[country] || '+1'
    }
    
    const inputClass = error 
      ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400'
      : className || ''

    return (
      <div>
        {requireCountryCode === false ? (
          // Simple phone field (stores strings)
          <Input
            type="tel"
            value={localValue}
            onChange={(e) => {
              const newValue = e.target.value
              setLocalValue(newValue)
              onChange(newValue)
            }}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className={inputClass}
            placeholder={defaultCountry ? `e.g. ${getCountryCode(defaultCountry)} 555-123-4567` : `Enter ${field.display_name || field.name}`}
            autoFocus={autoFocus}
            // Required attribute handled by FieldWrapper
          />
        ) : (
          (() => {
            // Helper function to clean phone numbers
            const cleanPhoneNumber = (phoneValue: any, countryCode: string) => {
              if (!phoneValue) return ''
              
              let cleanValue = ''
              if (typeof phoneValue === 'string') {
                cleanValue = phoneValue.replace(/[^\d]/g, '') // Keep only digits
              } else if (typeof phoneValue === 'object' && phoneValue.number !== undefined) {
                cleanValue = String(phoneValue.number).replace(/[^\d]/g, '')
              }
              
              // Remove leading country code digits if user included them
              const countryCodeDigits = countryCode.replace(/\D/g, '') // Remove + and other non-digits
              if (cleanValue.startsWith(countryCodeDigits)) {
                // Check if it's likely a full international number
                const expectedLengthMappings: Record<string, number> = {
                  '1': 11,   // US/Canada: 1 + 10 digits
                  '44': 14,  // UK: 44 + 10-11 digits (check for 13-14 total)
                  '27': 12,  // South Africa: 27 + 9 digits
                  '49': 14,  // Germany: 49 + 10-12 digits
                  '33': 12,  // France: 33 + 9 digits
                  '61': 12,  // Australia: 61 + 9 digits
                }
                
                const expectedLength = expectedLengthMappings[countryCodeDigits]
                if (expectedLength && cleanValue.length >= expectedLength - 1) {
                  // Likely includes country code, remove it
                  cleanValue = cleanValue.substring(countryCodeDigits.length)
                }
              }
              
              return cleanValue
            }
            
            // State management for phone fields (similar to currency fields)
            // Track both country and phone code to handle duplicates like US/CA (+1)
            const [selectedCountry, setSelectedCountry] = useState<string>(() => {
              // Parse existing value to get country
              if (value && typeof value === 'object' && value.country) {
                return value.country
              }
              
              // Use configured default country  
              if (defaultCountry) {
                return defaultCountry
              }
              
              // Check if there are allowed countries - use the first one
              if (allowedCountries && allowedCountries.length > 0) {
                return allowedCountries[0]
              }
              
              // Final fallback to US
              return 'US'
            })
            
            const [currentCountryCode, setCurrentCountryCode] = useState(() => {
              // Get the phone code for the selected country
              return getCountryCode(selectedCountry)
            })
            
            const [currentNumber, setCurrentNumber] = useState(() => {
              const initialCountryCode = value && typeof value === 'object' && value.country_code 
                ? value.country_code 
                : (defaultCountry ? getCountryCode(defaultCountry) : '+1')
              
              return cleanPhoneNumber(value, initialCountryCode)
            })
            
            // Update state when external value changes (for existing records)
            useEffect(() => {
              if (value && typeof value === 'object') {
                if (value.country) {
                  setSelectedCountry(value.country)
                  setCurrentCountryCode(getCountryCode(value.country))
                } else if (value.country_code) {
                  setCurrentCountryCode(value.country_code)
                  // Try to guess the country from the phone code (default to first match)
                  const allCountries = [
                    { code: 'US', phoneCode: '+1' },
                    { code: 'CA', phoneCode: '+1' },
                    { code: 'GB', phoneCode: '+44' },
                    { code: 'AU', phoneCode: '+61' },
                    { code: 'DE', phoneCode: '+49' },
                    { code: 'FR', phoneCode: '+33' },
                    { code: 'IT', phoneCode: '+39' },
                    { code: 'ES', phoneCode: '+34' },
                    { code: 'NL', phoneCode: '+31' },
                    { code: 'ZA', phoneCode: '+27' },
                    { code: 'NG', phoneCode: '+234' },
                    { code: 'IN', phoneCode: '+91' },
                    { code: 'CN', phoneCode: '+86' },
                    { code: 'JP', phoneCode: '+81' },
                    { code: 'SG', phoneCode: '+65' },
                    { code: 'BR', phoneCode: '+55' }
                  ]
                  const country = allCountries.find(c => c.phoneCode === value.country_code)
                  if (country) {
                    setSelectedCountry(country.code)
                  }
                }
                if (value.number) {
                  setCurrentNumber(value.number)
                }
              }
            }, [value])
            
            const updatePhoneValue = (newNumber: string | null, newCountryCode: string, country?: string) => {
              if (newNumber === null || newNumber === '') {
                onChange(null)
              } else {
                // Use helper function to clean the number
                const cleanNumber = cleanPhoneNumber(newNumber, newCountryCode)
                
                // Phone number cleaned and validated
                
                const phoneObject = {
                  country_code: newCountryCode,
                  number: cleanNumber,
                  country: country || selectedCountry  // Store country to distinguish US/CA
                }
                onChange(phoneObject)
              }
            }
            
            return (
              <div 
                className="flex space-x-2" 
                onBlur={(e) => {
                  // Only call parent onBlur if focus is leaving the entire phone field container
                  const isLeavingContainer = !e.currentTarget.contains(e.relatedTarget as Node)
                  if (isLeavingContainer) {
                    handleBlur()
                  }
                }}
              >
                <Select
                  value={`${selectedCountry}:${currentCountryCode}`}
                  onValueChange={(value) => {
                    // Extract country and phone code from the combined value (e.g., "US:+1")
                    const [country, phoneCode] = value.split(':')
                    setSelectedCountry(country)
                    setCurrentCountryCode(phoneCode)
                    updatePhoneValue(currentNumber, phoneCode, country)
                  }}
                  disabled={disabled}
                >
                  <SelectTrigger className="w-32 text-sm">
                    <SelectValue placeholder="+1" />
                  </SelectTrigger>
                  <SelectContent>
                    {(() => {
                      // Available countries with their codes
                      const allCountries = [
                        { code: 'US', name: 'United States', phoneCode: '+1' },
                        { code: 'CA', name: 'Canada', phoneCode: '+1' },
                        { code: 'GB', name: 'United Kingdom', phoneCode: '+44' },
                        { code: 'AU', name: 'Australia', phoneCode: '+61' },
                        { code: 'DE', name: 'Germany', phoneCode: '+49' },
                        { code: 'FR', name: 'France', phoneCode: '+33' },
                        { code: 'IT', name: 'Italy', phoneCode: '+39' },
                        { code: 'ES', name: 'Spain', phoneCode: '+34' },
                        { code: 'NL', name: 'Netherlands', phoneCode: '+31' },
                        { code: 'ZA', name: 'South Africa', phoneCode: '+27' },
                        { code: 'NG', name: 'Nigeria', phoneCode: '+234' },
                        { code: 'IN', name: 'India', phoneCode: '+91' },
                        { code: 'CN', name: 'China', phoneCode: '+86' },
                        { code: 'JP', name: 'Japan', phoneCode: '+81' },
                        { code: 'SG', name: 'Singapore', phoneCode: '+65' },
                        { code: 'BR', name: 'Brazil', phoneCode: '+55' }
                      ]
                      
                      // Filter countries based on allowedCountries config
                      const availableCountries = allowedCountries.length > 0 
                        ? allCountries.filter(country => allowedCountries.includes(country.code))
                        : allCountries
                      
                      return availableCountries.map(country => (
                        <SelectItem key={country.code} value={`${country.code}:${country.phoneCode}`}>
                          {country.phoneCode} ({country.code})
                        </SelectItem>
                      ))
                    })()}
                  </SelectContent>
                </Select>
                <Input
                  type="tel"
                  value={currentNumber || ''}
                  onChange={(e) => {
                    const newValue = e.target.value
                    setLocalValue(newValue)  // Update local state for smooth typing
                    
                    if (newValue === '') {
                      setCurrentNumber('')
                      updatePhoneValue(null, currentCountryCode, selectedCountry)
                    } else {
                      setCurrentNumber(newValue)
                      updatePhoneValue(newValue, currentCountryCode, selectedCountry)
                    }
                  }}
                  onFocus={handleFocus}
                  onKeyDown={handleKeyDown}
                  disabled={disabled}
                  className={`${inputClass} flex-1`}
                  placeholder="Enter phone number"
                  autoFocus={autoFocus}
                  // Required attribute handled by FieldWrapper
                />
              </div>
            )
          })()
        )}
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    
    // Handle phone objects with null/empty numbers (similar to currency objects)
    if (typeof value === 'object' && value !== null && value.country_code !== undefined && value.number !== undefined) {
      if (value.number === null || value.number === undefined || value.number === '') {
        if (context === 'table') {
          return <span className="text-gray-400 italic">—</span>
        }
        return ''
      }
      // For phone objects, format as country code + number
      const displayPhone = `${value.country_code} ${value.number}`
      const formatDisplay = getFieldConfig(field, 'format_display', true)
      const displayFormat = getFieldConfig(field, 'display_format', 'international')
      const formattedPhone = formatDisplay ? formatPhoneDisplay(displayPhone, value.country_code, displayFormat) : displayPhone
      
      if (context === 'table') {
        // Only return JSX link for table context
        return (
          <a 
            href={`tel:${displayPhone.replace(/\s/g, '')}`} 
            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {formattedPhone}
          </a>
        )
      }
      
      // Return plain string for detail and all other contexts (like currency field does)
      return formattedPhone
    }
    
    if (value === null || value === undefined || value === '') {
      if (context === 'table') {
        return <span className="text-gray-400 italic">—</span>
      }
      return ''
    }
    
    // Handle any other object types or unknown formats - convert to string safely
    if (typeof value === 'object' && value !== null) {
      // If it's an object but not a proper phone object, try to extract something meaningful
      if (value.country_code || value.number) {
        const displayPhone = `${value.country_code || ''} ${value.number || ''}`.trim()
        return displayPhone || '[Invalid phone format]'
      }
      
      // Try to extract phone-like properties from unknown objects
      const phoneKeys = ['phone', 'phoneNumber', 'number', 'tel', 'telephone']
      for (const key of phoneKeys) {
        if (value[key]) {
          console.warn('🚨 Found phone-like property in unknown object:', { key, value: value[key], fullObject: value })
          return String(value[key])
        }
      }
      
      // If we can't extract anything meaningful, show debug info instead of [object Object]
      console.error('🚨 Phone field received unrecognized object format:', value)
      return `[Unknown phone format: ${Object.keys(value).join(', ')}]`
    }
    
    // Handle string phone numbers
    const phoneStr = String(value)
    const formatDisplay = getFieldConfig(field, 'format_display', true)
    const displayFormat = getFieldConfig(field, 'display_format', 'international')
    const formattedPhoneStr = formatDisplay ? formatPhoneDisplay(phoneStr, undefined, displayFormat) : phoneStr
    
    if (context === 'table') {
      return (
        <a 
          href={`tel:${phoneStr.replace(/\s/g, '')}`} 
          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {formattedPhoneStr}
        </a>
      )
    }
    
    // Return plain string for detail and all other contexts
    return formattedPhoneStr
  },

  validate: (value: any, _field: Field): ValidationResult => {
    // Handle phone objects - check if number is null/empty (similar to currency validation)
    let actualPhone = value
    if (typeof value === 'object' && value !== null && value.number !== undefined) {
      actualPhone = value.number
    }
    
    // Check if field is required and value is empty
    const isEmpty = actualPhone === null || actualPhone === undefined || actualPhone === ''
    // Note: Required validation handled by permission system

    // If not empty, validate the phone value
    if (!isEmpty) {
      let phoneStr: string
      
      // Handle phone objects
      if (typeof value === 'object' && value !== null && value.number !== undefined) {
        phoneStr = `${value.country_code || ''}${value.number || ''}`
      } else {
        phoneStr = String(value)
      }
      
      // Basic phone validation - allow various formats
      const cleanPhone = phoneStr.replace(/[\s\-\(\)\.]/g, '')
      const phoneRegex = /^[\+]?[1-9][\d]{6,15}$/
      
      if (cleanPhone.length < 7 || !phoneRegex.test(cleanPhone)) {
        return {
          isValid: false,
          error: 'Please enter a valid phone number'
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const defaultValue = getFieldConfig(field, 'default_value')
    if (defaultValue !== undefined) {
      return defaultValue
    }
    return null
  },

  isEmpty: (value: any) => {
    // Handle phone objects - check if number is null/empty (similar to currency isEmpty)
    if (typeof value === 'object' && value !== null && value.number !== undefined) {
      return value.number === null || value.number === undefined || value.number === ''
    }
    return value === null || value === undefined || value === ''
  }
}

// Helper function to format phone display with country-specific patterns
function formatPhoneDisplay(phone: string, countryCode?: string, displayFormat: string = 'international'): string {
  const cleaned = phone.replace(/\D/g, '')
  
  // Country-specific formatting patterns with display format support
  const formatPatterns: Record<string, (num: string, format: string) => string> = {
    '+1': (num, format) => {
      // US/Canada formats
      if (num.length >= 10) {
        const area = num.slice(-10, -7)
        const first = num.slice(-7, -4)
        const last = num.slice(-4)
        
        switch (format) {
          case 'national':
            return `(${area}) ${first}-${last}`
          case 'compact':
            return `+1${area}${first}${last}`
          default: // international
            return `+1 (${area}) ${first}-${last}`
        }
      }
      return num
    },
    '+44': (num, format) => {
      // UK formats
      if (num.length >= 10) {
        const withoutCountry = num.replace(/^44/, '')
        if (withoutCountry.startsWith('20') || withoutCountry.startsWith('11')) {
          // London/Geographic
          const area = withoutCountry.slice(0, 2)
          const first = withoutCountry.slice(2, 6)
          const last = withoutCountry.slice(6)
          
          switch (format) {
            case 'national':
              return `${area} ${first} ${last}`
            case 'compact':
              return `+44${area}${first}${last}`
            default: // international
              return `+44 ${area} ${first} ${last}`
          }
        } else {
          // Mobile
          const first = withoutCountry.slice(0, 4)
          const last = withoutCountry.slice(4)
          
          switch (format) {
            case 'national':
              return `${first} ${last}`
            case 'compact':
              return `+44${first}${last}`
            default: // international
              return `+44 ${first} ${last}`
          }
        }
      }
      return num
    },
    '+27': (num, format) => {
      // South Africa formats
      if (num.length >= 9) {
        const withoutCountry = num.replace(/^27/, '')
        const area = withoutCountry.slice(0, 2)
        const first = withoutCountry.slice(2, 5)
        const last = withoutCountry.slice(5)
        
        switch (format) {
          case 'national':
            return `${area} ${first} ${last}`
          case 'compact':
            return `+27${area}${first}${last}`
          default: // international
            return `+27 ${area} ${first} ${last}`
        }
      }
      return num
    },
    '+49': (num, format) => {
      // Germany formats
      if (num.length >= 10) {
        const withoutCountry = num.replace(/^49/, '')
        const area = withoutCountry.slice(0, 2)
        const rest = withoutCountry.slice(2)
        
        switch (format) {
          case 'national':
            return `${area} ${rest}`
          case 'compact':
            return `+49${area}${rest}`
          default: // international
            return `+49 ${area} ${rest}`
        }
      }
      return num
    },
    '+33': (num, format) => {
      // France formats
      if (num.length >= 9) {
        const withoutCountry = num.replace(/^33/, '')
        const area = withoutCountry.slice(0, 1)
        const p1 = withoutCountry.slice(1, 3)
        const p2 = withoutCountry.slice(3, 5)
        const p3 = withoutCountry.slice(5, 7)
        const p4 = withoutCountry.slice(7)
        
        switch (format) {
          case 'national':
            return `${area} ${p1} ${p2} ${p3} ${p4}`
          case 'compact':
            return `+33${area}${p1}${p2}${p3}${p4}`
          default: // international
            return `+33 ${area} ${p1} ${p2} ${p3} ${p4}`
        }
      }
      return num
    },
    '+61': (num, format) => {
      // Australia formats
      if (num.length >= 9) {
        const withoutCountry = num.replace(/^61/, '')
        const area = withoutCountry.slice(0, 1)
        const first = withoutCountry.slice(1, 5)
        const last = withoutCountry.slice(5)
        
        switch (format) {
          case 'national':
            return `${area} ${first} ${last}`
          case 'compact':
            return `+61${area}${first}${last}`
          default: // international
            return `+61 ${area} ${first} ${last}`
        }
      }
      return num
    }
  }
  
  // Extract country code from phone string if not provided
  if (!countryCode) {
    for (const code of Object.keys(formatPatterns)) {
      if (phone.startsWith(code)) {
        countryCode = code
        break
      }
    }
  }
  
  // Apply country-specific formatting
  if (countryCode && formatPatterns[countryCode]) {
    return formatPatterns[countryCode](cleaned, displayFormat)
  }
  
  // Fallback to generic formatting
  if (cleaned.length >= 10) {
    const country = cleaned.substring(0, cleaned.length - 10)
    const area = cleaned.substring(cleaned.length - 10, cleaned.length - 7)
    const first = cleaned.substring(cleaned.length - 7, cleaned.length - 4)
    const last = cleaned.substring(cleaned.length - 4)
    
    if (country) {
      return `+${country} (${area}) ${first}-${last}`
    }
    return `(${area}) ${first}-${last}`
  }
  
  return phone
}