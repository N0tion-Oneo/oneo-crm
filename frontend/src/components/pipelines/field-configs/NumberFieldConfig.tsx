'use client'

import React, { useState, useEffect } from 'react'
import { useGlobalOptions } from '@/contexts/FieldConfigCacheContext'
import {
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Separator,
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
  Button
} from '@/components/ui'
import { FieldOption } from '../config-components/FieldOption'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'
import { ChevronDown } from 'lucide-react'

interface NumberFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
  globalOptions?: Record<string, any>
}

interface Currency {
  code: string
  name: string
  symbol: string
}

const numberFormats = [
  { value: 'integer', label: 'Whole Numbers' },
  { value: 'decimal', label: 'Decimal Numbers' },
  { value: 'currency', label: 'Currency' },
  { value: 'percentage', label: 'Percentage' },
  { value: 'auto_increment', label: 'Auto-Increment' }
]

export function NumberFieldConfig({
  config,
  onChange,
  globalOptions: propGlobalOptions
}: NumberFieldConfigProps) {
  // Use cached global options, but fall back to prop if provided
  const { globalOptions: cachedGlobalOptions, loading, error } = useGlobalOptions()
  const globalOptions = propGlobalOptions || cachedGlobalOptions
  const currencies = globalOptions?.currencies || []

  const selectedFormat = config.format || 'integer'

  // Debug logging for component state
  React.useEffect(() => {
    console.log('[NumberFieldConfig] Component state:', {
      config,
      hasGlobalOptions: !!globalOptions,
      hasPropOptions: !!propGlobalOptions,
      loading,
      error,
      currenciesCount: currencies.length,
      selectedFormat
    })
  }, [config, globalOptions, propGlobalOptions, loading, error, currencies.length, selectedFormat])

  return (
    <div className="space-y-6">
      {/* Number Format Selection */}
      <div className="space-y-2">
        <HelpTooltipWrapper helpText="Choose how this number field should be formatted and displayed">
          <Label htmlFor="number-format">Number Format</Label>
        </HelpTooltipWrapper>
        
        <Select
          value={selectedFormat}
          onValueChange={(value) => {
            try {
              console.log('[NumberFieldConfig] format dropdown changed:', value)
              onChange('format', value)
            } catch (error) {
              console.error('[NumberFieldConfig] Error in format dropdown:', error)
            }
          }}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {numberFormats.map((format) => (
              <SelectItem key={format.value} value={format.value}>
                {format.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Currency-specific Configuration */}
      {selectedFormat === 'currency' && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Currency Settings</Label>
            
            <div className="space-y-2">
              <HelpTooltipWrapper helpText="Restrict this field to a specific currency, or leave blank to allow any currency">
                <Label>Currency Restriction (Optional)</Label>
              </HelpTooltipWrapper>
              
              {loading ? (
                <div className="p-3 text-sm border rounded-md bg-muted text-gray-700 dark:text-gray-300">
                  Loading currencies...
                </div>
              ) : (
                <Select
                  value={config.currency_code || 'any'}
                  onValueChange={(value) => {
                    try {
                      console.log('[NumberFieldConfig] currency_code dropdown changed:', value)
                      const newValue = value === 'any' ? null : value
                      console.log('[NumberFieldConfig] Setting currency_code to:', newValue)
                      onChange('currency_code', newValue)
                    } catch (error) {
                      console.error('[NumberFieldConfig] Error in currency_code dropdown:', error)
                    }
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Allow any currency" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Allow any currency</SelectItem>
                    {currencies.map((currency: any) => (
                      <SelectItem key={currency.code} value={currency.code}>
                        {currency.name} ({currency.symbol})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <p className="text-xs text-muted-foreground">
                Leave blank to allow users to select any currency. Choose a specific currency to restrict the field to only that currency.
              </p>
            </div>

            <FieldOption
              label="Currency Display"
              type="select"
              value={config.currency_display || 'symbol'}
              onChange={(value) => onChange('currency_display', value)}
              options={[
                { value: 'symbol', label: 'Symbol ($100)' },
                { value: 'code', label: 'Code (USD 100)' },
                { value: 'none', label: 'Number only (100)' }
              ]}
            />
          </div>
        </>
      )}

      {/* Percentage-specific Configuration */}
      {selectedFormat === 'percentage' && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Percentage Settings</Label>
            
            <FieldOption
              label="Percentage Display"
              type="select"
              value={config.percentage_display || 'decimal'}
              onChange={(value) => onChange('percentage_display', value)}
              options={[
                { value: 'decimal', label: 'Decimal (0.75)' },
                { value: 'whole', label: 'Whole (75%)' }
              ]}
            />

            <FieldOption
              label="Percentage Decimal Places"
              description="Number of decimal places to show for percentages"
              type="number"
              value={config.percentage_decimal_places || 2}
              onChange={(value) => onChange('percentage_decimal_places', value || 2)}
            />
          </div>
        </>
      )}

      {/* Auto-increment Configuration */}
      {selectedFormat === 'auto_increment' && (
        <>
          <Separator />
          <div className="space-y-4">
            <Label className="text-base font-medium text-gray-900 dark:text-white">Auto-Increment Settings</Label>
            
            <FieldOption
              label="Prefix (Optional)"
              description="Text to prefix before the number (e.g., INV-, CUST-, etc.)"
              type="text"
              value={config.auto_increment_prefix || ''}
              onChange={(value) => onChange('auto_increment_prefix', value)}
              placeholder="INV-, CUST-, etc."
            />

            <FieldOption
              label="Zero Padding (Optional)"
              description="Number of digits to pad with zeros (e.g., 4 → 0001, 0002, 0003...)"
              type="number"
              value={config.auto_increment_padding || ''}
              onChange={(value) => onChange('auto_increment_padding', value)}
              placeholder="e.g., 4 for 0001, 0002..."
            />

            <FieldOption
              label="Starting Number"
              description="The first number in the auto-increment sequence"
              type="number"
              value={config.auto_increment_start || 1}
              onChange={(value) => onChange('auto_increment_start', value || 1)}
            />
          </div>
        </>
      )}

      {/* General Number Configuration */}
      <Separator />
      
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Number Settings</Label>
        
        {selectedFormat !== 'auto_increment' && (
          <FieldOption
            label="Decimal Places"
            description="Number of decimal places to display"
            type="number"
            value={config.decimal_places || 2}
            onChange={(value) => onChange('decimal_places', value || 2)}
          />
        )}

        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 p-0 h-auto font-normal">
              <ChevronDown className="h-4 w-4" />
              Advanced Validation
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <FieldOption
                label="Minimum Value"
                description="Minimum allowed value (optional)"
                type="number"
                value={config.min_value || ''}
                onChange={(value) => onChange('min_value', value)}
              />

              <FieldOption
                label="Maximum Value"
                description="Maximum allowed value (optional)"
                type="number"
                value={config.max_value || ''}
                onChange={(value) => onChange('max_value', value)}
              />
            </div>

            <FieldOption
              label="Default Value"
              description="Default value when creating new records"
              type="number"
              value={config.default_value || ''}
              onChange={(value) => onChange('default_value', value)}
            />
          </CollapsibleContent>
        </Collapsible>
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Number Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• Format: {numberFormats.find(f => f.value === selectedFormat)?.label}</div>
            {selectedFormat === 'currency' && config.currency_code && (
              <div>• Currency: {currencies.find((c: any) => c.code === config.currency_code)?.name}</div>
            )}
            {selectedFormat === 'auto_increment' && (
              <div>• Auto-increment: {config.auto_increment_prefix || ''}{(config.auto_increment_start || 1).toString().padStart(config.auto_increment_padding || 1, '0')}</div>
            )}
            <div>• Decimal places: {config.decimal_places || 2}</div>
            {(config.min_value || config.max_value) && (
              <div>• Range: {config.min_value || '∞'} to {config.max_value || '∞'}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}