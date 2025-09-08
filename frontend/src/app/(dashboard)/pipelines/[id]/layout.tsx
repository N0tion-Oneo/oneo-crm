/**
 * Pipeline Detail Layout
 * 
 * ✅ This is the ACTIVE pipeline configuration sidebar component
 * 
 * This layout renders the configuration navigation sidebar for individual pipeline pages
 * (Overview, Field Configuration, Business Rules, etc.)
 * 
 * The navigation items are filtered based on user permissions:
 * - Field Configuration: Only shown if user has field permissions
 * - Business Rules: Only shown if user has business_rules permissions  
 * - Duplicate Management: Only shown if user has duplicates permissions
 * 
 * NOTE: There are unused components (config-sections-sidebar.tsx and pipeline-config-wrapper.tsx)
 * in /src/components/pipelines/layout/ that appear to be orphaned code from an incomplete
 * refactoring. This layout.tsx file is the actual working implementation.
 */

"use client";

import React, { ReactNode, useEffect, useState } from "react";
import { useRouter, usePathname, useParams } from "next/navigation";
import {
  BarChart3,
  Settings,
  Database,
  FileText,
  Copy,
  TrendingUp,
  FileDown,
  History,
  ChevronRight,
  ArrowLeft
} from "lucide-react";
import { cn } from "@/lib/utils";
import { pipelinesApi } from '@/lib/api';
import { useAuth } from '@/features/auth/context';

const navigationItems = [
  { 
    name: 'Overview', 
    href: (id: string) => `/pipelines/${id}`, 
    icon: BarChart3,
    description: 'Pipeline statistics and quick actions'
  },
  { 
    name: 'General Settings', 
    href: (id: string) => `/pipelines/${id}/settings`, 
    icon: Settings,
    description: 'Basic configuration and display options'
  },
  { 
    name: 'Field Configuration', 
    href: (id: string) => `/pipelines/${id}/fields`, 
    icon: Database,
    description: 'Manage pipeline fields and data structure'
  },
  { 
    name: 'Business Rules', 
    href: (id: string) => `/pipelines/${id}/business-rules`, 
    icon: FileText,
    description: 'Configure validation and automation rules'
  },
  { 
    name: 'Duplicate Management', 
    href: (id: string) => `/pipelines/${id}/duplicates`, 
    icon: Copy,
    description: 'Set up duplicate detection and merging'
  },
  { 
    name: 'Analytics', 
    href: (id: string) => `/pipelines/${id}/analytics`, 
    icon: TrendingUp,
    description: 'View pipeline performance and metrics'
  },
  { 
    name: 'Import/Export', 
    href: (id: string) => `/pipelines/${id}/import-export`, 
    icon: FileDown,
    description: 'Import data or export configuration'
  },
  { 
    name: 'Activity Log', 
    href: (id: string) => `/pipelines/${id}/activity`, 
    icon: History,
    description: 'View pipeline change history'
  }
];

export default function PipelineDetailLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams();
  const { hasPermission } = useAuth();
  const pipelineId = params.id as string;
  const [pipeline, setPipeline] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  // Check permissions
  const canUpdatePipelines = hasPermission('pipelines', 'update');
  
  // Check field permissions - only show config if user has manage or delete permissions
  // Users with only 'read' permission should NOT see the Field Configuration section
  const hasFieldPermissions = 
    hasPermission('fields', 'manage') ||
    hasPermission('fields', 'delete');
    
  // Check business rules permissions
  const hasBusinessRulesPermissions = 
    hasPermission('business_rules', 'read') ||
    hasPermission('business_rules', 'create') ||
    hasPermission('business_rules', 'update') ||
    hasPermission('business_rules', 'delete');
    
  // Check duplicate permissions
  const hasDuplicatePermissions = 
    hasPermission('duplicates', 'read') ||
    hasPermission('duplicates', 'create') ||
    hasPermission('duplicates', 'update') ||
    hasPermission('duplicates', 'delete') ||
    hasPermission('duplicates', 'resolve') ||
    hasPermission('duplicates', 'detect');
  
  // Check if we're on the records page - if so, don't show the sidebar
  const isRecordsPage = pathname.endsWith('/records');
  
  // Load pipeline details - MUST be before any conditional returns
  useEffect(() => {
    const loadPipeline = async () => {
      if (!pipelineId) return;
      
      try {
        setLoading(true);
        const response = await pipelinesApi.get(pipelineId);
        setPipeline(response.data);
      } catch (error) {
        console.error('Failed to load pipeline:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPipeline();
  }, [pipelineId]);

  // Determine active section
  const getActiveSection = () => {
    const pathSegments = pathname.split('/');
    if (pathSegments.length === 3) return 'overview'; // /pipelines/[id]
    return pathSegments[3]; // /pipelines/[id]/section
  };

  const activeSection = getActiveSection();
  
  // If user doesn't have update permission OR we're on records page, don't show configuration sidebar
  if (!canUpdatePipelines || isRecordsPage) {
    // Just render children without the configuration sidebar
    return <>{children}</>;
  }

  return (
    <div className="flex h-full">
      {/* Secondary Sidebar - Configuration Sections */}
      <div className="w-72 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <div className="p-4">
          <div className="flex items-center gap-2 mb-1">
            <ChevronRight className="h-4 w-4 text-gray-400" />
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Pipeline Configuration
            </h3>
          </div>
          {loading ? (
            <div className="animate-pulse">
              <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
            </div>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {pipeline?.name || 'Loading...'}
              </h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {pipeline?.pipeline_type || 'Custom'} Pipeline • {pipeline?.record_count || 0} records
              </p>
            </>
          )}
        </div>
        
        <nav className="px-3 pb-3">
          <div className="space-y-1">
            {/* Configuration Section Navigation */}
            {navigationItems.filter((item) => {
              // Filter out items based on permissions
              if (item.name === 'Field Configuration' && !hasFieldPermissions) return false;
              if (item.name === 'Business Rules' && !hasBusinessRulesPermissions) return false;
              if (item.name === 'Duplicate Management' && !hasDuplicatePermissions) return false;
              return true;
            }).map((item) => {
              const href = item.href(pipelineId);
              const isActive = 
                (item.name === 'Overview' && pathname === `/pipelines/${pipelineId}`) ||
                (item.name !== 'Overview' && pathname === href);
              const Icon = item.icon;
              
              return (
                <button
                  key={item.name}
                  onClick={() => router.push(href)}
                  className={cn(
                    "w-full group flex items-start gap-3 px-3 py-2.5 text-sm rounded-lg transition-colors",
                    isActive
                      ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  )}
                >
                  <Icon className={cn(
                    "mt-0.5 h-5 w-5 flex-shrink-0",
                    isActive 
                      ? "text-blue-600 dark:text-blue-400" 
                      : "text-gray-400 dark:text-gray-500"
                  )} />
                  <div className="text-left">
                    <div className={cn(
                      "font-medium",
                      isActive 
                        ? "text-blue-600 dark:text-blue-400" 
                        : "text-gray-900 dark:text-white"
                    )}>
                      {item.name}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {item.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </nav>

        {/* Quick Stats */}
        {!loading && pipeline && (
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-2">
              <div className="flex justify-between">
                <span>Status</span>
                <span className="font-medium text-green-600 dark:text-green-400">
                  {pipeline.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Fields</span>
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  {pipeline.field_count || '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Created</span>
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  {pipeline.created_at ? new Date(pipeline.created_at).toLocaleDateString() : '—'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  );
}