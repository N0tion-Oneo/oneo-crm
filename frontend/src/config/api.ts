// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// API Endpoints
export const API_ENDPOINTS = {
  // Authentication
  auth: {
    login: '/auth/login/',
    logout: '/auth/logout/',
    refresh: '/auth/refresh/',
    me: '/auth/me/',
  },
  
  // Communications
  communications: {
    email: {
      accounts: '/communications/email/accounts/',
      threads: '/communications/email/threads/',
      threadMessages: (threadId: string) => `/communications/email/threads/${threadId}/messages/`,
      send: '/communications/email/send/',
      sync: '/communications/email/sync/',
      folders: '/communications/email/folders/',
    },
    whatsapp: {
      accounts: '/communications/whatsapp/accounts/',
      conversations: '/communications/whatsapp/conversations/',
      messages: (conversationId: string) => `/communications/whatsapp/conversations/${conversationId}/messages/`,
      send: '/communications/whatsapp/send/',
    },
  },
}

// Helper function to build full URL
export const buildApiUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`
}