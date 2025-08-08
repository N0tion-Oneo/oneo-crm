'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Textarea } from '../ui/textarea'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog'
import { Badge } from '../ui/badge'
import { Switch } from '../ui/switch'
import { Plus, Edit, Trash2, TestTube, Play } from 'lucide-react'
import { api } from '@/lib/api'

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
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isTestModalOpen, setIsTestModalOpen] = useState(false)

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    domain_patterns: [''],
    extraction_pattern: '',
    extraction_format: '',
    case_sensitive: false,
    remove_protocol: true,
    remove_www: true,
    remove_query_params: true,
    remove_fragments: true,
    is_active: true
  })

  // Test state
  const [testUrls, setTestUrls] = useState([''])
  const [testResults, setTestResults] = useState<any>(null)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    fetchRules()
  }, [])

  const fetchRules = async () => {
    try {
      setLoading(true)
      const response = await api.get('/url-extraction-rules/')
      setRules(response.data.results || response.data)
    } catch (error) {
      console.error('Failed to fetch URL extraction rules:', error)
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      domain_patterns: [''],
      extraction_pattern: '',
      extraction_format: '',
      case_sensitive: false,
      remove_protocol: true,
      remove_www: true,
      remove_query_params: true,
      remove_fragments: true,
      is_active: true
    })
  }

  const handleCreate = async () => {
    try {
      const payload = {
        ...formData,
        domain_patterns: formData.domain_patterns.filter(p => p.trim())
      }
      
      await api.post('/url-extraction-rules/', payload)
      await fetchRules()
      setIsCreateModalOpen(false)
      resetForm()
    } catch (error) {
      console.error('Failed to create URL extraction rule:', error)
    }
  }

  const handleEdit = async () => {
    if (!selectedRule) return
    
    try {
      const payload = {
        ...formData,
        domain_patterns: formData.domain_patterns.filter(p => p.trim())
      }
      
      await api.put(`/url-extraction-rules/${selectedRule.id}/`, payload)
      await fetchRules()
      setIsEditModalOpen(false)
      setSelectedRule(null)
      resetForm()
    } catch (error) {
      console.error('Failed to update URL extraction rule:', error)
    }
  }

  const handleDelete = async (ruleId: number) => {
    if (!confirm('Are you sure you want to delete this URL extraction rule?')) return
    
    try {
      await api.delete(`/url-extraction-rules/${ruleId}/`)
      await fetchRules()
    } catch (error) {
      console.error('Failed to delete URL extraction rule:', error)
    }
  }

  const handleToggleActive = async (rule: URLExtractionRule) => {
    try {
      await api.patch(`/url-extraction-rules/${rule.id}/`, {
        is_active: !rule.is_active
      })
      await fetchRules()
    } catch (error) {
      console.error('Failed to toggle rule status:', error)
    }
  }

  const openCreateModal = () => {
    resetForm()
    setIsCreateModalOpen(true)
  }

  const openEditModal = (rule: URLExtractionRule) => {
    setSelectedRule(rule)
    setFormData({
      name: rule.name,
      description: rule.description,
      domain_patterns: rule.domain_patterns.length > 0 ? rule.domain_patterns : [''],
      extraction_pattern: rule.extraction_pattern,
      extraction_format: rule.extraction_format,
      case_sensitive: rule.case_sensitive,
      remove_protocol: rule.remove_protocol,
      remove_www: rule.remove_www,
      remove_query_params: rule.remove_query_params,
      remove_fragments: rule.remove_fragments,
      is_active: rule.is_active
    })
    setIsEditModalOpen(true)
  }

  const openTestModal = (rule: URLExtractionRule) => {
    setSelectedRule(rule)
    setTestUrls([''])
    setTestResults(null)
    setIsTestModalOpen(true)
  }

  const handleTestRule = async () => {
    if (!selectedRule) return
    
    try {
      setTesting(true)
      const response = await api.post(`/url-extraction-rules/${selectedRule.id}/test_extraction/`, {
        test_urls: testUrls.filter(url => url.trim())
      })
      setTestResults(response.data)
    } catch (error) {
      console.error('Failed to test URL extraction rule:', error)
    } finally {
      setTesting(false)
    }
  }

  const addDomainPattern = () => {
    setFormData(prev => ({
      ...prev,
      domain_patterns: [...prev.domain_patterns, '']
    }))
  }

  const updateDomainPattern = (index: number, value: string) => {
    setFormData(prev => ({
      ...prev,
      domain_patterns: prev.domain_patterns.map((p, i) => i === index ? value : p)
    }))
  }

  const removeDomainPattern = (index: number) => {
    setFormData(prev => ({
      ...prev,
      domain_patterns: prev.domain_patterns.filter((_, i) => i !== index)
    }))
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
          <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
            <DialogTrigger asChild>
              <Button onClick={openCreateModal}>
                <Plus className="w-4 h-4 mr-2" />
                Create Rule
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create URL Extraction Rule</DialogTitle>
                <DialogDescription>
                  Create a new rule to extract identifiers from URLs
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="name">Name *</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({...prev, name: e.target.value}))}
                      placeholder="e.g., LinkedIn Profile"
                    />
                  </div>
                  <div>
                    <Label htmlFor="extraction_format">Extraction Format *</Label>
                    <Input
                      id="extraction_format"
                      value={formData.extraction_format}
                      onChange={(e) => setFormData(prev => ({...prev, extraction_format: e.target.value}))}
                      placeholder="e.g., linkedin:{}"
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({...prev, description: e.target.value}))}
                    placeholder="Describe what this rule extracts"
                  />
                </div>
                
                <div>
                  <Label>Domain Patterns *</Label>
                  {formData.domain_patterns.map((pattern, index) => (
                    <div key={index} className="flex items-center gap-2 mt-2">
                      <Input
                        value={pattern}
                        onChange={(e) => updateDomainPattern(index, e.target.value)}
                        placeholder="e.g., linkedin.com or *.linkedin.com"
                      />
                      {formData.domain_patterns.length > 1 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => removeDomainPattern(index)}
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
                    onClick={addDomainPattern}
                    className="mt-2"
                  >
                    Add Pattern
                  </Button>
                </div>
                
                <div>
                  <Label htmlFor="extraction_pattern">Extraction Pattern (Regex) *</Label>
                  <Input
                    id="extraction_pattern"
                    value={formData.extraction_pattern}
                    onChange={(e) => setFormData(prev => ({...prev, extraction_pattern: e.target.value}))}
                    placeholder="e.g., /in/([^/]+)"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="case_sensitive"
                      checked={formData.case_sensitive}
                      onCheckedChange={(checked) => setFormData(prev => ({...prev, case_sensitive: checked}))}
                    />
                    <Label htmlFor="case_sensitive">Case Sensitive</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="is_active"
                      checked={formData.is_active}
                      onCheckedChange={(checked) => setFormData(prev => ({...prev, is_active: checked}))}
                    />
                    <Label htmlFor="is_active">Active</Label>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="remove_protocol"
                      checked={formData.remove_protocol}
                      onCheckedChange={(checked) => setFormData(prev => ({...prev, remove_protocol: checked}))}
                    />
                    <Label htmlFor="remove_protocol">Remove Protocol</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="remove_www"
                      checked={formData.remove_www}
                      onCheckedChange={(checked) => setFormData(prev => ({...prev, remove_www: checked}))}
                    />
                    <Label htmlFor="remove_www">Remove WWW</Label>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="remove_query_params"
                      checked={formData.remove_query_params}
                      onCheckedChange={(checked) => setFormData(prev => ({...prev, remove_query_params: checked}))}
                    />
                    <Label htmlFor="remove_query_params">Remove Query Params</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="remove_fragments"
                      checked={formData.remove_fragments}
                      onCheckedChange={(checked) => setFormData(prev => ({...prev, remove_fragments: checked}))}
                    />
                    <Label htmlFor="remove_fragments">Remove Fragments</Label>
                  </div>
                </div>
                
                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreate}>
                    Create Rule
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
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
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        {rule.description}
                      </p>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium">Domain Patterns:</span>
                          <div className="mt-1">
                            {rule.domain_patterns.map((pattern, index) => (
                              <Badge key={index} variant="outline" className="mr-1 mb-1">
                                {pattern}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <div>
                          <span className="font-medium">Extraction Format:</span>
                          <code className="ml-2 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
                            {rule.extraction_format}
                          </code>
                        </div>
                        <div>
                          <span className="font-medium">Pattern:</span>
                          <code className="ml-2 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
                            {rule.extraction_pattern}
                          </code>
                        </div>
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

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit URL Extraction Rule</DialogTitle>
            <DialogDescription>
              Update the URL extraction rule configuration
            </DialogDescription>
          </DialogHeader>
          
          {/* Same form as create modal */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edit_name">Name *</Label>
                <Input
                  id="edit_name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({...prev, name: e.target.value}))}
                  placeholder="e.g., LinkedIn Profile"
                />
              </div>
              <div>
                <Label htmlFor="edit_extraction_format">Extraction Format *</Label>
                <Input
                  id="edit_extraction_format"
                  value={formData.extraction_format}
                  onChange={(e) => setFormData(prev => ({...prev, extraction_format: e.target.value}))}
                  placeholder="e.g., linkedin:{}"
                />
              </div>
            </div>
            
            <div>
              <Label htmlFor="edit_description">Description</Label>
              <Textarea
                id="edit_description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({...prev, description: e.target.value}))}
                placeholder="Describe what this rule extracts"
              />
            </div>
            
            <div>
              <Label>Domain Patterns *</Label>
              {formData.domain_patterns.map((pattern, index) => (
                <div key={index} className="flex items-center gap-2 mt-2">
                  <Input
                    value={pattern}
                    onChange={(e) => updateDomainPattern(index, e.target.value)}
                    placeholder="e.g., linkedin.com or *.linkedin.com"
                  />
                  {formData.domain_patterns.length > 1 && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => removeDomainPattern(index)}
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
                onClick={addDomainPattern}
                className="mt-2"
              >
                Add Pattern
              </Button>
            </div>
            
            <div>
              <Label htmlFor="edit_extraction_pattern">Extraction Pattern (Regex) *</Label>
              <Input
                id="edit_extraction_pattern"
                value={formData.extraction_pattern}
                onChange={(e) => setFormData(prev => ({...prev, extraction_pattern: e.target.value}))}
                placeholder="e.g., /in/([^/]+)"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="edit_case_sensitive"
                  checked={formData.case_sensitive}
                  onCheckedChange={(checked) => setFormData(prev => ({...prev, case_sensitive: checked}))}
                />
                <Label htmlFor="edit_case_sensitive">Case Sensitive</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="edit_is_active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData(prev => ({...prev, is_active: checked}))}
                />
                <Label htmlFor="edit_is_active">Active</Label>
              </div>
            </div>
            
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setIsEditModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleEdit}>
                Update Rule
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Test Modal */}
      <Dialog open={isTestModalOpen} onOpenChange={setIsTestModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Test URL Extraction Rule</DialogTitle>
            <DialogDescription>
              Test the rule against sample URLs to verify extraction works correctly
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>Test URLs</Label>
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