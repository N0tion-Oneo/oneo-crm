'use client'

import React, { useState } from 'react'

const currencyOptions = [
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'EUR', symbol: '€', name: 'Euro' },
  { code: 'GBP', symbol: '£', name: 'British Pound' },
  { code: 'ZAR', symbol: 'R', name: 'South African Rand' },
  { code: 'CAD', symbol: 'CA$', name: 'Canadian Dollar' },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar' },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen' },
  { code: 'CNY', symbol: '¥', name: 'Chinese Yuan' }
]

export function TestDropdownOnly() {
  const [selectedCurrency, setSelectedCurrency] = useState('USD')
  const [clickCount, setClickCount] = useState(0)

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Currency Dropdown Test</h1>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Simple Dropdown Test (should be clickable):
          </label>
          <select
            value={selectedCurrency}
            onChange={(e) => {
              console.log('Dropdown changed to:', e.target.value)
              setSelectedCurrency(e.target.value)
              setClickCount(prev => prev + 1)
            }}
            onClick={(e) => {
              console.log('Dropdown clicked')
              e.stopPropagation()
            }}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
          >
            {currencyOptions.map(currency => (
              <option key={currency.code} value={currency.code}>
                {currency.symbol} {currency.code} - {currency.name}
              </option>
            ))}
          </select>
        </div>
        
        <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <h3 className="font-semibold mb-2">Debug Info:</h3>
          <p>Selected Currency: <strong>{selectedCurrency}</strong></p>
          <p>Change Count: <strong>{clickCount}</strong></p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            If the dropdown is working, you should be able to click it and see different currencies.
            The change count should increase when you select different options.
          </p>
        </div>
        
        <div className="space-y-2">
          <h3 className="font-semibold">Currency Flex Layout Test:</h3>
          <div className="flex space-x-2">
            <select
              value={selectedCurrency}
              onChange={(e) => {
                console.log('Flex dropdown changed to:', e.target.value)
                setSelectedCurrency(e.target.value)
              }}
              className="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer relative z-10"
              style={{ minWidth: '120px' }}
            >
              {currencyOptions.map(currency => (
                <option key={currency.code} value={currency.code}>
                  {currency.symbol} {currency.code}
                </option>
              ))}
            </select>
            <input
              type="number"
              placeholder="Amount"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <p className="text-xs text-gray-500">
            This tests the exact flex layout used in the currency field
          </p>
        </div>
        
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <h3 className="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">Troubleshooting:</h3>
          <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
            <li>• Check browser console for "Dropdown clicked" and "Dropdown changed" messages</li>
            <li>• Try clicking directly on the dropdown arrow</li>
            <li>• Try using keyboard (Tab to focus, then Space/Enter to open)</li>
            <li>• Check if the dropdown options appear when clicking</li>
          </ul>
        </div>
      </div>
    </div>
  )
}