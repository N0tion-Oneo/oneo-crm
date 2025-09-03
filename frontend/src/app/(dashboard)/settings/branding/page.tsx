"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { tenantSettingsAPI, type BrandingSettings } from "@/lib/api/tenant-settings";
import { Palette, Loader2 } from "lucide-react";

export default function BrandingSettingsPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [branding, setBranding] = useState<BrandingSettings>({
    primary_color: "#3B82F6",
    secondary_color: "#10B981",
    email_header_html: "",
    login_message: "",
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await tenantSettingsAPI.getSettings();
      if (data.branding_settings) {
        setBranding({
          primary_color: data.branding_settings.primary_color || "#3B82F6",
          secondary_color: data.branding_settings.secondary_color || "#10B981",
          email_header_html: data.branding_settings.email_header_html || "",
          login_message: data.branding_settings.login_message || "",
        });
      }
    } catch (error) {
      toast({
        title: "Error loading settings",
        description: "Could not load branding settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    // Validate hex colors
    const hexRegex = /^#[0-9A-Fa-f]{6}$/;
    if (!hexRegex.test(branding.primary_color)) {
      toast({
        title: "Invalid primary color",
        description: "Please enter a valid hex color code (e.g., #3B82F6)",
        variant: "destructive",
      });
      return;
    }
    if (!hexRegex.test(branding.secondary_color)) {
      toast({
        title: "Invalid secondary color",
        description: "Please enter a valid hex color code (e.g., #10B981)",
        variant: "destructive",
      });
      return;
    }

    setSaving(true);
    try {
      await tenantSettingsAPI.updateBranding(branding);
      toast({
        title: "Settings saved",
        description: "Branding settings have been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error saving settings",
        description: "Could not save branding settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <Palette className="mr-2 h-6 w-6" />
          Branding Settings
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Customize your organization's branding and appearance
        </p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
        <div className="p-6 space-y-6">
          {/* Color Settings */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Primary Color
              </label>
              <div className="flex items-center space-x-3">
                <input
                  type="color"
                  value={branding.primary_color}
                  onChange={(e) => setBranding({ ...branding, primary_color: e.target.value })}
                  className="h-10 w-20 border border-gray-300 dark:border-gray-600 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={branding.primary_color}
                  onChange={(e) => setBranding({ ...branding, primary_color: e.target.value })}
                  pattern="^#[0-9A-Fa-f]{6}$"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                  placeholder="#3B82F6"
                />
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Used for primary buttons and key UI elements
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Secondary Color
              </label>
              <div className="flex items-center space-x-3">
                <input
                  type="color"
                  value={branding.secondary_color}
                  onChange={(e) => setBranding({ ...branding, secondary_color: e.target.value })}
                  className="h-10 w-20 border border-gray-300 dark:border-gray-600 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={branding.secondary_color}
                  onChange={(e) => setBranding({ ...branding, secondary_color: e.target.value })}
                  pattern="^#[0-9A-Fa-f]{6}$"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                  placeholder="#10B981"
                />
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Used for success states and secondary actions
              </p>
            </div>
          </div>

          {/* Color Preview */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Color Preview
            </label>
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800/50">
              <div className="flex items-center space-x-4">
                <button
                  className="px-4 py-2 rounded-lg text-white font-medium"
                  style={{ backgroundColor: branding.primary_color }}
                >
                  Primary Button
                </button>
                <button
                  className="px-4 py-2 rounded-lg text-white font-medium"
                  style={{ backgroundColor: branding.secondary_color }}
                >
                  Secondary Button
                </button>
                <div className="flex items-center space-x-2">
                  <div
                    className="h-8 w-8 rounded"
                    style={{ backgroundColor: branding.primary_color }}
                  />
                  <div
                    className="h-8 w-8 rounded"
                    style={{ backgroundColor: branding.secondary_color }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Login Message */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Login Page Message
            </label>
            <textarea
              value={branding.login_message || ""}
              onChange={(e) => setBranding({ ...branding, login_message: e.target.value })}
              rows={3}
              maxLength={500}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
              placeholder="Welcome message displayed on the login page..."
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {branding.login_message?.length || 0}/500 characters
            </p>
          </div>

          {/* Email Header HTML */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Email Header HTML
            </label>
            <textarea
              value={branding.email_header_html || ""}
              onChange={(e) => setBranding({ ...branding, email_header_html: e.target.value })}
              rows={6}
              maxLength={5000}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
              placeholder="<div style='...'> Custom HTML for email headers </div>"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Custom HTML to include in email headers. {branding.email_header_html?.length || 0}/5000 characters
            </p>
          </div>
        </div>

        {/* Save Button */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}