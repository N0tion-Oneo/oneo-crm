'use client'

import React from 'react'
import { FieldResolver } from '@/lib/field-system/field-registry'
import { Field } from '@/lib/field-system/types'
// Import field system to ensure initialization
import '@/lib/field-system'

// Test with the actual field configurations from the user's Sales Pipeline
const realFieldTests = [
  {
    field: {
      id: 'number_field',
      name: 'number',
      display_name: 'Number',
      field_type: 'number',
      field_config: {
        format: 'currency',
        currency_code: 'ZAR'
      }
    } as Field,
    value: 3000.0,
    expectedDisplay: 'R 3,000.00'
  },
  {
    field: {
      id: 'pipeline_stages',
      name: 'pipeline_stages', 
      display_name: 'Pipeline Stages',
      field_type: 'select',
      field_config: {
        options: [
          { value: 'Onboarding', label: 'Onboarding' },
          { value: 'Lead', label: 'Lead' }
        ],
        allow_custom: false
      }
    } as Field,
    value: 'Onboarding',
    expectedDisplay: 'Onboarding'
  },
  {
    field: {
      id: 'deal_value',
      name: 'deal_value',
      display_name: 'Deal Value', 
      field_type: 'number',
      field_config: {}
    } as Field,
    value: 21312131.0,
    expectedDisplay: '21,312,131'
  }
]

export function TestRealData() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Real Data Field Formatting Test</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        Testing field formatting with actual data from Sales Pipeline in oneotalent.localhost
      </p>
      
      <div className="space-y-4">
        {realFieldTests.map((test, index) => {
          const formattedValue = FieldResolver.formatValue(test.field, test.value, 'table')
          const isExpected = String(formattedValue) === test.expectedDisplay
          
          return (
            <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-medium">{test.field.display_name}</h3>
                  <p className="text-sm text-gray-500">
                    Type: {test.field.field_type} | Value: {JSON.stringify(test.value)}
                  </p>
                  <p className="text-xs text-gray-400">
                    Config: {JSON.stringify(test.field.field_config)}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded text-xs ${
                  isExpected 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                    : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                }`}>
                  {isExpected ? '✓ Expected' : '✗ Unexpected'}
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Expected:</span>
                  <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded border">
                    {test.expectedDisplay}
                  </div>
                </div>
                <div>
                  <span className="font-medium">Actual:</span>
                  <div className="p-2 bg-gray-50 dark:bg-gray-800 rounded border">
                    {typeof formattedValue === 'object' ? 
                      JSON.stringify(formattedValue) : 
                      String(formattedValue)
                    }
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      
      <div className="mt-8 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Field System Test
            </h3>
            <div className="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
              <p>
                This test verifies that the enhanced field system is working with real data from your Sales Pipeline.
                If values don't match expectations, the field components may need updates or frontend restart.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}