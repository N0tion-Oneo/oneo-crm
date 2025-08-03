'use client'

import React from 'react'
import { usePermissions } from '@/hooks/usePermissions'
import { Shield, CheckCircle, XCircle, Info, Users, Database, Settings } from 'lucide-react'

/**
 * Demo component showcasing enhanced permission system capabilities
 * This demonstrates the integration between static and dynamic permissions
 */
export function PermissionDemo() {
  const {
    // Traditional permission functions
    canCreateUsers,
    canManageSettings,
    isSystemAdmin,
    
    // Enhanced dynamic functions
    getAvailableActions,
    isCategoryAvailable,
    getDynamicResourcePermissions,
    hasPipelinePermission,
    hasWorkflowPermission,
    getAccessiblePipelines,
    getExecutableWorkflows,
    getPermissionSummary,
    getCategoryPermissions,
    
    // Schema helpers
    frontendConfig,
    user
  } = usePermissions()

  const summary = getPermissionSummary
  const userPermissions = getCategoryPermissions('users')
  const pipelinePermissions = getCategoryPermissions('pipelines')
  
  const accessiblePipelines = getAccessiblePipelines()
  const executableWorkflows = getExecutableWorkflows()
  const dynamicResources = getDynamicResourcePermissions()

  return (
    <div className="space-y-6 p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center space-x-2">
        <Shield className="h-5 w-5 text-blue-500" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Enhanced Permission System Demo
        </h3>
      </div>

      {/* Permission Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-600 dark:text-blue-400">Total Categories</p>
              <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">{summary.totalCategories}</p>
            </div>
            <Database className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-600 dark:text-green-400">Dynamic Resources</p>
              <p className="text-2xl font-bold text-green-900 dark:text-green-100">{summary.dynamicResources}</p>
            </div>
            <Settings className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-purple-600 dark:text-purple-400">Total Permissions</p>
              <p className="text-2xl font-bold text-purple-900 dark:text-purple-100">{summary.totalPermissions}</p>
            </div>
            <Users className="h-8 w-8 text-purple-500" />
          </div>
        </div>

        <div className="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-600 dark:text-orange-400">Access Level</p>
              <p className="text-lg font-bold text-orange-900 dark:text-orange-100">
                {summary.hasSystemAccess ? 'System Admin' : summary.hasAdminAccess ? 'Admin' : 'User'}
              </p>
            </div>
            <Shield className="h-8 w-8 text-orange-500" />
          </div>
        </div>
      </div>

      {/* Traditional vs Enhanced Permission Checks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Traditional Static Permissions */}
        <div className="space-y-4">
          <h4 className="text-md font-semibold text-gray-900 dark:text-white flex items-center">
            <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
            Static Permissions
          </h4>
          
          <div className="space-y-2">
            <PermissionCheck 
              label="Can Create Users" 
              hasPermission={canCreateUsers()} 
            />
            <PermissionCheck 
              label="Can Manage Settings" 
              hasPermission={canManageSettings()} 
            />
            <PermissionCheck 
              label="Is System Admin" 
              hasPermission={isSystemAdmin()} 
            />
          </div>

          {/* Category Details */}
          <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded">
            <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-2">User Category Analysis</h5>
            <div className="text-sm space-y-1">
              <div>Available Actions: {userPermissions.availableActions.join(', ')}</div>
              <div>User Actions: {userPermissions.userPermissions.join(', ')}</div>
              <div className="flex items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                  userPermissions.hasFullAccess ? 'bg-green-500' : 
                  userPermissions.hasPartialAccess ? 'bg-yellow-500' : 'bg-red-500'
                }`}></span>
                Access Level: {
                  userPermissions.hasFullAccess ? 'Full' : 
                  userPermissions.hasPartialAccess ? 'Partial' : 'None'
                }
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic Resource Permissions */}
        <div className="space-y-4">
          <h4 className="text-md font-semibold text-gray-900 dark:text-white flex items-center">
            <Database className="h-4 w-4 mr-2 text-blue-500" />
            Dynamic Resources
          </h4>

          <div className="space-y-2">
            <div className="text-sm">
              <strong>Accessible Pipelines:</strong> {accessiblePipelines.length}
            </div>
            {accessiblePipelines.slice(0, 3).map((pipeline, index) => (
              <PermissionCheck
                key={index}
                label={`Pipeline: ${pipeline.data.metadata?.pipeline_name || 'Unknown'}`}
                hasPermission={hasPipelinePermission(pipeline.data.resource_id!, 'read')}
              />
            ))}
          </div>

          <div className="space-y-2">
            <div className="text-sm">
              <strong>Executable Workflows:</strong> {executableWorkflows.length}
            </div>
            {executableWorkflows.slice(0, 3).map((workflow, index) => (
              <PermissionCheck
                key={index}
                label={`Workflow: ${workflow.data.metadata?.workflow_name || 'Unknown'}`}
                hasPermission={hasWorkflowPermission(workflow.data.resource_id!, 'execute')}
              />
            ))}
          </div>

          {/* Dynamic Resources Summary */}
          <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded">
            <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-2">Resource Breakdown</h5>
            <div className="text-sm space-y-1">
              {Object.entries(
                dynamicResources.reduce((acc, resource) => {
                  const type = resource.data.resource_type || 'unknown'
                  acc[type] = (acc[type] || 0) + 1
                  return acc
                }, {} as Record<string, number>)
              ).map(([type, count]) => (
                <div key={type} className="flex justify-between">
                  <span className="capitalize">{type}s:</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Schema Information */}
      <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
        <h4 className="text-md font-semibold text-blue-900 dark:text-blue-100 flex items-center mb-3">
          <Info className="h-4 w-4 mr-2" />
          Schema Information
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <strong>Tenant:</strong> {frontendConfig?.tenant_info?.name || 'Unknown'}
          </div>
          <div>
            <strong>Schema:</strong> {frontendConfig?.tenant_info?.schema_name || 'Unknown'}
          </div>
          <div>
            <strong>Static Categories:</strong> {summary.staticCategories}
          </div>
          <div>
            <strong>Cache Status:</strong> {frontendConfig?.cached ? 'Cached' : 'Fresh'}
          </div>
        </div>
      </div>

      {/* Example API Usage */}
      <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
        <h4 className="text-md font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Example Usage
        </h4>
        <pre className="text-xs bg-white dark:bg-gray-800 p-3 rounded border overflow-x-auto">
{`// Traditional static permission check
const canCreate = canCreateUsers()

// Enhanced dynamic resource check  
const canAccessPipeline = hasPipelinePermission(123, 'read')

// Get available actions for validation
const actions = getAvailableActions('users')

// Check if category exists in schema
const exists = isCategoryAvailable('custom_category')

// Get accessible resources
const pipelines = getAccessiblePipelines()
const workflows = getExecutableWorkflows()`}
        </pre>
      </div>
    </div>
  )
}

interface PermissionCheckProps {
  label: string
  hasPermission: boolean
}

function PermissionCheck({ label, hasPermission }: PermissionCheckProps) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
      <div className="flex items-center">
        {hasPermission ? (
          <CheckCircle className="h-4 w-4 text-green-500" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500" />
        )}
      </div>
    </div>
  )
}

export default PermissionDemo