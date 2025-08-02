'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '@/features/auth/context'

// Enable WebSocket connections for real-time messaging
const ENABLE_WEBSOCKET = true // Always enabled for messaging features

export interface RealtimeMessage {
  type: 'record_update' | 'record_create' | 'record_delete' | 'pipeline_update' | 'user_presence' | 'field_lock' | 'field_unlock'
  payload: any
  user?: {
    id: string
    name: string
    email: string
  }
  timestamp: string
}

export interface UserPresence {
  user_id: string
  user_name: string
  user_email: string
  last_seen: string
  active_record?: string
  active_field?: string
}

export interface FieldLock {
  field_name: string
  record_id: string
  user_id: string
  user_name: string
  locked_at: string
}

interface UseRealtimeOptions {
  room?: string // Room to join (e.g., "pipeline_123", "record_456")
  onMessage?: (message: RealtimeMessage) => void
  onUserPresence?: (users: UserPresence[]) => void
  onFieldLock?: (locks: FieldLock[]) => void
  autoConnect?: boolean
}

export function useRealtime({
  room,
  onMessage,
  onUserPresence,
  onFieldLock,
  autoConnect = true
}: UseRealtimeOptions = {}) {
  const { user, isAuthenticated } = useAuth()
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const [activeUsers, setActiveUsers] = useState<UserPresence[]>([])
  const [fieldLocks, setFieldLocks] = useState<FieldLock[]>([])
  const [lastMessage, setLastMessage] = useState<RealtimeMessage | null>(null)
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const heartbeatIntervalRef = useRef<NodeJS.Timeout>()
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  // Get WebSocket URL with authentication
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    // Always use port 8000 for WebSocket (Django backend), not the frontend port
    const port = '8000'
    
    // Try to get JWT token from cookies
    const getCookie = (name: string) => {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop()?.split(';').shift();
      return null;
    }
    
    const accessToken = getCookie('oneo_access_token')
    let url = `${protocol}//${host}:${port}/ws/realtime/`
    
    console.log('🍪 Cookie check:', {
      cookieCount: document.cookie.split(';').length,
      hasAccessToken: !!accessToken,
      tokenLength: accessToken ? accessToken.length : 0
    })
    
    // Add JWT token as query parameter if available
    if (accessToken) {
      // Basic token validation - check if it looks like a JWT
      const tokenParts = accessToken.split('.')
      const isValidFormat = tokenParts.length === 3
      
      if (!isValidFormat) {
        console.log('❌ Invalid JWT token format')
        return url // Return URL without token
      }
      
      url += `?token=${encodeURIComponent(accessToken)}`
      console.log('🔑 WebSocket URL constructed:', {
        protocol,
        host,
        port,
        hasToken: true,
        tokenValid: isValidFormat
      })
    } else {
      console.log('❌ No access token found in cookies')
    }
    
    return url
  }, [])

  // Send message
  const sendMessage = useCallback((message: Partial<RealtimeMessage>) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const fullMessage: RealtimeMessage = {
        type: message.type!,
        payload: message.payload || {},
        user: user ? {
          id: user.id,
          name: `${user.firstName} ${user.lastName}`,
          email: user.email
        } : undefined,
        timestamp: new Date().toISOString(),
        ...message
      }
      
      wsRef.current.send(JSON.stringify(fullMessage))
      return true
    }
    return false
  }, [user])

  // Join room
  const joinRoom = useCallback((roomName: string) => {
    return sendMessage({
      type: 'subscribe',
      channel: roomName
    } as any)
  }, [sendMessage])

  // Leave room
  const leaveRoom = useCallback((roomName: string) => {
    return sendMessage({
      type: 'unsubscribe', 
      channel: roomName
    } as any)
  }, [sendMessage])

  // Lock field
  const lockField = useCallback((recordId: string, fieldName: string) => {
    return sendMessage({
      type: 'field_lock',
      payload: {
        record_id: recordId,
        field_name: fieldName,
        action: 'lock'
      }
    })
  }, [sendMessage])

  // Unlock field
  const unlockField = useCallback((recordId: string, fieldName: string) => {
    return sendMessage({
      type: 'field_unlock',
      payload: {
        record_id: recordId,
        field_name: fieldName,
        action: 'unlock'
      }
    })
  }, [sendMessage])

  // Broadcast record update
  const broadcastRecordUpdate = useCallback((recordId: string, fieldName: string, value: any) => {
    return sendMessage({
      type: 'record_update',
      payload: {
        record_id: recordId,
        field_name: fieldName,
        value: value,
        action: 'update'
      }
    })
  }, [sendMessage])

  // Connect WebSocket
  const connect = useCallback(() => {
    console.log('🔌 WebSocket connect called', {
      isAuthenticated,
      user: user ? { id: user.id, email: user.email } : null,
      currentReadyState: wsRef.current?.readyState
    })

    if (!isAuthenticated || !user) {
      console.log('❌ Cannot connect to WebSocket: user not authenticated')
      return
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('✅ WebSocket already connected')
      return
    }

    try {
      setConnectionStatus('connecting')
      const wsUrl = getWebSocketUrl()
      console.log('🚀 Connecting to WebSocket:', wsUrl)
      console.log('🔑 User context:', { id: user.id, email: user.email })
      
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('✅ WebSocket connected successfully')
        setIsConnected(true)
        setConnectionStatus('connected')
        reconnectAttempts.current = 0

        // Join room if specified
        if (room) {
          console.log(`🚪 Joining room: ${room}`)
          setTimeout(() => joinRoom(room), 100)
        }

        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000) // 30 seconds
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message: RealtimeMessage = JSON.parse(event.data)
          setLastMessage(message)

          // Handle different message types
          switch (message.type) {
            case 'user_presence':
              if (message.payload.users) {
                setActiveUsers(message.payload.users)
                onUserPresence?.(message.payload.users)
              }
              break

            case 'field_lock':
            case 'field_unlock':
              if (message.payload.locks) {
                setFieldLocks(message.payload.locks)
                onFieldLock?.(message.payload.locks)
              }
              break

            default:
              // Pass all messages to the callback
              onMessage?.(message)
              break
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      wsRef.current.onclose = (event) => {
        console.log('🔌 WebSocket closed:', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        })
        setIsConnected(false)
        
        if (event.code !== 1000) { // Not a normal closure
          setConnectionStatus('error')
          
          // Attempt to reconnect
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.pow(2, reconnectAttempts.current) * 1000 // Exponential backoff
            console.log(`🔄 Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`)
            
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttempts.current++
              connect()
            }, delay)
          } else {
            console.log('❌ Max reconnection attempts reached')
            setConnectionStatus('disconnected')
          }
        } else {
          setConnectionStatus('disconnected')
        }
      }

      wsRef.current.onerror = (error) => {
        const hasToken = document.cookie.includes('oneo_access_token=')
        console.error('❌ WebSocket connection failed:', {
          readyState: (error.target as any)?.readyState,
          hasToken,
          connectionAttempt: reconnectAttempts.current + 1,
          room: room || 'none',
          currentUrl: window.location.href,
          wsUrl: getWebSocketUrl().replace(/token=[^&]+/, 'token=HIDDEN')
        })
        setConnectionStatus('error')
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnectionStatus('error')
    }
  }, [isAuthenticated, user, room, getWebSocketUrl, joinRoom, onMessage, onUserPresence, onFieldLock])

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }

    setIsConnected(false)
    setConnectionStatus('disconnected')
    setActiveUsers([])
    setFieldLocks([])
    reconnectAttempts.current = 0
  }, [])

  // Auto-connect effect with small delay to ensure authentication is stable
  useEffect(() => {
    if (autoConnect && isAuthenticated) {
      // Add small delay to ensure authentication is fully established
      const connectTimeout = setTimeout(() => {
        connect()
      }, 500) // 500ms delay
      
      return () => {
        clearTimeout(connectTimeout)
        disconnect()
      }
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, isAuthenticated]) // Remove connect, disconnect from dependencies

  // Room change effect
  useEffect(() => {
    if (isConnected && room) {
      joinRoom(room)
    }
  }, [isConnected, room]) // Remove joinRoom from dependencies

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, []) // Remove disconnect from dependencies

  return {
    // Connection state
    isConnected,
    connectionStatus,
    
    // Real-time data
    activeUsers,
    fieldLocks,
    lastMessage,
    
    // Actions
    connect,
    disconnect,
    sendMessage,
    joinRoom,
    leaveRoom,
    lockField,
    unlockField,
    broadcastRecordUpdate,
    
    // Utilities
    isFieldLocked: (recordId: string, fieldName: string) => 
      fieldLocks.some(lock => 
        lock.record_id === recordId && 
        lock.field_name === fieldName && 
        lock.user_id !== user?.id
      ),
    
    getFieldLock: (recordId: string, fieldName: string) =>
      fieldLocks.find(lock => 
        lock.record_id === recordId && 
        lock.field_name === fieldName
      ),
    
    getUsersInRoom: () => activeUsers,
    
    isUserActive: (userId: string) =>
      activeUsers.some(u => u.user_id === userId)
  }
}