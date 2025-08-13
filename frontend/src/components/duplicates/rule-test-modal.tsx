'use client'

import { useState } from 'react'
import { X, Play, TestTube, AlertCircle, CheckCircle, Info } from 'lucide-react'
import { duplicatesApi } from '@/lib/api'

interface RuleTestModalProps {
  isOpen: boolean
  onClose: () => void
  rule: any
  pipelineFields: Array<{ name: string; display_name: string; field_type: string }>
  pipelineId: string
}

export function RuleTestModal({ isOpen, onClose, rule, pipelineFields, pipelineId }: RuleTestModalProps) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  const [record1Data, setRecord1Data] = useState<{ [key: string]: string }>({})
  const [record2Data, setRecord2Data] = useState<{ [key: string]: string }>({})

  const handleTest = async () => {
    try {
      setTesting(true)
      setTestResult(null)

      const response = await duplicatesApi.testDuplicateRule(rule.id, {
        record1_data: record1Data,
        record2_data: record2Data
      }, pipelineId)

      setTestResult(response.data)
    } catch (error: any) {
      console.error('Failed to test rule:', error)
      setTestResult({
        error: error?.response?.data?.detail || error?.message || 'Test failed'
      })
    } finally {
      setTesting(false)
    }
  }

  const updateRecord1Field = (field: string, value: string) => {
    setRecord1Data(prev => ({ ...prev, [field]: value }))
  }

  const updateRecord2Field = (field: string, value: string) => {
    setRecord2Data(prev => ({ ...prev, [field]: value }))
  }

  const clearTestData = () => {
    setRecord1Data({})
    setRecord2Data({})
    setTestResult(null)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-6xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
              Test Duplicate Rule
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Rule: <span className="font-medium">{rule.name}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Info Box */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <Info className="w-5 h-5 text-blue-500 mt-0.5" />
              <div>
                <h5 className="text-sm font-semibold text-blue-800 dark:text-blue-300">
                  How Rule Testing Works
                </h5>
                <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
                  Enter sample data for two records below. The rule will be evaluated to determine if these records would be detected as duplicates.
                </p>
              </div>
            </div>
          </div>

          {/* Test Data Input */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Record 1 */}
            <div className="space-y-4">
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                Record A (Test Data)
              </h4>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 space-y-3">
                {(rule.logic?.fields || []).map((ruleField: any, index: number) => {
                  // Find the pipeline field info for this rule field
                  const pipelineField = pipelineFields.find(f => f.name === ruleField.field) || {
                    name: ruleField.field,
                    display_name: ruleField.field,
                    field_type: 'unknown'
                  }
                  return (
                    <div key={index}>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {pipelineField.display_name} ({pipelineField.field_type})
                        <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                          {ruleField.match_type}
                        </span>
                      </label>
                      <input
                        type="text"
                        value={record1Data[ruleField.field] || ''}
                        onChange={(e) => updateRecord1Field(ruleField.field, e.target.value)}
                        placeholder={`Enter ${pipelineField.display_name.toLowerCase()}...`}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                      />
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Record 2 */}
            <div className="space-y-4">
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                Record B (Test Data)
              </h4>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 space-y-3">
                {(rule.logic?.fields || []).map((ruleField: any, index: number) => {
                  // Find the pipeline field info for this rule field
                  const pipelineField = pipelineFields.find(f => f.name === ruleField.field) || {
                    name: ruleField.field,
                    display_name: ruleField.field,
                    field_type: 'unknown'
                  }
                  return (
                    <div key={index}>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {pipelineField.display_name} ({pipelineField.field_type})
                        <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                          {ruleField.match_type}
                        </span>
                      </label>
                      <input
                        type="text"
                        value={record2Data[ruleField.field] || ''}
                        onChange={(e) => updateRecord2Field(ruleField.field, e.target.value)}
                        placeholder={`Enter ${pipelineField.display_name.toLowerCase()}...`}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Test Result */}
          {testResult && (
            <div className="space-y-4">
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                Test Results
              </h4>
              
              {testResult.error ? (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    <span className="font-semibold text-red-800 dark:text-red-300">Test Failed</span>
                  </div>
                  <p className="text-red-700 dark:text-red-400 mt-2">{testResult.error}</p>
                </div>
              ) : (
                <div className={`border rounded-lg p-4 ${
                  testResult.result?.is_duplicate 
                    ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800'
                    : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                }`}>
                  <div className="flex items-center space-x-2 mb-3">
                    {testResult.result?.is_duplicate ? (
                      <>
                        <AlertCircle className="w-5 h-5 text-orange-500" />
                        <span className="font-semibold text-orange-800 dark:text-orange-300">
                          Duplicate Detected
                        </span>
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        <span className="font-semibold text-green-800 dark:text-green-300">
                          No Duplicate Detected
                        </span>
                      </>
                    )}
                  </div>
                  
                  {/* Rule Evaluation Details */}
                  {testResult.result?.evaluation_details && (
                    <div className="space-y-2">
                      <h5 className="font-medium text-gray-900 dark:text-white">
                        Rule Evaluation:
                      </h5>
                      <div className="text-sm space-y-1">
                        <p className="text-gray-700 dark:text-gray-300">
                          Logic Operator: <span className="font-medium">{rule.logic?.operator}</span>
                        </p>
                        {testResult.result.evaluation_details.conditions?.map((condition: any, index: number) => (
                          <div key={index} className="ml-4 text-gray-600 dark:text-gray-400">
                            • Field "{condition.field}": {condition.result ? '✓ Match' : '✗ No Match'}
                            {condition.operator === 'fuzzy_match' && condition.similarity && (
                              <span className="ml-2">({Math.round(condition.similarity * 100)}% similarity)</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Matched Fields */}
                  {testResult.result?.matched_fields && testResult.result.matched_fields.length > 0 && (
                    <div className="mt-3">
                      <h5 className="font-medium text-gray-900 dark:text-white mb-2">
                        Matched Fields:
                      </h5>
                      <div className="flex flex-wrap gap-2">
                        {testResult.result.matched_fields.map((field: string, index: number) => (
                          <span
                            key={index}
                            className="px-2 py-1 bg-orange-200 dark:bg-orange-800 text-orange-800 dark:text-orange-200 rounded-md text-xs font-medium"
                          >
                            {field}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <button
              onClick={clearTestData}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            >
              Clear Test Data
            </button>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Close
              </button>
              <button
                onClick={handleTest}
                disabled={testing || Object.keys(record1Data).length === 0 || Object.keys(record2Data).length === 0}
                className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {testing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Testing...</span>
                  </>
                ) : (
                  <>
                    <TestTube className="w-4 h-4" />
                    <span>Run Test</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}