'use client'

import {
  Checkbox,
  Input,
  Label,
  Separator
} from '@/components/ui'
import { FieldOption } from '../config-components/FieldOption'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'

interface FileFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
}

export function FileFieldConfig({
  config,
  onChange
}: FileFieldConfigProps) {
  const allowedTypes = config.allowed_types || []
  const commonFileTypes = [
    { value: 'image/*', label: 'All Images', description: 'jpg, png, gif, webp, etc.' },
    { value: 'image/jpeg', label: 'JPEG Images', description: '.jpg, .jpeg' },
    { value: 'image/png', label: 'PNG Images', description: '.png' },
    { value: 'application/pdf', label: 'PDF Documents', description: '.pdf' },
    { value: 'text/*', label: 'Text Files', description: '.txt, .csv, .md, etc.' },
    { value: 'application/msword', label: 'Word Documents', description: '.doc' },
    { value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', label: 'Word Documents (Modern)', description: '.docx' },
    { value: 'application/vnd.ms-excel', label: 'Excel Files', description: '.xls' },
    { value: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', label: 'Excel Files (Modern)', description: '.xlsx' }
  ]

  const handleToggleFileType = (mimeType: string, checked: boolean) => {
    const newTypes = checked
      ? [...allowedTypes, mimeType]
      : allowedTypes.filter((type: string) => type !== mimeType)
    onChange('allowed_types', newTypes)
  }

  const handleAddCustomType = (customType: string) => {
    if (customType && !allowedTypes.includes(customType)) {
      onChange('allowed_types', [...allowedTypes, customType])
    }
  }

  const handleRemoveCustomType = (typeToRemove: string) => {
    onChange('allowed_types', allowedTypes.filter((type: string) => type !== typeToRemove))
  }

  const customTypes = allowedTypes.filter((type: string) => 
    !commonFileTypes.some(common => common.value === type)
  )

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">File Upload Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          File upload with type restrictions and size limits
        </p>
      </div>

      {/* File Type Restrictions */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <HelpTooltipWrapper helpText="Choose which file types users can upload. Leave all unchecked to allow any file type.">
            <Label className="text-base font-medium text-gray-900 dark:text-white">
              Allowed File Types 
              <span className="text-xs text-muted-foreground ml-2 font-normal">
                ({allowedTypes.length} type{allowedTypes.length !== 1 ? 's' : ''} selected)
              </span>
            </Label>
          </HelpTooltipWrapper>
        </div>

        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Select common file types or add custom MIME types below.
          </p>

          {/* Common File Types */}
          <div className="space-y-2">
            {commonFileTypes.map((fileType) => (
              <div key={fileType.value} className="flex items-start space-x-3">
                <Checkbox
                  id={`type-${fileType.value}`}
                  checked={allowedTypes.includes(fileType.value)}
                  onCheckedChange={(checked) => handleToggleFileType(fileType.value, !!checked)}
                />
                <div className="space-y-1">
                  <Label htmlFor={`type-${fileType.value}`} className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300">
                    {fileType.label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{fileType.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Custom File Types */}
          {customTypes.length > 0 && (
            <div className="space-y-2">
              <Label className="text-sm font-medium text-gray-900 dark:text-white">Custom Types:</Label>
              <div className="flex flex-wrap gap-2">
                {customTypes.map((type: string) => (
                  <div key={type} className="flex items-center space-x-1 px-2 py-1 bg-secondary rounded-md">
                    <span className="text-xs text-gray-600 dark:text-gray-400">{type}</span>
                    <button
                      onClick={() => handleRemoveCustomType(type)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Add Custom Type */}
          <div className="flex items-center space-x-2">
            <Input
              type="text"
              placeholder="application/pdf or .pdf"
              className="flex-1"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  const input = e.target as HTMLInputElement
                  handleAddCustomType(input.value.trim())
                  input.value = ''
                }
              }}
            />
            <button
              onClick={(e) => {
                const input = (e.target as HTMLButtonElement).previousElementSibling as HTMLInputElement
                handleAddCustomType(input.value.trim())
                input.value = ''
              }}
              className="px-3 py-2 text-sm text-primary-foreground bg-primary rounded-md hover:bg-primary/90"
            >
              Add
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Enter MIME type (e.g., application/pdf) or file extension (e.g., .pdf)
          </p>
        </div>
      </div>

      <Separator />

      {/* File Size Limits */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">File Size Limits</Label>

        <div className="grid grid-cols-2 gap-4">
          <FieldOption
            label="Maximum File Size (MB)"
            description="Maximum size per file in megabytes"
            type="number"
            value={config.max_size_mb || ''}
            onChange={(value) => onChange('max_size_mb', value)}
            placeholder="10"
          />

          <FieldOption
            label="Total Size Limit (MB)"
            description="Maximum total size for all files"
            type="number"
            value={config.total_size_mb || ''}
            onChange={(value) => onChange('total_size_mb', value)}
            placeholder="100"
          />
        </div>
      </div>

      <Separator />

      {/* Upload Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Upload Options</Label>

        <div className="grid grid-cols-2 gap-4">
          <FieldOption
            label="Maximum Files"
            description="Maximum number of files that can be uploaded"
            type="number"
            value={config.max_files || ''}
            onChange={(value) => onChange('max_files', value)}
            placeholder="5"
          />

          <FieldOption
            label="Minimum Files"
            description="Minimum number of files required"
            type="number"
            value={config.min_files || ''}
            onChange={(value) => onChange('min_files', value)}
            placeholder="1"
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="multiple-files"
              checked={config.multiple_files !== false}
              onCheckedChange={(checked) => onChange('multiple_files', checked)}
            />
            <HelpTooltipWrapper helpText="Allow users to select and upload multiple files at once">
              <Label htmlFor="multiple-files" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Allow multiple files
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="drag-drop"
              checked={config.drag_drop !== false}
              onCheckedChange={(checked) => onChange('drag_drop', checked)}
            />
            <HelpTooltipWrapper helpText="Enable drag-and-drop file upload interface">
              <Label htmlFor="drag-drop" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Enable drag & drop
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="show-preview"
              checked={config.show_preview !== false}
              onCheckedChange={(checked) => onChange('show_preview', checked)}
            />
            <HelpTooltipWrapper helpText="Show thumbnail previews for images and file icons">
              <Label htmlFor="show-preview" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Show file previews
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="auto-upload"
              checked={config.auto_upload || false}
              onCheckedChange={(checked) => onChange('auto_upload', checked)}
            />
            <HelpTooltipWrapper helpText="Automatically start upload when files are selected">
              <Label htmlFor="auto-upload" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Auto-upload on selection
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      <Separator />

      {/* Storage Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Storage & Security</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="virus-scan"
              checked={config.virus_scan !== false}
              onCheckedChange={(checked) => onChange('virus_scan', checked)}
            />
            <HelpTooltipWrapper helpText="Scan uploaded files for viruses and malware">
              <Label htmlFor="virus-scan" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Enable virus scanning
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="private-files"
              checked={config.private_files || false}
              onCheckedChange={(checked) => onChange('private_files', checked)}
            />
            <HelpTooltipWrapper helpText="Store files privately (not publicly accessible)">
              <Label htmlFor="private-files" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Private file storage
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="encrypt-files"
              checked={config.encrypt_files || false}
              onCheckedChange={(checked) => onChange('encrypt_files', checked)}
            />
            <HelpTooltipWrapper helpText="Encrypt files at rest for additional security">
              <Label htmlFor="encrypt-files" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Encrypt stored files
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">File Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• File types: {allowedTypes.length === 0 ? 'Any file type' : `${allowedTypes.length} type(s) allowed`}</div>
            {config.max_size_mb && <div>• Max size: {config.max_size_mb}MB per file</div>}
            {config.max_files && <div>• Max files: {config.max_files}</div>}
            <div>• Multiple files: {config.multiple_files !== false ? 'Allowed' : 'Single file only'}</div>
            {config.virus_scan !== false && <div>• Virus scanning enabled</div>}
            {config.private_files && <div>• Private file storage</div>}
            {config.encrypt_files && <div>• File encryption enabled</div>}
          </div>
        </div>
      </div>
    </div>
  )
}