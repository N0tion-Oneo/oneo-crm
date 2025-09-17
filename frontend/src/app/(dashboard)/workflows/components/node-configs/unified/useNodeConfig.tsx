/**
 * Hook to fetch node configuration
 * First checks frontend registry for nodes with custom logic, then uses backend schemas
 * Re-exported from ConfigProvider to maintain consistency
 */

export { useNodeConfig } from './ConfigProvider';

// Old implementation kept for reference but not used
import { useState, useEffect } from 'react';
import { WorkflowNodeType } from '../../../types';
import { UnifiedNodeConfig } from './types';
import { workflowSchemaService } from '@/services/workflowSchemaService';
import { nodeConfigRegistry } from './registry';

function useNodeConfigOld(nodeType: WorkflowNodeType) {
  const [config, setConfig] = useState<UnifiedNodeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadConfig() {
      if (!nodeType) {
        setConfig(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // First check frontend registry
        const frontendConfig = nodeConfigRegistry[nodeType];

        if (frontendConfig) {
          console.log(`Using frontend config for ${nodeType}`);
          if (!cancelled) {
            setConfig(frontendConfig);
            setLoading(false);
          }
          return;
        }

        // Fall back to backend if not found in frontend
        console.log(`No frontend config for ${nodeType}, fetching from backend`);
        const nodeConfig = await workflowSchemaService.getNodeConfig(nodeType);

        if (!cancelled) {
          if (nodeConfig) {
            setConfig(nodeConfig);
          } else {
            setError(`No configuration found for node type: ${nodeType}`);
            setConfig(null);
          }
        }
      } catch (err) {
        if (!cancelled) {
          console.error(`Failed to load config for ${nodeType}:`, err);
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