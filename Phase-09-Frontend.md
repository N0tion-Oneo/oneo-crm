# Phase 09: Frontend Interface & User Experience

## 🎯 Overview & Objectives

Build a modern, responsive React-based frontend that serves as the reference implementation for the headless Oneo CRM API. This phase creates an intuitive, powerful interface supporting all system features including collaborative editing, real-time dashboards, AI workflows, and comprehensive pipeline management.

### Primary Goals
- Modern React 18+ application with TypeScript
- Responsive design supporting desktop, tablet, and mobile
- Real-time collaborative features with live updates
- Advanced dashboard system with drag-and-drop components
- Comprehensive pipeline and record management interfaces
- AI workflow builder with visual node-based editor
- Integrated communication interface with omni-channel support

### Success Criteria
- ✅ Sub-2s initial page load times
- ✅ Responsive design working across all device sizes
- ✅ Real-time updates with <100ms latency
- ✅ Accessibility compliance (WCAG 2.1 AA)
- ✅ Comprehensive mobile experience
- ✅ Advanced data visualization and analytics

## 🏗️ Technical Requirements & Dependencies

### Phase Dependencies
- ✅ **Phase 01**: Backend API endpoints and authentication
- ✅ **Phase 02**: User authentication and permission system
- ✅ **Phase 03**: Pipeline API and dynamic schema support
- ✅ **Phase 04**: Relationship API with graph traversal
- ✅ **Phase 05**: REST and GraphQL API endpoints
- ✅ **Phase 06**: WebSocket and real-time infrastructure
- ✅ **Phase 07**: AI integration APIs and workflows
- ✅ **Phase 08**: Communication APIs and sequence management

### Core Technologies
- **React 18** with concurrent features and suspense
- **Next.js 14** with App Router and server components
- **TypeScript 5** for type safety and developer experience
- **Tailwind CSS** for utility-first styling
- **React Query (TanStack Query)** for server state management
- **Zustand** for client state management
- **React Flow** for workflow and relationship visualization

### Additional Dependencies
```json
{
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "typescript": "^5.4.0",
    "@tanstack/react-query": "^5.28.0",
    "zustand": "^4.5.0",
    "tailwindcss": "^3.4.0",
    "framer-motion": "^11.0.0",
    "react-flow": "^11.11.0",
    "recharts": "^2.12.0",
    "react-hook-form": "^7.51.0",
    "zod": "^3.22.0",
    "@headlessui/react": "^1.7.0",
    "@heroicons/react": "^2.1.0",
    "react-hot-toast": "^2.4.0",
    "socket.io-client": "^4.7.0",
    "graphql": "^16.8.0",
    "graphql-request": "^6.1.0",
    "@apollo/client": "^3.9.0",
    "date-fns": "^3.6.0",
    "react-datepicker": "^6.3.0",
    "react-select": "^5.8.0",
    "react-table": "^7.8.0",
    "react-virtual": "^2.10.0",
    "react-window": "^1.8.0",
    "react-beautiful-dnd": "^13.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/node": "^20.12.0",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.0",
    "prettier": "^3.2.0",
    "@tailwindcss/forms": "^0.5.0",
    "@tailwindcss/typography": "^0.5.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

## 🎨 Frontend Architecture Design

### Application Structure
```
frontend/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # Auth-related pages
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/              # Main dashboard layout
│   │   ├── pipelines/
│   │   ├── records/
│   │   ├── relationships/
│   │   ├── communications/
│   │   ├── workflows/
│   │   ├── analytics/
│   │   └── settings/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/                   # Reusable components
│   ├── ui/                      # Base UI components
│   ├── forms/                   # Form components
│   ├── charts/                  # Chart and visualization components
│   ├── tables/                  # Data table components
│   ├── modals/                  # Modal and dialog components
│   └── workflow/                # Workflow builder components
├── hooks/                       # Custom React hooks
├── lib/                         # Utility libraries
├── stores/                      # Zustand stores
├── types/                       # TypeScript type definitions
└── utils/                       # Utility functions
```

## 🛠️ Implementation Steps

### Step 1: Core Application Setup (Day 1-3)

#### 1.1 Next.js Configuration and Setup
```typescript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['@tanstack/react-query'],
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  webpack: (config) => {
    config.externals = [...config.externals, 'canvas', 'jsdom'];
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
```

#### 1.2 TypeScript Type Definitions
```typescript
// types/index.ts
export interface User {
  id: string;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  userType: UserType;
  permissions: UserPermissions;
  avatar?: string;
  isActive: boolean;
  lastActivity?: string;
  createdAt: string;
}

export interface UserType {
  id: string;
  name: string;
  slug: string;
  description?: string;
  isSystemDefault: boolean;
  basePermissions: Record<string, any>;
}

export interface Pipeline {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon: string;
  color: string;
  pipelineType: 'crm' | 'ats' | 'cms' | 'custom';
  fieldSchema: Record<string, FieldDefinition>;
  viewConfig: Record<string, any>;
  settings: Record<string, any>;
  isActive: boolean;
  recordCount: number;
  createdAt: string;
  updatedAt: string;
  createdBy: User;
}

export interface FieldDefinition {
  name: string;
  slug: string;
  fieldType: string;
  fieldConfig: Record<string, any>;
  isRequired: boolean;
  isUnique: boolean;
  isSearchable: boolean;
  displayOrder: number;
  width: 'quarter' | 'half' | 'full';
  isVisibleInList: boolean;
  isVisibleInDetail: boolean;
  isAiField: boolean;
  aiConfig?: Record<string, any>;
}

export interface Record {
  id: string;
  pipelineId: string;
  pipeline: Pipeline;
  data: Record<string, any>;
  title: string;
  status: string;
  createdBy: User;
  updatedBy: User;
  createdAt: string;
  updatedAt: string;
  version: number;
  aiSummary?: string;
  tags: string[];
}

export interface Relationship {
  id: string;
  relationshipType: RelationshipType;
  sourceRecord: Record;
  targetRecord: Record;
  metadata: Record<string, any>;
  strength: number;
  status: 'active' | 'inactive';
  createdAt: string;
}

export interface RelationshipType {
  id: string;
  name: string;
  slug: string;
  forwardLabel: string;
  reverseLabel: string;
  cardinality: 'one_to_one' | 'one_to_many' | 'many_to_many';
  isBidirectional: boolean;
}

export interface Dashboard {
  id: string;
  name: string;
  description?: string;
  layout: DashboardWidget[];
  isShared: boolean;
  createdBy: User;
  createdAt: string;
  updatedAt: string;
}

export interface DashboardWidget {
  id: string;
  type: 'chart' | 'metric' | 'table' | 'text';
  title: string;
  position: { x: number; y: number; w: number; h: number };
  config: Record<string, any>;
  dataSource: {
    type: 'pipeline' | 'custom';
    pipelineId?: string;
    query?: string;
  };
}

export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, any>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  data?: Record<string, any>;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  isActive: boolean;
  triggers: Record<string, any>;
  createdBy: User;
  createdAt: string;
  updatedAt: string;
}
```

#### 1.3 API Client Setup
```typescript
// lib/api-client.ts
import { GraphQLClient } from 'graphql-request';

class APIClient {
  private baseURL: string;
  private graphqlClient: GraphQLClient;
  private token: string | null = null;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.graphqlClient = new GraphQLClient(`${this.baseURL}/graphql`);
    
    // Initialize with stored token
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
      this.updateHeaders();
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
    this.updateHeaders();
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
    this.updateHeaders();
  }

  private updateHeaders() {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    this.graphqlClient.setHeaders(headers);
  }

  // REST API methods
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${this.baseURL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Authorization': this.token ? `Bearer ${this.token}` : '',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': this.token ? `Bearer ${this.token}` : '',
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PUT',
      headers: {
        'Authorization': this.token ? `Bearer ${this.token}` : '',
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'DELETE',
      headers: {
        'Authorization': this.token ? `Bearer ${this.token}` : '',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // GraphQL methods
  async graphql<T>(query: string, variables?: Record<string, any>): Promise<T> {
    try {
      return await this.graphqlClient.request<T>(query, variables);
    } catch (error) {
      console.error('GraphQL Error:', error);
      throw error;
    }
  }

  // WebSocket connection
  createWebSocket(path: string = '/ws'): WebSocket {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}${path}`;
    
    return new WebSocket(wsUrl);
  }

  // Server-Sent Events
  createEventSource(path: string): EventSource {
    const url = `${this.baseURL}${path}`;
    return new EventSource(url);
  }
}

export const apiClient = new APIClient();
```

### Step 2: State Management and Real-time Updates (Day 4-6)

#### 2.1 Zustand Stores
```typescript
// stores/auth-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '@/types';
import { apiClient } from '@/lib/api-client';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
          const response = await apiClient.post<{
            access: string;
            refresh: string;
            user: User;
          }>('/api/auth/login/', { email, password });

          apiClient.setToken(response.access);
          
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
          });

          return true;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
          });
          return false;
        }
      },

      logout: () => {
        apiClient.clearToken();
        set({
          user: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshUser: async () => {
        if (!get().isAuthenticated) return;

        try {
          const user = await apiClient.get<User>('/api/users/profile/');
          set({ user });
        } catch (error) {
          console.error('Failed to refresh user:', error);
          get().logout();
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// stores/realtime-store.ts
import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

interface RealtimeState {
  connections: Map<string, WebSocket>;
  eventSources: Map<string, EventSource>;
  isConnected: boolean;
  
  // Actions
  connect: (key: string, url: string) => void;
  disconnect: (key: string) => void;
  sendMessage: (key: string, message: any) => void;
  subscribeToEvents: (key: string, url: string) => void;
  unsubscribeFromEvents: (key: string) => void;
}

export const useRealtimeStore = create<RealtimeState>()(
  subscribeWithSelector((set, get) => ({
    connections: new Map(),
    eventSources: new Map(),
    isConnected: false,

    connect: (key: string, url: string) => {
      const { connections } = get();
      
      // Close existing connection
      const existing = connections.get(key);
      if (existing) {
        existing.close();
      }

      // Create new WebSocket connection
      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        console.log(`WebSocket connected: ${key}`);
        set({ isConnected: true });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Handle different message types
          handleRealtimeMessage(key, data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log(`WebSocket disconnected: ${key}`);
        connections.delete(key);
        set({ 
          connections: new Map(connections),
          isConnected: connections.size > 0 
        });
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error (${key}):`, error);
      };

      connections.set(key, ws);
      set({ connections: new Map(connections) });
    },

    disconnect: (key: string) => {
      const { connections } = get();
      const ws = connections.get(key);
      
      if (ws) {
        ws.close();
        connections.delete(key);
        set({ 
          connections: new Map(connections),
          isConnected: connections.size > 0 
        });
      }
    },

    sendMessage: (key: string, message: any) => {
      const { connections } = get();
      const ws = connections.get(key);
      
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    },

    subscribeToEvents: (key: string, url: string) => {
      const { eventSources } = get();
      
      // Close existing event source
      const existing = eventSources.get(key);
      if (existing) {
        existing.close();
      }

      // Create new EventSource
      const eventSource = new EventSource(url);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleRealtimeMessage(key, data);
        } catch (error) {
          console.error('Failed to parse SSE message:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error(`SSE error (${key}):`, error);
      };

      eventSources.set(key, eventSource);
      set({ eventSources: new Map(eventSources) });
    },

    unsubscribeFromEvents: (key: string) => {
      const { eventSources } = get();
      const eventSource = eventSources.get(key);
      
      if (eventSource) {
        eventSource.close();
        eventSources.delete(key);
        set({ eventSources: new Map(eventSources) });
      }
    },
  }))
);

// Handle realtime messages
function handleRealtimeMessage(key: string, data: any) {
  // This would dispatch to appropriate stores based on message type
  switch (data.type) {
    case 'record_updated':
      // Update record in pipeline store
      break;
    case 'user_presence':
      // Update presence in collaboration store
      break;
    case 'notification':
      // Add notification to notification store
      break;
    default:
      console.log('Unhandled realtime message:', data);
  }
}
```

#### 2.2 React Query Setup and Hooks
```typescript
// lib/react-query.ts
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 401/403 errors
        if (error?.status === 401 || error?.status === 403) {
          return false;
        }
        return failureCount < 3;
      },
    },
  },
});

// hooks/use-pipelines.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Pipeline } from '@/types';
import { apiClient } from '@/lib/api-client';

export function usePipelines() {
  return useQuery({
    queryKey: ['pipelines'],
    queryFn: () => apiClient.get<{ results: Pipeline[] }>('/api/pipelines/'),
    select: (data) => data.results,
  });
}

export function usePipeline(id: string) {
  return useQuery({
    queryKey: ['pipelines', id],
    queryFn: () => apiClient.get<Pipeline>(`/api/pipelines/${id}/`),
    enabled: !!id,
  });
}

export function useCreatePipeline() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: Partial<Pipeline>) =>
      apiClient.post<Pipeline>('/api/pipelines/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
    },
  });
}

export function useUpdatePipeline() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, ...data }: Partial<Pipeline> & { id: string }) =>
      apiClient.put<Pipeline>(`/api/pipelines/${id}/`, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      queryClient.invalidateQueries({ queryKey: ['pipelines', variables.id] });
    },
  });
}

// hooks/use-records.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Record as RecordType } from '@/types';
import { apiClient } from '@/lib/api-client';

interface RecordsParams {
  pipelineId: string;
  page?: number;
  pageSize?: number;
  search?: string;
  filters?: Record<string, any>;
  ordering?: string;
}

export function useRecords(params: RecordsParams) {
  return useQuery({
    queryKey: ['records', params],
    queryFn: () =>
      apiClient.get<{
        count: number;
        results: RecordType[];
        pages: number;
        currentPage: number;
      }>(`/api/pipelines/${params.pipelineId}/records/`, {
        page: params.page,
        page_size: params.pageSize,
        search: params.search,
        ordering: params.ordering,
        ...params.filters,
      }),
    enabled: !!params.pipelineId,
  });
}

export function useRecord(pipelineId: string, recordId: string) {
  return useQuery({
    queryKey: ['records', pipelineId, recordId],
    queryFn: () =>
      apiClient.get<RecordType>(`/api/pipelines/${pipelineId}/records/${recordId}/`),
    enabled: !!(pipelineId && recordId),
  });
}

export function useCreateRecord(pipelineId: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: Partial<RecordType>) =>
      apiClient.post<RecordType>(`/api/pipelines/${pipelineId}/records/`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', pipelineId] });
    },
  });
}

export function useUpdateRecord(pipelineId: string) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, ...data }: Partial<RecordType> & { id: string }) =>
      apiClient.put<RecordType>(`/api/pipelines/${pipelineId}/records/${id}/`, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['records', pipelineId] });
      queryClient.invalidateQueries({ 
        queryKey: ['records', pipelineId, variables.id] 
      });
    },
  });
}
```

### Step 3: Core UI Components (Day 7-10)

#### 3.1 Base UI Components
```tsx
// components/ui/button.tsx
import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'underline-offset-4 hover:underline text-primary',
      },
      size: {
        default: 'h-10 py-2 px-4',
        sm: 'h-9 px-3 rounded-md',
        lg: 'h-11 px-8 rounded-md',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };

// components/ui/data-table.tsx
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  SortingState,
  getFilteredRowModel,
  ColumnFiltersState,
  getPaginationRowModel,
} from '@tanstack/react-table';
import { useState } from 'react';
import { Button } from './button';
import { Input } from './input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './table';

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchKey?: string;
  searchPlaceholder?: string;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  searchKey,
  searchPlaceholder = 'Search...',
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    onColumnFiltersChange: setColumnFilters,
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      sorting,
      columnFilters,
    },
  });

  return (
    <div className="space-y-4">
      {searchKey && (
        <div className="flex items-center py-4">
          <Input
            placeholder={searchPlaceholder}
            value={(table.getColumn(searchKey)?.getFilterValue() as string) ?? ''}
            onChange={(event) =>
              table.getColumn(searchKey)?.setFilterValue(event.target.value)
            }
            className="max-w-sm"
          />
        </div>
      )}
      
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && 'selected'}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      
      <div className="flex items-center justify-end space-x-2 py-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

// components/ui/field-renderer.tsx
import { FieldDefinition } from '@/types';
import { Input } from './input';
import { Textarea } from './textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './select';
import { Checkbox } from './checkbox';
import { DatePicker } from './date-picker';
import { Badge } from './badge';

interface FieldRendererProps {
  field: FieldDefinition;
  value: any;
  onChange: (value: any) => void;
  disabled?: boolean;
  error?: string;
}

export function FieldRenderer({
  field,
  value,
  onChange,
  disabled = false,
  error,
}: FieldRendererProps) {
  const renderField = () => {
    switch (field.fieldType) {
      case 'text':
      case 'email':
      case 'url':
        return (
          <Input
            type={field.fieldType === 'email' ? 'email' : field.fieldType === 'url' ? 'url' : 'text'}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.fieldConfig.placeholder}
            disabled={disabled}
            required={field.isRequired}
          />
        );

      case 'textarea':
        return (
          <Textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.fieldConfig.placeholder}
            disabled={disabled}
            required={field.isRequired}
            rows={field.fieldConfig.rows || 3}
          />
        );

      case 'number':
      case 'decimal':
        return (
          <Input
            type="number"
            value={value || ''}
            onChange={(e) => onChange(parseFloat(e.target.value) || null)}
            placeholder={field.fieldConfig.placeholder}
            disabled={disabled}
            required={field.isRequired}
            min={field.fieldConfig.minValue}
            max={field.fieldConfig.maxValue}
            step={field.fieldConfig.step}
          />
        );

      case 'boolean':
        return (
          <Checkbox
            checked={!!value}
            onCheckedChange={onChange}
            disabled={disabled}
          />
        );

      case 'date':
      case 'datetime':
        return (
          <DatePicker
            value={value ? new Date(value) : undefined}
            onChange={(date) => onChange(date?.toISOString())}
            disabled={disabled}
            showTime={field.fieldType === 'datetime'}
          />
        );

      case 'select':
        return (
          <Select value={value} onValueChange={onChange} disabled={disabled}>
            <SelectTrigger>
              <SelectValue placeholder={field.fieldConfig.placeholder} />
            </SelectTrigger>
            <SelectContent>
              {field.fieldConfig.options?.map((option: any) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case 'multiselect':
        return (
          <div className="space-y-2">
            {field.fieldConfig.options?.map((option: any) => (
              <div key={option.value} className="flex items-center space-x-2">
                <Checkbox
                  checked={Array.isArray(value) && value.includes(option.value)}
                  onCheckedChange={(checked) => {
                    const currentValues = Array.isArray(value) ? value : [];
                    if (checked) {
                      onChange([...currentValues, option.value]);
                    } else {
                      onChange(currentValues.filter((v: any) => v !== option.value));
                    }
                  }}
                  disabled={disabled}
                />
                <label className="text-sm">{option.label}</label>
              </div>
            ))}
          </div>
        );

      case 'ai_summary':
      case 'ai_sentiment':
      case 'ai_classification':
        return (
          <div className="space-y-2">
            <div className="p-3 bg-muted rounded-md">
              <div className="flex items-center space-x-2 mb-2">
                <Badge variant="secondary">AI Generated</Badge>
                {field.isAiField && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {/* Trigger AI regeneration */}}
                    disabled={disabled}
                  >
                    Regenerate
                  </Button>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                {value || 'AI analysis will appear here...'}
              </p>
            </div>
          </div>
        );

      default:
        return (
          <Input
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          />
        );
    }
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">
        {field.name}
        {field.isRequired && <span className="text-red-500 ml-1">*</span>}
      </label>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
      {renderField()}
      {error && <p className="text-xs text-red-500">{error}</p>}
      {field.helpText && !error && (
        <p className="text-xs text-muted-foreground">{field.helpText}</p>
      )}
    </div>
  );
}
```

## 📱 Enhanced Communication Interface Components

### Communication Hub Architecture
Building on the existing frontend architecture, we need sophisticated communication management interfaces that integrate with the enhanced Phase 8 Communication system.

```typescript
// Enhanced app directory structure for communications
app/(dashboard)/communications/
├── page.tsx                 # Main communications dashboard
├── inbox/
│   ├── page.tsx            # Unified inbox across all channels
│   └── [conversationId]/
│       └── page.tsx        # Individual conversation view
├── channels/
│   ├── page.tsx            # Channel management
│   └── connect/
│       └── page.tsx        # Channel connection wizard
├── sequences/
│   ├── page.tsx            # Sequence management (workflow-based)
│   ├── create/
│   │   └── page.tsx        # Create new sequence workflow
│   └── [sequenceId]/
│       └── page.tsx        # Sequence detail/edit
└── analytics/
    └── page.tsx            # Communication analytics dashboard
```

### Enhanced Type Definitions for Communications
```typescript
// Add to types/index.ts
export interface Channel {
  id: string;
  name: string;
  channelType: 'email' | 'whatsapp' | 'linkedin' | 'sms' | 'slack';
  authStatus: 'connected' | 'disconnected' | 'error';
  unipileAccountId?: string;
  providerName: string;
  isActive: boolean;
  isDefault: boolean;
  rateLimitPerHour: number;
  lastSyncAt?: string;
  connectedBy: User;
  canSendMessages: boolean;
}

export interface Conversation {
  id: string;
  subject?: string;
  channel: Channel;
  participants: ConversationParticipant[];
  primaryContact?: Record;
  status: 'active' | 'archived' | 'closed';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  sentiment?: 'positive' | 'negative' | 'neutral';
  sentimentScore?: number;
  intent?: string;
  lastMessageAt?: string;
  messageCount: number;
  assignedTo?: User;
  assignedAt?: string;
  messages: Message[];
  relatedContacts: Record[];
}

export interface Message {
  id: string;
  conversationId: string;
  content: string;
  contentType: 'text' | 'html' | 'markdown';
  direction: 'inbound' | 'outbound';
  messageType: 'message' | 'reply' | 'forward';
  senderEmail?: string;
  senderName?: string;
  recipientInfo: Record<string, any>;
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
  sentAt?: string;
  deliveredAt?: string;
  readAt?: string;
  sentiment?: string;
  intent?: string;
  attachments: MessageAttachment[];
  relatedContacts: Record[];
  createdAt: string;
}

export interface ConversationParticipant {
  email?: string;
  name?: string;
  phone?: string;
  role?: string;
}

export interface MessageAttachment {
  id: string;
  filename: string;
  contentType: string;
  size: number;
  url: string;
}

export interface CommunicationTimeline {
  type: 'message' | 'call' | 'meeting' | 'note';
  id: string;
  timestamp: string;
  direction?: 'inbound' | 'outbound';
  content: string;
  channel?: string;
  status?: string;
  sender?: string;
  conversationId?: string;
}
```

### Core Communication Components
```tsx
// components/communications/unified-inbox.tsx
export function UnifiedInbox() {
  // Unified view of all conversations across channels
  // Real-time message updates via WebSocket
  // Conversation filtering and search
  // Quick reply functionality
  // Assignment management
  // Contact context sidebar
}

// components/communications/conversation-view.tsx
export function ConversationView({ conversationId }: { conversationId: string }) {
  // Full conversation thread with message history
  // Real-time message updates and typing indicators
  // Rich text message composition
  // Contact sidebar with record information
  // Communication timeline integration
  // AI-powered response suggestions
}

// components/communications/contact-timeline.tsx
export function ContactTimeline({ contactId }: { contactId: string }) {
  // Chronological view of all communications with contact
  // Cross-channel message threading
  // Integration with record detail pages
  // Quick communication actions
  // Communication context and metadata
  // Sentiment and engagement tracking
}

// components/communications/channel-manager.tsx
export function ChannelManager() {
  // List of connected channels with status
  // Channel connection wizard (UniPile integration)
  // Sync status and manual sync controls
  // Channel-specific settings and rate limits
  // Authentication status management
}

// components/communications/message-composer.tsx
export function MessageComposer({
  conversationId,
  defaultChannel,
  recipientRecord,
  onSend
}: {
  conversationId?: string;
  defaultChannel?: Channel;
  recipientRecord?: Record;
  onSend: (message: any) => void;
}) {
  // Rich text message composition with mentions
  // Channel selection and switching
  // Template insertion and AI assistance
  // Attachment handling and file uploads
  // Send scheduling and delayed delivery
  // Real-time collaboration features
}
```

### Record Integration Components
```tsx
// Enhanced components/records/record-detail.tsx
export function RecordCommunicationTab({ record }: { record: Record }) {
  return (
    <div className="space-y-6">
      {/* Communication Timeline */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-semibold mb-4">Communication History</h3>
        <ContactTimeline contactId={record.id} />
      </div>
      
      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2">
        <Button 
          onClick={() => openMessageComposer('email', record)}
          className="flex items-center gap-2"
        >
          <MailIcon size={16} />
          Send Email
        </Button>
        <Button 
          onClick={() => openMessageComposer('linkedin', record)}
          variant="outline"
          className="flex items-center gap-2"
        >
          <LinkedinIcon size={16} />
          LinkedIn Message
        </Button>
        <Button 
          onClick={() => openMessageComposer('whatsapp', record)}
          variant="outline"
          className="flex items-center gap-2"
        >
          <MessageCircleIcon size={16} />
          WhatsApp
        </Button>
        <Button 
          onClick={() => openMessageComposer('sms', record)}
          variant="outline"
          className="flex items-center gap-2"
        >
          <PhoneIcon size={16} />
          SMS
        </Button>
      </div>
      
      {/* Communication Stats */}
      <CommunicationStats contactId={record.id} />
      
      {/* Recent Conversations */}
      <RecentConversations contactId={record.id} />
    </div>
  );
}

// components/communications/communication-stats.tsx
export function CommunicationStats({ contactId }: { contactId: string }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-blue-50 p-4 rounded-lg">
        <div className="text-2xl font-bold text-blue-600">24</div>
        <div className="text-sm text-gray-600">Total Messages</div>
      </div>
      <div className="bg-green-50 p-4 rounded-lg">
        <div className="text-2xl font-bold text-green-600">85%</div>
        <div className="text-sm text-gray-600">Response Rate</div>
      </div>
      <div className="bg-purple-50 p-4 rounded-lg">
        <div className="text-2xl font-bold text-purple-600">2.3h</div>
        <div className="text-sm text-gray-600">Avg Response Time</div>
      </div>
      <div className="bg-orange-50 p-4 rounded-lg">
        <div className="text-2xl font-bold text-orange-600">Positive</div>
        <div className="text-sm text-gray-600">Overall Sentiment</div>
      </div>
    </div>
  );
}
```

### Real-time Communication Hooks
```typescript
// hooks/use-communications.ts
export function useConversations(filters?: ConversationFilters) {
  return useQuery({
    queryKey: ['conversations', filters],
    queryFn: () => apiClient.get('/api/communications/conversations/', filters),
    // Real-time subscription for live updates
  });
}

export function useConversation(conversationId: string) {
  // Individual conversation with real-time messages
  // WebSocket integration for live updates
  // Typing indicators and read receipts
  // Optimistic UI updates for sent messages
}

export function useContactCommunications(contactId: string) {
  return useQuery({
    queryKey: ['contact-communications', contactId],
    queryFn: () => apiClient.get(`/api/pipelines/records/${contactId}/communication-timeline/`),
    enabled: !!contactId,
  });
}

// hooks/use-realtime-messages.ts
export function useRealtimeMessages(conversationId: string) {
  const { connections, connect, disconnect, sendMessage } = useRealtimeStore();
  
  useEffect(() => {
    if (conversationId) {
      connect('conversation', `/ws/conversations/${conversationId}/`);
      return () => disconnect('conversation');
    }
  }, [conversationId, connect, disconnect]);
  
  const sendRealtimeMessage = useCallback((content: string) => {
    sendMessage('conversation', {
      type: 'message.send',
      content,
      conversationId
    });
  }, [conversationId, sendMessage]);
  
  return { sendRealtimeMessage };
}
```

### Communication Analytics Dashboard
```tsx
// components/communications/analytics-dashboard.tsx
export function CommunicationAnalytics() {
  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Messages Sent" value="1,234" change="+12%" />
        <MetricCard title="Response Rate" value="68%" change="+5%" />
        <MetricCard title="Avg Response Time" value="2.4h" change="-15%" />
        <MetricCard title="Active Conversations" value="45" change="+8%" />
      </div>
      
      {/* Channel Performance Chart */}
      <div className="bg-white p-6 rounded-lg border">
        <h3 className="text-lg font-semibold mb-4">Channel Performance</h3>
        <ChannelPerformanceChart />
      </div>
      
      {/* Communication Trends */}
      <div className="bg-white p-6 rounded-lg border">
        <h3 className="text-lg font-semibold mb-4">Communication Trends</h3>
        <CommunicationTrendsChart />
      </div>
      
      {/* Sentiment Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border">
          <h3 className="text-lg font-semibold mb-4">Sentiment Analysis</h3>
          <SentimentAnalysisChart />
        </div>
        <div className="bg-white p-6 rounded-lg border">
          <h3 className="text-lg font-semibold mb-4">Top Contacts</h3>
          <TopCommunicatingContacts />
        </div>
      </div>
    </div>
  );
}
```

### Enhanced Dependencies for Communication Features
```json
{
  "dependencies": {
    // Existing dependencies from above...
    
    // Communication-specific additions
    "@emoji-mart/react": "^1.1.0",
    "react-mentions": "^4.4.0",
    "react-linkify": "^1.0.0",
    "react-use-websocket": "^4.8.0",
    "emoji-picker-react": "^4.8.0",
    
    // Rich text editing for message composition
    "@tiptap/react": "^2.1.0",
    "@tiptap/starter-kit": "^2.1.0",
    "@tiptap/extension-link": "^2.1.0",
    "@tiptap/extension-mention": "^2.1.0",
    "@tiptap/extension-placeholder": "^2.1.0",
    
    // File handling and attachments
    "react-dropzone": "^14.2.0",
    "file-saver": "^2.0.0",
    
    // Audio/Video capabilities (future enhancement)
    "react-mic": "^12.4.0",
    "recordrtc": "^5.6.0",
    
    // Push notifications
    "web-push": "^3.6.0"
  }
}
```

### Mobile-First Communication Interface
```tsx
// Mobile-optimized communication components
// components/communications/mobile-conversation.tsx
export function MobileConversationView() {
  // Swipe gestures for message actions
  // Pull-to-refresh for message sync
  // Optimized virtual scrolling
  // Touch-friendly message composition
  // Voice message recording (future)
}

// components/communications/mobile-inbox.tsx
export function MobileInbox() {
  // Swipe-based conversation management
  // Quick reply from notification
  // Offline message composition
  // Push notification integration
}
```

### Integration with Main Dashboard
```tsx
// Enhanced dashboard components with communication widgets
// components/dashboard/communication-widget.tsx
export function CommunicationWidget() {
  return (
    <div className="bg-white p-6 rounded-lg border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Recent Communications</h3>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/communications">View All</Link>
        </Button>
      </div>
      
      {/* Unread message count */}
      <div className="mb-4">
        <div className="text-2xl font-bold text-blue-600">12</div>
        <div className="text-sm text-gray-600">Unread Messages</div>
      </div>
      
      {/* Recent conversations */}
      <div className="space-y-2">
        {/* Conversation previews */}
      </div>
    </div>
  );
}
```

## 🎯 Communication Interface Success Criteria

### User Experience Excellence
- ✅ **Unified inbox** across all communication channels (email, LinkedIn, WhatsApp, SMS)
- ✅ **Real-time message updates** with <100ms latency via WebSocket
- ✅ **Mobile-first responsive design** with touch-optimized interactions
- ✅ **Offline message composition** with automatic sync when online
- ✅ **Contextual contact information** displayed in all communication views

### Seamless CRM Integration
- ✅ **Automatic contact record linking** for all incoming/outgoing messages
- ✅ **Communication timeline** embedded in contact record details
- ✅ **Cross-channel conversation threading** for complete conversation history
- ✅ **AI-powered message insights** (sentiment, intent, suggested responses)
- ✅ **Workflow-driven sequences** replacing traditional email campaigns

### Performance & Scalability
- ✅ **Virtual scrolling** for large conversation histories (10k+ messages)
- ✅ **Lazy loading** with intelligent preloading of recent conversations
- ✅ **Optimistic UI updates** for immediate user feedback
- ✅ **Efficient WebSocket connection management** with automatic reconnection
- ✅ **Smart caching strategy** balancing freshness and performance

This comprehensive communication interface transforms the frontend into a true unified communication hub, where every message is automatically linked to CRM records and provides complete visibility into customer relationships across all channels.