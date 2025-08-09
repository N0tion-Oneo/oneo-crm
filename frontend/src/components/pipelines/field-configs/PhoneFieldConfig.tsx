'use client'

import { useState, useEffect } from 'react'
import { globalOptionsApi } from '@/lib/api'
import {
  Checkbox,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
  Separator
} from '@/components/ui'
import { HelpCircle } from 'lucide-react'

interface Country {
  code: string
  name: string
  phone_code: string
}

interface PhoneFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
}

export function PhoneFieldConfig({
  config,
  onChange
}: PhoneFieldConfigProps) {
  const [countries, setCountries] = useState<Country[]>([])
  const [loading, setLoading] = useState(true)

  // Load available countries
  useEffect(() => {
    const loadCountries = async () => {
      try {
        setLoading(true)
        const response = await globalOptionsApi.getAll()
        setCountries(response.data.countries || [])
      } catch (error) {
        console.error('Failed to load countries:', error)
        setCountries([])
      } finally {
        setLoading(false)
      }
    }

    loadCountries()
  }, [])

  const displayFormats = [
    { 
      value: 'international', 
      label: 'International', 
      example: '+27 72 123 4567',
      description: 'Standard international format with country code and spacing'
    },
    { 
      value: 'national', 
      label: 'National', 
      example: '072 123 4567',
      description: 'National format without country code'
    },
    { 
      value: 'compact', 
      label: 'Compact', 
      example: '+27721234567',
      description: 'Compact format without spaces'
    }
  ]

  const handleCountryToggle = (countryCode: string, checked: boolean) => {
    const currentCountries = config.allowed_countries || []
    const newCountries = checked
      ? [...currentCountries, countryCode]
      : currentCountries.filter((c: string) => c !== countryCode)
    onChange('allowed_countries', newCountries)
  }

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Default Country Selection */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="default-country">Default Country (Optional)</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">Pre-select a default country for phone number input. Users can still change it unless restricted below.</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {loading ? (
            <div className="p-3 text-sm border rounded-md bg-muted text-gray-700 dark:text-gray-300">
              Loading countries...
            </div>
          ) : (
            <Select
              value={config.default_country || 'any'}
              onValueChange={(value) => onChange('default_country', value === 'any' ? null : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Allow any country" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Allow any country</SelectItem>
                {countries.map((country) => (
                  <SelectItem key={country.code} value={country.code}>
                    {country.name} ({country.phone_code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <p className="text-xs text-muted-foreground">
            Leave blank to let users select any country. Choose a specific country to pre-select it by default.
          </p>
        </div>

        {/* Allowed Countries */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Label>Allowed Countries (Optional)</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">Restrict phone number input to specific countries. Leave all unchecked to allow any country.</p>
              </TooltipContent>
            </Tooltip>
          </div>

          <div className="p-3 border rounded-md">
            <p className="text-xs text-muted-foreground mb-3">
              Leave all unchecked to allow any country, or select specific countries to restrict choices.
            </p>
            
            {loading ? (
              <div className="text-sm text-gray-600 dark:text-gray-400">Loading countries...</div>
            ) : countries.length === 0 ? (
              <div className="text-sm text-gray-600 dark:text-gray-400">No countries available</div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {countries.map((country) => (
                  <div key={country.code} className="flex items-center space-x-2">
                    <Checkbox
                      id={`country-${country.code}`}
                      checked={(config.allowed_countries || []).includes(country.code)}
                      onCheckedChange={(checked) => handleCountryToggle(country.code, !!checked)}
                    />
                    <Label htmlFor={`country-${country.code}`} className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      {country.name} ({country.phone_code})
                    </Label>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <Separator />

        {/* Phone Number Validation */}
        <div className="space-y-4">
          <Label className="text-sm font-medium text-gray-900 dark:text-white">Phone Number Validation</Label>
          
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="require-country-code"
                checked={config.require_country_code !== false}
                onCheckedChange={(checked) => onChange('require_country_code', checked)}
              />
              <Label htmlFor="require-country-code" className="text-sm text-gray-700 dark:text-gray-300">
                Require country code
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="format-display"
                checked={config.format_display !== false}
                onCheckedChange={(checked) => onChange('format_display', checked)}
              />
              <Label htmlFor="format-display" className="text-sm text-gray-700 dark:text-gray-300">
                Format display with country-specific patterns
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="auto-format-input"
                checked={config.auto_format_input !== false}
                onCheckedChange={(checked) => onChange('auto_format_input', checked)}
              />
              <Label htmlFor="auto-format-input" className="text-sm text-gray-700 dark:text-gray-300">
                Auto-format phone number as user types
              </Label>
            </div>
          </div>
        </div>

        {/* Display Format */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="display-format">Display Format</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">Choose how phone numbers are displayed throughout the system once saved.</p>
              </TooltipContent>
            </Tooltip>
          </div>

          <Select
            value={config.display_format || 'international'}
            onValueChange={(value) => onChange('display_format', value)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {displayFormats.map((format) => (
                <SelectItem key={format.value} value={format.value}>
                  <div>
                    <div className="font-medium">{format.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {format.example} - {format.description}
                    </div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <p className="text-xs text-muted-foreground">
            Choose how phone numbers are displayed throughout the system
          </p>
        </div>

        {/* Configuration Summary */}
        {(config.default_country || (config.allowed_countries && config.allowed_countries.length > 0)) && (
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <div className="text-sm text-gray-700 dark:text-gray-300">
              <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Phone Field Configuration</p>
              <div className="text-blue-700 dark:text-blue-300 space-y-1">
                {config.default_country && (
                  <div>• Default country: {countries.find(c => c.code === config.default_country)?.name}</div>
                )}
                {config.allowed_countries && config.allowed_countries.length > 0 && (
                  <div>• Restricted to {config.allowed_countries.length} countries</div>
                )}
                <div>• Display format: {displayFormats.find(f => f.value === (config.display_format || 'international'))?.label}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}