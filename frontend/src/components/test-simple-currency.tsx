'use client'

import React, { useState } from 'react'
import { FieldRenderer } from '@/lib/field-system/field-renderer'
import { Field } from '@/lib/field-system/types'
// Import field system to ensure initialization
import '@/lib/field-system'

export function TestSimpleCurrency() {
  const [value, setValue] = useState({ amount: 1000, currency: 'USD' })

  // Test field with currency selection enabled
  const testField: Field = {
    id: 'test_currency',
    name: 'test_currency',
    display_name: 'Test Multi-Currency Field',
    field_type: 'number',
    field_config: {
      format: 'currency',
      allow_currency_selection: true,
      decimal_places: 2
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Simple Currency Dropdown Test</h1>
      
      <div className="space-y-4">
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-medium mb-2">Multi-Currency Field</h3>
          <p className="text-sm text-gray-600 mb-4">
            This should show a dropdown for currency selection + amount input
          </p>
          
          <FieldRenderer
            field={testField}
            value={value}
            onChange={setValue}
            error=""
            context="form"
          />
        </div>
        
        <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <h3 className="font-semibold mb-2">Current Value:</h3>
          <pre className="text-sm">
            {JSON.stringify(value, null, 2)}
          </pre>
        </div>
        
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <h3 className="font-semibold mb-2 text-blue-800 dark:text-blue-200">Field Config:</h3>
          <pre className="text-sm text-blue-700 dark:text-blue-300">
            {JSON.stringify(testField.field_config, null, 2)}
          </pre>
        </div>
        
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <h3 className="font-semibold mb-2 text-yellow-800 dark:text-yellow-200">Expected Result:</h3>
          <ul className="text-sm text-yellow-700 dark:text-yellow-300">
            <li>• Should show "Currency" label with dropdown selector</li>
            <li>• Should show "Amount ($)" label with number input</li>
            <li>• Dropdown should be clickable and show USD, EUR, GBP, ZAR, etc.</li>
            <li>• Check browser console for debug messages</li>
          </ul>
        </div>
      </div>
    </div>
  )
}