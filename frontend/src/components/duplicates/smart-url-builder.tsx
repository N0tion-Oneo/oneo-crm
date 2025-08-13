'use client'

import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Textarea } from '../ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { Badge } from '../ui/badge'
import { Separator } from '../ui/separator'
import { Switch } from '../ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { 
  Play, TestTube, Wand2, Code, CheckCircle, XCircle, 
  AlertCircle, ArrowRight, Copy, Trash2, Plus 
} from 'lucide-react'
import { duplicatesApi } from '@/lib/api'

interface URLTestResult {
  original: string
  normalized: string
  extracted: string | null
  success: boolean
  processing_steps: string[]
  error?: string
}

interface TestResults {
  processing_results: {
    success_rate: number
    total_tested: number
    successful: number
    failed: number
    results: URLTestResult[]
    template_used: string
  }
  available_templates: string[]
  test_metadata: {
    total_urls: number
    template_used: string
    custom_template_provided: boolean
    timestamp: string
  }
}

interface SmartURLBuilderProps {
  onSave?: (config: any, metadata: { name: string; description?: string }) => void
  onCancel?: () => void
  initialConfig?: any
  initialMetadata?: { name: string; description?: string }
  mode?: 'create' | 'edit'
}

export default function SmartURLBuilder({ 
  onSave, 
  onCancel, 
  initialConfig, 
  initialMetadata, 
  mode = 'create' 
}: SmartURLBuilderProps) {
  // Template and mode state
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [availableTemplates, setAvailableTemplates] = useState<string[]>(['generic', 'domain', 'linkedin', 'linkedin-company', 'github', 'twitter', 'instagram', 'facebook', 'youtube'])
  const [builderMode, setBuilderMode] = useState<'template' | 'custom'>('template')
  
  // Get template-specific test URLs
  const getTemplateTestUrls = (templateName: string) => {
    const testUrlSets: Record<string, string[]> = {
      generic: [
        'https://example.com/profile/username',
        'https://mysite.com/user/johndoe',
        'https://platform.com/account/jane-smith'
      ],
      domain: [
        'https://apple.com',
        'https://www.microsoft.com',
        'microsoft.com',
        'https://blog.apple.com/news',
        'https://support.microsoft.com/help',
        'https://api.company.co.uk/docs',
        'https://cdn.jsdelivr.net/package',
        'https://docs.github.com/pages'
      ],
      linkedin: [
        'https://linkedin.com/in/john-doe',
        'linkedin.com/in/jane-smith',
        'https://www.linkedin.com/in/mike-jones?utm_source=google',
        'https://uk.linkedin.com/in/user123',
        'https://linkedin.com/in/sarah-wilson/',
        'https://linkedin.com/in/tech-expert?trk=profile'
      ],
      'linkedin-company': [
        'https://linkedin.com/company/microsoft',
        'linkedin.com/company/apple',
        'https://www.linkedin.com/company/google?utm_source=search',
        'https://uk.linkedin.com/company/openai',
        'https://linkedin.com/company/meta/',
        'https://linkedin.com/company/tesla?trk=company_logo',
        'https://linkedin.com/company/anthropic-ai'
      ],
      github: [
        'https://github.com/username',
        'http://github.com/username',
        'github.com/username',
        'www.github.com/username',
        'https://github.com/username/',
        'https://github.com/username?utm_source=linkedin&utm_medium=social',
        'https://github.com/username?tab=repositories'
      ],
      twitter: [
        'https://x.com/username',
        'http://x.com/username',
        'x.com/username',
        'https://twitter.com/username',
        'twitter.com/username',
        'https://twitter.com/username/',
        'https://twitter.com/username?utm_source=facebook&utm_medium=social'
      ],
      facebook: [
        'https://www.facebook.com/username',
        'facebook.com/username',
        'http://facebook.com/username',
        'https://facebook.com/username/',
        'https://facebook.com/username?utm_source=linkedin&utm_medium=social',
        'https://facebook.com/username?sk=about'
      ],
      instagram: [
        'https://www.instagram.com/username',
        'instagram.com/username',
        'http://instagram.com/username',
        'https://instagram.com/username/',
        'https://instagram.com/username?utm_source=facebook&utm_medium=social',
        'https://instagram.com/username?igsh=example'
      ],
      youtube: [
        'https://www.youtube.com/@username',
        'youtube.com/@username',
        'https://www.youtube.com/channel/UC1234567890',
        'youtube.com/channel/UC1234567890',
        'https://youtube.com/@username?utm_source=twitter&utm_medium=social',
        'https://www.youtube.com/c/channelname'
      ]
    }
    return testUrlSets[templateName] || testUrlSets.generic
  }

  // Test URLs state - starts with generic URLs
  const [testUrls, setTestUrls] = useState<string[]>(getTemplateTestUrls('generic'))
  
  // Test results state
  const [testResults, setTestResults] = useState<TestResults | null>(null)
  const [testing, setTesting] = useState(false)
  const [lastTestTime, setLastTestTime] = useState<string>('')
  
  // Metadata state
  const [metadata, setMetadata] = useState({
    name: initialMetadata?.name || '',
    description: initialMetadata?.description || ''
  })
  const [saving, setSaving] = useState(false)
  
  // Template configurations (starts with defaults, becomes editable)
  const [templateConfigs, setTemplateConfigs] = useState<Record<string, any>>({})

  // Custom template state
  const [customTemplate, setCustomTemplate] = useState({
    name: 'Custom Template',
    domains: ['example.com'],
    path_patterns: ['/profile/{username}'],
    identifier_regex: '([a-zA-Z0-9\\-\\_]+)',
    normalization_rules: {
      remove_protocol: true,
      remove_www: true,
      remove_subdomains: [],
      remove_params: ['utm_source', 'utm_medium', 'utm_campaign'],
      remove_trailing_slash: true,
      case_sensitive: false,
      strip_whitespace: true
    },
    mobile_schemes: []
  })

  // Initialize template configs with defaults
  useEffect(() => {
    const defaultConfigs: Record<string, any> = {
      generic: {
        domains: ['*'],
        path_patterns: ['/{username}', '/{identifier}'],
        identifier_regex: '([a-zA-Z0-9\\\\-\\\\_\\\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: [],
          remove_params: ['utm_source', 'utm_medium', 'utm_campaign'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      domain: {
        domains: ['*'],
        path_patterns: ['/', '/{path}', '/{path}/{subpath}'],
        identifier_regex: '([a-zA-Z0-9\\\\-\\\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: [],
          remove_params: [],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false,
          strip_subdomains: false  // NEW: Option to strip all subdomains and keep only main domain
        },
        mobile_schemes: []
      },
      linkedin: {
        domains: ['linkedin.com', '*.linkedin.com', 'lnkd.in'],
        path_patterns: ['/in/{username}', '/profile/{username}'],
        identifier_regex: '([a-zA-Z0-9\\\\-\\\\_\\\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['za', 'uk', 'au', 'ca', 'de', 'fr', 'es', 'it', 'nl', 'br'],
          remove_params: ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'trk', 'originalSubdomain', 'original_referer', '_l'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false  // FIXED: Disable separator normalization for LinkedIn
        },
        mobile_schemes: ['linkedin://']
      },
      github: {
        domains: ['github.com'],
        path_patterns: ['/{username}'],
        identifier_regex: '([a-zA-Z0-9\\\\-\\\\_]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['www', 'api', 'raw'],
          remove_params: ['tab', 'ref', 'utm_source', 'utm_medium', 'utm_campaign'],
          remove_trailing_slash: true,
          case_sensitive: true,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      twitter: {
        domains: ['twitter.com', 'x.com'],
        path_patterns: ['/{username}'],
        identifier_regex: '([a-zA-Z0-9_]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['mobile', 'm'],
          remove_params: ['s', 't', 'utm_source', 'utm_medium', 'ref_src', 'ref_url'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      instagram: {
        domains: ['instagram.com', '*.instagram.com', 'instagr.am'],
        path_patterns: ['/{username}'],
        identifier_regex: '([a-zA-Z0-9_\\\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['m', 'help'],
          remove_params: ['hl', 'igshid', 'utm_source', 'utm_medium'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      facebook: {
        domains: ['facebook.com', 'fb.com', '*.facebook.com'],
        path_patterns: ['/{username}'],
        identifier_regex: '([a-zA-Z0-9\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['m', 'mobile', 'touch'],
          remove_params: ['fref', 'ref', 'utm_source', 'utm_medium', '__tn__', '__xts__'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      youtube: {
        domains: ['youtube.com', '*.youtube.com', 'youtu.be'],
        path_patterns: ['/c/{username}', '/channel/{username}', '/user/{username}', '/@{username}'],
        identifier_regex: '([a-zA-Z0-9_\\\\-]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['m', 'music', 'gaming'],
          remove_params: ['feature', 'app', 'utm_source', 'utm_medium', 'si', 't', 'list'],
          remove_trailing_slash: true,
          case_sensitive: true,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      }
    }
    // Add LinkedIn company template
    defaultConfigs['linkedin-company'] = {
      domains: ['linkedin.com', '*.linkedin.com', 'lnkd.in'],
      path_patterns: ['/company/{username}', '/school/{username}', '/organization/{username}'],
      identifier_regex: '([a-zA-Z0-9\\\\-\\\\_\\\\.]+)',
      normalization_rules: {
        remove_protocol: true,
        remove_www: true,
        remove_subdomains: ['za', 'uk', 'au', 'ca', 'de', 'fr', 'es', 'it', 'nl', 'br'],
        remove_params: ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'trk', 'originalSubdomain', 'original_referer', '_l'],
        remove_trailing_slash: true,
        case_sensitive: false,
        strip_whitespace: true,
        normalize_separators: false  // FIXED: Disable separator normalization for LinkedIn
      },
      mobile_schemes: ['linkedin://']
    }
    
    setTemplateConfigs(defaultConfigs)
  }, [])

  // Update test URLs when template changes
  useEffect(() => {
    if (selectedTemplate) {
      const newTestUrls = getTemplateTestUrls(selectedTemplate)
      setTestUrls(newTestUrls)
    }
  }, [selectedTemplate])

  // Debug: Log template configurations when they change
  useEffect(() => {
    if (selectedTemplate && Object.keys(templateConfigs).length > 0) {
      console.log('Template Config Debug:', {
        selectedTemplate,
        config: getTemplateConfig(selectedTemplate),
        default: getDefaultTemplateConfig(selectedTemplate),
        isCustomized: JSON.stringify(getTemplateConfig(selectedTemplate)) !== JSON.stringify(getDefaultTemplateConfig(selectedTemplate))
      })
    }
  }, [selectedTemplate, templateConfigs])
  
  // Initialize with existing rule data
  useEffect(() => {
    if (initialConfig && mode === 'edit') {
      if (initialConfig.template_name) {
        setBuilderMode('template')
        setSelectedTemplate(initialConfig.template_name)
      } else if (initialConfig.custom_template) {
        setBuilderMode('custom')
        setCustomTemplate(initialConfig.custom_template)
      }
    }
  }, [initialConfig, mode])

  // Live testing - runs automatically when URLs or template change
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (testUrls.some(url => url.trim())) {
        runLiveTest()
      }
    }, 500) // 500ms debounce
    
    return () => clearTimeout(timeoutId)
  }, [testUrls, selectedTemplate, customTemplate, builderMode, templateConfigs])
  
  const runLiveTest = async () => {
    const validUrls = testUrls.filter(url => url.trim())
    if (validUrls.length === 0) return
    
    try {
      setTesting(true)
      
      const payload: any = {
        test_urls: validUrls
      }
      
      if (builderMode === 'template' && selectedTemplate) {
        const templateConfig = buildTemplateConfig(selectedTemplate)
        if (templateConfig.template_name && !templateConfig.custom_template) {
          // Use built-in template processing
          payload.template_name = templateConfig.template_name
        } else {
          // Use custom template
          payload.custom_template = templateConfig.custom_template
        }
      } else if (builderMode === 'custom') {
        payload.custom_template = customTemplate
      }
      
      console.log('Sending payload to backend:', payload)
      
      const response = await duplicatesApi.liveTestUrls(payload)
      setTestResults(response.data)
      setLastTestTime(new Date().toLocaleTimeString())
      
      console.log('Backend response:', response.data)
      
      // Update available templates if not already set
      if (response.data.available_templates && availableTemplates.length === 0) {
        setAvailableTemplates(response.data.available_templates)
      }
      
    } catch (error: any) {
      console.error('Live test error:', error)
      
      // Check if we have partial results from the response
      const responseData = error?.response?.data
      if (responseData && responseData.processing_results) {
        // Backend returned results but with an error - show the actual results
        console.log('Backend returned partial results:', responseData)
        setTestResults(responseData)
      } else {
        // Complete error - create error state
        setTestResults({
          processing_results: {
            success_rate: 0,
            total_tested: validUrls.length,
            successful: 0,
            failed: validUrls.length,
            results: validUrls.map(url => ({
              original: url,
              normalized: url,
              extracted: null,
              success: false,
              processing_steps: ['error'],
              error: error?.response?.data?.error || error?.message || 'Unknown error'
            })),
            template_used: selectedTemplate || 'custom'
          },
          available_templates: availableTemplates,
          test_metadata: {
            total_urls: validUrls.length,
            template_used: selectedTemplate || 'custom',
            custom_template_provided: builderMode === 'custom',
            timestamp: new Date().toISOString()
          }
        })
      }
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
  
  const addDomainPattern = () => {
    setCustomTemplate(prev => ({
      ...prev,
      domains: [...prev.domains, '']
    }))
  }
  
  const updateDomainPattern = (index: number, value: string) => {
    setCustomTemplate(prev => ({
      ...prev,
      domains: prev.domains.map((domain, i) => i === index ? value : domain)
    }))
  }
  
  const addPathPattern = () => {
    setCustomTemplate(prev => ({
      ...prev,
      path_patterns: [...prev.path_patterns, '/{username}']
    }))
  }
  
  const updatePathPattern = (index: number, value: string) => {
    setCustomTemplate(prev => ({
      ...prev,
      path_patterns: prev.path_patterns.map((pattern, i) => i === index ? value : pattern)
    }))
  }
  
  const copyResults = () => {
    if (!testResults) return
    
    const resultsText = testResults.processing_results.results
      .map(result => `${result.original} → ${result.extracted || 'FAILED'}`)
      .join('\n')
    
    navigator.clipboard.writeText(resultsText)
  }
  
  const handleSave = async () => {
    if (!metadata.name.trim()) {
      alert('Please enter a rule name')
      return
    }
    
    if (builderMode === 'template' && !selectedTemplate) {
      alert('Please select a template or switch to custom mode')
      return
    }
    
    if (builderMode === 'custom' && (!customTemplate.domains.length || !customTemplate.identifier_regex)) {
      alert('Please configure custom template domains and pattern')
      return
    }
    
    if (!onSave) return
    
    try {
      setSaving(true)
      
      const config = builderMode === 'template' ? 
        buildTemplateConfig(selectedTemplate) : 
        { custom_template: customTemplate }
      
      await onSave(config, metadata)
    } catch (error: any) {
      console.error('Save failed:', error)
      alert(`Failed to save rule: ${error?.message || 'Unknown error'}`)
    } finally {
      setSaving(false)
    }
  }
  
  const getTemplateDescription = (templateName: string) => {
    const descriptions: Record<string, string> = {
      generic: 'Generic URL processor - extracts last path segment as identifier',
      domain: 'Domain name extractor - extracts the domain name as identifier, with optional subdomain stripping',
      linkedin: 'LinkedIn profile URLs with /in/ paths, removes tracking params and locale codes',
      'linkedin-company': 'LinkedIn company/organization URLs with /company/, /school/, /organization/ paths',
      github: 'GitHub user profiles, excludes repositories and organization pages',
      twitter: 'Twitter/X profiles, handles both domains, excludes service pages',
      instagram: 'Instagram profiles, excludes posts, stories, and explore pages',
      facebook: 'Facebook profiles, excludes pages, groups, and marketplace',
      youtube: 'YouTube channels with /c/, /user/, /channel/, or @ prefixes'
    }
    return descriptions[templateName] || 'Custom URL extraction rule'
  }
  
  const getTemplateExample = (templateName: string) => {
    const examples: Record<string, string> = {
      generic: 'https://example.com/profile/user123 → user123',
      domain: 'https://blog.apple.com → apple.com (stripped) or blog.apple.com (full)',
      linkedin: 'https://linkedin.com/in/john-doe → john-doe',
      'linkedin-company': 'https://linkedin.com/company/microsoft → microsoft',
      github: 'https://github.com/username → username',
      twitter: 'https://x.com/username → username',
      instagram: 'https://instagram.com/username → username',
      facebook: 'https://facebook.com/username → username',
      youtube: 'https://youtube.com/@username → username'
    }
    return examples[templateName] || 'URL → extracted-identifier'
  }

  // Template configuration helper functions
  const getTemplateConfig = (templateName: string) => {
    return templateConfigs[templateName] || {
      domains: [],
      path_patterns: [],
      identifier_regex: '',
      normalization_rules: {}
    }
  }

  const updateTemplateDomain = (templateName: string, index: number, value: string) => {
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        domains: prev[templateName].domains.map((domain, i) => i === index ? value : domain)
      }
    }))
  }

  const addTemplateDomain = (templateName: string) => {
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        domains: [...prev[templateName].domains, '']
      }
    }))
  }

  const removeTemplateDomain = (templateName: string, index: number) => {
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        domains: prev[templateName].domains.filter((_, i) => i !== index)
      }
    }))
  }

  const updateTemplatePattern = (templateName: string, index: number, value: string) => {
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        path_patterns: prev[templateName].path_patterns.map((pattern, i) => i === index ? value : pattern)
      }
    }))
  }

  const addTemplatePattern = (templateName: string) => {
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        path_patterns: [...prev[templateName].path_patterns, '/{username}']
      }
    }))
  }

  const removeTemplatePattern = (templateName: string, index: number) => {
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        path_patterns: prev[templateName].path_patterns.filter((_, i) => i !== index)
      }
    }))
  }

  const updateTemplateRegex = (templateName: string, value: string) => {
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        identifier_regex: value
      }
    }))
  }

  const updateTemplateNormalization = (templateName: string, key: string, value: boolean) => {
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        normalization_rules: {
          ...prev[templateName].normalization_rules,
          [key]: value
        }
      }
    }))
  }

  const updateTemplateParam = (templateName: string, index: number, value: string) => {
    const config = getTemplateConfig(templateName)
    const params = config.normalization_rules?.remove_params || []
    
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        normalization_rules: {
          ...prev[templateName].normalization_rules,
          remove_params: params.map((param, i) => i === index ? value : param)
        }
      }
    }))
  }

  const addTemplateParam = (templateName: string) => {
    const config = getTemplateConfig(templateName)
    const params = config.normalization_rules?.remove_params || []
    
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        normalization_rules: {
          ...prev[templateName].normalization_rules,
          remove_params: [...params, '']
        }
      }
    }))
  }

  const removeTemplateParam = (templateName: string, index: number) => {
    const config = getTemplateConfig(templateName)
    const params = config.normalization_rules?.remove_params || []
    
    setTemplateConfigs(prev => ({
      ...prev,
      [templateName]: {
        ...prev[templateName],
        normalization_rules: {
          ...prev[templateName].normalization_rules,
          remove_params: params.filter((_, i) => i !== index)
        }
      }
    }))
  }

  // Helper function to get the default generic config
  const getDefaultGenericConfig = () => ({
    domains: ['*'],
    path_patterns: ['/{username}', '/{identifier}'],
    identifier_regex: '([a-zA-Z0-9\\\\-\\\\_\\\\.]+)',
    normalization_rules: {
      remove_protocol: true,
      remove_www: true,
      remove_subdomains: [],
      remove_params: ['utm_source', 'utm_medium', 'utm_campaign'],
      remove_trailing_slash: true,
      case_sensitive: false,
      strip_whitespace: true,
      normalize_separators: false
    },
    mobile_schemes: []
  })

  // Helper function to get the default template configuration from initial state
  const getDefaultTemplateConfig = (templateName: string) => {
    const defaultConfigs: Record<string, any> = {
      generic: getDefaultGenericConfig(),
      domain: {
        domains: ['*'],
        path_patterns: ['/', '/{path}', '/{path}/{subpath}'],
        identifier_regex: '([a-zA-Z0-9\\\\-\\\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: [],
          remove_params: [],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false,
          strip_subdomains: false  // NEW: Option to strip all subdomains and keep only main domain
        },
        mobile_schemes: []
      },
      linkedin: {
        domains: ['linkedin.com', '*.linkedin.com', 'lnkd.in'],
        path_patterns: ['/in/{username}', '/profile/{username}'],
        identifier_regex: '([a-zA-Z0-9\\\\-\\\\_\\\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['za', 'uk', 'au', 'ca', 'de', 'fr', 'es', 'it', 'nl', 'br'],
          remove_params: ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'trk', 'originalSubdomain', 'original_referer', '_l'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false  // FIXED: Disable separator normalization for LinkedIn
        },
        mobile_schemes: ['linkedin://']
      },
      github: {
        domains: ['github.com'],
        path_patterns: ['/{username}'],
        identifier_regex: '([a-zA-Z0-9\\\\-\\\\_]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['www', 'api', 'raw'],
          remove_params: ['tab', 'ref', 'utm_source', 'utm_medium', 'utm_campaign'],
          remove_trailing_slash: true,
          case_sensitive: true,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      twitter: {
        domains: ['twitter.com', 'x.com'],
        path_patterns: ['/{username}'],
        identifier_regex: '([a-zA-Z0-9_]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['mobile', 'm'],
          remove_params: ['s', 't', 'utm_source', 'utm_medium', 'ref_src', 'ref_url'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      instagram: {
        domains: ['instagram.com', '*.instagram.com', 'instagr.am'],
        path_patterns: ['/{username}'],
        identifier_regex: '([a-zA-Z0-9_\\\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['m', 'help'],
          remove_params: ['hl', 'igshid', 'utm_source', 'utm_medium'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      facebook: {
        domains: ['facebook.com', 'fb.com', '*.facebook.com'],
        path_patterns: ['/{username}'],
        identifier_regex: '([a-zA-Z0-9\\\\.]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['m', 'mobile', 'touch'],
          remove_params: ['fref', 'ref', 'utm_source', 'utm_medium', '__tn__', '__xts__'],
          remove_trailing_slash: true,
          case_sensitive: false,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      },
      youtube: {
        domains: ['youtube.com', '*.youtube.com', 'youtu.be'],
        path_patterns: ['/c/{username}', '/channel/{username}', '/user/{username}', '/@{username}'],
        identifier_regex: '([a-zA-Z0-9_\\\\-]+)',
        normalization_rules: {
          remove_protocol: true,
          remove_www: true,
          remove_subdomains: ['m', 'music', 'gaming'],
          remove_params: ['feature', 'app', 'utm_source', 'utm_medium', 'si', 't', 'list'],
          remove_trailing_slash: true,
          case_sensitive: true,
          strip_whitespace: true,
          normalize_separators: false
        },
        mobile_schemes: []
      }
    }
    return defaultConfigs[templateName] || {}
  }

  // Helper function to convert frontend regex escaping to backend format
  const normalizeRegexForBackend = (frontendRegex: string) => {
    // Frontend displays: ([a-zA-Z0-9\\-\\_\\.]+) (escaped for display)
    // Backend needs: ([a-zA-Z0-9\-\_\.]+) (actual regex pattern)
    // When JSON stringified, the frontend escapes become double-escaped
    // So we need to "unescape" them once before sending
    return frontendRegex.replace(/\\\\/g, '\\')
  }

  // Helper function to build template configuration
  const buildTemplateConfig = (templateName: string) => {
    const configuredTemplate = getTemplateConfig(templateName)
    const defaultTemplate = getDefaultTemplateConfig(templateName)
    
    // Check if user has customized the template
    const isCustomized = JSON.stringify(configuredTemplate) !== JSON.stringify(defaultTemplate)
    
    console.log('Template Config Comparison:', {
      templateName,
      isCustomized,
      configured: configuredTemplate,
      default: defaultTemplate,
      configJSON: JSON.stringify(configuredTemplate, null, 2),
      defaultJSON: JSON.stringify(defaultTemplate, null, 2)
    })
    
    
    if (isCustomized) {
      // Use custom template with user modifications
      return { 
        template_name: templateName,
        custom_template: {
          name: templateName,
          ...configuredTemplate
        }
      }
    } else {
      // Use built-in template processing
      return { template_name: templateName }
    }
  }

  const successRate = testResults?.processing_results.success_rate ?? 0
  const hasResults = testResults && testResults.processing_results.results.length > 0
  
  return (
    <div className="space-y-6">
      {/* Rule Metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wand2 className="w-5 h-5" />
            {mode === 'create' ? 'Create Smart URL Rule' : 'Edit URL Rule'}
          </CardTitle>
          <CardDescription>
            Configure rule name and description before testing
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="rule_name">Rule Name *</Label>
              <Input
                id="rule_name"
                value={metadata.name}
                onChange={(e) => setMetadata(prev => ({...prev, name: e.target.value}))}
                placeholder="e.g., LinkedIn Profile URLs"
              />
            </div>
            <div>
              <Label htmlFor="rule_description">Description</Label>
              <Input
                id="rule_description"
                value={metadata.description}
                onChange={(e) => setMetadata(prev => ({...prev, description: e.target.value}))}
                placeholder="Optional description"
              />
            </div>
          </div>
        </CardContent>
      </Card>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Builder Panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">URL Pattern Builder</CardTitle>
            <CardDescription>
              Choose a template or create custom extraction rules
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <Tabs value={builderMode} onValueChange={(value: any) => setBuilderMode(value)}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="template">Built-in Templates</TabsTrigger>
                <TabsTrigger value="custom">Custom Rules</TabsTrigger>
              </TabsList>
              
              <TabsContent value="template" className="space-y-4">
                <div>
                  <Label htmlFor="template">Select & Configure Platform Template</Label>
                  <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a template to configure" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableTemplates.map(template => (
                        <SelectItem key={template} value={template}>
                          {template}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-gray-500 mt-1">
                    Select a template, then customize its configuration below
                  </p>
                  
                  {selectedTemplate && (
                    <div className="mt-4 space-y-4">
                      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <h4 className="font-medium text-sm text-blue-900 dark:text-blue-100 mb-2">
                          {selectedTemplate === 'generic' ? 'Generic Processor' : `${selectedTemplate.charAt(0).toUpperCase() + selectedTemplate.slice(1)} Profile`} Configuration
                        </h4>
                        <div className="text-xs text-blue-700 dark:text-blue-300 mb-3">
                          <div><span className="font-medium">Default behavior:</span> {getTemplateDescription(selectedTemplate)}</div>
                          <div><span className="font-medium">Example:</span> {getTemplateExample(selectedTemplate)}</div>
                        </div>
                      </div>
                      
                      {/* Template Configuration Form */}
                      <div className="border rounded-lg p-4 space-y-4">
                        <h5 className="font-medium">Template Settings</h5>
                        
                        {/* Domain Patterns */}
                        <div>
                          <Label>Domain Patterns</Label>
                          {getTemplateConfig(selectedTemplate).domains.map((domain, index) => (
                            <div key={index} className="flex items-center gap-2 mt-2">
                              <Input
                                value={domain}
                                onChange={(e) => updateTemplateDomain(selectedTemplate, index, e.target.value)}
                                placeholder="e.g., linkedin.com or *.linkedin.com"
                              />
                              {getTemplateConfig(selectedTemplate).domains.length > 1 && (
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  onClick={() => removeTemplateDomain(selectedTemplate, index)}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          ))}
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => addTemplateDomain(selectedTemplate)}
                            className="mt-2"
                          >
                            <Plus className="w-4 h-4 mr-1" />
                            Add Domain
                          </Button>
                        </div>
                        
                        {/* Path Patterns */}
                        <div>
                          <Label>Path Patterns</Label>
                          <p className="text-sm text-gray-500 mb-2">Use {`{username}`} as placeholder for the identifier</p>
                          {getTemplateConfig(selectedTemplate).path_patterns.map((pattern, index) => (
                            <div key={index} className="flex items-center gap-2 mt-2">
                              <Input
                                value={pattern}
                                onChange={(e) => updateTemplatePattern(selectedTemplate, index, e.target.value)}
                                placeholder="e.g., /in/{username}"
                              />
                              {getTemplateConfig(selectedTemplate).path_patterns.length > 1 && (
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  onClick={() => removeTemplatePattern(selectedTemplate, index)}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          ))}
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => addTemplatePattern(selectedTemplate)}
                            className="mt-2"
                          >
                            <Plus className="w-4 h-4 mr-1" />
                            Add Pattern
                          </Button>
                        </div>
                        
                        {/* Identifier Regex */}
                        <div>
                          <Label htmlFor="template_regex">Identifier Pattern (Regex)</Label>
                          <Input
                            id="template_regex"
                            value={getTemplateConfig(selectedTemplate).identifier_regex}
                            onChange={(e) => updateTemplateRegex(selectedTemplate, e.target.value)}
                            placeholder="e.g., ([a-zA-Z0-9\\-\\.]+)"
                          />
                          <p className="text-sm text-gray-500 mt-1">Regular expression to match valid identifiers</p>
                        </div>
                        
                        {/* Normalization Options */}
                        <div>
                          <Label className="text-base font-medium">Normalization Options</Label>
                          <div className="grid grid-cols-2 gap-4 mt-3">
                            <div className="flex items-center space-x-2">
                              <Switch
                                checked={getTemplateConfig(selectedTemplate).normalization_rules?.remove_protocol || false}
                                onCheckedChange={(checked) => updateTemplateNormalization(selectedTemplate, 'remove_protocol', checked)}
                              />
                              <Label className="text-sm">Remove Protocol</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Switch
                                checked={getTemplateConfig(selectedTemplate).normalization_rules?.remove_www || false}
                                onCheckedChange={(checked) => updateTemplateNormalization(selectedTemplate, 'remove_www', checked)}
                              />
                              <Label className="text-sm">Remove WWW</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Switch
                                checked={getTemplateConfig(selectedTemplate).normalization_rules?.case_sensitive || false}
                                onCheckedChange={(checked) => updateTemplateNormalization(selectedTemplate, 'case_sensitive', checked)}
                              />
                              <Label className="text-sm">Case Sensitive</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Switch
                                checked={getTemplateConfig(selectedTemplate).normalization_rules?.remove_trailing_slash || false}
                                onCheckedChange={(checked) => updateTemplateNormalization(selectedTemplate, 'remove_trailing_slash', checked)}
                              />
                              <Label className="text-sm">Remove Trailing Slash</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Switch
                                checked={getTemplateConfig(selectedTemplate).normalization_rules?.strip_whitespace || false}
                                onCheckedChange={(checked) => updateTemplateNormalization(selectedTemplate, 'strip_whitespace', checked)}
                              />
                              <Label className="text-sm">Strip Whitespace</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Switch
                                checked={getTemplateConfig(selectedTemplate).normalization_rules?.normalize_separators || false}
                                onCheckedChange={(checked) => updateTemplateNormalization(selectedTemplate, 'normalize_separators', checked)}
                              />
                              <Label className="text-sm">Normalize Separators</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Switch
                                checked={getTemplateConfig(selectedTemplate).normalization_rules?.strip_subdomains || false}
                                onCheckedChange={(checked) => updateTemplateNormalization(selectedTemplate, 'strip_subdomains', checked)}
                              />
                              <div className="flex flex-col">
                                <Label className="text-sm">Strip Subdomains</Label>
                                <p className="text-xs text-gray-500">
                                  Convert blog.apple.com → apple.com, handles .co.uk domains
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {/* URL Parameters to Remove */}
                        <div>
                          <Label>URL Parameters to Remove</Label>
                          <p className="text-sm text-gray-500 mb-2">Common tracking parameters that should be removed</p>
                          {getTemplateConfig(selectedTemplate).normalization_rules.remove_params?.map((param, index) => (
                            <div key={index} className="flex items-center gap-2 mt-2">
                              <Input
                                value={param}
                                onChange={(e) => updateTemplateParam(selectedTemplate, index, e.target.value)}
                                placeholder="e.g., utm_source"
                              />
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => removeTemplateParam(selectedTemplate, index)}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          )) || <div className="text-sm text-gray-400">No parameters configured</div>}
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => addTemplateParam(selectedTemplate)}
                            className="mt-2"
                          >
                            <Plus className="w-4 h-4 mr-1" />
                            Add Parameter
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>
              
              <TabsContent value="custom" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="custom_name">Template Name</Label>
                    <Input
                      id="custom_name"
                      value={customTemplate.name}
                      onChange={(e) => setCustomTemplate(prev => ({...prev, name: e.target.value}))}
                      placeholder="e.g., Custom Platform"
                    />
                  </div>
                  <div>
                    <Label htmlFor="identifier_regex">Identifier Pattern</Label>
                    <Input
                      id="identifier_regex"
                      value={customTemplate.identifier_regex}
                      onChange={(e) => setCustomTemplate(prev => ({...prev, identifier_regex: e.target.value}))}
                      placeholder="e.g., ([a-zA-Z0-9\\-\\_]+)"
                    />
                  </div>
                </div>
                
                <div>
                  <Label>Domain Patterns</Label>
                  {customTemplate.domains.map((domain, index) => (
                    <div key={index} className="flex items-center gap-2 mt-2">
                      <Input
                        value={domain}
                        onChange={(e) => updateDomainPattern(index, e.target.value)}
                        placeholder="e.g., example.com or *.example.com"
                      />
                      {customTemplate.domains.length > 1 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setCustomTemplate(prev => ({
                            ...prev,
                            domains: prev.domains.filter((_, i) => i !== index)
                          }))}
                        >
                          <Trash2 className="w-4 h-4" />
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
                    <Plus className="w-4 h-4 mr-1" />
                    Add Domain
                  </Button>
                </div>
                
                <div>
                  <Label>Path Patterns</Label>
                  <p className="text-sm text-gray-500 mb-2">
                    Use {`{username}`} as placeholder for the identifier to extract
                  </p>
                  {customTemplate.path_patterns.map((pattern, index) => (
                    <div key={index} className="flex items-center gap-2 mt-2">
                      <Input
                        value={pattern}
                        onChange={(e) => updatePathPattern(index, e.target.value)}
                        placeholder="e.g., /profile/{username}"
                      />
                      {customTemplate.path_patterns.length > 1 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setCustomTemplate(prev => ({
                            ...prev,
                            path_patterns: prev.path_patterns.filter((_, i) => i !== index)
                          }))}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addPathPattern}
                    className="mt-2"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Add Pattern
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
        
        {/* Live Testing Panel */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TestTube className="w-5 h-5" />
                  Live URL Testing
                </CardTitle>
                <CardDescription>
                  Test URLs instantly as you type - no saving required
                </CardDescription>
              </div>
              {hasResults && (
                <div className="flex items-center gap-2">
                  <Badge 
                    variant={successRate >= 0.8 ? 'default' : successRate >= 0.5 ? 'secondary' : 'destructive'}
                    className="text-xs"
                  >
                    {(successRate * 100).toFixed(0)}% success
                  </Badge>
                  <Button variant="outline" size="sm" onClick={copyResults}>
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Live Results Summary */}
            {hasResults && (
              <div className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold text-sm flex items-center gap-2">
                    <div className="animate-pulse w-2 h-2 bg-green-500 rounded-full"></div>
                    Live Processing Results
                  </h4>
                  <div className="flex items-center gap-2">
                    <Badge variant={successRate >= 0.8 ? 'default' : successRate >= 0.5 ? 'secondary' : 'destructive'}>
                      {(successRate * 100).toFixed(0)}% Success
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {testResults.processing_results.template_used}
                    </Badge>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                  <div className="bg-white dark:bg-gray-800 p-3 rounded border">
                    <div className="text-xs text-gray-500 mb-1">URLs Processed</div>
                    <div className="font-bold text-lg">
                      {testResults.processing_results.total_tested}
                    </div>
                  </div>
                  
                  <div className="bg-white dark:bg-gray-800 p-3 rounded border">
                    <div className="text-xs text-green-600 mb-1">Successful Extractions</div>
                    <div className="font-bold text-lg text-green-600">
                      {testResults.processing_results.successful}
                    </div>
                  </div>
                  
                  <div className="bg-white dark:bg-gray-800 p-3 rounded border">
                    <div className="text-xs text-red-600 mb-1">Failed Extractions</div>
                    <div className="font-bold text-lg text-red-600">
                      {testResults.processing_results.failed}
                    </div>
                  </div>
                </div>
                
                <div className="mt-3 text-xs text-gray-600 dark:text-gray-300">
                  💡 Adjust template settings above to improve success rate in real-time
                </div>
              </div>
            )}
            
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label>Test URLs</Label>
                {testing && (
                  <Badge variant="outline" className="text-xs">
                    <div className="animate-spin w-3 h-3 border border-current border-t-transparent rounded-full mr-1" />
                    Testing...
                  </Badge>
                )}
              </div>
              
              {testUrls.map((url, index) => (
                <div key={index} className="space-y-2 mb-3">
                  <div className="flex items-center gap-2">
                    <Input
                      value={url}
                      onChange={(e) => updateTestUrl(index, e.target.value)}
                      placeholder="Enter URL to test..."
                    />
                    {testUrls.length > 1 && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => removeTestUrl(index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                  
                  {/* Collapsible Processing Results */}
                  {hasResults && testResults.processing_results.results[index] && (
                    <div className="ml-4">
                      <details className="group">
                        <summary className="flex items-center gap-2 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800 cursor-pointer hover:shadow-sm transition-shadow">
                          <div className="flex items-center gap-2 flex-1">
                            {testResults.processing_results.results[index].success ? (
                              <CheckCircle className="w-4 h-4 text-green-500" />
                            ) : (
                              <XCircle className="w-4 h-4 text-red-500" />
                            )}
                            <span className="font-medium text-sm">
                              {testResults.processing_results.results[index].success ? 
                                testResults.processing_results.results[index].extracted : 
                                'Failed'
                              }
                            </span>
                            <Badge variant={testResults.processing_results.results[index].success ? 'default' : 'destructive'} className="text-xs">
                              {testResults.processing_results.results[index].success ? '✓' : '✗'}
                            </Badge>
                          </div>
                          <div className="text-xs text-gray-500 group-open:rotate-180 transition-transform">
                            ▼
                          </div>
                        </summary>
                        
                        <div className="mt-2 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                          <div className="space-y-3">
                            {/* Processing Flow */}
                            <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded border">
                              <div className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2">Processing Flow:</div>
                              <div className="flex items-center gap-1 flex-wrap text-xs">
                                {testResults.processing_results.results[index].processing_steps.map((step, stepIndex) => (
                                  <div key={stepIndex} className="flex items-center gap-1">
                                    <Badge variant="outline" className="text-xs px-2 py-0.5">
                                      {step.replace('_', ' ')}
                                    </Badge>
                                    {stepIndex < testResults.processing_results.results[index].processing_steps.length - 1 && (
                                      <ArrowRight className="w-3 h-3 text-gray-400" />
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                            
                            {/* URL Transformation */}
                            <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded border">
                              <div className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2">URL Transformation:</div>
                              <div className="space-y-2">
                                <div>
                                  <span className="text-xs text-gray-500">Input:</span>
                                  <code className="ml-2 text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                                    {testResults.processing_results.results[index].original}
                                  </code>
                                </div>
                                
                                {testResults.processing_results.results[index].normalized && testResults.processing_results.results[index].normalized !== testResults.processing_results.results[index].original && (
                                  <div>
                                    <span className="text-xs text-gray-500">Normalized:</span>
                                    <code className="ml-2 text-xs bg-blue-100 dark:bg-blue-900/30 px-2 py-1 rounded">
                                      {testResults.processing_results.results[index].normalized}
                                    </code>
                                  </div>
                                )}
                                
                                <div>
                                  <span className="text-xs text-gray-500">Extracted:</span>
                                  {testResults.processing_results.results[index].success ? (
                                    <code className="ml-2 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-2 py-1 rounded font-medium">
                                      {testResults.processing_results.results[index].extracted || 'null'}
                                    </code>
                                  ) : (
                                    <code className="ml-2 text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300 px-2 py-1 rounded">
                                      {testResults.processing_results.results[index].extracted || 'null'}
                                    </code>
                                  )}
                                </div>
                                
                                {!testResults.processing_results.results[index].success && (
                                  <div>
                                    <span className="text-xs text-gray-500">Error:</span>
                                    <span className="ml-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-2 py-1 rounded">
                                      {testResults.processing_results.results[index].error || 'No match found'}
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>
                            
                            {/* Template Configuration Debug */}
                            {builderMode === 'template' && selectedTemplate && (
                              <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded border">
                                <div className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2">Template Configuration:</div>
                                <div className="space-y-1 text-xs">
                                  <div>
                                    <span className="text-gray-500">Template:</span>
                                    <code className="ml-2 bg-gray-100 dark:bg-gray-700 px-1 rounded">
                                      {selectedTemplate}
                                    </code>
                                  </div>
                                  <div>
                                    <span className="text-gray-500">Path Patterns:</span>
                                    <code className="ml-2 bg-gray-100 dark:bg-gray-700 px-1 rounded text-xs">
                                      {getTemplateConfig(selectedTemplate).path_patterns?.join(', ') || 'none'}
                                    </code>
                                  </div>
                                  <div>
                                    <span className="text-gray-500">Identifier Regex:</span>
                                    <code className="ml-2 bg-gray-100 dark:bg-gray-700 px-1 rounded text-xs">
                                      {getTemplateConfig(selectedTemplate).identifier_regex || 'none'}
                                    </code>
                                  </div>
                                  <div>
                                    <span className="text-gray-500">URL Path:</span>
                                    <code className="ml-2 bg-gray-100 dark:bg-gray-700 px-1 rounded text-xs">
                                      {new URL(testResults.processing_results.results[index].original.startsWith('http') ? 
                                        testResults.processing_results.results[index].original : 
                                        `https://${testResults.processing_results.results[index].original}`
                                      ).pathname}
                                    </code>
                                  </div>
                                  <div>
                                    <span className="text-gray-500">Expected Regex:</span>
                                    <code className="ml-2 bg-yellow-100 dark:bg-yellow-900/30 px-1 rounded text-xs">
                                      ^\/in\/([a-zA-Z0-9\\-\\_\\.]+)$
                                    </code>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Configuration Hint */}
                            {!testResults.processing_results.results[index].success && (
                              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-3 rounded">
                                <div className="text-xs font-medium text-amber-800 dark:text-amber-200 mb-1">💡 Debugging Info:</div>
                                <div className="text-xs text-amber-700 dark:text-amber-300 space-y-1">
                                  <div>• Check if the path pattern matches the URL path structure</div>
                                  <div>• Verify the identifier regex captures the right part</div>
                                  <div>• Look at the processing steps to see where it failed</div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </details>
                    </div>
                  )}
                </div>
              ))}
              
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addTestUrl}
                  className="flex-1"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Test URL
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (selectedTemplate) {
                      setTestUrls(getTemplateTestUrls(selectedTemplate))
                    }
                  }}
                  className="flex-1"
                >
                  Reset to Template URLs
                </Button>
              </div>
            </div>
            
            {/* Overall Results Summary */}
            {hasResults && (
              <div className="border-t pt-4">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <Code className="w-4 h-4" />
                  Processing Summary
                </h4>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Template Used:</span>
                    <div className="font-medium">
                      {testResults.test_metadata.template_used || 'Custom Template'}
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-500">Success Rate:</span>
                    <div className="font-medium flex items-center gap-1">
                      {testResults.processing_results.successful}/{testResults.processing_results.total_tested}
                      <span className="text-xs text-gray-400">
                        ({(successRate * 100).toFixed(0)}%)
                      </span>
                    </div>
                  </div>
                </div>
                
                {/* Debug Information */}
                <details className="mt-4">
                  <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                    🔍 Show Raw Backend Response (Debug)
                  </summary>
                  <pre className="mt-2 text-xs bg-gray-50 dark:bg-gray-800 p-3 rounded overflow-auto max-h-40">
                    {JSON.stringify(testResults, null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      
      {/* Save/Action Buttons */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {lastTestTime && (
                <Badge variant="outline" className="text-xs">
                  Last tested: {lastTestTime}
                </Badge>
              )}
              {hasResults && (
                <Badge 
                  variant={successRate >= 0.8 ? 'default' : successRate >= 0.5 ? 'secondary' : 'destructive'}
                  className="text-xs"
                >
                  {(successRate * 100).toFixed(0)}% success
                </Badge>
              )}
            </div>
            <div className="flex gap-2">
              {onCancel && (
                <Button 
                  variant="outline"
                  onClick={onCancel}
                  disabled={saving}
                >
                  Cancel
                </Button>
              )}
              <Button 
                variant="outline"
                onClick={() => runLiveTest()}
                disabled={testing || saving}
              >
                <Play className="w-4 h-4 mr-1" />
                {testing ? 'Testing...' : 'Test Again'}
              </Button>
              {onSave && (
                <Button 
                  onClick={handleSave}
                  disabled={
                    saving || 
                    !metadata.name.trim() || 
                    (builderMode === 'template' && !selectedTemplate) ||
                    (builderMode === 'custom' && (!customTemplate.domains.length || !customTemplate.identifier_regex))
                  }
                >
                  {saving ? 'Saving...' : (mode === 'create' ? 'Create Rule' : 'Update Rule')}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}