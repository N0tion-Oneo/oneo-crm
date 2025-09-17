/**
 * ConfigProvider - Uses backend schemas as the single source of truth
 * No fallbacks, no frontend configs - just backend schemas with widget system
 */

import { useState, useEffect, useCallback } from 'react';
import { WorkflowNodeType } from '../../../types';
import { UnifiedNodeConfig } from './types';
import { workflowSchemaService } from '@/services/workflowSchemaService';

interface ConfigProviderProps {
  nodeType: WorkflowNodeType;
  children: (config: UnifiedNodeConfig | null, loading: boolean, error: string | null) => React.ReactNode;
}

export function ConfigProvider({ nodeType, children }: ConfigProviderProps) {
  const [config, setConfig] = useState<UnifiedNodeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadConfig() {
      if (!nodeType) {
        setConfig(null);
        setLoading(false);
        setError('No node type provided');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        console.log(`Loading ${nodeType} config from backend...`);
        const nodeConfig = await workflowSchemaService.getNodeConfig(nodeType);

        if (nodeConfig) {
          console.log(`✅ Loaded ${nodeType} from backend schema`);
          setConfig(nodeConfig);
        } else {
          throw new Error(`No backend schema found for node type: ${nodeType}`);
        }
      } catch (err) {
        console.error(`Failed to load config for ${nodeType}:`, err);
        setError(err instanceof Error ? err.message : 'Failed to load configuration');
        setConfig(null);
      } finally {
        setLoading(false);
      }
    }

    loadConfig();
  }, [nodeType]);

  return <>{children(config, loading, error)}</>;
}

/**
 * Hook to use node config from backend schemas
 */
export function useNodeConfig(nodeType: WorkflowNodeType) {
  const [config, setConfig] = useState<UnifiedNodeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadConfig() {
      if (!nodeType) {
        setConfig(null);
        setLoading(false);
        setError('No node type provided');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const nodeConfig = await workflowSchemaService.getNodeConfig(nodeType);

        if (!cancelled) {
          if (nodeConfig) {
            setConfig(nodeConfig);
          } else {
            setError(`No backend schema found for ${nodeType}`);
            setConfig(null);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load configuration');
          setConfig(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadConfig();

    return () => {
      cancelled = true;
    };
  }, [nodeType]);

  return { config, loading, error };
}

/**
 * Get status of node config system
 */
export function getNodeConfigStatus() {
  return {
    source: 'backend',
    message: 'Using backend schemas as single source of truth'
  };
}