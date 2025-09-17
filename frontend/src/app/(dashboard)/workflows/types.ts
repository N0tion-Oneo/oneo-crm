export interface Workflow {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'inactive' | 'draft';
  trigger_type: string;
  definition: WorkflowDefinition;
  execution_count: number;
  last_execution?: WorkflowExecution;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  settings?: {
    max_execution_time?: number;
    retry_on_failure?: boolean;
    notification_emails?: string[];
  };
}

export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  position: { x: number; y: number };
  data: any;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  label?: string;
  type?: 'default' | 'conditional';
}

export enum WorkflowNodeType {
  // Triggers - using lowercase to match backend Django model
  TRIGGER_MANUAL = 'trigger_manual',
  TRIGGER_SCHEDULED = 'trigger_scheduled',
  TRIGGER_WEBHOOK = 'trigger_webhook',
  TRIGGER_RECORD_CREATED = 'trigger_record_created',
  TRIGGER_RECORD_UPDATED = 'trigger_record_updated',
  TRIGGER_RECORD_DELETED = 'trigger_record_deleted',
  TRIGGER_FORM_SUBMITTED = 'trigger_form_submitted',
  TRIGGER_EMAIL_RECEIVED = 'trigger_email_received',
  TRIGGER_LINKEDIN_MESSAGE = 'trigger_linkedin_message',
  TRIGGER_WHATSAPP_MESSAGE = 'trigger_whatsapp_message',
  TRIGGER_DATE_REACHED = 'trigger_date_reached',
  TRIGGER_CONDITION_MET = 'trigger_condition_met',
  TRIGGER_PIPELINE_STAGE_CHANGED = 'trigger_pipeline_stage_changed',
  TRIGGER_WORKFLOW_COMPLETED = 'trigger_workflow_completed',

  // Data Operations - matching backend Django model
  RECORD_CREATE = 'record_create',
  RECORD_UPDATE = 'record_update',
  RECORD_FIND = 'record_find',
  RECORD_DELETE = 'record_delete',
  MERGE_DATA = 'merge_data',
  RESOLVE_CONTACT = 'resolve_contact',
  CREATE_FOLLOW_UP_TASK = 'create_follow_up_task',
  UPDATE_CONTACT_STATUS = 'update_contact_status',

  // Control Flow - matching backend Django model
  CONDITION = 'condition',
  FOR_EACH = 'for_each',
  WORKFLOW_LOOP_CONTROLLER = 'workflow_loop_controller',
  WORKFLOW_LOOP_BREAKER = 'workflow_loop_breaker',
  WAIT_DELAY = 'wait_delay',
  WAIT_FOR_RESPONSE = 'wait_for_response',
  WAIT_FOR_RECORD_EVENT = 'wait_for_record_event',
  WAIT_FOR_CONDITION = 'wait_for_condition',
  CONVERSATION_STATE = 'conversation_state',

  // Communication - matching backend Django model
  UNIPILE_SEND_EMAIL = 'unipile_send_email',
  UNIPILE_SEND_WHATSAPP = 'unipile_send_whatsapp',
  UNIPILE_SEND_LINKEDIN = 'unipile_send_linkedin',
  UNIPILE_SEND_SMS = 'unipile_send_sms',
  UNIPILE_SYNC_MESSAGES = 'unipile_sync_messages',
  LOG_COMMUNICATION = 'log_communication',
  ANALYZE_COMMUNICATION = 'analyze_communication',
  SCORE_ENGAGEMENT = 'score_engagement',

  // AI Operations - matching backend Django model
  AI_PROMPT = 'ai_prompt',
  AI_ANALYSIS = 'ai_analysis',
  AI_CONVERSATION_LOOP = 'ai_conversation_loop',
  AI_MESSAGE_GENERATOR = 'ai_message_generator',
  AI_RESPONSE_EVALUATOR = 'ai_response_evaluator',

  // Utility - matching backend Django model
  HTTP_REQUEST = 'http_request',
  WEBHOOK_OUT = 'webhook_out',
  TASK_NOTIFY = 'task_notify',
  GENERATE_FORM_LINK = 'generate_form_link',

  // Workflow Control - matching backend Django model
  APPROVAL = 'approval',
  SUB_WORKFLOW = 'sub_workflow',
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  error_message?: string;
  trigger_data?: any;
  execution_context?: any;
  logs?: WorkflowExecutionLog[];
}

export interface WorkflowExecutionLog {
  id: string;
  execution_id: string;
  node_id: string;
  node_type: string;
  node_name: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  input_data?: any;
  output_data?: any;
  error_details?: any;
}