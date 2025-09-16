import { WorkflowNodeType } from '../../../types';
import { UnifiedNodeConfig, NodeConfigRegistry } from './types';

// Trigger nodes
import { TriggerRecordCreatedConfig } from './configs/TriggerRecordCreatedConfig';
import { TriggerRecordUpdatedConfig } from './configs/TriggerRecordUpdatedConfig';
import { TriggerRecordDeletedConfig } from './configs/TriggerRecordDeletedConfig';
import { TriggerWebhookConfig } from './configs/TriggerWebhookConfig';
import { TriggerManualConfig } from './configs/TriggerManualConfig';
import { TriggerScheduleConfig } from './configs/TriggerScheduleConfig';
// Deprecated - functionality moved to TriggerRecordUpdatedConfig
// import { TriggerFieldChangedConfig } from './configs/TriggerFieldChangedConfig';
// import { TriggerStatusChangedConfig } from './configs/TriggerStatusChangedConfig';
import { TriggerFormSubmittedConfig } from './configs/TriggerFormSubmittedConfig';
import { TriggerDateReachedConfig } from './configs/TriggerDateReachedConfig';
import { TriggerAPIEndpointConfig } from './configs/TriggerAPIEndpointConfig';
import { TriggerEmailReceivedConfig } from './configs/TriggerEmailReceivedConfig';
import { TriggerLinkedInMessageConfig } from './configs/TriggerLinkedInMessageConfig';
import { TriggerWhatsAppMessageConfig } from './configs/TriggerWhatsAppMessageConfig';

// Data operation nodes
import { RecordCreateNodeConfig } from './configs/RecordCreateNodeConfig';
import { RecordUpdateNodeConfig } from './configs/RecordUpdateNodeConfig';
import { RecordFindNodeConfig } from './configs/RecordFindNodeConfig';
import { RecordDeleteNodeConfig } from './configs/RecordDeleteNodeConfig';
import { MergeDataNodeConfig } from './configs/MergeDataNodeConfig';
import { FindOrCreateRecordNodeConfig } from './configs/FindOrCreateRecordNodeConfig';
import { CreateFollowUpTaskNodeConfig } from './configs/CreateFollowUpTaskNodeConfig';

// Control flow nodes
import { ConditionNodeConfig } from './configs/ConditionNodeConfig';
import { ForEachNodeConfig } from './configs/ForEachNodeConfig';
import { WorkflowLoopControllerConfig } from './configs/WorkflowLoopControllerConfig';
import { WaitDelayNodeConfig } from './configs/WaitDelayNodeConfig';
import { WaitForResponseNodeConfig } from './configs/WaitForResponseNodeConfig';
import { WaitForRecordEventNodeConfig } from './configs/WaitForRecordEventNodeConfig';
import { WaitForConditionNodeConfig } from './configs/WaitForConditionNodeConfig';
import { ApprovalNodeConfig } from './configs/ApprovalNodeConfig';
import { SubWorkflowNodeConfig } from './configs/SubWorkflowNodeConfig';

// Communication nodes
import { EmailNodeConfig } from './configs/EmailNodeConfig';
import { WhatsAppNodeConfig } from './configs/WhatsAppNodeConfig';
import { LinkedInNodeConfig } from './configs/LinkedInNodeConfig';
import { SMSNodeConfig } from './configs/SMSNodeConfig';

// AI nodes
import { AIPromptNodeConfig } from './configs/AIPromptNodeConfig';
import { AIAnalysisNodeConfig } from './configs/AIAnalysisNodeConfig';
import { AIConversationLoopNodeConfig } from './configs/AIConversationLoopNodeConfig';
import { AIMessageGeneratorConfig } from './configs/AIMessageGeneratorConfig';
import { AIResponseEvaluatorConfig } from './configs/AIResponseEvaluatorConfig';

// Utility nodes
import { HTTPRequestNodeConfig } from './configs/HTTPRequestNodeConfig';
import { WebhookOutNodeConfig } from './configs/WebhookOutNodeConfig';
import { TaskNotifyNodeConfig } from './configs/TaskNotifyNodeConfig';
import { ConversationStateConfig } from './configs/ConversationStateConfig';
import { GenerateFormLinkConfig } from './configs/GenerateFormLinkConfig';

/**
 * Central registry of all node configurations.
 * Each node type has exactly ONE configuration here.
 */
export const nodeConfigRegistry: Partial<NodeConfigRegistry> = {
  // Trigger nodes
  [WorkflowNodeType.TRIGGER_RECORD_CREATED]: TriggerRecordCreatedConfig,
  [WorkflowNodeType.TRIGGER_RECORD_UPDATED]: TriggerRecordUpdatedConfig,
  [WorkflowNodeType.TRIGGER_RECORD_DELETED]: TriggerRecordDeletedConfig,
  [WorkflowNodeType.TRIGGER_WEBHOOK]: TriggerWebhookConfig,
  [WorkflowNodeType.TRIGGER_MANUAL]: TriggerManualConfig,
  [WorkflowNodeType.TRIGGER_SCHEDULE]: TriggerScheduleConfig,
  // Deprecated triggers - use TRIGGER_RECORD_UPDATED with appropriate config
  // [WorkflowNodeType.TRIGGER_FIELD_CHANGED]: TriggerFieldChangedConfig,
  // [WorkflowNodeType.TRIGGER_STATUS_CHANGED]: TriggerStatusChangedConfig,
  [WorkflowNodeType.TRIGGER_FORM_SUBMITTED]: TriggerFormSubmittedConfig,
  [WorkflowNodeType.TRIGGER_DATE_REACHED]: TriggerDateReachedConfig,
  [WorkflowNodeType.TRIGGER_API_ENDPOINT]: TriggerAPIEndpointConfig,
  [WorkflowNodeType.TRIGGER_EMAIL_RECEIVED]: TriggerEmailReceivedConfig,
  [WorkflowNodeType.TRIGGER_LINKEDIN_MESSAGE]: TriggerLinkedInMessageConfig,
  [WorkflowNodeType.TRIGGER_WHATSAPP_MESSAGE]: TriggerWhatsAppMessageConfig,

  // Data operation nodes
  [WorkflowNodeType.RECORD_CREATE]: RecordCreateNodeConfig,
  [WorkflowNodeType.RECORD_UPDATE]: RecordUpdateNodeConfig,
  [WorkflowNodeType.RECORD_FIND]: RecordFindNodeConfig,
  [WorkflowNodeType.RECORD_DELETE]: RecordDeleteNodeConfig,
  [WorkflowNodeType.MERGE_DATA]: MergeDataNodeConfig,
  [WorkflowNodeType.RESOLVE_CONTACT]: FindOrCreateRecordNodeConfig,
  [WorkflowNodeType.CREATE_FOLLOW_UP_TASK]: CreateFollowUpTaskNodeConfig,

  // Control flow nodes
  [WorkflowNodeType.CONDITION]: ConditionNodeConfig,
  [WorkflowNodeType.FOR_EACH]: ForEachNodeConfig,
  [WorkflowNodeType.WORKFLOW_LOOP_CONTROLLER]: WorkflowLoopControllerConfig,
  [WorkflowNodeType.WAIT_DELAY]: WaitDelayNodeConfig,
  [WorkflowNodeType.WAIT_FOR_RESPONSE]: WaitForResponseNodeConfig,
  [WorkflowNodeType.WAIT_FOR_RECORD_EVENT]: WaitForRecordEventNodeConfig,
  [WorkflowNodeType.WAIT_FOR_CONDITION]: WaitForConditionNodeConfig,
  [WorkflowNodeType.APPROVAL]: ApprovalNodeConfig,
  [WorkflowNodeType.SUB_WORKFLOW]: SubWorkflowNodeConfig,

  // Communication nodes
  [WorkflowNodeType.UNIPILE_SEND_EMAIL]: EmailNodeConfig,
  [WorkflowNodeType.UNIPILE_SEND_WHATSAPP]: WhatsAppNodeConfig,
  [WorkflowNodeType.UNIPILE_SEND_LINKEDIN]: LinkedInNodeConfig,
  [WorkflowNodeType.UNIPILE_SEND_SMS]: SMSNodeConfig,

  // AI nodes
  [WorkflowNodeType.AI_PROMPT]: AIPromptNodeConfig,
  [WorkflowNodeType.AI_ANALYSIS]: AIAnalysisNodeConfig,
  [WorkflowNodeType.AI_CONVERSATION_LOOP]: AIConversationLoopNodeConfig,
  [WorkflowNodeType.AI_MESSAGE_GENERATOR]: AIMessageGeneratorConfig,
  [WorkflowNodeType.AI_RESPONSE_EVALUATOR]: AIResponseEvaluatorConfig,

  // Utility nodes
  [WorkflowNodeType.HTTP_REQUEST]: HTTPRequestNodeConfig,
  [WorkflowNodeType.WEBHOOK_OUT]: WebhookOutNodeConfig,
  [WorkflowNodeType.TASK_NOTIFY]: TaskNotifyNodeConfig,
  [WorkflowNodeType.CONVERSATION_STATE]: ConversationStateConfig,
  [WorkflowNodeType.GENERATE_FORM_LINK]: GenerateFormLinkConfig,
};

/**
 * Get the configuration for a specific node type
 */
export function getNodeConfig(nodeType: WorkflowNodeType): UnifiedNodeConfig | undefined {
  return nodeConfigRegistry[nodeType];
}

/**
 * Check if a node type has a configuration
 */
export function hasNodeConfig(nodeType: WorkflowNodeType): boolean {
  return nodeType in nodeConfigRegistry;
}

/**
 * Get all available node configurations
 */
export function getAllNodeConfigs(): UnifiedNodeConfig[] {
  return Object.values(nodeConfigRegistry).filter(Boolean) as UnifiedNodeConfig[];
}

/**
 * Get node configurations by category
 */
export function getNodeConfigsByCategory(category: UnifiedNodeConfig['category']): UnifiedNodeConfig[] {
  return getAllNodeConfigs().filter(config => config.category === category);
}