'use client';

import { useEffect, useState } from 'react';
import { workflowSchemaService } from '@/services/workflowSchemaService';
import { WorkflowNodeType } from './types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function DebugTest() {
  const [schema, setSchema] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const testRecordTrigger = async () => {
    setLoading(true);
    try {
      // Clear cache first
      workflowSchemaService.clearCache();

      // Get the transformed config for record created trigger
      const nodeConfig = await workflowSchemaService.getNodeConfig(WorkflowNodeType.TRIGGER_RECORD_CREATED);
      setConfig(nodeConfig);

      console.log('Transformed Config:', nodeConfig);

      // Log all fields and their types
      if (nodeConfig?.sections) {
        nodeConfig.sections.forEach((section: any) => {
          console.log(`Section: ${section.label}`);
          section.fields?.forEach((field: any) => {
            console.log(`  Field: ${field.key}`);
            console.log(`    Type: ${field.type}`);
            console.log(`    Multiple: ${field.multiple}`);
            console.log(`    Options Source: ${field.optionsSource}`);
            console.log(`    Widget: ${field.widget}`);
            console.log(`    UI Hints:`, field.uiHints);
          });
        });
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="max-w-2xl mx-auto mt-8">
      <CardHeader>
        <CardTitle>Debug: Field Type Transformation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button onClick={testRecordTrigger} disabled={loading}>
          {loading ? 'Loading...' : 'Test Record Created Trigger'}
        </Button>

        {config && (
          <div className="space-y-2">
            <h3 className="font-semibold">Transformed Config:</h3>
            {config.sections?.map((section: any, idx: number) => (
              <div key={idx} className="border rounded p-2">
                <h4 className="font-medium">{section.label}</h4>
                {section.fields?.map((field: any, fidx: number) => (
                  <div key={fidx} className="pl-4 text-sm">
                    <strong>{field.label}:</strong>
                    <span className="ml-2">type={field.type}, multiple={field.multiple ? 'true' : 'false'}</span>
                    {field.optionsSource && <span className="ml-2">, source={field.optionsSource}</span>}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        <div className="mt-4">
          <p className="text-sm text-muted-foreground">Check console for detailed output</p>
        </div>
      </CardContent>
    </Card>
  );
}