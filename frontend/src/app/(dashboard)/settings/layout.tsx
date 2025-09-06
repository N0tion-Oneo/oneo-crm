"use client";

import { ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/features/auth/context";
import {
  Building2,
  Users,
  Shield as ShieldIcon,
  Palette,
  Globe,
  Shield,
  Database,
  BarChart3,
  MessageCircle,
  Brain,
  Activity,
} from "lucide-react";

const settingsTabs = [
  { 
    name: "Organization", 
    href: "/settings", 
    icon: Building2,
    permission: 'organization'
  },
  { 
    name: "Users & Teams", 
    href: "/settings/users", 
    icon: Users,
    permission: 'users'
  },
  { 
    name: "Permissions", 
    href: "/settings/permissions", 
    icon: ShieldIcon,
    permission: 'permissions'
  },
  { 
    name: "Branding", 
    href: "/settings/branding", 
    icon: Palette,
    permission: 'branding'
  },
  { 
    name: "Communications", 
    href: "/settings/communications", 
    icon: MessageCircle,
    // Show if user has the main communications permission OR any sub-page permission
    permission: 'communications',
    additionalPermissions: {
      resource: 'communication_settings',
      actions: ['general', 'accounts', 'providers', 'advanced']
    }
  },
  { 
    name: "Localization", 
    href: "/settings/localization", 
    icon: Globe,
    permission: 'localization'
  },
  { 
    name: "Security", 
    href: "/settings/security", 
    icon: Shield,
    permission: 'security'
  },
  { 
    name: "Data Policies", 
    href: "/settings/data-policies", 
    icon: Database,
    permission: 'data_policies'
  },
  { 
    name: "Usage & Billing", 
    href: "/settings/usage", 
    icon: BarChart3,
    permission: 'usage'
  },
  { 
    name: "AI Configuration", 
    href: "/settings/ai", 
    icon: Brain,
    permission: 'ai'
  },
  { 
    name: "Celery Tasks", 
    href: "/settings/celery", 
    icon: Activity,
    permission: 'celery'
  },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { hasPermission } = useAuth();

  // Filter settings tabs based on simplified page permissions
  const visibleTabs = settingsTabs.filter(tab => {
    // Handle tabs with single permission
    if (tab.permission) {
      // Check main permission first
      if (hasPermission('settings', tab.permission)) {
        return true;
      }
      
      // Check additional permissions for tabs like Communications
      if (tab.additionalPermissions) {
        const { resource, actions } = tab.additionalPermissions;
        return actions.some(action => hasPermission(resource, action));
      }
    }
    return false;
  });

  // If user has no access to any settings, show a message
  if (visibleTabs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No Access
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            You don't have permission to access settings.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Sidebar Navigation */}
      <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Settings
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage your organization settings
          </p>
        </div>
        <nav className="space-y-1 px-3">
          {visibleTabs.map((tab) => {
            const isActive = pathname === tab.href;
            const Icon = tab.icon;
            return (
              <button
                key={tab.name}
                onClick={() => router.push(tab.href)}
                className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                  isActive
                    ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                }`}
              >
                <Icon className="mr-3 h-5 w-5" />
                {tab.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-950">
        {children}
      </div>
    </div>
  );
}