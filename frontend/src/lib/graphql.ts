import axios, { AxiosInstance } from 'axios'
import Cookies from 'js-cookie'

// GraphQL Configuration - Dynamic URL based on current hostname
const getGraphQLEndpoint = () => {
  if (typeof window === 'undefined') {
    // Server-side: use environment variable or default
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${apiUrl}/graphql/`
  }
  
  // Client-side: use current hostname but change port to 8000
  const currentHost = window.location.hostname
  return `http://${currentHost}:8000/graphql/`
}

// Create GraphQL client with dynamic base URL
export const graphqlClient: AxiosInstance = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

// Request interceptor to add tenant headers and dynamic base URL
graphqlClient.interceptors.request.use(
  (config) => {
    // Set dynamic base URL
    config.baseURL = getGraphQLEndpoint()
    
    // Add tenant header if available
    const tenant = Cookies.get('oneo_tenant')
    if (tenant) {
      config.headers['X-Tenant'] = tenant
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle GraphQL errors
graphqlClient.interceptors.response.use(
  (response) => {
    // Check for GraphQL errors
    if (response.data.errors && response.data.errors.length > 0) {
      const error = new Error(response.data.errors[0].message)
      error.name = 'GraphQLError'
      throw error
    }
    return response
  },
  async (error) => {
    // Handle network errors and authentication
    if (error.response?.status === 401) {
      // Session expired, redirect to login
      Cookies.remove('oneo_session_id')
      Cookies.remove('oneo_tenant')
      
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

// GraphQL query function
export async function graphqlQuery<T = any>(
  query: string, 
  variables?: Record<string, any>
): Promise<T> {
  const response = await graphqlClient.post('', {
    query,
    variables,
  })
  
  return response.data.data
}

// GraphQL mutation function  
export async function graphqlMutation<T = any>(
  mutation: string,
  variables?: Record<string, any>
): Promise<T> {
  const response = await graphqlClient.post('', {
    query: mutation,
    variables,
  })
  
  return response.data.data
}

// Authentication GraphQL operations
export const authGraphQL = {
  login: async (credentials: { username: string; password: string; remember_me?: boolean }) => {
    const mutation = `
      mutation Login($input: LoginInput!) {
        login(input: $input) {
          success
          errors
          user {
            id
            email
            firstName
            lastName
          }
          permissions
        }
      }
    `
    
    return graphqlMutation(mutation, { 
      input: {
        username: credentials.username,
        password: credentials.password,
        rememberMe: credentials.remember_me || false
      }
    })
  },

  logout: async () => {
    const mutation = `
      mutation Logout {
        logout {
          success
          message
        }
      }
    `
    
    return graphqlMutation(mutation)
  },

  getCurrentUser: async () => {
    const query = `
      query CurrentUser {
        currentUser {
          id
          email
          firstName
          lastName
          isActive
          createdAt
        }
      }
    `
    
    return graphqlQuery(query)
  },

  getUserPermissions: async () => {
    const query = `
      query UserPermissions {
        userPermissions
      }
    `
    
    return graphqlQuery(query)
  },
}

export default graphqlClient