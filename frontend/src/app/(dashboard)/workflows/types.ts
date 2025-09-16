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
  // Triggers (17 types - added TIME_BASED)
  TRIGGER_MANUAL = 'TRIGGER_MANUAL',
  TRIGGER_SCHEDULE = 'TRIGGER_SCHEDULE',
  TRIGGER_TIME_BASED = 'TRIGGER_TIME_BASED',
  TRIGGER_WEBHOOK = 'TRIGGER_WEBHOOK',
  TRIGGER_EVENT = 'TRIGGER_EVENT',
  TRIGGER_RECORD_CREATED = 'TRIGGER_RECORD_CREATED',
  TRIGGER_RECORD_UPDATED = 'TRIGGER_RECORD_UPDATED',
  TRIGGER_RECORD_DELETED = 'TRIGGER_RECORD_DELETED',
  /** @deprecated Use TRIGGER_RECORD_UPDATED with update_type: 'specific_fields' */
  TRIGGER_FIELD_CHANGED = 'TRIGGER_FIELD_CHANGED',
  TRIGGER_API_ENDPOINT = 'TRIGGER_API_ENDPOINT',
  TRIGGER_FORM_SUBMITTED = 'TRIGGER_FORM_SUBMITTED',
  TRIGGER_EMAIL_RECEIVED = 'TRIGGER_EMAIL_RECEIVED',
  TRIGGER_MESSAGE_RECEIVED = 'TRIGGER_MESSAGE_RECEIVED',
  TRIGGER_LINKEDIN_MESSAGE = 'TRIGGER_LINKEDIN_MESSAGE',
  TRIGGER_WHATSAPP_MESSAGE = 'TRIGGER_WHATSAPP_MESSAGE',
  /** @deprecated Use TRIGGER_RECORD_UPDATED with update_type: 'status_only' or 'status_progression' */
  TRIGGER_STATUS_CHANGED = 'TRIGGER_STATUS_CHANGED',
  TRIGGER_DATE_REACHED = 'TRIGGER_DATE_REACHED',
  TRIGGER_CONDITION_MET = 'TRIGGER_CONDITION_MET',
  TRIGGER_PIPELINE_STAGE_CHANGED = 'TRIGGER_PIPELINE_STAGE_CHANGED',
  TRIGGER_ENGAGEMENT_THRESHOLD = 'TRIGGER_ENGAGEMENT_THRESHOLD',
  TRIGGER_WORKFLOW_COMPLETED = 'TRIGGER_WORKFLOW_COMPLETED',

  // Data Operations
  RECORD_CREATE = 'RECORD_CREATE',
  RECORD_UPDATE = 'RECORD_UPDATE',
  RECORD_FIND = 'RECORD_FIND',
  RECORD_DELETE = 'RECORD_DELETE',
  MERGE_DATA = 'MERGE_DATA',
  RESOLVE_CONTACT = 'RESOLVE_CONTACT',
  CREATE_FOLLOW_UP_TASK = 'CREATE_FOLLOW_UP_TASK',

  // Control Flow
  CONDITION = 'CONDITION',
  FOR_EACH = 'FOR_EACH',
  WORKFLOW_LOOP_CONTROLLER = 'WORKFLOW_LOOP_CONTROLLER',
  WORKFLOW_LOOP_BREAKER = 'WORKFLOW_LOOP_BREAKER',
  WAIT_DELAY = 'WAIT_DELAY',
  WAIT_FOR_RESPONSE = 'WAIT_FOR_RESPONSE',
  WAIT_FOR_RECORD_EVENT = 'WAIT_FOR_RECORD_EVENT',
  WAIT_FOR_CONDITION = 'WAIT_FOR_CONDITION',
  CONVERSATION_STATE = 'CONVERSATION_STATE',

  // Communication
  UNIPILE_SEND_EMAIL = 'UNIPILE_SEND_EMAIL',
  UNIPILE_SEND_WHATSAPP = 'UNIPILE_SEND_WHATSAPP',
  UNIPILE_SEND_LINKEDIN = 'UNIPILE_SEND_LINKEDIN',
  UNIPILE_SEND_SMS = 'UNIPILE_SEND_SMS',

  // AI Operations
  AI_PROMPT = 'AI_PROMPT',
  AI_ANALYSIS = 'AI_ANALYSIS',
  AI_CONVERSATION_LOOP = 'AI_CONVERSATION_LOOP',
  AI_MESSAGE_GENERATOR = 'AI_MESSAGE_GENERATOR',
  AI_RESPONSE_EVALUATOR = 'AI_RESPONSE_EVALUATOR',

  // Utility
  HTTP_REQUEST = 'HTTP_REQUEST',
  WEBHOOK_OUT = 'WEBHOOK_OUT',
  TASK_NOTIFY = 'TASK_NOTIFY',
  GENERATE_FORM_LINK = 'GENERATE_FORM_LINK',

  // Workflow Control
  APPROVAL = 'APPROVAL',
  SUB_WORKFLOW = 'SUB_WORKFLOW',
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