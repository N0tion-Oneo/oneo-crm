import { useCallback } from 'react'
import { useWebSocket, WebSocketMessage } from './use-websocket'

interface Message {
  id: string
  content: string
  direction: 'inbound' | 'outbound'
  contact_email: string
  timestamp: string
  conversation_id: string
  // ... other message properties
}

interface Conversation {
  id: string
  last_message: Message
  unread_count: number
  // ... other conversation properties
}

interface UseCommunicationsWebSocketOptions {
  onNewMessage?: (message: Message) => void
  onConversationUpdate?: (conversation: Conversation) => void
  onConnectionStatusChange?: (status: string) => void
}

export function useCommunicationsWebSocket(options: UseCommunicationsWebSocketOptions = {}) {
  const { onNewMessage, onConversationUpdate, onConnectionStatusChange } = options

  // Get WebSocket URL - using localhost for development
  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = '8000' // Django backend port
    
    // Add JWT token for authentication if available
    const token = document.cookie
      .split('; ')
      .find(row => row.startsWith('oneo_access_token='))
      ?.split('=')[1]
    
    const baseUrl = `${protocol}//${host}:${port}/ws/realtime/`
    
    // Add token as query parameter if available
    if (token) {
      return `${baseUrl}?token=${token}`
    }
    
    return baseUrl
  }

  const handleMessage = useCallback((data: WebSocketMessage) => {
    console.log('📨 Communications WebSocket message:', data.type, data)

    switch (data.type) {
      case 'message_update':
        // New message received
        if (data.message && onNewMessage) {
          onNewMessage(data.message)
        }
        break

      case 'new_conversation':
        // New conversation or conversation updated
        if (data.conversation && onConversationUpdate) {
          onConversationUpdate(data.conversation)
        }
        break

      case 'conversation_update':
        // Existing conversation updated
        if (data.conversation && onConversationUpdate) {
          onConversationUpdate(data.conversation)
        }
        break

      case 'authenticated':
        console.log('✅ Communications WebSocket authenticated:', data.message)
        onConnectionStatusChange?.('authenticated')
        break

      case 'auth_required':
        console.log('🔐 Communications WebSocket requires authentication')
        onConnectionStatusChange?.('auth_required')
        break

      case 'error':
        console.error('❌ Communications WebSocket error:', data.message)
        onConnectionStatusChange?.('error')
        break

      default:
        console.log('📝 Unhandled WebSocket message type:', data.type, data)
    }
  }, [onNewMessage, onConversationUpdate, onConnectionStatusChange])

  const handleOpen = useCallback(() => {
    console.log('🔌 Communications WebSocket connected')
    onConnectionStatusChange?.('connected')
  }, [onConnectionStatusChange])

  const handleClose = useCallback(() => {
    console.log('🔌 Communications WebSocket disconnected')
    onConnectionStatusChange?.('disconnected')
  }, [onConnectionStatusChange])

  const handleError = useCallback((error: Event) => {
    const wsUrl = getWebSocketUrl()
    console.error('❌ Communications WebSocket error:', error)
    console.error('❌ Connection details:', {
      attemptedUrl: wsUrl,
      readyState: error.target?.readyState,
      timestamp: new Date().toISOString(),
      currentOrigin: window.location.origin,
      hasToken: wsUrl.includes('token=')
    })
    onConnectionStatusChange?.('error')
  }, [onConnectionStatusChange])

  const { isConnected, connectionStatus, sendMessage, connect, disconnect } = useWebSocket(
    getWebSocketUrl(),
    {
      onMessage: handleMessage,
      onOpen: handleOpen,
      onClose: handleClose,
      onError: handleError,
      reconnectOnClose: true,
      reconnectInterval: 3000
    }
  )

  // Subscribe to a conversation for real-time updates
  const subscribeToConversation = useCallback((conversationId: string) => {
    return sendMessage({
      type: 'subscribe',
      channel: `conversation_${conversationId}`
    })
  }, [sendMessage])

  // Subscribe to a channel for inbox-wide updates
  const subscribeToChannel = useCallback((channelId: string) => {
    return sendMessage({
      type: 'subscribe', 
      channel: `channel_${channelId}`
    })
  }, [sendMessage])

  // Unsubscribe from a conversation
  const unsubscribeFromConversation = useCallback((conversationId: string) => {
    return sendMessage({
      type: 'unsubscribe',
      channel: `conversation_${conversationId}`
    })
  }, [sendMessage])

  // Unsubscribe from a channel
  const unsubscribeFromChannel = useCallback((channelId: string) => {
    return sendMessage({
      type: 'unsubscribe',
      channel: `channel_${channelId}`
    })
  }, [sendMessage])

  return {
    isConnected,
    connectionStatus,
    connect,
    disconnect,
    subscribeToConversation,
    subscribeToChannel,
    unsubscribeFromConversation,
    unsubscribeFromChannel,
    sendMessage
  }
}