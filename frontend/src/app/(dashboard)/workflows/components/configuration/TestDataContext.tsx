/**
 * TestDataContext
 * Manages test data for workflow nodes to simulate data flow
 * Now supports real pipeline records for triggers
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { WorkflowNodeType } from '../../types';
import { workflowsApi, pipelinesApi } from '@/lib/api';

interface NodeTestData {
  input: Record<string, any>;
  output: Record<string, any>;
  timestamp: number;
  testRecords?: any[];
  selectedRecord?: any;
}

interface TestDataContextType {
  testData: Record<string, NodeTestData>;
  setNodeTestData: (nodeId: string, data: Partial<NodeTestData>) => void;
  getNodeTestData: (nodeId: string) => NodeTestData | undefined;
  clearNodeTestData: (nodeId: string) => void;
  clearAllTestData: () => void;
  generateSampleOutput: (nodeType: WorkflowNodeType, config: any, input: any) => any;
  loadTestDataForNode: (nodeType: WorkflowNodeType, config: any) => Promise<any[]>;
  loadPipelineRecords: (pipelineId: string) => Promise<any[]>;
}

const TestDataContext = createContext<TestDataContextType | undefined>(undefined);

export const useTestData = () => {
  const context = useContext(TestDataContext);
  if (!context) {
    throw new Error('useTestData must be used within a TestDataProvider');
  }
  return context;
};

export function TestDataProvider({ children }: { children: React.ReactNode }) {
  const [testData, setTestData] = useState<Record<string, NodeTestData>>({});

  const setNodeTestData = useCallback((nodeId: string, data: Partial<NodeTestData>) => {
    setTestData(prev => ({
      ...prev,
      [nodeId]: {
        ...prev[nodeId],
        ...data,
        timestamp: Date.now()
      }
    }));
  }, []);

  const getNodeTestData = useCallback((nodeId: string) => {
    return testData[nodeId];
  }, [testData]);

  const clearNodeTestData = useCallback((nodeId: string) => {
    setTestData(prev => {
      const next = { ...prev };
      delete next[nodeId];
      return next;
    });
  }, []);

  const clearAllTestData = useCallback(() => {
    setTestData({});
  }, []);

  const loadTestDataForNode = useCallback(async (nodeType: WorkflowNodeType, config: any): Promise<any[]> => {
    try {
      // Determine if we need a pipeline ID
      let pipelineId = null;

      // Check if this is a communication trigger (they don't need pipeline)
      const isCommunicationTrigger = nodeType.toLowerCase().includes('email') ||
                                     nodeType.toLowerCase().includes('linkedin') ||
                                     nodeType.toLowerCase().includes('whatsapp') ||
                                     nodeType.toLowerCase().includes('message');

      if (!isCommunicationTrigger) {
        // Get pipeline ID from config
        if (config?.pipeline_id) {
          pipelineId = String(config.pipeline_id);
        } else if (config?.pipeline_ids && config.pipeline_ids.length > 0) {
          pipelineId = String(config.pipeline_ids[0]);
        }
      }

      const response = await workflowsApi.getTestData({
        node_type: nodeType,
        pipeline_id: pipelineId || undefined,
        node_config: config ? JSON.stringify(config) : undefined
      });

      return response.data.data || [];
    } catch (error) {
      console.error('Failed to load test data:', error);
      return [];
    }
  }, []);

  const loadPipelineRecords = useCallback(async (pipelineId: string): Promise<any[]> => {
    try {
      const response = await pipelinesApi.getRecords(pipelineId, {
        page_size: 20,
        ordering: '-created_at'
      });
      return response.data.results || [];
    } catch (error) {
      console.error('Failed to load pipeline records:', error);
      return [];
    }
  }, []);

  const generateSampleOutput = useCallback((nodeType: WorkflowNodeType, config: any, input: any) => {
    // Generate sample output based on node type
    switch (nodeType) {
      case WorkflowNodeType.TRIGGER_MANUAL:
        return {
          triggered_by: 'manual',
          timestamp: new Date().toISOString(),
          user: 'test_user',
          ...input
        };

      case WorkflowNodeType.RECORD_FIND:
        return {
          success: true,
          record: {
            id: 'record_123',
            pipeline_id: config.pipeline_id,
            data: {
              name: 'Sample Record',
              email: 'sample@example.com',
              ...input
            }
          },
          found: true
        };

      case WorkflowNodeType.RECORD_CREATE:
        return {
          success: true,
          record: {
            id: 'new_record_456',
            pipeline_id: config.pipeline_id,
            created_at: new Date().toISOString(),
            data: config.field_mappings || {}
          }
        };

      case WorkflowNodeType.UNIPILE_SEND_EMAIL:
        return {
          success: true,
          message_id: 'msg_789',
          status: 'sent',
          to: config.to_email,
          subject: config.subject,
          sent_at: new Date().toISOString()
        };

      case WorkflowNodeType.AI_PROMPT:
        return {
          success: true,
          result: 'AI generated response based on prompt',
          prompt: config.prompt,
          model: config.model || 'gpt-4',
          tokens: 150
        };

      case WorkflowNodeType.CONDITION:
        return {
          success: true,
          condition_met: true,
          evaluated_conditions: config.conditions || [],
          branch: 'true'
        };

      case WorkflowNodeType.FOR_EACH:
        return {
          success: true,
          items_processed: 5,
          results: [],
          iteration_count: 5
        };

      case WorkflowNodeType.WAIT_DELAY:
        return {
          success: true,
          waited_for: config.delay_minutes || 0,
          continued_at: new Date().toISOString()
        };

      case WorkflowNodeType.HTTP_REQUEST:
        return {
          success: true,
          status_code: 200,
          response: {
            data: 'Response data'
          },
          headers: {},
          url: config.url
        };

      case WorkflowNodeType.RECORD_UPDATE:
        return {
          success: true,
          updated: true,
          record_id: input.record_id || 'record_123',
          updated_fields: Object.keys(config.field_mappings || {}),
          updated_at: new Date().toISOString()
        };

      case WorkflowNodeType.MERGE_DATA:
        return {
          success: true,
          merged_data: {
            ...input,
            ...(config.additional_data || {})
          }
        };

      default:
        return {
          success: true,
          node_type: nodeType,
          config: config,
          input: input,
          output: 'Sample output for ' + nodeType
        };
    }
  }, []);

  const value = {
    testData,
    setNodeTestData,
    getNodeTestData,
    clearNodeTestData,
    clearAllTestData,
    generateSampleOutput,
    loadTestDataForNode,
    loadPipelineRecords
  };

  return (
    <TestDataContext.Provider value={value}>
      {children}
    </TestDataContext.Provider>
  );
}