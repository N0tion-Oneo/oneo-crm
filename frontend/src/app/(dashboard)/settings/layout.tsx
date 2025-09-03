"use client";

import { ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Building2,
  Palette,
  Globe,
  Shield,
  Database,
  BarChart3,
} from "lucide-react";

const settingsTabs = [
  { name: "Organization", href: "/settings", icon: Building2 },
  { name: "Branding", href: "/settings/branding", icon: Palette },
  { name: "Localization", href: "/settings/localization", icon: Globe },
  { name: "Security", href: "/settings/security", icon: Shield },
  { name: "Data Policies", href: "/settings/data-policies", icon: Database },
  { name: "Usage & Billing", href: "/settings/usage", icon: BarChart3 },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

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
          {settingsTabs.map((tab) => {
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