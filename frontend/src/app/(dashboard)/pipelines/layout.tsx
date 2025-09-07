"use client";

import { ReactNode, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { 
  Database, 
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  Archive
} from "lucide-react";
import { cn } from "@/lib/utils";
import { pipelinesApi } from '@/lib/api';

const PIPELINE_TYPE_ICONS: Record<string, string> = {
  crm: '🎯',
  ats: '👥',
  cms: '📝',
  custom: '⚙️',
  contacts: '👤',
  companies: '🏢',
  deals: '💰',
  support: '🎧',
  inventory: '📦'
};

export default function PipelinesLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsed, setCollapsed] = useState(false);

  // Load pipelines
  useEffect(() => {
    const loadPipelines = async () => {
      try {
        setLoading(true);
        const response = await pipelinesApi.list();
        const pipelinesData = response.data.results || response.data || [];
        setPipelines(pipelinesData);
      } catch (error) {
        console.error('Failed to load pipelines:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPipelines();
  }, []);

  // Filter pipelines based on search
  const filteredPipelines = pipelines.filter(p => 
    !searchQuery || 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Separate active and archived pipelines
  const activePipelines = filteredPipelines.filter(p => !p.is_archived);
  const archivedPipelines = filteredPipelines.filter(p => p.is_archived);

  const handlePipelineClick = (pipelineId: string) => {
    router.push(`/pipelines/${pipelineId}`);
  };

  const handleNewPipeline = () => {
    router.push('/pipelines?action=new');
  };

  // Check if we're on the main pipelines page
  const isMainPage = pathname === '/pipelines';
  const currentPipelineId = pathname.split('/')[2];

  if (collapsed) {
    return (
      <div className="flex h-full">
        <div className="w-16 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setCollapsed(false)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Expand sidebar"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2">
            {activePipelines.slice(0, 5).map(pipeline => (
              <button
                key={pipeline.id}
                onClick={() => handlePipelineClick(pipeline.id)}
                className={cn(
                  "w-full p-2 mb-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700",
                  currentPipelineId === pipeline.id.toString() && "bg-blue-50 dark:bg-blue-900/20"
                )}
                title={pipeline.name}
              >
                <span className="text-lg">
                  {PIPELINE_TYPE_ICONS[pipeline.pipeline_type] || '📊'}
                </span>
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1">{children}</div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Main Pipeline Sidebar */}
      <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-lg text-gray-900 dark:text-white">Pipelines</h2>
            <button
              onClick={() => setCollapsed(true)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Collapse sidebar"
            >
              <ChevronLeft className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          
          <button
            onClick={handleNewPipeline}
            className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium flex items-center justify-center"
          >
            <Plus className="w-4 h-4 mr-1" />
            New Pipeline
          </button>
        </div>

        {/* Search */}
        <div className="p-3 border-b border-gray-200 dark:border-gray-700">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="search"
              placeholder="Search pipelines..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Pipeline List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4">
              <div className="animate-pulse space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Active Pipelines */}
              {activePipelines.length > 0 && (
                <div className="p-3">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    Active Pipelines ({activePipelines.length})
                  </div>
                  {activePipelines.map(pipeline => (
                    <button
                      key={pipeline.id}
                      onClick={() => handlePipelineClick(pipeline.id)}
                      className={cn(
                        "w-full text-left px-3 py-2 rounded-md mb-1 transition-colors",
                        currentPipelineId === pipeline.id.toString()
                          ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
                          : "hover:bg-gray-50 dark:hover:bg-gray-700"
                      )}
                    >
                      <div className="flex items-start">
                        <span className="text-lg mr-2 flex-shrink-0">
                          {PIPELINE_TYPE_ICONS[pipeline.pipeline_type] || '📊'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
                            {pipeline.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {pipeline.record_count || 0} records
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Archived */}
              {archivedPipelines.length > 0 && (
                <div className="p-3 border-t border-gray-200 dark:border-gray-700">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 flex items-center">
                    <Archive className="w-3 h-3 mr-1" />
                    Archived ({archivedPipelines.length})
                  </div>
                  {archivedPipelines.map(pipeline => (
                    <button
                      key={pipeline.id}
                      onClick={() => handlePipelineClick(pipeline.id)}
                      className={cn(
                        "w-full text-left px-3 py-2 rounded-md mb-1 transition-colors opacity-60",
                        currentPipelineId === pipeline.id.toString()
                          ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
                          : "hover:bg-gray-50 dark:hover:bg-gray-700"
                      )}
                    >
                      <div className="flex items-start">
                        <span className="text-lg mr-2 flex-shrink-0">
                          {PIPELINE_TYPE_ICONS[pipeline.pipeline_type] || '📊'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
                            {pipeline.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {pipeline.record_count || 0} records
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Empty State */}
              {activePipelines.length === 0 && archivedPipelines.length === 0 && (
                <div className="p-4 text-center">
                  <Database className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {searchQuery ? 'No pipelines found' : 'No pipelines yet'}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1">
        {children}
      </div>
    </div>
  );
}