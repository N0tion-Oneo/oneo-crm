'use client'

import {
  Checkbox,
  Input,
  Label,
  Separator
} from '@/components/ui'
import { FieldOption } from '../config-components/FieldOption'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'

interface TagsFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
}

export function TagsFieldConfig({
  config,
  onChange
}: TagsFieldConfigProps) {
  const predefinedTags = config.predefined_tags || []

  const handleAddTag = (tag: string) => {
    if (tag && !predefinedTags.includes(tag)) {
      const newTags = [...predefinedTags, tag]
      onChange('predefined_tags', newTags)
    }
  }

  const handleRemoveTag = (index: number) => {
    const newTags = predefinedTags.filter((_: string, i: number) => i !== index)
    onChange('predefined_tags', newTags)
  }

  const handleUpdateTag = (index: number, newTag: string) => {
    if (newTag) {
      const newTags = [...predefinedTags]
      newTags[index] = newTag
      onChange('predefined_tags', newTags)
    }
  }

  return (
    <div className="space-y-6">
      {/* Field Type Info */}
      <div className="p-3 bg-muted/50 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">Tags Field</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Multiple tag input with autocomplete and predefined options
        </p>
      </div>

      {/* Predefined Tags */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <HelpTooltipWrapper helpText="Define a list of common tags that users can quickly select from">
            <Label className="text-base font-medium text-gray-900 dark:text-white">
              Predefined Tags 
              <span className="text-xs text-muted-foreground ml-2 font-normal">
                ({predefinedTags.length} tag{predefinedTags.length !== 1 ? 's' : ''})
              </span>
            </Label>
          </HelpTooltipWrapper>
        </div>

        <div className="space-y-2">
          {predefinedTags.map((tag: string, index: number) => (
            <div key={index} className="flex items-center space-x-2">
              <Input
                type="text"
                placeholder="Tag name"
                value={tag}
                onChange={(e) => handleUpdateTag(index, e.target.value)}
                className="flex-1"
              />
              <button
                onClick={() => handleRemoveTag(index)}
                className="p-2 text-destructive hover:text-destructive/80 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
          
          <button
            onClick={() => handleAddTag('')}
            className="w-full px-3 py-2 border-2 border-dashed border-muted-foreground/25 rounded-md text-muted-foreground hover:border-primary hover:text-primary transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            Add predefined tag
          </button>
        </div>
      </div>

      <Separator />

      {/* Tag Input Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Input Options</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="allow-custom"
              checked={config.allow_custom_tags !== false}
              onCheckedChange={(checked) => onChange('allow_custom_tags', checked)}
            />
            <HelpTooltipWrapper helpText="Allow users to create new tags beyond the predefined list">
              <Label htmlFor="allow-custom" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Allow custom tags
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="case-sensitive"
              checked={config.case_sensitive || false}
              onCheckedChange={(checked) => onChange('case_sensitive', checked)}
            />
            <HelpTooltipWrapper helpText="Make tag matching case-sensitive (e.g., 'Tag' vs 'tag')">
              <Label htmlFor="case-sensitive" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Case sensitive tags
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="auto-complete"
              checked={config.auto_complete !== false}
              onCheckedChange={(checked) => onChange('auto_complete', checked)}
            />
            <HelpTooltipWrapper helpText="Show autocomplete suggestions as user types">
              <Label htmlFor="auto-complete" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Enable autocomplete
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="allow-duplicates"
              checked={config.allow_duplicates || false}
              onCheckedChange={(checked) => onChange('allow_duplicates', checked)}
            />
            <HelpTooltipWrapper helpText="Allow the same tag to be added multiple times">
              <Label htmlFor="allow-duplicates" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Allow duplicate tags
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      <Separator />

      {/* Display Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Display Options</Label>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="show-count"
              checked={config.show_count || false}
              onCheckedChange={(checked) => onChange('show_count', checked)}
            />
            <HelpTooltipWrapper helpText="Show the number of tags next to the field">
              <Label htmlFor="show-count" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Show tag count
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="sortable"
              checked={config.sortable || false}
              onCheckedChange={(checked) => onChange('sortable', checked)}
            />
            <HelpTooltipWrapper helpText="Allow users to reorder tags by dragging">
              <Label htmlFor="sortable" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Allow tag reordering
              </Label>
            </HelpTooltipWrapper>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="show-suggestions"
              checked={config.show_suggestions !== false}
              onCheckedChange={(checked) => onChange('show_suggestions', checked)}
            />
            <HelpTooltipWrapper helpText="Show predefined tags as clickable suggestions">
              <Label htmlFor="show-suggestions" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                Show tag suggestions
              </Label>
            </HelpTooltipWrapper>
          </div>
        </div>
      </div>

      <Separator />

      {/* Validation Options */}
      <div className="space-y-4">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Validation</Label>

        <div className="grid grid-cols-2 gap-4">
          <FieldOption
            label="Minimum Tags"
            description="Minimum number of tags required"
            type="number"
            value={config.min_tags || ''}
            onChange={(value) => onChange('min_tags', value)}
          />

          <FieldOption
            label="Maximum Tags"
            description="Maximum number of tags allowed"
            type="number"
            value={config.max_tags || ''}
            onChange={(value) => onChange('max_tags', value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FieldOption
            label="Min Tag Length"
            description="Minimum characters per tag"
            type="number"
            value={config.min_tag_length || 1}
            onChange={(value) => onChange('min_tag_length', value || 1)}
          />

          <FieldOption
            label="Max Tag Length"
            description="Maximum characters per tag"
            type="number"
            value={config.max_tag_length || ''}
            onChange={(value) => onChange('max_tag_length', value)}
          />
        </div>

        <FieldOption
          label="Forbidden Characters"
          description="Characters not allowed in tags (e.g., ,;|)"
          type="text"
          value={config.forbidden_chars || ''}
          onChange={(value) => onChange('forbidden_chars', value)}
          placeholder=",;|<>"
        />
      </div>

      {/* Configuration Summary */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">Tags Field Configuration</p>
          <div className="text-blue-700 dark:text-blue-300 space-y-1">
            <div>• {predefinedTags.length} predefined tag{predefinedTags.length !== 1 ? 's' : ''}</div>
            <div>• Custom tags: {config.allow_custom_tags !== false ? 'Allowed' : 'Not allowed'}</div>
            {config.min_tags && <div>• Minimum tags: {config.min_tags}</div>}
            {config.max_tags && <div>• Maximum tags: {config.max_tags}</div>}
            {config.case_sensitive && <div>• Case sensitive matching</div>}
            {config.allow_duplicates && <div>• Duplicate tags allowed</div>}
            {config.sortable && <div>• User can reorder tags</div>}
          </div>
        </div>
      </div>
    </div>
  )
}