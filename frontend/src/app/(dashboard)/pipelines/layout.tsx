"use client";

import { ReactNode } from "react";
import { useAuth } from '@/features/auth/context';

export default function PipelinesLayout({ children }: { children: ReactNode }) {
  const { hasPermission } = useAuth();
  
  // Check if user has pipeline permissions
  const canReadPipelines = hasPermission('pipelines', 'read');
  
  // If user doesn't have permission to read pipelines, show access denied
  if (!canReadPipelines) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
            Access Denied
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            You don't have permission to view pipelines.
          </p>
        </div>
      </div>
    );
  }
  
  // Just render children - no sidebar needed since we have pipeline navigation in main sidebar
  return <>{children}</>;
}