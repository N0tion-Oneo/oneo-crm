import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '@/features/auth/context'

export interface WebSocketMessage {
  type: string
  message?: any
  conversation?: any
  [key: string]: any
}

export interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
  reconnectOnClose?: boolean
  reconnectInterval?: number
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const { isAuthenticated, user } = useAuth()

  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectOnClose = true,
    reconnectInterval = 3000
  } = options

  const connect = useCallback(() => {
    if (!isAuthenticated || !user) {
      console.log('🔌 WebSocket: Not authenticated, skipping connection')
      setConnectionStatus('disconnected')
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log('🔌 WebSocket: Already connected or connecting')
      return
    }

    try {
      setConnectionStatus('connecting')
      console.log('🔌 WebSocket: Attempting to connect to', url)
      
      // Check if URL is valid before attempting connection
      if (!url || !url.includes('ws://') && !url.includes('wss://')) {
        throw new Error(`Invalid WebSocket URL: ${url}`)
      }
      
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('🔌 WebSocket: Connected to', url)
        setIsConnected(true)
        setConnectionStatus('connected')
        onOpen?.()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('📨 WebSocket message received:', data)
          onMessage?.(data)
        } catch (error) {
          console.error('❌ WebSocket: Error parsing message:', error)
        }
      }

      ws.onclose = (event) => {
        console.log('🔌 WebSocket: Connection closed', event.code, event.reason)
        setIsConnected(false)
        setConnectionStatus('disconnected')
        wsRef.current = null
        onClose?.()

        // Reconnect if enabled and not a clean close
        if (reconnectOnClose && event.code !== 1000 && isAuthenticated) {
          console.log(`🔄 WebSocket: Reconnecting in ${reconnectInterval}ms`)
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        }
      }

      ws.onerror = (error) => {
        console.error('❌ WebSocket: Connection error to', url)
        console.error('❌ WebSocket: Error details:', {
          type: error.type || 'unknown',
          readyState: ws.readyState,
          url: ws.url,
          timestamp: new Date().toISOString(),
          errorEvent: error
        })
        setConnectionStatus('error')
        onError?.(error)
      }
    } catch (error) {
      console.error('❌ WebSocket: Failed to create connection:', error)
      setConnectionStatus('error')
    }
  }, [url, isAuthenticated, user, onMessage, onOpen, onClose, onError, reconnectOnClose, reconnectInterval])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      console.log('🔌 WebSocket: Disconnecting from', url)
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    
    setIsConnected(false)
    setConnectionStatus('disconnected')
  }, [url])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message)
      console.log('📤 WebSocket: Sending message:', message)
      wsRef.current.send(messageStr)
      return true
    } else {
      console.warn('⚠️ WebSocket: Cannot send message, connection not open')
      return false
    }
  }, [])

  // Connect when component mounts and user is authenticated
  useEffect(() => {
    if (isAuthenticated && user) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
  }, [isAuthenticated, user, connect, disconnect])

  return {
    isConnected,
    connectionStatus,
    sendMessage,
    connect,
    disconnect
  }
}