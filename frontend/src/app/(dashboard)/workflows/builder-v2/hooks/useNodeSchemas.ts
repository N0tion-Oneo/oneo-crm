/**
 * useNodeSchemas Hook
 * Fetches and manages workflow node schemas from backend
 */

import { useState, useEffect } from 'react';
import { workflowSchemaService } from '@/services/workflowSchemaService';
import { WorkflowNodeType } from '../../types';
import { NodeDefinition, NodeCategory } from '../types';

// Define available node types with categories
// This will be replaced with backend data eventually
const NODE_DEFINITIONS: NodeDefinition[] = [
  // Triggers
  { type: WorkflowNodeType.TRIGGER_MANUAL, label: 'Manual Trigger', category: 'Triggers', icon: '▶️' },
  { type: WorkflowNodeType.TRIGGER_SCHEDULED, label: 'Scheduled', category: 'Triggers', icon: '⏰' },
  { type: WorkflowNodeType.TRIGGER_WEBHOOK, label: 'Webhook', category: 'Triggers', icon: '🔗' },
  { type: WorkflowNodeType.TRIGGER_RECORD_CREATED, label: 'Record Created', category: 'Triggers', icon: '➕' },
  { type: WorkflowNodeType.TRIGGER_RECORD_UPDATED, label: 'Record Updated', category: 'Triggers', icon: '✏️' },
  { type: WorkflowNodeType.TRIGGER_RECORD_DELETED, label: 'Record Deleted', category: 'Triggers', icon: '🗑️' },
  { type: WorkflowNodeType.TRIGGER_FORM_SUBMITTED, label: 'Form Submitted', category: 'Triggers', icon: '📝' },
  { type: WorkflowNodeType.TRIGGER_EMAIL_RECEIVED, label: 'Email Received', category: 'Triggers', icon: '📨' },
  { type: WorkflowNodeType.TRIGGER_LINKEDIN_MESSAGE, label: 'LinkedIn Message', category: 'Triggers', icon: '💼' },
  { type: WorkflowNodeType.TRIGGER_WHATSAPP_MESSAGE, label: 'WhatsApp Message', category: 'Triggers', icon: '📱' },
  { type: WorkflowNodeType.TRIGGER_DATE_REACHED, label: 'Date Reached', category: 'Triggers', icon: '📅' },
  { type: WorkflowNodeType.TRIGGER_CONDITION_MET, label: 'Condition Met', category: 'Triggers', icon: '✅' },
  { type: WorkflowNodeType.TRIGGER_PIPELINE_STAGE_CHANGED, label: 'Stage Changed', category: 'Triggers', icon: '📊' },
  { type: WorkflowNodeType.TRIGGER_WORKFLOW_COMPLETED, label: 'Workflow Completed', category: 'Triggers', icon: '🏁' },

  // Data Operations
  { type: WorkflowNodeType.RECORD_CREATE, label: 'Create Record', category: 'Data', icon: '💾' },
  { type: WorkflowNodeType.RECORD_UPDATE, label: 'Update Record', category: 'Data', icon: '🔄' },
  { type: WorkflowNodeType.RECORD_FIND, label: 'Find Record', category: 'Data', icon: '🔍' },
  { type: WorkflowNodeType.RECORD_DELETE, label: 'Delete Record', category: 'Data', icon: '🗑️' },
  { type: WorkflowNodeType.MERGE_DATA, label: 'Merge Data', category: 'Data', icon: '🔗' },
  { type: WorkflowNodeType.RESOLVE_CONTACT, label: 'Resolve Contact', category: 'Data', icon: '👤' },
  { type: WorkflowNodeType.CREATE_FOLLOW_UP_TASK, label: 'Create Task', category: 'Data', icon: '📌' },
  { type: WorkflowNodeType.UPDATE_CONTACT_STATUS, label: 'Update Status', category: 'Data', icon: '🏷️' },

  // AI Operations
  { type: WorkflowNodeType.AI_PROMPT, label: 'AI Prompt', category: 'AI', icon: '🤖' },
  { type: WorkflowNodeType.AI_ANALYSIS, label: 'AI Analysis', category: 'AI', icon: '🧠' },
  { type: WorkflowNodeType.AI_MESSAGE_GENERATOR, label: 'Generate Message', category: 'AI', icon: '✨' },
  { type: WorkflowNodeType.AI_RESPONSE_EVALUATOR, label: 'Evaluate Response', category: 'AI', icon: '📊' },
  { type: WorkflowNodeType.AI_CONVERSATION_LOOP, label: 'AI Conversation', category: 'AI', icon: '💬' },

  // Communication
  { type: WorkflowNodeType.UNIPILE_SEND_EMAIL, label: 'Send Email', category: 'Communication', icon: '📧' },
  { type: WorkflowNodeType.UNIPILE_SEND_SMS, label: 'Send SMS', category: 'Communication', icon: '💬' },
  { type: WorkflowNodeType.UNIPILE_SEND_WHATSAPP, label: 'Send WhatsApp', category: 'Communication', icon: '📱' },
  { type: WorkflowNodeType.UNIPILE_SEND_LINKEDIN, label: 'Send LinkedIn', category: 'Communication', icon: '💼' },
  { type: WorkflowNodeType.UNIPILE_SYNC_MESSAGES, label: 'Sync Messages', category: 'Communication', icon: '🔄' },
  { type: WorkflowNodeType.LOG_COMMUNICATION, label: 'Log Communication', category: 'Communication', icon: '📝' },
  { type: WorkflowNodeType.ANALYZE_COMMUNICATION, label: 'Analyze Communication', category: 'Communication', icon: '📊' },
  { type: WorkflowNodeType.SCORE_ENGAGEMENT, label: 'Score Engagement', category: 'Communication', icon: '⭐' },

  // Control Flow
  { type: WorkflowNodeType.CONDITION, label: 'Condition', category: 'Control', icon: '🔀' },
  { type: WorkflowNodeType.FOR_EACH, label: 'For Each', category: 'Control', icon: '🔁' },
  { type: WorkflowNodeType.WORKFLOW_LOOP_CONTROLLER, label: 'Loop Controller', category: 'Control', icon: '♾️' },
  { type: WorkflowNodeType.WORKFLOW_LOOP_BREAKER, label: 'Break Loop', category: 'Control', icon: '⛔' },
  { type: WorkflowNodeType.WAIT_DELAY, label: 'Wait/Delay', category: 'Control', icon: '⏱️' },
  { type: WorkflowNodeType.WAIT_FOR_RESPONSE, label: 'Wait for Response', category: 'Control', icon: '⏳' },
  { type: WorkflowNodeType.WAIT_FOR_RECORD_EVENT, label: 'Wait for Event', category: 'Control', icon: '👁️' },
  { type: WorkflowNodeType.WAIT_FOR_CONDITION, label: 'Wait for Condition', category: 'Control', icon: '🎯' },
  { type: WorkflowNodeType.CONVERSATION_STATE, label: 'Conversation State', category: 'Control', icon: '💭' },

  // External/Utility
  { type: WorkflowNodeType.HTTP_REQUEST, label: 'HTTP Request', category: 'External', icon: '🌐' },
  { type: WorkflowNodeType.WEBHOOK_OUT, label: 'Webhook Out', category: 'External', icon: '📤' },
  { type: WorkflowNodeType.TASK_NOTIFY, label: 'Send Notification', category: 'External', icon: '🔔' },
  { type: WorkflowNodeType.SUB_WORKFLOW, label: 'Run Sub-Workflow', category: 'External', icon: '🔄' },

  // Workflow Control
  { type: WorkflowNodeType.APPROVAL, label: 'Approval', category: 'Control', icon: '✋' },
  { type: WorkflowNodeType.GENERATE_FORM_LINK, label: 'Generate Form Link', category: 'Data', icon: '🔗' },
];

export function useNodeSchemas() {
  const [nodeCategories, setNodeCategories] = useState<NodeCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadNodeSchemas();
  }, []);

  const loadNodeSchemas = async () => {
    setLoading(true);
    setError(null);

    try {
      // Group nodes by category
      const categoryMap = new Map<string, NodeDefinition[]>();

      for (const node of NODE_DEFINITIONS) {
        if (!categoryMap.has(node.category)) {
          categoryMap.set(node.category, []);
        }
        categoryMap.get(node.category)!.push(node);
      }

      // Convert to category array
      const categories: NodeCategory[] = Array.from(categoryMap.entries()).map(([id, nodes]) => ({
        id,
        label: id,
        nodes
      }));

      setNodeCategories(categories);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load node schemas');
    } finally {
      setLoading(false);
    }
  };

  // Get schema for a specific node type
  const getNodeSchema = async (nodeType: WorkflowNodeType) => {
    try {
      const config = await workflowSchemaService.getNodeConfig(nodeType);
      return config;
    } catch (err) {
      console.error(`Failed to get schema for ${nodeType}:`, err);
      return null;
    }
  };

  // Get node definition
  const getNodeDefinition = (nodeType: WorkflowNodeType): NodeDefinition | undefined => {
    return NODE_DEFINITIONS.find(n => n.type === nodeType);
  };

  return {
    nodeCategories,
    loading,
    error,
    getNodeSchema,
    getNodeDefinition,
    refresh: loadNodeSchemas
  };
}