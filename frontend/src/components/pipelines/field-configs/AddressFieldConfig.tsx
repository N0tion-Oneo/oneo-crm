'use client'

import { useState, useEffect } from 'react'
import { globalOptionsApi } from '@/lib/api'
import {
  Checkbox,
  Label,
  RadioGroup,
  RadioGroupItem,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Separator
} from '@/components/ui'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'

interface AddressFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
  globalOptions?: Record<string, any>
}

interface Country {
  code: string
  name: string
  phone_code: string
}

export function AddressFieldConfig({
  config,
  onChange,
  globalOptions
}: AddressFieldConfigProps) {
  const [countries, setCountries] = useState<Country[]>([])
  const [loading, setLoading] = useState(false)

  // Load countries if not provided in globalOptions
  useEffect(() => {
    if (!globalOptions?.countries) {
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
    } else {
      setCountries(globalOptions?.countries || [])
    }
  }, [globalOptions?.countries])

  const addressFormats = [
    { value: 'single_line', label: 'Single Line', description: 'One text field for the entire address' },
    { value: 'multi_line', label: 'Multi-line', description: 'Separate lines but in one text area' },
    { value: 'structured', label: 'Structured', description: 'Individual fields for each component' }
  ]

  const displayFormats = [
    { value: 'full', label: 'Full Address', description: 'Show complete address with all components' },
    { value: 'compact', label: 'Compact', description: 'Condensed single-line format' },
    { value: 'custom', label: 'Custom', description: 'Custom format based on component visibility' }
  ]

  const components = config.components || {
    street_address: true,
    apartment_suite: true,
    city: true,
    state_province: true,
    postal_code: true,
    country: true
  }

  const handleComponentToggle = (component: string, checked: boolean) => {
    onChange('components', {
      ...components,
      [component]: checked
    })
  }

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">Address Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Structured address input with geocoding and validation options
        </p>
      </div>

      {/* Address Format Configuration */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Address Format</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Choose how the address input field is structured">
            <Label>Input Format</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={config.address_format || 'structured'}
            onValueChange={(value) => onChange('address_format', value)}
            className="space-y-2"
          >
            {addressFormats.map((format) => (
              <div key={format.value} className="flex items-start space-x-3">
                <RadioGroupItem value={format.value} id={`format-${format.value}`} className="mt-1" />
                <div className="space-y-1">
                  <Label htmlFor={`format-${format.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                    {format.label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{format.description}</p>
                </div>
              </div>
            ))}
          </RadioGroup>
        </div>
      </div>

      {/* Address Components (for structured format) */}
      {config.address_format === 'structured' && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Address Components</Label>

            <div className="space-y-3">
              <HelpTooltipWrapper helpText="Select which address components to include in the form">
                <Label>Include Components</Label>
              </HelpTooltipWrapper>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="component-street"
                    checked={components.street_address}
                    onCheckedChange={(checked) => handleComponentToggle('street_address', !!checked)}
                  />
                  <Label htmlFor="component-street" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Street Address
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="component-apartment"
                    checked={components.apartment_suite}
                    onCheckedChange={(checked) => handleComponentToggle('apartment_suite', !!checked)}
                  />
                  <Label htmlFor="component-apartment" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Apartment/Suite
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="component-city"
                    checked={components.city}
                    onCheckedChange={(checked) => handleComponentToggle('city', !!checked)}
                  />
                  <Label htmlFor="component-city" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    City
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="component-state"
                    checked={components.state_province}
                    onCheckedChange={(checked) => handleComponentToggle('state_province', !!checked)}
                  />
                  <Label htmlFor="component-state" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    State/Province
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="component-postal"
                    checked={components.postal_code}
                    onCheckedChange={(checked) => handleComponentToggle('postal_code', !!checked)}
                  />
                  <Label htmlFor="component-postal" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Postal Code
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="component-country"
                    checked={components.country}
                    onCheckedChange={(checked) => handleComponentToggle('country', !!checked)}
                  />
                  <Label htmlFor="component-country" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Country
                  </Label>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      <Separator />

      {/* Default Country */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Default Settings</Label>

        <div className="space-y-2">
          <HelpTooltipWrapper helpText="Pre-select a default country for new addresses">
            <Label>Default Country (Optional)</Label>
          </HelpTooltipWrapper>
          
          {loading ? (
            <div className="p-3 text-sm border rounded-md bg-muted text-gray-700 dark:text-gray-300">
              Loading countries...
            </div>
          ) : (
            <Select
              value={config.default_country || 'none'}
              onValueChange={(value) => onChange('default_country', value === 'none' ? null : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="No default country" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No default country</SelectItem>
                {countries.map((country) => (
                  <SelectItem key={country.code} value={country.code}>
                    {country.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </div>

      <Separator />

      {/* Advanced Features */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Advanced Features</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="enable-geocoding"
              checked={config.enable_geocoding || false}
              onCheckedChange={(checked) => onChange('enable_geocoding', checked)}
            />
            <HelpTooltipWrapper helpText="Enable address autocomplete and geocoding for accurate addresses">
              <Label htmlFor="enable-geocoding" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Enable geocoding & autocomplete
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="require-validation"
              checked={config.require_validation || false}
              onCheckedChange={(checked) => onChange('require_validation', checked)}
            />
            <HelpTooltipWrapper helpText="Require addresses to be validated as real locations">
              <Label htmlFor="require-validation" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Require address validation
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      <Separator />

      {/* Display Format */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Display Format</Label>

        <div className="space-y-3">
          <HelpTooltipWrapper helpText="Choose how addresses are displayed in lists and detail views">
            <Label>Display Style</Label>
          </HelpTooltipWrapper>
          
          <RadioGroup
            value={config.display_format || 'full'}
            onValueChange={(value) => onChange('display_format', value)}
            className="space-y-2"
          >
            {displayFormats.map((format) => (
              <div key={format.value} className="flex items-start space-x-3">
                <RadioGroupItem value={format.value} id={`display-${format.value}`} className="mt-1" />
                <div className="space-y-1">
                  <Label htmlFor={`display-${format.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                    {format.label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{format.description}</p>
                </div>
              </div>
            ))}
          </RadioGroup>
        </div>
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Address Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• Format: {addressFormats.find(f => f.value === (config.address_format || 'structured'))?.label}</div>
            {config.address_format === 'structured' && (
              <div>• Components: {Object.entries(components).filter(([_, enabled]) => enabled).length}/6 enabled</div>
            )}
            {config.default_country && (
              <div>• Default country: {countries.find(c => c.code === config.default_country)?.name}</div>
            )}
            <div>• Display: {displayFormats.find(d => d.value === (config.display_format || 'full'))?.label}</div>
            {config.enable_geocoding && <div>• Geocoding enabled</div>}
            {config.require_validation && <div>• Validation required</div>}
          </div>
        </div>
      </div>
    </div>
  )
}