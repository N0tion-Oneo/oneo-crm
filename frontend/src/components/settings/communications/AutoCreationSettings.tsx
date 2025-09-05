'use client'

import { useState } from 'react'
import { Settings, AlertCircle, Info } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

interface AutoCreationSettingsProps {
  settings: any
  pipelines: any[]
  pipelineFields: any[]
  loadingFields: boolean
  onUpdateSettings: (updates: any) => void
  saving: boolean
  canEdit: boolean
}

export function AutoCreationSettings({
  settings,
  pipelines,
  pipelineFields,
  loadingFields,
  onUpdateSettings,
  saving,
  canEdit
}: AutoCreationSettingsProps) {
  if (!settings) return null

  return (
    <div className="space-y-6">
      {/* Main Toggle */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Auto-Creation Configuration
              </CardTitle>
              <CardDescription>
                Automatically convert participants to contact records based on rules
              </CardDescription>
            </div>
            <Switch
              checked={settings.auto_create_enabled}
              disabled={saving || !canEdit}
              onCheckedChange={(checked) => onUpdateSettings({ auto_create_enabled: checked })}
            />
          </div>
        </CardHeader>
      </Card>

      {settings.auto_create_enabled && (
        <>
          {/* Eligibility Rules */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Eligibility Criteria</CardTitle>
              <CardDescription>
                Define when participants qualify for auto-creation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="min-messages">Minimum Messages</Label>
                  <Input
                    id="min-messages"
                    type="number"
                    min="0"
                    value={settings.min_messages_before_create}
                    disabled={saving || !canEdit}
                    onChange={(e) => onUpdateSettings({ 
                      min_messages_before_create: parseInt(e.target.value) 
                    })}
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Number of messages before creating a contact
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="delay-hours">Creation Delay (Hours)</Label>
                  <Input
                    id="delay-hours"
                    type="number"
                    min="0"
                    value={settings.creation_delay_hours}
                    disabled={saving || !canEdit}
                    onChange={(e) => onUpdateSettings({ 
                      creation_delay_hours: parseInt(e.target.value) 
                    })}
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Wait period before auto-creating
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Check for Duplicates</Label>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Prevent duplicate contacts by checking existing records
                    </p>
                  </div>
                  <Switch
                    checked={settings.check_duplicates_before_create}
                    disabled={saving || !canEdit}
                    onCheckedChange={(checked) => onUpdateSettings({ 
                      check_duplicates_before_create: checked 
                    })}
                  />
                </div>

                {settings.check_duplicates_before_create && (
                  <div className="mt-4 space-y-2">
                    <Label htmlFor="confidence">Duplicate Confidence Threshold</Label>
                    <div className="flex items-center gap-4">
                      <Input
                        id="confidence"
                        type="number"
                        min="0"
                        max="1"
                        step="0.1"
                        value={settings.duplicate_confidence_threshold}
                        disabled={saving || !canEdit}
                        onChange={(e) => onUpdateSettings({ 
                          duplicate_confidence_threshold: parseFloat(e.target.value) 
                        })}
                        className="w-32"
                      />
                      <span className="text-sm text-gray-500">
                        {(settings.duplicate_confidence_threshold * 100).toFixed(0)}% match required
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Pipeline Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Target Pipeline</CardTitle>
              <CardDescription>
                Select which pipeline to create contacts in
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label htmlFor="pipeline">Default Contact Pipeline</Label>
                <Select
                  value={settings.default_contact_pipeline || 'none'}
                  onValueChange={(value) => onUpdateSettings({ 
                    default_contact_pipeline: value === 'none' ? null : value 
                  })}
                  disabled={saving || !canEdit}
                >
                  <SelectTrigger id="pipeline">
                    <SelectValue placeholder="Select a pipeline" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None Selected</SelectItem>
                    {pipelines.map((pipeline) => (
                      <SelectItem key={pipeline.id} value={pipeline.id}>
                        <div className="flex items-center gap-2">
                          <span>{pipeline.name}</span>
                          {pipeline.pipeline_type && (
                            <Badge variant="secondary" className="text-xs">
                              {pipeline.pipeline_type}
                            </Badge>
                          )}
                          <span className="text-xs text-gray-400 ml-2">
                            {pipeline.email_fields?.length > 0 && `${pipeline.email_fields.length} email`}
                            {pipeline.phone_fields?.length > 0 && ` ${pipeline.phone_fields.length} phone`}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {pipelines.length === 0 && (
                  <Alert className="mt-2">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      No compatible pipelines found. Create a pipeline with email or phone fields first.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Name Field Mapping */}
          {settings.default_contact_pipeline && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  Name Field Mapping
                </CardTitle>
                <CardDescription>
                  Configure how participant names map to contact fields
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingFields ? (
                  <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto" />
                    <p className="text-sm text-gray-500 mt-2">Loading pipeline fields...</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Mapping Strategy */}
                    <div className="grid grid-cols-2 gap-4">
                      <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                        <input
                          type="radio"
                          name="nameMapping"
                          value="single"
                          checked={settings.name_mapping_mode === 'single'}
                          onChange={() => onUpdateSettings({
                            name_mapping_mode: 'single',
                            first_name_field: '',
                            last_name_field: ''
                          })}
                          disabled={!canEdit}
                          className="mt-1"
                        />
                        <div>
                          <div className="font-medium">Single Name Field</div>
                          <div className="text-sm text-gray-500">Use one field for full name</div>
                        </div>
                      </label>
                      
                      <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                        <input
                          type="radio"
                          name="nameMapping"
                          value="split"
                          checked={settings.name_mapping_mode === 'split'}
                          onChange={() => onUpdateSettings({
                            name_mapping_mode: 'split',
                            full_name_field: ''
                          })}
                          disabled={!canEdit}
                          className="mt-1"
                        />
                        <div>
                          <div className="font-medium">Split Name Fields</div>
                          <div className="text-sm text-gray-500">Separate first and last names</div>
                        </div>
                      </label>
                    </div>

                    {/* Field Selection */}
                    {settings.name_mapping_mode === 'single' && (
                      <div className="space-y-2">
                        <Label>Full Name Field</Label>
                        <Select
                          value={settings.full_name_field || 'none'}
                          onValueChange={(value) => onUpdateSettings({ 
                            full_name_field: value === 'none' ? '' : value 
                          })}
                          disabled={!canEdit}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select field for full name" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">No field selected</SelectItem>
                            {pipelineFields
                              .filter(field => ['text', 'single_line_text', 'name'].includes(field.field_type))
                              .map(field => (
                                <SelectItem key={field.id} value={field.slug}>
                                  {field.display_name} ({field.slug})
                                </SelectItem>
                              ))
                            }
                          </SelectContent>
                        </Select>
                      </div>
                    )}

                    {settings.name_mapping_mode === 'split' && (
                      <div className="grid grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label>First Name</Label>
                          <Select
                            value={settings.first_name_field || 'none'}
                            onValueChange={(value) => onUpdateSettings({ 
                              first_name_field: value === 'none' ? '' : value 
                            })}
                            disabled={!canEdit}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select field" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">None</SelectItem>
                              {pipelineFields
                                .filter(field => ['text', 'single_line_text', 'name'].includes(field.field_type))
                                .map(field => (
                                  <SelectItem key={field.id} value={field.slug}>
                                    {field.display_name}
                                  </SelectItem>
                                ))
                              }
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label>Last Name</Label>
                          <Select
                            value={settings.last_name_field || 'none'}
                            onValueChange={(value) => onUpdateSettings({ 
                              last_name_field: value === 'none' ? '' : value 
                            })}
                            disabled={!canEdit}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select field" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">None</SelectItem>
                              {pipelineFields
                                .filter(field => ['text', 'single_line_text', 'name'].includes(field.field_type))
                                .map(field => (
                                  <SelectItem key={field.id} value={field.slug}>
                                    {field.display_name}
                                  </SelectItem>
                                ))
                              }
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label>Split Strategy</Label>
                          <Select
                            value={settings.name_split_strategy || 'smart'}
                            onValueChange={(value) => onUpdateSettings({ 
                              name_split_strategy: value 
                            })}
                            disabled={!canEdit}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="smart">Smart Detection</SelectItem>
                              <SelectItem value="first_space">First Space</SelectItem>
                              <SelectItem value="last_space">Last Space</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}