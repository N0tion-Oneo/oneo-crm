/**
 * Shared hook for fetching entity data with caching
 */

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';

interface CacheEntry {
  data: any;
  timestamp: number;
}

// Global cache for entity data
const entityCache = new Map<string, CacheEntry>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export interface UseEntityDataOptions {
  endpoint?: string;
  enabled?: boolean;
  cacheTTL?: number;
  transform?: (data: any) => any;
  dependencies?: any[];
}

export function useEntityData(
  entityType: 'pipelines' | 'users' | 'workflows' | 'userTypes' | 'fields',
  options: UseEntityDataOptions = {}
) {
  const {
    endpoint,
    enabled = true,
    cacheTTL = CACHE_TTL,
    transform,
    dependencies = []
  } = options;

  const [data, setData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Determine the API endpoint
  const getEndpoint = () => {
    if (endpoint) return endpoint;

    switch (entityType) {
      case 'pipelines':
        return '/api/v1/pipelines/';
      case 'users':
        return '/api/v1/auth/users/';
      case 'workflows':
        return '/api/v1/workflows/';
      case 'userTypes':
        return '/api/v1/auth/user-types/';
      case 'fields':
        return '/api/v1/pipelines/fields/';
      default:
        return null;
    }
  };

  useEffect(() => {
    if (!enabled) return;

    const fetchData = async () => {
      const apiEndpoint = getEndpoint();
      if (!apiEndpoint) {
        setError(`No endpoint configured for entity type: ${entityType}`);
        return;
      }

      const cacheKey = `${entityType}:${apiEndpoint}:${JSON.stringify(dependencies)}`;

      // Check cache first
      const cached = entityCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < cacheTTL) {
        setData(cached.data);
        return;
      }

      // Cancel previous request if any
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller
      abortControllerRef.current = new AbortController();

      setIsLoading(true);
      setError(null);

      try {
        const response = await api.get(apiEndpoint, {
          signal: abortControllerRef.current.signal
        });

        let responseData = response.data;

        // Handle paginated responses
        if (responseData.results && Array.isArray(responseData.results)) {
          responseData = responseData.results;
        }

        // Transform data if needed
        if (transform) {
          responseData = transform(responseData);
        }

        // Update cache
        entityCache.set(cacheKey, {
          data: responseData,
          timestamp: Date.now()
        });

        setData(responseData);
      } catch (err: any) {
        // Don't log or set error for canceled requests (happens on unmount)
        if (err.name !== 'CanceledError' && err.name !== 'AbortError' && err.code !== 'ERR_CANCELED') {
          console.error(`Error fetching ${entityType}:`, err);
          setError(err.message || `Failed to fetch ${entityType}`);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();

    // Cleanup
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [enabled, entityType, ...dependencies]);

  return { data, isLoading, error, refetch: () => entityCache.clear() };
}

/**
 * Hook for fetching pipeline fields
 */
export function usePipelineFields(pipelineId?: string | string[]) {
  const pipelineIds = Array.isArray(pipelineId) ? pipelineId : [pipelineId].filter(Boolean);

  return useEntityData('fields', {
    endpoint: pipelineIds.length > 0 ? `/api/v1/pipelines/${pipelineIds[0]}/fields/` : undefined,
    enabled: pipelineIds.length > 0,
    dependencies: [pipelineId]
  });
}

/**
 * Clear entity cache (useful when data is updated)
 */
export function clearEntityCache(entityType?: string) {
  if (entityType) {
    // Clear specific entity type
    for (const [key] of entityCache) {
      if (key.startsWith(`${entityType}:`)) {
        entityCache.delete(key);
      }
    }
  } else {
    // Clear all cache
    entityCache.clear();
  }
}