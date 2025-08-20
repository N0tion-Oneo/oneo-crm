'use client'

import React from 'react'
import { useWebSocket } from '@/contexts/websocket-context'
import { useAuth } from '@/features/auth/context'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export function WebSocketDebug() {
  const { 
    isConnected, 
    connectionStatus, 
    connect, 
    disconnect,
    subscribe,
    unsubscribe
  } = useWebSocket()
  
  const { user, isAuthenticated } = useAuth()

  const handleTestSubscription = () => {
    const testSub = subscribe('conversation_test', (message) => {
      console.log('🧪 Test subscription received:', message)
    })
    console.log('🧪 Created test subscription:', testSub)
    
    // Unsubscribe after 5 seconds
    setTimeout(() => {
      unsubscribe(testSub)
      console.log('🧪 Unsubscribed from test')
    }, 5000)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'bg-green-500'
      case 'connecting': return 'bg-yellow-500'
      case 'disconnected': return 'bg-gray-500'
      case 'error': return 'bg-red-500'
      default: return 'bg-gray-400'
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="text-sm">🔌 WebSocket Debug</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Auth Status:</span>
            <Badge variant={isAuthenticated ? "default" : "secondary"}>
              {isAuthenticated ? '✅ Authenticated' : '❌ Not Authenticated'}
            </Badge>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">User:</span>
            <span className="text-sm">{user?.email || 'None'}</span>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Connection:</span>
            <Badge 
              variant="outline" 
              className={`${getStatusColor(connectionStatus)} text-white`}
            >
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </Badge>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Status:</span>
            <span className="text-sm">{connectionStatus}</span>
          </div>
        </div>

        <div className="flex gap-2">
          <Button 
            size="sm" 
            onClick={connect}
            disabled={isConnected}
          >
            Connect
          </Button>
          <Button 
            size="sm" 
            variant="outline" 
            onClick={disconnect}
            disabled={!isConnected}
          >
            Disconnect
          </Button>
        </div>

        <Button 
          size="sm" 
          variant="secondary" 
          onClick={handleTestSubscription}
          disabled={!isConnected}
          className="w-full"
        >
          🧪 Test Subscription
        </Button>

        <div className="text-xs text-gray-500 space-y-1">
          <div>URL: {typeof window !== 'undefined' ? window.location.href : 'N/A'}</div>
          <div>Host: {typeof window !== 'undefined' ? window.location.hostname : 'N/A'}</div>
        </div>
      </CardContent>
    </Card>
  )
}