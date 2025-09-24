'use client';

import { useState, useEffect } from 'react';
import { workflowsApi } from '@/lib/api';
import { WorkflowNodeType } from '../types';

interface UseWorkflowTestDataProps {
  nodeType: WorkflowNodeType | string;
  config: any;
  enabled?: boolean;
}

interface UseWorkflowTestDataReturn {
  testData: any[];
  testDataType: string;
  selectedTestData: any;
  setSelectedTestData: (data: any) => void;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Hook to load test data for workflow nodes based on their type and configuration.
 * Handles special cases for different trigger types (communication, date_reached, etc.)
 */
export function useWorkflowTestData({
  nodeType,
  config,
  enabled = true
}: UseWorkflowTestDataProps): UseWorkflowTestDataReturn {
  const [testData, setTestData] = useState<any[]>([]);
  const [testDataType, setTestDataType] = useState<string>('');
  const [selectedTestData, setSelectedTestData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset all test data when node type changes
  useEffect(() => {
    console.log('Node type changed to:', nodeType, '- resetting test data');
    setTestData([]);
    setTestDataType('');
    setSelectedTestData(null);
    setError(null);
  }, [nodeType]);

  const loadTestData = async () => {
    if (!nodeType || !enabled) return;

    // Clear selected test data at the start to prevent stale data
    setSelectedTestData(null);

    const nodeLower = nodeType.toLowerCase();
    
    // Check if this is a trigger node
    const isTrigger = nodeLower.includes('trigger');
    if (!isTrigger) {
      // Non-trigger nodes don't have test data
      setTestData([]);
      setTestDataType('');
      return;
    }

    // Check if this is a communication trigger (doesn't need pipeline)
    const isCommunicationTrigger = nodeLower.includes('email') ||
                                   nodeLower.includes('linkedin') ||
                                   nodeLower.includes('whatsapp') ||
                                   nodeLower.includes('message');

    // Check if this is a date reached trigger in static mode
    const isDateReachedTrigger = nodeLower.includes('date_reached');
    const isUsingDynamicDateField = isDateReachedTrigger && config?.date_field;

    // Manual and webhook triggers don't need pipelines either
    const isManualTrigger = nodeLower.includes('manual');
    const isWebhookTrigger = nodeLower.includes('webhook');

    // Determine if we need a pipeline
    let pipelineId: string | undefined = undefined;
    const needsPipeline = !isCommunicationTrigger && 
                         !isManualTrigger && 
                         !isWebhookTrigger &&
                         !(isDateReachedTrigger && !isUsingDynamicDateField);

    if (needsPipeline) {
      // Get pipeline from config
      pipelineId = config?.pipeline_id || config?.pipeline_ids?.[0];
      
      if (!pipelineId) {
        console.log(`No pipeline configured for ${nodeType} - test data not available`);
        setTestData([]);
        setTestDataType('');
        return;
      }
    }

    setLoading(true);
    setError(null);

    try {
      console.log('Loading test data for:', {
        nodeType,
        pipelineId,
        config,
        isCommunicationTrigger,
        isDateReachedTrigger,
        isUsingDynamicDateField
      });

      const response = await workflowsApi.getTestData({
        node_type: nodeType,
        pipeline_id: pipelineId,
        node_config: config ? JSON.stringify(config) : undefined
      });

      console.log('Test data loaded:', response.data);
      
      const data = response.data.data || [];
      const dataType = response.data.data_type || '';
      
      setTestData(data);
      setTestDataType(dataType);

      // Auto-select first item if available
      if (data.length > 0) {
        setSelectedTestData(data[0]);
      }
    } catch (err: any) {
      console.error('Failed to load test data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load test data');
      setTestData([]);
      setTestDataType('');
      setSelectedTestData(null);
    } finally {
      setLoading(false);
    }
  };

  // Load test data when dependencies change
  useEffect(() => {
    loadTestData();
  }, [
    nodeType,
    enabled,
    // Config dependencies that affect test data
    config?.pipeline_id,
    config?.pipeline_ids,
    config?.form_selection,  // For form triggers
    config?.mode,            // For form triggers
    config?.stage,           // For stage change triggers
    config?.monitor_users,   // For communication triggers
    config?.date_field,      // For date reached triggers
  ]);

  return {
    testData,
    testDataType,
    selectedTestData,
    setSelectedTestData,
    loading,
    error,
    refetch: loadTestData
  };
}