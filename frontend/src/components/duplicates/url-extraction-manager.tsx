'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog'
import { Badge } from '../ui/badge'
import { Switch } from '../ui/switch'
import { Plus, Edit, Trash2, TestTube, Play, Wand2 } from 'lucide-react'
import { duplicatesApi } from '@/lib/api'
import SmartURLBuilder from './smart-url-builder'

interface URLExtractionRule {
  id: number
  name: string
  description: string
  domain_patterns: string[]
  extraction_pattern: string
  extraction_format: string
  case_sensitive: boolean
  remove_protocol: boolean
  remove_www: boolean
  remove_query_params: boolean
  remove_fragments: boolean
  normalization_steps: any[]
  template_type: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

interface URLExtractionManagerProps {
  pipelineId: string
}

export default function URLExtractionManager({ pipelineId }: URLExtractionManagerProps) {
  const [rules, setRules] = useState<URLExtractionRule[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRule, setSelectedRule] = useState<URLExtractionRule | null>(null)
  const [isSmartBuilderOpen, setIsSmartBuilderOpen] = useState(false)
  const [builderMode, setBuilderMode] = useState<'create' | 'edit'>('create')
  const [isTestModalOpen, setIsTestModalOpen] = useState(false)

  // Test state for existing rules
  const [testUrls, setTestUrls] = useState([''])
  const [testResults, setTestResults] = useState<any>(null)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    fetchRules()
  }, [])

  const fetchRules = async () => {
    try {
      setLoading(true)
      const response = await duplicatesApi.getUrlExtractionRules(pipelineId)
      setRules(response.data.results || response.data)
    } catch (error) {
      console.error('Failed to fetch URL extraction rules:', error)
    } finally {
      setLoading(false)
    }
  }

  const convertSmartBuilderConfigToRule = (config: any, name: string, description: string = '') => {
    // Convert SmartURLBuilder config to database URLExtractionRule format
    if (config.template_name) {
      // Template-based rule - use template settings
      const templateDefaults = getTemplateDefaults(config.template_name)
      return {
        name,
        description: description || `Auto-generated rule for ${config.template_name} URLs`,
        domain_patterns: templateDefaults.domains,
        extraction_pattern: templateDefaults.extraction_pattern,
        extraction_format: templateDefaults.extraction_format,
        case_sensitive: templateDefaults.case_sensitive,
        remove_protocol: templateDefaults.remove_protocol,
        remove_www: templateDefaults.remove_www,
        remove_query_params: templateDefaults.remove_query_params,
        remove_fragments: templateDefaults.remove_fragments,
        normalization_steps: [],
        template_type: config.template_name,
        is_active: true
      }
    } else if (config.custom_template) {
      // Custom template rule
      const custom = config.custom_template
      return {
        name,
        description: description || custom.name,
        domain_patterns: custom.domains,
        extraction_pattern: custom.identifier_regex,
        extraction_format: '{0}', // Default format
        case_sensitive: custom.normalization_rules?.case_sensitive ?? false,
        remove_protocol: custom.normalization_rules?.remove_protocol ?? true,
        remove_www: custom.normalization_rules?.remove_www ?? true,
        remove_query_params: true, // Default
        remove_fragments: true, // Default
        normalization_steps: [],
        template_type: 'custom',
        is_active: true
      }
    }
    throw new Error('Invalid SmartURLBuilder configuration')
  }

  const getTemplateDefaults = (templateName: string) => {
    // Template defaults based on Smart URL Processor templates
    const templates: Record<string, any> = {
      domain: {
        domains: ['*'],
        extraction_pattern: '([a-zA-Z0-9\\-\\.]+)',
        extraction_format: '{0}',
        case_sensitive: false,
        remove_protocol: true,
        remove_www: true,
        remove_query_params: false,
        remove_fragments: true
      },
      linkedin: {
        domains: ['linkedin.com', '*.linkedin.com'],
        extraction_pattern: 'linkedin\\.com/in/([a-zA-Z0-9\\-\\.]+)(?:/|$)',
        extraction_format: '{0}',
        case_sensitive: false,
        remove_protocol: true,
        remove_www: true,
        remove_query_params: true,
        remove_fragments: true
      },
      'linkedin-company': {
        domains: ['linkedin.com', '*.linkedin.com'],
        extraction_pattern: 'linkedin\\.com/(?:company|school|organization)/([a-zA-Z0-9\\-\\.]+)(?:/|$)',
        extraction_format: '{0}',
        case_sensitive: false,
        remove_protocol: true,
        remove_www: true,
        remove_query_params: true,
        remove_fragments: true
      },
      github: {
        domains: ['github.com'],
        extraction_pattern: 'github\\.com/(?!(?:marketplace|pricing|features|enterprise|collections|about|contact|security|orgs|organizations)(?:/|$))([a-zA-Z0-9\\-\\_]+)(?:/?)$',
        extraction_format: '{0}',
        case_sensitive: true,
        remove_protocol: true,
        remove_www: true,
        remove_query_params: true,
        remove_fragments: true
      },
      twitter: {
        domains: ['twitter.com', 'x.com'],
        extraction_pattern: '(?:twitter|x)\\.com/(?!(?:i|search|hashtag|explore|settings|privacy|help|support|tos|login)(?:/|$))([a-zA-Z0-9_]+)(?:/(?:status/\\d+|following|followers)?/?)?$',
        extraction_format: '{0}',
        case_sensitive: false,
        remove_protocol: true,
        remove_www: true,
        remove_query_params: true,
        remove_fragments: true
      }
    }
    
    return templates[templateName] || templates.linkedin
  }

  const handleSmartBuilderSave = async (config: any, metadata: { name: string; description?: string }) => {
    try {
      const ruleData = convertSmartBuilderConfigToRule(config, metadata.name, metadata.description)
      
      if (builderMode === 'create') {
        await duplicatesApi.createUrlExtractionRule(ruleData, pipelineId)
      } else if (builderMode === 'edit' && selectedRule) {
        await duplicatesApi.updateUrlExtractionRule(selectedRule.id.toString(), ruleData, pipelineId)
      }
      
      await fetchRules()
      setIsSmartBuilderOpen(false)
      setSelectedRule(null)
    } catch (error) {
      console.error('Failed to save URL extraction rule:', error)
      throw error // Let SmartURLBuilder handle the error display
    }
  }

  const handleDelete = async (ruleId: number) => {
    if (!confirm('Are you sure you want to delete this URL extraction rule?')) return
    
    try {
      await duplicatesApi.deleteUrlExtractionRule(ruleId.toString(), pipelineId)
      await fetchRules()
    } catch (error) {
      console.error('Failed to delete URL extraction rule:', error)
    }
  }

  const handleToggleActive = async (rule: URLExtractionRule) => {
    try {
      await duplicatesApi.updateUrlExtractionRule(rule.id.toString(), {
        is_active: !rule.is_active
      }, pipelineId)
      await fetchRules()
    } catch (error) {
      console.error('Failed to toggle rule status:', error)
    }
  }

  const openCreateModal = () => {
    setBuilderMode('create')
    setSelectedRule(null)
    setIsSmartBuilderOpen(true)
  }

  const openEditModal = (rule: URLExtractionRule) => {
    setBuilderMode('edit')
    setSelectedRule(rule)
    setIsSmartBuilderOpen(true)
  }
  
  const getTemplateInfo = (templateType: string | null): { type: string; displayName: string; description: string } => {
    // Just return the template type as the display name - no custom mapping
    if (templateType && templateType !== 'custom') {
      return {
        type: templateType,
        displayName: templateType,
        description: `${templateType} URL extraction template`
      }
    }

    return {
      type: 'custom',
      displayName: 'custom',
      description: 'Custom URL extraction pattern with user-defined rules'
    }
  }

  const convertRuleToSmartBuilderConfig = (rule: URLExtractionRule) => {
    // Simple: if it has a template_type, use that. Otherwise, treat as custom
    if (rule.template_type && rule.template_type !== 'custom') {
      return {
        template_name: rule.template_type
      }
    }
    
    // For custom templates, use custom_template format
    return {
      custom_template: {
        name: rule.name,
        domains: rule.domain_patterns,
        path_patterns: ['/{username}'], // Default pattern
        identifier_regex: rule.extraction_pattern,
        normalization_rules: {
          remove_protocol: rule.remove_protocol,
          remove_www: rule.remove_www,
          case_sensitive: rule.case_sensitive,
          remove_query_params: rule.remove_query_params,
          remove_fragments: rule.remove_fragments,
          strip_whitespace: true,
          remove_trailing_slash: true
        }
      }
    }
  }

  const openTestModal = (rule: URLExtractionRule) => {
    setSelectedRule(rule)
    setTestUrls([''])
    setTestResults(null)
    setIsTestModalOpen(true)
  }

  const handleTestRule = async () => {
    if (!selectedRule) return
    
    // Validate URLs before sending
    const validUrls = testUrls
      .filter(url => url.trim())
      .filter(url => {
        try {
          // Basic URL validation
          new URL(url.startsWith('http') ? url : `https://${url}`)
          return true
        } catch {
          return false
        }
      })
    
    if (validUrls.length === 0) {
      alert('Please enter at least one valid URL to test.')
      return
    }
    
    try {
      setTesting(true)
      
      // Convert database rule to SmartURLBuilder format for testing
      const ruleConfig = convertRuleToSmartBuilderConfig(selectedRule)
      
      // Use live testing API with Smart URL Processor
      const response = await duplicatesApi.liveTestUrls({
        test_urls: validUrls,
        custom_template: ruleConfig.custom_template
      })
      
      // Convert Smart URL Processor results to expected format
      const convertedResults = {
        test_results: response.data.processing_results.results.map((result: any) => ({
          original_url: result.original,
          extracted_value: result.extracted,
          success: result.success,
          error: result.error
        })),
        success_rate: response.data.processing_results.success_rate
      }
      
      setTestResults(convertedResults)
    } catch (error: any) {
      console.error('Failed to test URL extraction rule:', error)
      alert(`Test failed: ${error?.response?.data?.error || error?.message || 'Please check the URLs and try again.'}`)
    } finally {
      setTesting(false)
    }
  }

  const addTestUrl = () => {
    setTestUrls(prev => [...prev, ''])
  }

  const updateTestUrl = (index: number, value: string) => {
    setTestUrls(prev => prev.map((url, i) => i === index ? value : url))
  }

  const removeTestUrl = (index: number) => {
    setTestUrls(prev => prev.filter((_, i) => i !== index))
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>URL Extraction Rules</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>URL Extraction Rules</CardTitle>
            <CardDescription>
              Configure patterns to extract standardized identifiers from URLs for duplicate detection
            </CardDescription>
          </div>
          <Button onClick={openCreateModal}>
            <Wand2 className="w-4 h-4 mr-2" />
            Create Smart Rule
          </Button>
        </CardHeader>
        <CardContent>
          {rules.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <TestTube className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No URL extraction rules configured.</p>
              <p className="text-sm">Create rules to standardize URL-based field matching.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="border rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-medium">{rule.name}</h3>
                        <Badge variant={rule.is_active ? 'default' : 'secondary'}>
                          {rule.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        {(() => {
                          const templateInfo = getTemplateInfo(rule.template_type);
                          const variantMap: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
                            'domain': 'outline',
                            'linkedin': 'default', 
                            'linkedin-company': 'default',
                            'github': 'secondary',
                            'twitter': 'secondary',
                            'custom': 'outline'
                          };
                          return (
                            <Badge variant={variantMap[templateInfo.type] || 'outline'}>
                              {templateInfo.displayName}
                            </Badge>
                          );
                        })()}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                        {rule.description || getTemplateInfo(rule.template_type).description}
                      </p>
                      
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium text-gray-700 dark:text-gray-300">Domains:</span>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {rule.domain_patterns.map((pattern, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {pattern}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        
                        <div>
                          <span className="font-medium text-gray-700 dark:text-gray-300">Output Format:</span>
                          <div className="mt-1">
                            <code className="px-2 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs">
                              {rule.extraction_format}
                            </code>
                          </div>
                        </div>
                        
                        <div className="lg:col-span-2">
                          <span className="font-medium text-gray-700 dark:text-gray-300">Extraction Pattern:</span>
                          <div className="mt-1">
                            <code className="block px-2 py-1 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded text-xs break-all">
                              {rule.extraction_pattern}
                            </code>
                          </div>
                        </div>
                        
                        {/* Normalization Options */}
                        <div className="lg:col-span-2">
                          <span className="font-medium text-gray-700 dark:text-gray-300">Normalization:</span>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {rule.remove_protocol && (
                              <Badge variant="outline" className="text-xs bg-green-50 dark:bg-green-900/30">
                                Remove Protocol
                              </Badge>
                            )}
                            {rule.remove_www && (
                              <Badge variant="outline" className="text-xs bg-green-50 dark:bg-green-900/30">
                                Remove WWW
                              </Badge>
                            )}
                            {rule.remove_query_params && (
                              <Badge variant="outline" className="text-xs bg-green-50 dark:bg-green-900/30">
                                Remove Params
                              </Badge>
                            )}
                            {rule.remove_fragments && (
                              <Badge variant="outline" className="text-xs bg-green-50 dark:bg-green-900/30">
                                Remove Fragments
                              </Badge>
                            )}
                            {rule.case_sensitive && (
                              <Badge variant="outline" className="text-xs bg-yellow-50 dark:bg-yellow-900/30">
                                Case Sensitive
                              </Badge>
                            )}
                          </div>
                        </div>
                        
                        {/* Example URLs for this template */}
                        {(() => {
                          const templateInfo = getTemplateInfo(rule.template_type);
                          const examples: Record<string, string[]> = {
                            'domain': ['https://example.com/path → example.com', 'https://www.subdomain.site.co.uk → site.co.uk'],
                            'linkedin': ['https://linkedin.com/in/johndoe → johndoe', 'https://www.linkedin.com/in/jane-smith/ → jane-smith'],
                            'linkedin-company': ['https://linkedin.com/company/acme-corp → acme-corp', 'https://linkedin.com/school/stanford-university → stanford-university'],
                            'github': ['https://github.com/username → username', 'https://github.com/company/repo → company'],
                            'twitter': ['https://twitter.com/username → username', 'https://x.com/handle → handle'],
                            'custom': ['Custom pattern matching based on your configuration']
                          };
                          
                          if (examples[templateInfo.type]) {
                            return (
                              <div className="lg:col-span-2">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Examples:</span>
                                <div className="mt-1 space-y-1">
                                  {examples[templateInfo.type].map((example, index) => (
                                    <div key={index} className="text-xs text-gray-500 dark:text-gray-400 font-mono bg-gray-50 dark:bg-gray-800 px-2 py-1 rounded">
                                      {example}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          }
                          return null;
                        })()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <Switch
                        checked={rule.is_active}
                        onCheckedChange={() => handleToggleActive(rule)}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openTestModal(rule)}
                      >
                        <Play className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditModal(rule)}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(rule.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Smart URL Builder Modal */}
      <Dialog open={isSmartBuilderOpen} onOpenChange={setIsSmartBuilderOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {builderMode === 'create' ? 'Create Smart URL Rule' : 'Edit URL Rule'}
            </DialogTitle>
          </DialogHeader>
          
          <SmartURLBuilder
            onSave={handleSmartBuilderSave}
            onCancel={() => setIsSmartBuilderOpen(false)}
            initialConfig={selectedRule ? convertRuleToSmartBuilderConfig(selectedRule) : undefined}
            initialMetadata={{
              name: selectedRule?.name || '',
              description: selectedRule?.description || ''
            }}
            mode={builderMode}
          />
        </DialogContent>
      </Dialog>

      {/* Test Modal for Existing Rules */}
      <Dialog open={isTestModalOpen} onOpenChange={setIsTestModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Test URL Extraction Rule</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>Test URLs</Label>
              <p className="text-sm text-gray-500 mb-2">
                Test the saved rule against sample URLs to verify it works correctly.
              </p>
              {testUrls.map((url, index) => (
                <div key={index} className="flex items-center gap-2 mt-2">
                  <Input
                    value={url}
                    onChange={(e) => updateTestUrl(index, e.target.value)}
                    placeholder="https://linkedin.com/in/john-doe"
                  />
                  {testUrls.length > 1 && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => removeTestUrl(index)}
                    >
                      Remove
                    </Button>
                  )}
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addTestUrl}
                className="mt-2"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add URL
              </Button>
            </div>
            
            {testResults && (
              <div className="border rounded-lg p-4">
                <h4 className="font-medium mb-2">Test Results</h4>
                <div className="space-y-2">
                  {testResults.test_results?.map((result: any, index: number) => (
                    <div key={index} className="text-sm">
                      <div className="font-medium">{result.original_url}</div>
                      <div className={`ml-4 ${result.success ? 'text-green-600' : 'text-red-600'}`}>
                        {result.success ? (
                          <>✅ Extracted: <code>{result.extracted_value}</code></>
                        ) : (
                          <>❌ {result.error || 'No match'}</>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4 text-sm text-gray-600">
                  Success Rate: {((testResults.success_rate || 0) * 100).toFixed(1)}%
                </div>
              </div>
            )}
            
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setIsTestModalOpen(false)}>
                Close
              </Button>
              <Button onClick={handleTestRule} disabled={testing}>
                {testing ? 'Testing...' : 'Run Test'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}