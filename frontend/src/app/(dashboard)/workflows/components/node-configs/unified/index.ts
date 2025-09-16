// Main exports for the unified configuration system
export { UnifiedConfigRenderer } from './UnifiedConfigRenderer';
export { getNodeConfig, hasNodeConfig, getAllNodeConfigs, getNodeConfigsByCategory } from './registry';
export type { UnifiedNodeConfig, ConfigSection, ConfigField, NodeConfigComponentProps } from './types';