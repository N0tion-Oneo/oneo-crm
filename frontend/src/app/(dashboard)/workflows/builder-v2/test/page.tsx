/**
 * Test page for Workflow Builder V2
 * Simple page to test the new clean workflow builder
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { WorkflowBuilder } from '../WorkflowBuilder';
import { WorkflowDefinition } from '../types';
import { ArrowLeft, Save, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

export default function WorkflowBuilderTestPage() {
  const router = useRouter();
  const [definition, setDefinition] = useState<WorkflowDefinition>({
    nodes: [],
    edges: [],
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    console.log('Saving workflow definition:', definition);

    // Simulate save
    await new Promise(resolve => setTimeout(resolve, 1000));

    toast.success('Workflow saved successfully');
    setSaving(false);
  };

  const handleReset = () => {
    setDefinition({ nodes: [], edges: [] });
    toast.info('Workflow reset');
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="flex items-center justify-between h-16 px-6">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/workflows')}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            <div className="h-6 w-px bg-border" />
            <h1 className="text-lg font-semibold">Workflow Builder V2 Test</h1>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Reset
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving}
              className="gap-2"
            >
              {saving ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Builder */}
      <div className="flex-1 overflow-hidden">
        <WorkflowBuilder
          initialDefinition={definition}
          onChange={setDefinition}
        />
      </div>

      {/* Debug Panel */}
      <div className="border-t bg-card p-4">
        <details className="cursor-pointer">
          <summary className="text-sm font-medium mb-2">Debug Info</summary>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">Workflow Stats</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Nodes:</span>
                    <span className="font-medium">{definition.nodes.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Edges:</span>
                    <span className="font-medium">{definition.edges.length}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">Definition JSON</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-32">
                  {JSON.stringify(definition, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </div>
        </details>
      </div>
    </div>
  );
}