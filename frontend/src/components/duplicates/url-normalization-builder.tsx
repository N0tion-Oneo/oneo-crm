'use client'

import { useState, useEffect } from 'react'
import { 
  Plus, 
  Trash2, 
  ArrowRight,
  Code,
  Globe,
  Settings,
  TestTube,
  Info,
  AlertCircle,
  CheckCircle,
  Eye,
  EyeOff
} from 'lucide-react'

interface NormalizationStep {
  id: string
  type: 'protocol' | 'www' | 'query' | 'fragment' | 'case' | 'trailing_slash' | 'custom_regex' | 'domain_extract' | 'path_extract'
  enabled: boolean
  config: {
    [key: string]: any
  }
}

interface URLNormalizationBuilderProps {
  initialSteps?: NormalizationStep[]
  onChange: (steps: NormalizationStep[]) => void
  testUrl?: string
  onTestUrlChange?: (url: string) => void
}

export function URLNormalizationBuilder({ 
  initialSteps = [], 
  onChange, 
  testUrl = '', 
  onTestUrlChange 
}: URLNormalizationBuilderProps) {
  const [steps, setSteps] = useState<NormalizationStep[]>(initialSteps)
  const [testResult, setTestResult] = useState<string>('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Available step types
  const stepTypes = {
    protocol: {
      name: 'Protocol Handling',
      description: 'Add, remove, or normalize URL protocols (http/https)',
      icon: Globe,
      defaultConfig: {
        action: 'add_if_missing', // add_if_missing, remove, force_https
        protocol: 'https'
      }
    },
    www: {
      name: 'WWW Handling',
      description: 'Add, remove, or normalize www subdomain',
      icon: Globe,
      defaultConfig: {
        action: 'remove' // add, remove, keep_as_is
      }
    },
    case: {
      name: 'Case Normalization',
      description: 'Convert URL parts to specific case',
      icon: Code,
      defaultConfig: {
        domain: 'lowercase', // lowercase, uppercase, keep_as_is
        path: 'keep_as_is' // lowercase, uppercase, keep_as_is
      }
    },
    query: {
      name: 'Query Parameters',
      description: 'Handle URL query parameters and sorting',
      icon: Settings,
      defaultConfig: {
        action: 'remove_all', // keep_all, remove_all, remove_specific, sort_params
        remove_params: [], // specific params to remove
        sort: false
      }
    },
    fragment: {
      name: 'URL Fragment',
      description: 'Handle URL fragments (hash parts)',
      icon: Settings,
      defaultConfig: {
        action: 'remove' // keep, remove
      }
    },
    trailing_slash: {
      name: 'Trailing Slash',
      description: 'Normalize trailing slashes',
      icon: Code,
      defaultConfig: {
        action: 'remove' // add, remove, keep_as_is
      }
    },
    domain_extract: {
      name: 'Domain Extraction',
      description: 'Extract and normalize domain patterns',
      icon: Globe,
      defaultConfig: {
        include_subdomains: false,
        normalize_international: true
      }
    },
    path_extract: {
      name: 'Path Processing',
      description: 'Extract and process URL path components',
      icon: Code,
      defaultConfig: {
        keep_segments: 'all', // all, first_n, last_n, specific
        segment_count: 1,
        decode_percent: true
      }
    },
    custom_regex: {
      name: 'Custom Regex',
      description: 'Apply custom regex transformations',
      icon: Code,
      defaultConfig: {
        pattern: '',
        replacement: '',
        flags: 'gi'
      }
    }
  }

  useEffect(() => {
    onChange(steps)
    runTest()
  }, [steps])

  const addStep = (type: keyof typeof stepTypes) => {
    const newStep: NormalizationStep = {
      id: `${type}-${Date.now()}`,
      type,
      enabled: true,
      config: { ...stepTypes[type].defaultConfig }
    }
    setSteps([...steps, newStep])
  }

  const updateStep = (id: string, updates: Partial<NormalizationStep>) => {
    setSteps(steps.map(step => 
      step.id === id ? { ...step, ...updates } : step
    ))
  }

  const removeStep = (id: string) => {
    setSteps(steps.filter(step => step.id !== id))
  }

  const moveStep = (id: string, direction: 'up' | 'down') => {
    const currentIndex = steps.findIndex(step => step.id === id)
    if (currentIndex === -1) return

    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
    if (newIndex < 0 || newIndex >= steps.length) return

    const newSteps = [...steps]
    const [movedStep] = newSteps.splice(currentIndex, 1)
    newSteps.splice(newIndex, 0, movedStep)
    setSteps(newSteps)
  }

  const runTest = () => {
    if (!testUrl) {
      setTestResult('')
      return
    }

    try {
      let result = testUrl
      const appliedSteps: string[] = []

      for (const step of steps) {
        if (!step.enabled) continue

        const beforeResult = result
        result = applyNormalizationStep(result, step)
        
        if (result !== beforeResult) {
          appliedSteps.push(`${stepTypes[step.type].name}: ${beforeResult} → ${result}`)
        }
      }

      setTestResult(result)
    } catch (error) {
      setTestResult(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const applyNormalizationStep = (url: string, step: NormalizationStep): string => {
    try {
      let parsedUrl: URL
      
      // Handle URLs without protocol
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        parsedUrl = new URL(`https://${url}`)
      } else {
        parsedUrl = new URL(url)
      }

      switch (step.type) {
        case 'protocol':
          switch (step.config.action) {
            case 'remove':
              return url.replace(/^https?:\/\//, '')
            case 'force_https':
              parsedUrl.protocol = 'https:'
              break
            case 'add_if_missing':
              // Already handled above
              break
          }
          break

        case 'www':
          switch (step.config.action) {
            case 'remove':
              parsedUrl.hostname = parsedUrl.hostname.replace(/^www\./, '')
              break
            case 'add':
              if (!parsedUrl.hostname.startsWith('www.')) {
                parsedUrl.hostname = `www.${parsedUrl.hostname}`
              }
              break
          }
          break

        case 'case':
          if (step.config.domain === 'lowercase') {
            parsedUrl.hostname = parsedUrl.hostname.toLowerCase()
          } else if (step.config.domain === 'uppercase') {
            parsedUrl.hostname = parsedUrl.hostname.toUpperCase()
          }
          
          if (step.config.path === 'lowercase') {
            parsedUrl.pathname = parsedUrl.pathname.toLowerCase()
          } else if (step.config.path === 'uppercase') {
            parsedUrl.pathname = parsedUrl.pathname.toUpperCase()
          }
          break

        case 'query':
          switch (step.config.action) {
            case 'remove_all':
              parsedUrl.search = ''
              break
            case 'remove_specific':
              const params = new URLSearchParams(parsedUrl.search)
              step.config.remove_params.forEach((param: string) => params.delete(param))
              parsedUrl.search = params.toString()
              break
            case 'sort_params':
              const sortedParams = new URLSearchParams(parsedUrl.search)
              const sortedEntries = Array.from(sortedParams.entries()).sort(([a], [b]) => a.localeCompare(b))
              parsedUrl.search = new URLSearchParams(sortedEntries).toString()
              break
          }
          break

        case 'fragment':
          if (step.config.action === 'remove') {
            parsedUrl.hash = ''
          }
          break

        case 'trailing_slash':
          switch (step.config.action) {
            case 'remove':
              parsedUrl.pathname = parsedUrl.pathname.replace(/\/$/, '')
              break
            case 'add':
              if (!parsedUrl.pathname.endsWith('/')) {
                parsedUrl.pathname += '/'
              }
              break
          }
          break

        case 'custom_regex':
          if (step.config.pattern) {
            const regex = new RegExp(step.config.pattern, step.config.flags)
            return url.replace(regex, step.config.replacement)
          }
          break

        case 'domain_extract':
          return parsedUrl.hostname
          
        case 'path_extract':
          let path = parsedUrl.pathname
          if (step.config.decode_percent) {
            path = decodeURIComponent(path)
          }
          
          const segments = path.split('/').filter(Boolean)
          switch (step.config.keep_segments) {
            case 'first_n':
              return segments.slice(0, step.config.segment_count).join('/')
            case 'last_n':
              return segments.slice(-step.config.segment_count).join('/')
            case 'all':
            default:
              return segments.join('/')
          }
      }

      return parsedUrl.toString()
    } catch (error) {
      throw new Error(`Step ${step.type} failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  useEffect(() => {
    runTest()
  }, [testUrl])

  const renderStepConfig = (step: NormalizationStep) => {
    const stepType = stepTypes[step.type]
    
    switch (step.type) {
      case 'protocol':
        return (
          <div className="space-y-3">
            <select
              value={step.config.action}
              onChange={(e) => updateStep(step.id, {
                config: { ...step.config, action: e.target.value }
              })}
              className="w-full px-3 py-2 border rounded-md text-sm"
            >
              <option value="add_if_missing">Add if missing</option>
              <option value="force_https">Force HTTPS</option>
              <option value="remove">Remove protocol</option>
            </select>
          </div>
        )

      case 'www':
        return (
          <select
            value={step.config.action}
            onChange={(e) => updateStep(step.id, {
              config: { ...step.config, action: e.target.value }
            })}
            className="w-full px-3 py-2 border rounded-md text-sm"
          >
            <option value="remove">Remove www</option>
            <option value="add">Add www</option>
            <option value="keep_as_is">Keep as is</option>
          </select>
        )

      case 'case':
        return (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium mb-1">Domain</label>
              <select
                value={step.config.domain}
                onChange={(e) => updateStep(step.id, {
                  config: { ...step.config, domain: e.target.value }
                })}
                className="w-full px-3 py-2 border rounded-md text-sm"
              >
                <option value="lowercase">Lowercase</option>
                <option value="uppercase">Uppercase</option>
                <option value="keep_as_is">Keep as is</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Path</label>
              <select
                value={step.config.path}
                onChange={(e) => updateStep(step.id, {
                  config: { ...step.config, path: e.target.value }
                })}
                className="w-full px-3 py-2 border rounded-md text-sm"
              >
                <option value="lowercase">Lowercase</option>
                <option value="uppercase">Uppercase</option>
                <option value="keep_as_is">Keep as is</option>
              </select>
            </div>
          </div>
        )

      case 'query':
        return (
          <div className="space-y-3">
            <select
              value={step.config.action}
              onChange={(e) => updateStep(step.id, {
                config: { ...step.config, action: e.target.value }
              })}
              className="w-full px-3 py-2 border rounded-md text-sm"
            >
              <option value="remove_all">Remove all parameters</option>
              <option value="keep_all">Keep all parameters</option>
              <option value="remove_specific">Remove specific parameters</option>
              <option value="sort_params">Sort parameters</option>
            </select>
            
            {step.config.action === 'remove_specific' && (
              <div>
                <label className="block text-xs font-medium mb-1">Parameters to remove (comma-separated)</label>
                <input
                  type="text"
                  value={step.config.remove_params?.join(', ') || ''}
                  onChange={(e) => updateStep(step.id, {
                    config: { 
                      ...step.config, 
                      remove_params: e.target.value.split(',').map(p => p.trim()).filter(Boolean)
                    }
                  })}
                  placeholder="utm_source, utm_medium"
                  className="w-full px-3 py-2 border rounded-md text-sm"
                />
              </div>
            )}
          </div>
        )

      case 'custom_regex':
        return (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium mb-1">Pattern</label>
              <input
                type="text"
                value={step.config.pattern}
                onChange={(e) => updateStep(step.id, {
                  config: { ...step.config, pattern: e.target.value }
                })}
                placeholder="/(\\w+)/"
                className="w-full px-3 py-2 border rounded-md text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Replacement</label>
              <input
                type="text"
                value={step.config.replacement}
                onChange={(e) => updateStep(step.id, {
                  config: { ...step.config, replacement: e.target.value }
                })}
                placeholder="$1"
                className="w-full px-3 py-2 border rounded-md text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Flags</label>
              <input
                type="text"
                value={step.config.flags}
                onChange={(e) => updateStep(step.id, {
                  config: { ...step.config, flags: e.target.value }
                })}
                placeholder="gi"
                className="w-full px-3 py-2 border rounded-md text-sm font-mono"
              />
            </div>
          </div>
        )

      case 'path_extract':
        return (
          <div className="space-y-3">
            <select
              value={step.config.keep_segments}
              onChange={(e) => updateStep(step.id, {
                config: { ...step.config, keep_segments: e.target.value }
              })}
              className="w-full px-3 py-2 border rounded-md text-sm"
            >
              <option value="all">Keep all segments</option>
              <option value="first_n">Keep first N segments</option>
              <option value="last_n">Keep last N segments</option>
            </select>
            
            {(step.config.keep_segments === 'first_n' || step.config.keep_segments === 'last_n') && (
              <div>
                <label className="block text-xs font-medium mb-1">Number of segments</label>
                <input
                  type="number"
                  min="1"
                  value={step.config.segment_count}
                  onChange={(e) => updateStep(step.id, {
                    config: { ...step.config, segment_count: parseInt(e.target.value) }
                  })}
                  className="w-full px-3 py-2 border rounded-md text-sm"
                />
              </div>
            )}
            
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={step.config.decode_percent}
                onChange={(e) => updateStep(step.id, {
                  config: { ...step.config, decode_percent: e.target.checked }
                })}
                className="mr-2"
              />
              <span className="text-xs">Decode percent-encoded characters</span>
            </label>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            URL Normalization Builder
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Configure how URLs should be processed and normalized
          </p>
        </div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
        >
          {showAdvanced ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          <span>{showAdvanced ? 'Hide' : 'Show'} Advanced</span>
        </button>
      </div>

      {/* Test URL Input */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <TestTube className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h4 className="font-medium text-blue-800 dark:text-blue-200">Live Testing</h4>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-blue-700 dark:text-blue-300 mb-1">
              Test URL
            </label>
            <input
              type="text"
              value={testUrl}
              onChange={(e) => onTestUrlChange?.(e.target.value)}
              placeholder="https://www.example.com/path?param=value#fragment"
              className="w-full px-3 py-2 border border-blue-300 dark:border-blue-600 rounded-md bg-white dark:bg-blue-800 text-gray-900 dark:text-white"
            />
          </div>
          {testResult && (
            <div className="flex items-start space-x-3">
              <ArrowRight className="w-4 h-4 text-blue-500 mt-1" />
              <div className="flex-1">
                <div className="text-sm font-medium text-blue-700 dark:text-blue-300">Result:</div>
                <div className="text-sm font-mono bg-white dark:bg-blue-800 border border-blue-200 dark:border-blue-700 rounded px-2 py-1 mt-1">
                  {testResult}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Normalization Steps */}
      <div className="space-y-4">
        <h4 className="text-md font-semibold text-gray-900 dark:text-white">
          Normalization Steps
        </h4>
        
        {steps.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No normalization steps configured. Add steps below to process URLs.
          </div>
        ) : (
          <div className="space-y-3">
            {steps.map((step, index) => {
              const stepType = stepTypes[step.type]
              const Icon = stepType.icon
              
              return (
                <div key={step.id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-2">
                        <span className="w-6 h-6 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center text-xs font-medium">
                          {index + 1}
                        </span>
                        <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                      </div>
                      <div>
                        <h5 className="font-medium text-gray-900 dark:text-white">
                          {stepType.name}
                        </h5>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {stepType.description}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={step.enabled}
                          onChange={(e) => updateStep(step.id, { enabled: e.target.checked })}
                          className="mr-2"
                        />
                        <span className="text-sm">Enabled</span>
                      </label>
                      
                      <button
                        onClick={() => moveStep(step.id, 'up')}
                        disabled={index === 0}
                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                        title="Move up"
                      >
                        ↑
                      </button>
                      
                      <button
                        onClick={() => moveStep(step.id, 'down')}
                        disabled={index === steps.length - 1}
                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                        title="Move down"
                      >
                        ↓
                      </button>
                      
                      <button
                        onClick={() => removeStep(step.id)}
                        className="p-1 text-red-500 hover:text-red-700"
                        title="Remove step"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  
                  {step.enabled && (
                    <div className="ml-11">
                      {renderStepConfig(step)}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Add Step Buttons */}
      <div>
        <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Add Normalization Step
        </h5>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {Object.entries(stepTypes).map(([key, stepType]) => {
            if (!showAdvanced && ['custom_regex', 'domain_extract', 'path_extract'].includes(key)) {
              return null
            }
            
            const Icon = stepType.icon
            return (
              <button
                key={key}
                onClick={() => addStep(key as keyof typeof stepTypes)}
                className="flex items-center space-x-2 p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-orange-300 hover:bg-orange-50 dark:hover:bg-orange-900/20 text-left"
              >
                <Icon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {stepType.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {stepType.description}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Info Panel */}
      <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-start space-x-2">
          <Info className="w-5 h-5 text-blue-500 mt-0.5" />
          <div>
            <h5 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
              How URL Normalization Works
            </h5>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Steps are applied in order from top to bottom. Each step processes the output of the previous step. 
              Use the test URL above to see how your configuration affects different URLs. Disabled steps are skipped.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}