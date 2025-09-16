import React from 'react';
import { FieldValueMatcher } from './FieldValueMatcher';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Info } from 'lucide-react';

interface DynamicFieldValueMatchesProps {
  value: any;
  onChange: (value: any) => void;
  config: any;
  pipelineFields?: any[];
}

export function DynamicFieldValueMatches({
  value = {},
  onChange,
  config,
  pipelineFields = []
}: DynamicFieldValueMatchesProps) {
  // Debug pipeline fields structure
  console.log('DynamicFieldValueMatches - Pipeline fields:', {
    count: pipelineFields.length,
    firstField: pipelineFields[0],
    selectFields: pipelineFields.filter(f =>
      f.field_type === 'select' || f.field_type === 'multiselect' ||
      f.fieldType === 'select' || f.fieldType === 'multiselect'
    ),
    trackedFields: config.tracked_fields
  });

  // Determine which fields we're tracking
  const trackedFields = React.useMemo(() => {
    if (config.track_all_changes) {
      // If tracking all changes, we don't show field-specific value matching
      return [];
    }
    return config.tracked_fields || [];
  }, [config.track_all_changes, config.tracked_fields]);

  // Get field data for each tracked field
  const getFieldData = (fieldIdentifier: string | number) => {
    // Convert to string for comparison since IDs might be numbers
    const fieldId = String(fieldIdentifier);

    return pipelineFields.find(f =>
      String(f.id) === fieldId ||
      f.name === fieldId ||
      f.slug === fieldId ||
      f.key === fieldId
    );
  };

  const updateFieldValue = (fieldKey: string, fieldValue: any) => {
    onChange({
      ...value,
      [fieldKey]: fieldValue
    });
  };

  if (trackedFields.length === 0) {
    return (
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          {config.track_all_changes
            ? "Value matching is not available when tracking all field changes. Select specific fields to enable value matching."
            : "Select specific fields to track in order to configure value matching."}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-2">
      <div className="text-sm text-muted-foreground mb-2">
        Configure value matching for each tracked field:
      </div>
      {trackedFields.map((fieldIdentifier: string | number) => {
        const fieldData = getFieldData(fieldIdentifier);
        const fieldKey = String(fieldIdentifier);
        return (
          <FieldValueMatcher
            key={fieldKey}
            fieldName={fieldData?.label || fieldData?.name || fieldKey}
            fieldData={fieldData}
            value={value[fieldKey]}
            onChange={(fieldValue) => updateFieldValue(fieldKey, fieldValue)}
          />
        );
      })}
    </div>
  );
}