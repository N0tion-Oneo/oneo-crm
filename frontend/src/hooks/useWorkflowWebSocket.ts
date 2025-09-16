import { useEffect, useRef, useState, useCallback } from 'react';
import Cookies from 'js-cookie';

interface WorkflowWebSocketOptions {
  workflowId?: string;
  executionId?: string;
  onExecutionStarted?: (data: any) => void;
  onNodeStarted?: (data: any) => void;
  onNodeCompleted?: (data: any) => void;
  onExecutionCompleted?: (data: any) => void;
  onExecutionLog?: (data: any) => void;
  onApprovalRequired?: (data: any) => void;
  onError?: (error: string) => void;
}

export function useWorkflowWebSocket(options: WorkflowWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    // Get auth token
    const token = Cookies.get('oneo_access_token');
    if (!token) {
      setConnectionError('No authentication token');
      return;
    }

    // Build WebSocket URL
    const currentHost = window.location.hostname;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${currentHost}:8000/ws/workflows/updates/?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('🔌 Workflow WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;

        // Subscribe to workflow if provided
        if (options.workflowId) {
          ws.send(JSON.stringify({
            type: 'subscribe_workflow',
            workflow_id: options.workflowId
          }));
        }

        // Subscribe to execution if provided
        if (options.executionId) {
          ws.send(JSON.stringify({
            type: 'subscribe_execution',
            execution_id: options.executionId
          }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ Workflow WebSocket error:', error);
        setConnectionError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('🔌 Workflow WebSocket disconnected', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect if not a normal closure
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnectionError('Failed to connect to WebSocket');
    }
  }, [options.workflowId, options.executionId]);

  const handleMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'connection':
        console.log('Connected to workflow WebSocket:', data);
        break;

      case 'subscribed':
        console.log('Subscribed to:', data);
        break;

      case 'execution_started':
        options.onExecutionStarted?.(data);
        break;

      case 'node_started':
        options.onNodeStarted?.(data);
        break;

      case 'node_completed':
        options.onNodeCompleted?.(data);
        break;

      case 'execution_completed':
        options.onExecutionCompleted?.(data);
        break;

      case 'execution_log':
        options.onExecutionLog?.(data);
        break;

      case 'approval_required':
        options.onApprovalRequired?.(data);
        break;

      case 'error':
        console.error('WebSocket error:', data.message);
        options.onError?.(data.message);
        break;

      case 'pong':
        // Heartbeat response
        break;

      default:
        console.log('Unknown WebSocket message type:', data.type);
    }
  }, [
    options.onExecutionStarted,
    options.onNodeStarted,
    options.onNodeCompleted,
    options.onExecutionCompleted,
    options.onExecutionLog,
    options.onApprovalRequired,
    options.onError
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, []);

  const subscribeToWorkflow = useCallback((workflowId: string) => {
    sendMessage({
      type: 'subscribe_workflow',
      workflow_id: workflowId
    });
  }, [sendMessage]);

  const subscribeToExecution = useCallback((executionId: string) => {
    sendMessage({
      type: 'subscribe_execution',
      execution_id: executionId
    });
  }, [sendMessage]);

  const unsubscribeFromWorkflow = useCallback((workflowId: string) => {
    sendMessage({
      type: 'unsubscribe_workflow',
      workflow_id: workflowId
    });
  }, [sendMessage]);

  const unsubscribeFromExecution = useCallback((executionId: string) => {
    sendMessage({
      type: 'unsubscribe_execution',
      execution_id: executionId
    });
  }, [sendMessage]);

  // Connect on mount
  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, []);

  // Send periodic heartbeat to keep connection alive
  useEffect(() => {
    const heartbeatInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(heartbeatInterval);
  }, []);

  return {
    isConnected,
    connectionError,
    sendMessage,
    subscribeToWorkflow,
    subscribeToExecution,
    unsubscribeFromWorkflow,
    unsubscribeFromExecution,
    disconnect,
    reconnect: connect
  };
}
