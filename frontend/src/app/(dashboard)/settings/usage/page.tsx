"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { tenantSettingsAPI, type TenantUsage } from "@/lib/api/tenant-settings";
import { BarChart3, Loader2, Users, HardDrive, Cpu, Globe, CreditCard } from "lucide-react";

export default function UsageBillingPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [usage, setUsage] = useState<TenantUsage | null>(null);

  useEffect(() => {
    loadUsage();
  }, []);

  const loadUsage = async () => {
    try {
      const data = await tenantSettingsAPI.getUsage();
      setUsage(data);
    } catch (error) {
      toast({
        title: "Error loading usage data",
        description: "Could not load usage statistics. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return "text-red-600 dark:text-red-400";
    if (percentage >= 75) return "text-yellow-600 dark:text-yellow-400";
    return "text-green-600 dark:text-green-400";
  };

  const getProgressBarColor = (percentage: number) => {
    if (percentage >= 90) return "bg-red-600";
    if (percentage >= 75) return "bg-yellow-600";
    return "bg-green-600";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
      </div>
    );
  }

  if (!usage) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500 dark:text-gray-400">No usage data available</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <BarChart3 className="mr-2 h-6 w-6" />
          Usage & Billing
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Monitor your organization's resource usage and billing information
        </p>
      </div>

      {/* Plan Information */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow mb-6">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <CreditCard className="mr-2 h-5 w-5" />
              Current Plan
            </h2>
            <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-full text-sm font-medium">
              {usage.plan_tier.toUpperCase()}
            </span>
          </div>
          
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Plan Name</p>
              <p className="text-base font-medium text-gray-900 dark:text-white">{usage.plan_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Billing Cycle</p>
              <p className="text-base font-medium text-gray-900 dark:text-white capitalize">{usage.billing_cycle}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Next Billing Date</p>
              <p className="text-base font-medium text-gray-900 dark:text-white">
                {formatDate(usage.next_billing_date)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Usage Statistics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Users */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
                <Users className="mr-2 h-5 w-5" />
                Users
              </h3>
              <span className={`text-sm font-medium ${getUsageColor(usage.user_percentage)}`}>
                {usage.user_percentage}%
              </span>
            </div>
            
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-gray-400">
                  {usage.current_users} of {usage.max_users} users
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${getProgressBarColor(usage.user_percentage)}`}
                  style={{ width: `${Math.min(usage.user_percentage, 100)}%` }}
                />
              </div>
            </div>
            
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {usage.max_users - usage.current_users} seats available
            </p>
          </div>
        </div>

        {/* Storage */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
                <HardDrive className="mr-2 h-5 w-5" />
                Storage
              </h3>
              <span className={`text-sm font-medium ${getUsageColor(usage.storage_percentage)}`}>
                {usage.storage_percentage}%
              </span>
            </div>
            
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-gray-400">
                  {(usage.storage_used_mb / 1024).toFixed(2)} GB of {(usage.storage_limit_mb / 1024).toFixed(0)} GB
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${getProgressBarColor(usage.storage_percentage)}`}
                  style={{ width: `${Math.min(usage.storage_percentage, 100)}%` }}
                />
              </div>
            </div>
            
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {((usage.storage_limit_mb - usage.storage_used_mb) / 1024).toFixed(2)} GB available
            </p>
          </div>
        </div>

        {/* AI Usage */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
                <Cpu className="mr-2 h-5 w-5" />
                AI Usage
              </h3>
              <span className={`text-sm font-medium ${getUsageColor(usage.ai_usage_percentage)}`}>
                {usage.ai_usage_percentage}%
              </span>
            </div>
            
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-gray-400">
                  ${usage.ai_usage_current} of ${usage.ai_usage_limit}
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${getProgressBarColor(usage.ai_usage_percentage)}`}
                  style={{ width: `${Math.min(usage.ai_usage_percentage, 100)}%` }}
                />
              </div>
            </div>
            
            <p className="text-xs text-gray-500 dark:text-gray-400">
              ${(usage.ai_usage_limit - usage.ai_usage_current).toFixed(2)} remaining this month
            </p>
          </div>
        </div>

        {/* API Calls */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
                <Globe className="mr-2 h-5 w-5" />
                API Usage
              </h3>
              <span className={`text-sm font-medium ${getUsageColor((usage.api_calls_this_month / usage.api_calls_limit_monthly) * 100)}`}>
                {((usage.api_calls_this_month / usage.api_calls_limit_monthly) * 100).toFixed(1)}%
              </span>
            </div>
            
            <div className="mb-2">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-gray-400">
                  {usage.api_calls_this_month.toLocaleString()} of {usage.api_calls_limit_monthly.toLocaleString()} calls
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${getProgressBarColor((usage.api_calls_this_month / usage.api_calls_limit_monthly) * 100)}`}
                  style={{ width: `${Math.min((usage.api_calls_this_month / usage.api_calls_limit_monthly) * 100, 100)}%` }}
                />
              </div>
            </div>
            
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {usage.api_calls_today.toLocaleString()} calls today
            </p>
          </div>
        </div>
      </div>

      {/* Usage Tips */}
      <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
          Usage Tips
        </h3>
        <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
          <li>• Usage resets at the beginning of each billing cycle</li>
          <li>• You'll receive notifications when approaching limits</li>
          <li>• Contact support to upgrade your plan or increase limits</li>
        </ul>
      </div>
    </div>
  );
}