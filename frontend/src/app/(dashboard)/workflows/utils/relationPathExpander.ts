/**
 * Relation Path Expander Utility
 *
 * Recursively traverses data structures with expanded relations and generates
 * all valid dot notation paths for use in variable pickers and field mappers.
 *
 * Supports:
 * - Simple fields: record.data.email
 * - Single relations: record.data.company.data.name
 * - Multi-hop relations: record.data.company.data.jobs[0].data.title
 * - Array relations: record.data.contacts[0].data.email
 */

export interface VariablePath {
  label: string;           // Human-readable label: "Company Name"
  value: string;           // Dot notation path: "record.data.company.data.name"
  description?: string;    // Optional description with type info
  type: string;            // Data type: string, number, relation, etc.
  isRelation: boolean;     // Whether this is a relation field
  depth: number;           // Nesting depth (0 = root)
  parent?: string;         // Parent path for grouping
  group?: string;          // Group label for display
}

/**
 * Check if a value is a relation field
 * Relation fields have the structure: {id, display_value, data, pipeline_id?, title?}
 */
function isRelationField(value: any): boolean {
  if (!value || typeof value !== 'object') return false;

  // Single relation
  if ('id' in value && 'display_value' in value && 'data' in value) {
    return true;
  }

  // Array of relations
  if (Array.isArray(value) && value.length > 0) {
    return value.every(item =>
      item && typeof item === 'object' &&
      'id' in item && 'display_value' in item && 'data' in item
    );
  }

  return false;
}

/**
 * Get human-readable label from field name
 */
function formatFieldLabel(fieldName: string): string {
  return fieldName
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
    .trim();
}

/**
 * Detect data type of a value
 */
function detectType(value: any): string {
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value)) return 'array';
  if (typeof value === 'object') {
    if (isRelationField(value)) return 'relation';
    return 'object';
  }
  if (typeof value === 'number') return 'number';
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'string') {
    // Check if it looks like a date
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) return 'datetime';
    return 'string';
  }
  return 'unknown';
}

/**
 * Expand relation paths recursively
 *
 * @param data - The data object to traverse
 * @param basePath - Current path prefix (e.g., "record.data")
 * @param baseLabel - Current label prefix (e.g., "Record")
 * @param maxDepth - Maximum nesting depth to traverse
 * @param currentDepth - Current depth in recursion
 * @param visited - Set of visited paths to prevent circular references
 * @param parentGroup - Parent group label for hierarchical display
 * @returns Array of variable paths
 */
export function expandRelationPaths(
  data: any,
  basePath: string = '',
  baseLabel: string = '',
  maxDepth: number = 3,
  currentDepth: number = 0,
  visited: Set<string> = new Set(),
  parentGroup?: string
): VariablePath[] {
  const paths: VariablePath[] = [];

  // Stop if max depth reached
  if (currentDepth >= maxDepth) {
    return paths;
  }

  // Stop if null or undefined
  if (data === null || data === undefined) {
    return paths;
  }

  // Prevent circular references
  const pathKey = `${basePath}-${JSON.stringify(data).substring(0, 100)}`;
  if (visited.has(pathKey)) {
    return paths;
  }
  visited.add(pathKey);

  // Handle different data types
  const type = detectType(data);

  // Handle arrays
  if (Array.isArray(data)) {
    // Add array itself as a path
    if (basePath) {
      paths.push({
        label: baseLabel || 'Array',
        value: basePath,
        description: `Array with ${data.length} item(s)`,
        type: 'array',
        isRelation: false,
        depth: currentDepth,
        parent: basePath.split('.').slice(0, -1).join('.') || undefined,
        group: parentGroup
      });
    }

    // Expand first element (as template for array access)
    if (data.length > 0 && currentDepth < maxDepth) {
      const firstItem = data[0];
      const itemPath = basePath ? `${basePath}[0]` : '[0]';
      const itemLabel = baseLabel ? `${baseLabel} [0]` : 'Item [0]';

      // Recursively expand the array item
      const itemPaths = expandRelationPaths(
        firstItem,
        itemPath,
        itemLabel,
        maxDepth,
        currentDepth + 1,
        visited,
        parentGroup || baseLabel
      );
      paths.push(...itemPaths);
    }

    return paths;
  }

  // Handle objects (including relations)
  if (typeof data === 'object') {
    const isRelation = isRelationField(data);

    // Add the object/relation itself
    if (basePath) {
      paths.push({
        label: baseLabel || formatFieldLabel(basePath.split('.').pop() || 'Object'),
        value: basePath,
        description: isRelation
          ? `Relation: ${data.display_value || 'Related Record'}`
          : `Object with ${Object.keys(data).length} properties`,
        type: isRelation ? 'relation' : 'object',
        isRelation,
        depth: currentDepth,
        parent: basePath.split('.').slice(0, -1).join('.') || undefined,
        group: parentGroup
      });
    }

    // Expand object properties
    for (const [key, value] of Object.entries(data)) {
      // Skip metadata fields for cleaner output
      if (['id', 'display_value', 'pipeline_id', 'title'].includes(key) && isRelation) {
        // For relation fields, add these specific fields
        const fieldPath = basePath ? `${basePath}.${key}` : key;
        const fieldLabel = baseLabel ? `${baseLabel} ${formatFieldLabel(key)}` : formatFieldLabel(key);

        paths.push({
          label: fieldLabel,
          value: fieldPath,
          description: `${formatFieldLabel(key)} (${detectType(value)})`,
          type: detectType(value),
          isRelation: false,
          depth: currentDepth + 1,
          parent: basePath || undefined,
          group: parentGroup || baseLabel
        });
        continue;
      }

      const fieldPath = basePath ? `${basePath}.${key}` : key;
      const fieldLabel = baseLabel ? `${baseLabel} ${formatFieldLabel(key)}` : formatFieldLabel(key);
      const fieldType = detectType(value);

      // For relation fields, expand the nested data
      if (isRelation && key === 'data' && typeof value === 'object') {
        // Recursively expand relation data
        const nestedPaths = expandRelationPaths(
          value,
          fieldPath,
          baseLabel || formatFieldLabel(basePath.split('.').pop() || 'Record'),
          maxDepth,
          currentDepth + 1,
          visited,
          parentGroup || baseLabel
        );
        paths.push(...nestedPaths);
      }
      // For primitive values or shallow objects, add as terminal path
      else if (
        fieldType === 'string' ||
        fieldType === 'number' ||
        fieldType === 'boolean' ||
        fieldType === 'datetime' ||
        fieldType === 'null'
      ) {
        paths.push({
          label: fieldLabel,
          value: fieldPath,
          description: `${formatFieldLabel(key)} (${fieldType})`,
          type: fieldType,
          isRelation: false,
          depth: currentDepth + 1,
          parent: basePath || undefined,
          group: parentGroup || baseLabel
        });
      }
      // For nested objects/arrays, recurse
      else if (fieldType === 'object' || fieldType === 'array' || fieldType === 'relation') {
        const nestedPaths = expandRelationPaths(
          value,
          fieldPath,
          fieldLabel,
          maxDepth,
          currentDepth + 1,
          visited,
          parentGroup || baseLabel
        );
        paths.push(...nestedPaths);
      }
    }
  }
  // Handle primitive values
  else {
    if (basePath) {
      paths.push({
        label: baseLabel || formatFieldLabel(basePath.split('.').pop() || 'Value'),
        value: basePath,
        description: `${type} value`,
        type,
        isRelation: false,
        depth: currentDepth,
        parent: basePath.split('.').slice(0, -1).join('.') || undefined,
        group: parentGroup
      });
    }
  }

  return paths;
}

/**
 * Build available variables from input data with expanded relation paths
 *
 * @param inputData - Input data from NodeConfigModal (trigger output or node outputs)
 * @param maxDepth - Maximum depth for relation traversal (default: 3)
 * @returns Array of variable paths suitable for dropdowns
 */
export function buildAvailableVariables(
  inputData: any,
  maxDepth: number = 3
): VariablePath[] {
  if (!inputData || typeof inputData !== 'object') {
    return [];
  }

  const variables: VariablePath[] = [];

  // Handle grouped node data (e.g., {trigger_record_created: {...}, node_xyz: {...}})
  if (Object.keys(inputData).length > 0) {
    for (const [nodeName, nodeData] of Object.entries(inputData)) {
      // Skip metadata fields
      if (['sources', 'availableVariables'].includes(nodeName)) continue;

      // Generate paths for this node's data
      const nodePaths = expandRelationPaths(
        nodeData,
        nodeName,
        formatFieldLabel(nodeName),
        maxDepth,
        0,
        new Set()
      );

      variables.push(...nodePaths);
    }
  }

  // Sort variables: prioritize shallower paths, then alphabetically
  variables.sort((a, b) => {
    if (a.depth !== b.depth) return a.depth - b.depth;
    return a.label.localeCompare(b.label);
  });

  return variables;
}

/**
 * Filter variables by search term
 */
export function filterVariables(
  variables: VariablePath[],
  searchTerm: string
): VariablePath[] {
  if (!searchTerm) return variables;

  const term = searchTerm.toLowerCase();
  return variables.filter(
    v =>
      v.label.toLowerCase().includes(term) ||
      v.value.toLowerCase().includes(term) ||
      v.description?.toLowerCase().includes(term)
  );
}

/**
 * Group variables by parent/group for hierarchical display
 */
export function groupVariables(
  variables: VariablePath[]
): Record<string, VariablePath[]> {
  const grouped: Record<string, VariablePath[]> = { root: [] };

  for (const variable of variables) {
    const group = variable.group || 'root';
    if (!grouped[group]) {
      grouped[group] = [];
    }
    grouped[group].push(variable);
  }

  return grouped;
}

/**
 * Expand target pipeline fields to include relation field paths
 *
 * This generates field paths for the FieldMapperWidget target field dropdown,
 * allowing users to map to nested relation fields like company.name or company.jobs[0].title
 *
 * @param pipelineFields - Array of field definitions for the target pipeline
 * @param pipelines - Array of all pipelines (for looking up related pipeline fields)
 * @param maxDepth - Maximum depth to traverse (default: 2, e.g., company.jobs[0].title)
 * @returns Array of expanded field definitions with dot notation paths
 */
export interface ExpandedTargetField {
  value: string;           // Dot notation path: "company.name" or "company.jobs[0].title"
  label: string;           // Human-readable: "Company Name" or "Company Jobs Title"
  field_type: string;      // Field type from the related pipeline
  is_required?: boolean;   // Whether the field is required
  depth: number;           // Nesting depth (0 = direct field, 1 = company.name, 2 = company.jobs[0].title)
  parent?: string;         // Parent path for grouping
  relationPath?: string;   // The relation field path (e.g., "company" or "company.jobs[0]")
  originalField?: any;     // Original field definition for reference
}

export function expandTargetFields(
  pipelineFields: any[],
  pipelines: any[] | Record<string, any[]>,
  maxDepth: number = 2
): ExpandedTargetField[] {
  if (!pipelineFields) return [];

  const expandedFields: ExpandedTargetField[] = [];

  // Helper to find pipeline fields by ID
  // Support both array of pipelines with fields, or a map of {pipelineId: fields[]}
  const findPipelineFields = (pipelineId: string): any[] | null => {
    // If pipelines is a map object (e.g., {1: [...fields], 2: [...fields]})
    if (pipelines && !Array.isArray(pipelines)) {
      return pipelines[pipelineId] || null;
    }

    // If pipelines is an array, find the pipeline and return its fields
    if (Array.isArray(pipelines)) {
      const pipeline = pipelines.find(p => String(p.id) === String(pipelineId));
      return pipeline?.fields || null;
    }

    return null;
  };

  // Helper to recursively expand relation fields
  const expandRelationField = (
    field: any,
    basePath: string = '',
    baseLabel: string = '',
    currentDepth: number = 0,
    visitedPipelines: Set<string> = new Set()
  ) => {
    // Stop if max depth reached
    if (currentDepth >= maxDepth) return;

    // Check if this is a relation field
    // Support both config and field_config property names
    const fieldConfig = field.config || field.field_config;
    if (field.field_type === 'relation' && fieldConfig?.target_pipeline_id) {
      const targetPipelineId = fieldConfig.target_pipeline_id;

      // Prevent circular references
      if (visitedPipelines.has(targetPipelineId)) return;
      visitedPipelines.add(targetPipelineId);

      // Find the related pipeline fields
      const relatedPipelineFields = findPipelineFields(targetPipelineId);

      console.log('🔍 [expandTargetFields] Looking for related pipeline:', {
        field: field.slug || field.name,
        targetPipelineId,
        foundFields: !!relatedPipelineFields,
        fieldsCount: relatedPipelineFields?.length
      });

      if (!relatedPipelineFields || relatedPipelineFields.length === 0) return;

      const fieldPath = basePath ? `${basePath}.${field.slug || field.name}` : (field.slug || field.name);
      const fieldLabel = baseLabel ? `${baseLabel} ${formatFieldLabel(field.display_name || field.name)}` : formatFieldLabel(field.display_name || field.name);

      // Check if this is a multi-valued relation (array)
      const isMultiple = fieldConfig?.cardinality === 'many' || fieldConfig?.allow_multiple;

      // For multiple relations, add array indexer [0]
      const relationPath = isMultiple ? `${fieldPath}[0]` : fieldPath;
      const relationLabel = isMultiple ? `${fieldLabel} [0]` : fieldLabel;

      // Expand the related pipeline's fields
      relatedPipelineFields.forEach((relatedField: any) => {
        // Skip system fields that shouldn't be editable
        if (relatedField.slug?.startsWith('system_')) return;

        const nestedPath = `${relationPath}.${relatedField.slug || relatedField.name}`;
        const nestedLabel = `${relationLabel} ${formatFieldLabel(relatedField.display_name || relatedField.name)}`;

        // Add the nested field
        expandedFields.push({
          value: nestedPath,
          label: nestedLabel,
          field_type: relatedField.field_type,
          is_required: relatedField.is_required,
          depth: currentDepth + 1,
          parent: fieldPath,
          relationPath: relationPath,
          originalField: relatedField
        });

        // Recursively expand if this nested field is also a relation
        if (relatedField.field_type === 'relation' && currentDepth + 1 < maxDepth) {
          expandRelationField(
            relatedField,
            relationPath,
            relationLabel,
            currentDepth + 1,
            new Set(visitedPipelines)
          );
        }
      });
    }
  };

  // First, add all direct fields (non-relation fields or relation fields themselves)
  pipelineFields.forEach(field => {
    // Skip deleted fields
    if (field.is_deleted) return;

    // Add direct field
    expandedFields.push({
      value: field.slug || field.name,
      label: field.display_name || field.name,
      field_type: field.field_type,
      is_required: field.is_required,
      depth: 0,
      originalField: field
    });

    // If it's a relation field, expand its nested fields
    if (field.field_type === 'relation') {
      expandRelationField(field, '', '', 0, new Set());
    }
  });

  // Sort fields: direct fields first, then by depth, then alphabetically
  expandedFields.sort((a, b) => {
    if (a.depth !== b.depth) return a.depth - b.depth;
    return a.label.localeCompare(b.label);
  });

  return expandedFields;
}
