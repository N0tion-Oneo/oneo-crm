"use client";

import { ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Link2,
  Settings2,
  Settings,
  Terminal,
  ChevronRight
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigationItems = [
  { 
    name: 'Overview', 
    href: '/settings/communications', 
    icon: LayoutDashboard,
    description: 'Communication settings overview and statistics'
  },
  { 
    name: 'Participants', 
    href: '/settings/communications/participants', 
    icon: Users,
    description: 'Auto-creation and participant management'
  },
  { 
    name: 'Account Connections', 
    href: '/settings/communications/accounts', 
    icon: Link2,
    description: 'Manage connected communication accounts'
  },
  { 
    name: 'Provider Settings', 
    href: '/settings/communications/providers', 
    icon: Settings2,
    description: 'Configure provider features and limits'
  },
  { 
    name: 'General', 
    href: '/settings/communications/general', 
    icon: Settings,
    description: 'Sync and API configurations'
  },
  { 
    name: 'Advanced', 
    href: '/settings/communications/advanced', 
    icon: Terminal,
    description: 'System information and debugging'
  }
];

export default function CommunicationsLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <div className="flex h-full">
      {/* Nested Sidebar Navigation */}
      <div className="w-72 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <div className="p-4">
          <div className="flex items-center gap-2 mb-1">
            <ChevronRight className="h-4 w-4 text-gray-400" />
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Settings
            </h3>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Communications
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Configure communication channels and integrations
          </p>
        </div>
        
        <nav className="px-3 pb-3">
          <div className="space-y-1">
            {navigationItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              
              return (
                <button
                  key={item.name}
                  onClick={() => router.push(item.href)}
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
                      : "text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-400"
                  )} />
                  <div className="text-left">
                    <div className={cn(
                      "font-medium",
                      isActive ? "text-blue-600 dark:text-blue-400" : ""
                    )}>
                      {item.name}
                    </div>
                    <div className={cn(
                      "text-xs mt-0.5",
                      isActive
                        ? "text-blue-600/70 dark:text-blue-400/70"
                        : "text-gray-500 dark:text-gray-400"
                    )}>
                      {item.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </nav>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  );
}