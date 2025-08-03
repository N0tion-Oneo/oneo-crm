'use client'

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '@/features/auth/context'

export interface RealtimeMessage {
  type: 'record_create' | 'record_update' | 'record_delete' | 'pipeline_update' | 'user_presence' | 'field_lock' | 'field_unlock' | 'permission_update'
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

interface ChannelSubscription {
  id: string
  channel: string
  callback: (message: RealtimeMessage) => void
}

interface WebSocketContextType {
  // Connection state
  isConnected: boolean
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
  
  // Subscription management
  subscribe: (channel: string, callback: (message: RealtimeMessage) => void) => string
  unsubscribe: (subscriptionId: string) => void
  
  // Direct messaging
  sendMessage: (message: Partial<RealtimeMessage>) => boolean
  
  // Presence and locks
  activeUsers: UserPresence[]
  fieldLocks: FieldLock[]
  
  // Connection management
  connect: () => void
  disconnect: () => void
}

const WebSocketContext = createContext<WebSocketContextType | null>(null)

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: React.ReactNode
  autoConnect?: boolean
}

export function WebSocketProvider({ children, autoConnect = true }: WebSocketProviderProps) {
  const { user, isAuthenticated } = useAuth()
  
  // Connection state
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const [activeUsers, setActiveUsers] = useState<UserPresence[]>([])
  const [fieldLocks, setFieldLocks] = useState<FieldLock[]>([])
  
  // Connection management
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const heartbeatIntervalRef = useRef<NodeJS.Timeout>()
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5
  
  // Subscription management
  const subscriptionsRef = useRef<Map<string, ChannelSubscription>>(new Map())
  const activeChannelsRef = useRef<Set<string>>(new Set())
  
  // Get WebSocket URL with authentication
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = '8000'
    
    // Get JWT token from cookies
    const getCookie = (name: string) => {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop()?.split(';').shift();
      return null;
    }
    
    const accessToken = getCookie('oneo_access_token')
    let url = `${protocol}//${host}:${port}/ws/realtime/`
    
    console.log('🍪 WebSocket Cookie Debug:', {
      allCookies: document.cookie,
      accessToken: accessToken ? 'PRESENT' : 'MISSING',
      tokenLength: accessToken ? accessToken.length : 0
    })
    
    if (accessToken) {
      // Basic token validation
      const tokenParts = accessToken.split('.')
      const isValidFormat = tokenParts.length === 3
      
      // Decode JWT payload to see what user it contains
      if (isValidFormat) {
        try {
          const payload = JSON.parse(atob(tokenParts[1]))
          console.log('🔓 JWT Token Contents:', {
            user_id: payload.user_id,
            username: payload.username,
            exp: new Date(payload.exp * 1000),
            iat: new Date(payload.iat * 1000)
          })
        } catch (e) {
          console.warn('❌ Could not decode JWT payload:', e)
        }
        
        url += `?token=${encodeURIComponent(accessToken)}`
        console.log('🔑 WebSocket URL constructed with valid token')
      } else {
        console.log('❌ Invalid JWT token format')
      }
    } else {
      console.log('❌ No access token found in cookies')
    }
    
    return url
  }, [])

  // Send message through WebSocket
  const sendMessage = useCallback((message: Partial<RealtimeMessage>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const fullMessage = {
        timestamp: new Date().toISOString(),
        user: user ? {
          id: user.id,
          name: `${user.first_name} ${user.last_name}`.trim(),
          email: user.email
        } : undefined,
        ...message
      }
      
      wsRef.current.send(JSON.stringify(fullMessage))
      return true
    }
    return false
  }, [user])

  // Subscribe to a channel
  const subscribe = useCallback((channel: string, callback: (message: RealtimeMessage) => void) => {
    const subscriptionId = `${channel}_${Date.now()}_${Math.random()}`
    
    // Store subscription
    subscriptionsRef.current.set(subscriptionId, {
      id: subscriptionId,
      channel,
      callback
    })
    
    // Send subscribe message if connected
    if (isConnected && !activeChannelsRef.current.has(channel)) {
      activeChannelsRef.current.add(channel)
      sendMessage({
        type: 'subscribe' as any,
        channel
      } as any)
      console.log(`📡 Subscribed to channel: ${channel}`)
    }
    
    return subscriptionId
  }, [isConnected, sendMessage])

  // Unsubscribe from a channel
  const unsubscribe = useCallback((subscriptionId: string) => {
    const subscription = subscriptionsRef.current.get(subscriptionId)
    if (!subscription) return
    
    subscriptionsRef.current.delete(subscriptionId)
    
    // Check if any other subscriptions use this channel
    const hasOtherSubscriptions = Array.from(subscriptionsRef.current.values())
      .some(sub => sub.channel === subscription.channel)
    
    // If no other subscriptions, unsubscribe from channel
    if (!hasOtherSubscriptions && activeChannelsRef.current.has(subscription.channel)) {
      activeChannelsRef.current.delete(subscription.channel)
      sendMessage({
        type: 'unsubscribe' as any,
        channel: subscription.channel
      } as any)
      console.log(`📡 Unsubscribed from channel: ${subscription.channel}`)
    }
  }, [sendMessage])

  // Handle incoming messages
  const handleMessage = useCallback((message: RealtimeMessage) => {
    // Handle system messages
    switch (message.type) {
      case 'user_presence':
        if (message.payload?.users) {
          setActiveUsers(message.payload.users)
        }
        break
      case 'field_lock':
      case 'field_unlock':
        // Update field locks
        break
    }
    
    // Broadcast to subscribers
    for (const subscription of subscriptionsRef.current.values()) {
      // Check if message is relevant to this subscription
      const isRelevant = 
        message.type === 'record_create' && subscription.channel.startsWith('pipeline_records_') ||
        message.type === 'record_update' && subscription.channel.startsWith('pipeline_records_') ||
        message.type === 'record_delete' && subscription.channel.startsWith('pipeline_records_') ||
        message.type === 'pipeline_update' && subscription.channel === 'pipeline_updates' ||
        message.type === 'user_presence' && subscription.channel === 'user_presence' ||
        message.type === 'permission_update' && subscription.channel.startsWith('permission') ||
        subscription.channel === 'pipelines_overview' // Special case for overview page
      
      if (isRelevant) {
        try {
          subscription.callback(message)
        } catch (error) {
          console.error('Error in subscription callback:', error)
        }
      }
    }
  }, [])

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!isAuthenticated || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }
    
    try {
      setConnectionStatus('connecting')
      const wsUrl = getWebSocketUrl()
      
      console.log('🚀 Connecting to centralized WebSocket')
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('✅ Centralized WebSocket connected')
        setIsConnected(true)
        setConnectionStatus('connected')
        reconnectAttempts.current = 0

        // Resubscribe to all active channels
        for (const channel of activeChannelsRef.current) {
          sendMessage({
            type: 'subscribe' as any,
            channel
          } as any)
        }

        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          sendMessage({ type: 'ping' as any })
        }, 30000)
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message: RealtimeMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      wsRef.current.onclose = (event) => {
        console.log('🔌 Centralized WebSocket closed:', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        })
        setIsConnected(false)
        
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current)
        }
        
        if (event.code !== 1000) {
          setConnectionStatus('error')
          
          // Attempt to reconnect
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.pow(2, reconnectAttempts.current) * 1000
            console.log(`🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`)
            
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
        console.error('❌ Centralized WebSocket error:', {
          readyState: (error.target as any)?.readyState,
          currentUrl: window.location.href
        })
        setConnectionStatus('error')
      }

    } catch (error) {
      console.error('Failed to create centralized WebSocket connection:', error)
      setConnectionStatus('error')
    }
  }, [isAuthenticated, getWebSocketUrl, sendMessage, handleMessage])

  // Disconnect from WebSocket
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
    activeChannelsRef.current.clear()
  }, [])

  // Auto-connect effect
  useEffect(() => {
    if (autoConnect && isAuthenticated) {
      console.log('👤 WebSocket Auth Context:', {
        isAuthenticated,
        user: user ? {
          id: user.id,
          email: user.email,
          username: user.username || 'NO_USERNAME',
          first_name: user.first_name,
          last_name: user.last_name
        } : 'NO_USER'
      })
      
      // Add delay to ensure authentication is stable
      const connectTimeout = setTimeout(() => {
        connect()
      }, 500)
      
      return () => {
        clearTimeout(connectTimeout)
      }
    }
  }, [autoConnect, isAuthenticated, connect, user])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  const contextValue: WebSocketContextType = {
    isConnected,
    connectionStatus,
    subscribe,
    unsubscribe,
    sendMessage,
    activeUsers,
    fieldLocks,
    connect,
    disconnect
  }

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  )
}