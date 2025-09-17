/**
 * Dynamic select widget that fetches options from an API endpoint
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
} from '@/components/ui/select';
import { Loader2, AlertCircle } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';
import { api } from '@/lib/api';

export const DynamicSelect: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {}, config = {} } = props;
  const [options, setOptions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    fetch_endpoint,
    depends_on,
    value_field = 'id',
    label_field = 'label',
    show_field_count,
    group_by
  } = uiHints;

  // Get dependency value
  const dependencyValue = depends_on ? config[depends_on] : null;

  // Build the endpoint URL
  const endpoint = useMemo(() => {
    if (!fetch_endpoint) return null;

    // Replace placeholders in endpoint with actual values
    let url = fetch_endpoint;
    if (depends_on && dependencyValue) {
      url = url.replace(`{${depends_on}}`, dependencyValue);
    }

    // Remove any remaining placeholders if dependency is missing
    url = url.replace(/\{[^}]+\}/g, '');

    return url;
  }, [fetch_endpoint, depends_on, dependencyValue]);

  useEffect(() => {
    // Clear options if dependency changes
    if (depends_on && !dependencyValue) {
      setOptions([]);
      return;
    }

    if (!endpoint) return;

    const fetchOptions = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await api.get(endpoint);
        let data = response.data;

        // Handle different response formats
        if (data.results && Array.isArray(data.results)) {
          data = data.results;
        } else if (data.items && Array.isArray(data.items)) {
          data = data.items;
        } else if (data.options && Array.isArray(data.options)) {
          data = data.options;
        } else if (data.forms && Array.isArray(data.forms)) {
          // Special handling for form responses
          data = data.forms;
        }

        setOptions(Array.isArray(data) ? data : []);
      } catch (err: any) {
        console.error('Failed to fetch dynamic options:', err);
        setError(err.message || 'Failed to load options');
        setOptions([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchOptions();
  }, [endpoint]);

  // Group options if needed
  const groupedOptions = useMemo(() => {
    if (!group_by || !options.length) return { '': options };

    const groups: Record<string, any[]> = {};
    options.forEach(option => {
      const groupKey = option[group_by] || 'Other';
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(option);
    });

    return groups;
  }, [options, group_by]);

  const placeholder = props.placeholder || uiHints.placeholder || 'Select an option';

  // Show dependency message if waiting for dependency
  if (depends_on && !dependencyValue) {
    return (
      <BaseWidgetWrapper {...props}>
        <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-500 text-sm">
          Please select {depends_on.replace(/_/g, ' ')} first
        </div>
      </BaseWidgetWrapper>
    );
  }

  // Show error state
  if (error) {
    return (
      <BaseWidgetWrapper {...props}>
        <div className="px-3 py-2 border border-red-200 rounded-md bg-red-50 text-red-600 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      </BaseWidgetWrapper>
    );
  }

  return (
    <BaseWidgetWrapper {...props}>
      <Select
        value={value || ''}
        onValueChange={onChange}
        disabled={props.disabled || props.readonly || isLoading}
      >
        <SelectTrigger>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading options...</span>
            </div>
          ) : (
            <SelectValue placeholder={placeholder} />
          )}
        </SelectTrigger>
        <SelectContent>
          {Object.entries(groupedOptions).map(([groupName, groupOptions]) => (
            <React.Fragment key={groupName}>
              {groupName && group_by && (
                <SelectGroup>
                  <SelectLabel>{groupName}</SelectLabel>
                  {renderOptions(groupOptions)}
                </SelectGroup>
              )}
              {!group_by && renderOptions(groupOptions)}
            </React.Fragment>
          ))}
        </SelectContent>
      </Select>
    </BaseWidgetWrapper>
  );

  function renderOptions(optionsList: any[]) {
    return optionsList.map((option) => {
      const optionValue = option[value_field] || option.value || option.id;
      const optionLabel = option[label_field] || option.label || option.name || optionValue;
      const fieldCount = show_field_count && option.field_count;

      return (
        <SelectItem key={optionValue} value={optionValue}>
          <div className="flex items-center justify-between w-full">
            <span>{optionLabel}</span>
            {fieldCount !== undefined && (
              <span className="text-xs text-gray-500 ml-2">
                ({fieldCount} field{fieldCount !== 1 ? 's' : ''})
              </span>
            )}
          </div>
        </SelectItem>
      );
    });
  }
};