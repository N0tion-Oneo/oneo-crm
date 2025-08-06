'use client'

import React, { useState, useEffect } from 'react'
import { useWebSocket } from '@/contexts/websocket-context'
import { usePipelineRecordsSubscription } from '@/hooks/use-websocket-subscription'

interface RealtimeDiagnosticsProps {
  pipelineId: string
}

export function RealtimeDiagnostics({ pipelineId }: RealtimeDiagnosticsProps) {
  const [messages, setMessages] = useState<any[]>([])
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  const { isConnected, connectionStatus } = useWebSocket()

  // Subscribe to pipeline records and log all messages
  const { isConnected: subscriptionConnected } = usePipelineRecordsSubscription(
    pipelineId,
    (message) => {
      console.log('🔍 DIAGNOSTIC: Received WebSocket message:', message)
      setMessages(prev => [...prev.slice(-9), {
        timestamp: new Date().toISOString(),
        message
      }])
    }
  )

  useEffect(() => {
    if (connectionStatus === 'connecting') {
      setConnectionAttempts(prev => prev + 1)
    }
  }, [connectionStatus])

  const connectionColor = {
    'connected': 'text-green-600',
    'connecting': 'text-yellow-600', 
    'disconnected': 'text-red-600',
    'error': 'text-red-600'
  }

  return (
    <div className="fixed bottom-4 right-4 bg-white border rounded-lg shadow-lg p-4 max-w-md z-50">
      <h3 className="font-semibold text-sm mb-2">🔧 Realtime Diagnostics</h3>
      
      {/* Connection Status */}
      <div className="space-y-1 text-xs">
        <div className={`font-medium ${connectionColor[connectionStatus]}`}>
          🔌 Status: {connectionStatus.toUpperCase()}
        </div>
        <div className={isConnected ? 'text-green-600' : 'text-red-600'}>
          📡 WebSocket: {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
        </div>
        <div className={subscriptionConnected ? 'text-green-600' : 'text-red-600'}>
          📋 Pipeline Sub: {subscriptionConnected ? 'ACTIVE' : 'INACTIVE'}
        </div>
        <div className="text-gray-600">
          🔄 Channel: pipeline_records_{pipelineId}
        </div>
        <div className="text-gray-600">
          📊 Attempts: {connectionAttempts}
        </div>
      </div>

      {/* Recent Messages */}
      <div className="mt-3 border-t pt-2">
        <div className="text-xs font-medium mb-1">Recent Messages ({messages.length}):</div>
        <div className="max-h-32 overflow-y-auto space-y-1">
          {messages.length === 0 ? (
            <div className="text-xs text-gray-500 italic">No messages received yet...</div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className="text-xs bg-gray-50 p-1 rounded">
                <div className="font-mono text-green-600">
                  {msg.message.type}
                </div>
                <div className="text-gray-600">
                  ID: {msg.message.payload?.record_id} | 
                  Pipeline: {msg.message.payload?.pipeline_id}
                </div>
                <div className="text-gray-500">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Test Button */}
      <button 
        onClick={() => {
          console.log('🧪 DIAGNOSTIC TEST: Current state:', {
            isConnected,
            connectionStatus,
            subscriptionConnected,
            pipelineId,
            messageCount: messages.length
          })
        }}
        className="mt-2 w-full bg-blue-500 text-white text-xs py-1 px-2 rounded hover:bg-blue-600"
      >
        🧪 Log Diagnostic Info
      </button>
    </div>
  )
}