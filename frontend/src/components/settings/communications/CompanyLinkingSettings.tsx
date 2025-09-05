'use client'

import { Building2, Link, Users, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface CompanyLinkingSettingsProps {
  settings: any
  companyPipelines: any[]
  companyPipelineFields: any[]
  loadingCompanyFields: boolean
  onUpdateSettings: (updates: any) => void
  onLoadPipelineFields: (pipelineId: string, type: 'company') => void
  saving: boolean
  canEdit: boolean
}

export function CompanyLinkingSettings({
  settings,
  companyPipelines,
  companyPipelineFields,
  loadingCompanyFields,
  onUpdateSettings,
  onLoadPipelineFields,
  saving,
  canEdit
}: CompanyLinkingSettingsProps) {
  if (!settings) return null

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5" />
          <div>
            <CardTitle>Company Linking</CardTitle>
            <CardDescription>
              Automatically link contacts to companies based on email domains
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Auto-Link Toggle */}
        <div className="flex items-center justify-between p-4 border rounded-lg">
          <div className="space-y-0.5">
            <Label className="text-base">Auto-Link by Domain</Label>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Match participants to companies using email domain
            </p>
          </div>
          <Switch
            checked={settings.auto_link_by_domain}
            disabled={saving || !canEdit}
            onCheckedChange={(checked) => onUpdateSettings({ auto_link_by_domain: checked })}
          />
        </div>

        {settings.auto_link_by_domain && (
          <>
            {/* Create Company Option */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50/50 dark:bg-gray-900/20">
              <div className="space-y-0.5">
                <Label className="text-base">Create Company if Missing</Label>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Automatically create new company records when no match exists
                </p>
              </div>
              <Switch
                checked={settings.create_company_if_missing}
                disabled={saving || !canEdit}
                onCheckedChange={(checked) => onUpdateSettings({ 
                  create_company_if_missing: checked 
                })}
              />
            </div>

            {settings.create_company_if_missing && (
              <>
                {/* Minimum Employees */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Users className="h-4 w-4" />
                    Minimum Employees for Company Creation
                  </Label>
                  <div className="flex items-center gap-4">
                    <Input
                      type="number"
                      min="1"
                      value={settings.min_employees_for_company}
                      disabled={saving || !canEdit}
                      onChange={(e) => onUpdateSettings({ 
                        min_employees_for_company: parseInt(e.target.value) 
                      })}
                      className="w-32"
                    />
                    <p className="text-sm text-gray-500">
                      participants from same domain
                    </p>
                  </div>
                  <p className="text-xs text-gray-500">
                    Wait until this many participants share the same email domain before creating a company
                  </p>
                </div>

                {/* Company Pipeline */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Link className="h-4 w-4" />
                    Default Company Pipeline
                  </Label>
                  <Select
                    value={settings.default_company_pipeline || 'none'}
                    onValueChange={(value) => {
                      onUpdateSettings({ 
                        default_company_pipeline: value === 'none' ? null : value 
                      })
                      if (value !== 'none') {
                        onLoadPipelineFields(value, 'company')
                      }
                    }}
                    disabled={saving || !canEdit}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a pipeline" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None Selected</SelectItem>
                      {companyPipelines.length > 0 ? (
                        companyPipelines.map((pipeline) => (
                          <SelectItem key={pipeline.id} value={pipeline.id}>
                            <div className="flex items-center gap-2">
                              <span>{pipeline.name}</span>
                              {pipeline.pipeline_type && (
                                <Badge variant="secondary" className="text-xs">
                                  {pipeline.pipeline_type}
                                </Badge>
                              )}
                              {(pipeline.domain_fields?.length > 0 || pipeline.url_fields?.length > 0) && (
                                <span className="text-xs text-gray-400 ml-2">
                                  {pipeline.domain_fields?.length > 0 && `${pipeline.domain_fields.length} domain`}
                                  {pipeline.url_fields?.length > 0 && ` ${pipeline.url_fields.length} url`}
                                </span>
                              )}
                            </div>
                          </SelectItem>
                        ))
                      ) : (
                        <SelectItem value="none" disabled>
                          No pipelines with domain/URL duplicate rules
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                  
                  {companyPipelines.length === 0 && (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        Configure duplicate detection rules with domain or URL fields to enable company linking
                      </AlertDescription>
                    </Alert>
                  )}
                </div>

                {/* Company Name Field Mapping */}
                {settings.default_company_pipeline && (
                  <div className="pt-4 border-t">
                    <Label className="mb-2 block">Company Name Field</Label>
                    {loadingCompanyFields ? (
                      <div className="text-center py-4">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto" />
                        <p className="text-sm text-gray-500 mt-2">Loading company pipeline fields...</p>
                      </div>
                    ) : (
                      <>
                        <Select
                          value={settings.company_name_field || 'none'}
                          onValueChange={(value) => onUpdateSettings({ 
                            company_name_field: value === 'none' ? '' : value 
                          })}
                          disabled={saving || !canEdit}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select field for company name" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">No field selected</SelectItem>
                            {companyPipelineFields
                              .filter(field => ['text', 'single_line_text', 'name'].includes(field.field_type))
                              .map(field => (
                                <SelectItem key={field.id} value={field.slug}>
                                  <div className="flex items-center gap-2">
                                    <span>{field.display_name}</span>
                                    <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded">
                                      {field.slug}
                                    </code>
                                  </div>
                                </SelectItem>
                              ))
                            }
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-gray-500 mt-2">
                          Company name will be derived from email domain (e.g., "acme.com" → "Acme")
                        </p>
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* Info Section */}
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex gap-3">
            <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
              <p>
                <strong>How Company Linking Works:</strong>
              </p>
              <ul className="list-disc list-inside space-y-0.5 ml-2">
                <li>Extracts domain from participant email addresses</li>
                <li>Searches for existing companies with matching domain</li>
                <li>Links contact to company or creates new company if configured</li>
                <li>Ignores common email providers (gmail.com, outlook.com, etc.)</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}