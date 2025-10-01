'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Variable, Search, X, ChevronRight, Clock, User,
  Database, Settings, Hash, Type, Calendar, List,
  ToggleLeft, Link, FileText, Code
} from 'lucide-react';

interface VariablePickerProps {
  availableVariables: Array<{
    nodeId: string;
    label: string;
    outputs: string[];
  }>;
  onSelect: (variable: string) => void;
  onClose: () => void;
  currentField?: string;
  showArraysOnly?: boolean;
}

interface VariableItem {
  path: string;
  label: string;
  type: string;
  category: string;
  description?: string;
  icon?: React.ReactNode;
}

export function VariablePicker({
  availableVariables,
  onSelect,
  onClose,
  currentField,
  showArraysOnly = false
}: VariablePickerProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [variables, setVariables] = useState<VariableItem[]>([]);

  useEffect(() => {
    const allVars: VariableItem[] = [];

    // System variables
    const systemVars: VariableItem[] = [
      {
        path: 'workflow.id',
        label: 'Workflow ID',
        type: 'string',
        category: 'system',
        description: 'Current workflow ID',
        icon: <Hash className="h-4 w-4" />
      },
      {
        path: 'workflow.name',
        label: 'Workflow Name',
        type: 'string',
        category: 'system',
        description: 'Current workflow name',
        icon: <Type className="h-4 w-4" />
      },
      {
        path: 'workflow.execution_id',
        label: 'Execution ID',
        type: 'string',
        category: 'system',
        description: 'Current execution ID',
        icon: <Hash className="h-4 w-4" />
      },
      {
        path: 'workflow.triggered_at',
        label: 'Triggered At',
        type: 'datetime',
        category: 'system',
        description: 'Workflow trigger time',
        icon: <Clock className="h-4 w-4" />
      },
      {
        path: 'user.id',
        label: 'User ID',
        type: 'string',
        category: 'system',
        description: 'Current user ID',
        icon: <User className="h-4 w-4" />
      },
      {
        path: 'user.email',
        label: 'User Email',
        type: 'string',
        category: 'system',
        description: 'Current user email',
        icon: <User className="h-4 w-4" />
      },
      {
        path: 'user.name',
        label: 'User Name',
        type: 'string',
        category: 'system',
        description: 'Current user name',
        icon: <User className="h-4 w-4" />
      },
      {
        path: 'now',
        label: 'Current Time',
        type: 'datetime',
        category: 'system',
        description: 'Current timestamp',
        icon: <Clock className="h-4 w-4" />
      },
      {
        path: 'today',
        label: 'Today\'s Date',
        type: 'date',
        category: 'system',
        description: 'Current date',
        icon: <Calendar className="h-4 w-4" />
      }
    ];

    // Record context variables
    const recordVars: VariableItem[] = [
      {
        path: 'record',
        label: 'Full Record',
        type: 'object',
        category: 'record',
        description: 'Complete record object',
        icon: <Database className="h-4 w-4" />
      },
      {
        path: 'record.id',
        label: 'Record ID',
        type: 'string',
        category: 'record',
        description: 'Current record ID',
        icon: <Hash className="h-4 w-4" />
      },
      {
        path: 'record.created_at',
        label: 'Created At',
        type: 'datetime',
        category: 'record',
        description: 'Record creation time',
        icon: <Calendar className="h-4 w-4" />
      },
      {
        path: 'record.updated_at',
        label: 'Updated At',
        type: 'datetime',
        category: 'record',
        description: 'Last update time',
        icon: <Calendar className="h-4 w-4" />
      },
      {
        path: 'record.status',
        label: 'Status',
        type: 'string',
        category: 'record',
        description: 'Record status',
        icon: <ToggleLeft className="h-4 w-4" />
      },
      {
        path: 'record.pipeline_id',
        label: 'Pipeline ID',
        type: 'string',
        category: 'record',
        description: 'Pipeline ID',
        icon: <Database className="h-4 w-4" />
      }
    ];

    // Relation field traversal examples
    const relationVars: VariableItem[] = [
      {
        path: 'record.company.name',
        label: 'Company Name',
        type: 'string',
        category: 'relations',
        description: 'Single-hop: Traverse to related company name',
        icon: <Link className="h-4 w-4" />
      },
      {
        path: 'record.company.industry',
        label: 'Company Industry',
        type: 'string',
        category: 'relations',
        description: 'Single-hop: Company industry field',
        icon: <Link className="h-4 w-4" />
      },
      {
        path: 'record.company.email',
        label: 'Company Email',
        type: 'string',
        category: 'relations',
        description: 'Single-hop: Company email address',
        icon: <Link className="h-4 w-4" />
      },
      {
        path: 'record.deal.company.name',
        label: 'Deal → Company Name',
        type: 'string',
        category: 'relations',
        description: 'Multi-hop: Traverse through deal to company name',
        icon: <Link className="h-4 w-4" />
      },
      {
        path: 'record.deal.company.industry',
        label: 'Deal → Company → Industry',
        type: 'string',
        category: 'relations',
        description: 'Multi-hop: Traverse through multiple relations',
        icon: <Link className="h-4 w-4" />
      },
      {
        path: 'record.contacts[0].email',
        label: 'First Contact Email',
        type: 'string',
        category: 'relations',
        description: 'Array relation: Access first contact\'s email',
        icon: <Link className="h-4 w-4" />
      },
      {
        path: 'record.contacts[0].name',
        label: 'First Contact Name',
        type: 'string',
        category: 'relations',
        description: 'Array relation: Access first contact\'s name',
        icon: <Link className="h-4 w-4" />
      },
      {
        path: 'record.manager.email',
        label: 'Manager Email',
        type: 'string',
        category: 'relations',
        description: 'Single-hop: Related manager email address',
        icon: <Link className="h-4 w-4" />
      }
    ];

    // Node output variables
    availableVariables.forEach(node => {
      node.outputs.forEach(output => {
        const type = inferType(output);
        const icon = getTypeIcon(type);

        allVars.push({
          path: `${node.nodeId}.${output}`,
          label: `${node.label} - ${formatOutputName(output)}`,
          type,
          category: 'nodes',
          description: `Output from ${node.label}`,
          icon
        });
      });
    });

    // Environment variables
    const envVars: VariableItem[] = [
      {
        path: 'env.API_URL',
        label: 'API URL',
        type: 'string',
        category: 'environment',
        description: 'API base URL',
        icon: <Link className="h-4 w-4" />
      },
      {
        path: 'env.API_KEY',
        label: 'API Key',
        type: 'string',
        category: 'environment',
        description: 'API authentication key',
        icon: <Settings className="h-4 w-4" />
      },
      {
        path: 'env.TENANT_ID',
        label: 'Tenant ID',
        type: 'string',
        category: 'environment',
        description: 'Current tenant ID',
        icon: <Database className="h-4 w-4" />
      }
    ];

    // Combine all variables
    let finalVars = [...systemVars, ...recordVars, ...relationVars, ...allVars, ...envVars];

    // Filter for arrays only if requested
    if (showArraysOnly) {
      finalVars = finalVars.filter(v => v.type === 'array');
    }

    setVariables(finalVars);
  }, [availableVariables, showArraysOnly]);

  const inferType = (output: string): string => {
    if (output.includes('[]') || output.includes('array') || output.includes('list')) {
      return 'array';
    }
    if (output.includes('date') || output.includes('time')) {
      return 'datetime';
    }
    if (output.includes('number') || output.includes('count') || output.includes('amount')) {
      return 'number';
    }
    if (output.includes('bool') || output.includes('is_') || output.includes('has_')) {
      return 'boolean';
    }
    if (output.includes('object') || output.includes('data')) {
      return 'object';
    }
    return 'string';
  };

  const getTypeIcon = (type: string): React.ReactNode => {
    switch (type) {
      case 'array':
        return <List className="h-4 w-4" />;
      case 'object':
        return <Code className="h-4 w-4" />;
      case 'number':
        return <Hash className="h-4 w-4" />;
      case 'boolean':
        return <ToggleLeft className="h-4 w-4" />;
      case 'datetime':
      case 'date':
        return <Calendar className="h-4 w-4" />;
      default:
        return <Type className="h-4 w-4" />;
    }
  };

  const formatOutputName = (output: string): string => {
    return output
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  const getTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      string: 'text-green-600',
      number: 'text-blue-600',
      boolean: 'text-purple-600',
      array: 'text-orange-600',
      object: 'text-pink-600',
      datetime: 'text-indigo-600',
      date: 'text-indigo-600'
    };
    return colors[type] || 'text-gray-600';
  };

  const getCategoryIcon = (category: string): React.ReactNode => {
    switch (category) {
      case 'system':
        return <Settings className="h-4 w-4" />;
      case 'record':
        return <Database className="h-4 w-4" />;
      case 'relations':
        return <Link className="h-4 w-4" />;
      case 'nodes':
        return <Variable className="h-4 w-4" />;
      case 'environment':
        return <Settings className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const filteredVariables = variables.filter(v => {
    const matchesSearch = searchTerm === '' ||
      v.path.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.description?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory = selectedCategory === 'all' || v.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  const categories = [
    { id: 'all', label: 'All Variables', count: variables.length },
    { id: 'system', label: 'System', count: variables.filter(v => v.category === 'system').length },
    { id: 'record', label: 'Record', count: variables.filter(v => v.category === 'record').length },
    { id: 'relations', label: 'Relations', count: variables.filter(v => v.category === 'relations').length },
    { id: 'nodes', label: 'Node Outputs', count: variables.filter(v => v.category === 'nodes').length },
    { id: 'environment', label: 'Environment', count: variables.filter(v => v.category === 'environment').length }
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-[600px] h-[500px] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h3 className="font-semibold">Insert Variable</h3>
            {currentField && (
              <p className="text-sm text-muted-foreground">
                For: {currentField}
              </p>
            )}
          </div>
          <Button size="sm" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Search */}
        <div className="p-4 border-b">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search variables..."
              className="pl-9"
              autoFocus
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Categories */}
          <div className="w-48 border-r p-4">
            <div className="space-y-1">
              {categories.map(category => (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selectedCategory === category.id
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-muted'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getCategoryIcon(category.id)}
                      <span>{category.label}</span>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {category.count}
                    </Badge>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Variables List */}
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-2">
              {filteredVariables.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Variable className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No variables found</p>
                  {searchTerm && (
                    <p className="text-sm mt-1">Try adjusting your search</p>
                  )}
                </div>
              ) : (
                filteredVariables.map(variable => (
                  <Card
                    key={variable.path}
                    className="p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => {
                      onSelect(variable.path);
                      onClose();
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 ${getTypeColor(variable.type)}`}>
                        {variable.icon}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{variable.label}</span>
                          <Badge variant="outline" className="text-xs">
                            {variable.type}
                          </Badge>
                        </div>
                        <code className="text-xs text-muted-foreground font-mono">
                          {`{{${variable.path}}}`}
                        </code>
                        {variable.description && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {variable.description}
                          </p>
                        )}
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </Card>
                ))
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-muted/50">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {filteredVariables.length} variable{filteredVariables.length !== 1 ? 's' : ''} available
            </p>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={onClose}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}