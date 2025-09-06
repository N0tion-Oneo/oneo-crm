"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/features/auth/context";
import { tenantSettingsAPI, type LocalizationSettings } from "@/lib/api/tenant-settings";
import { Globe, Loader2, AlertCircle } from "lucide-react";

const timezones = [
  "UTC",
  "America/New_York",
  "America/Chicago", 
  "America/Denver",
  "America/Los_Angeles",
  "America/Toronto",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Asia/Dubai",
  "Australia/Sydney",
];

const currencies = [
  { code: "USD", name: "US Dollar" },
  { code: "EUR", name: "Euro" },
  { code: "GBP", name: "British Pound" },
  { code: "JPY", name: "Japanese Yen" },
  { code: "CAD", name: "Canadian Dollar" },
  { code: "AUD", name: "Australian Dollar" },
  { code: "CHF", name: "Swiss Franc" },
  { code: "CNY", name: "Chinese Yuan" },
];

const languages = [
  { code: "en", name: "English" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
  { code: "de", name: "German" },
  { code: "it", name: "Italian" },
  { code: "pt", name: "Portuguese" },
  { code: "ja", name: "Japanese" },
  { code: "zh", name: "Chinese" },
];

export default function LocalizationSettingsPage() {
  const { toast } = useToast();
  const { hasPermission } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Check permissions
  // Check page-based permission - having permission means both view and edit
  const hasPageAccess = hasPermission('settings', 'localization');
  const canViewSettings = hasPageAccess;
  const canEditSettings = hasPageAccess;
  
  const [localization, setLocalization] = useState<LocalizationSettings>({
    timezone: "UTC",
    date_format: "MM/DD/YYYY",
    time_format: "12h",
    currency: "USD",
    language: "en",
    week_start_day: "sunday",
  });

  useEffect(() => {
    if (!canViewSettings) {
      setLoading(false);
      return;
    }
    loadSettings();
  }, [canViewSettings]);

  const loadSettings = async () => {
    try {
      const data = await tenantSettingsAPI.getSettings();
      if (data.localization_settings) {
        setLocalization(data.localization_settings);
      }
    } catch (error) {
      toast({
        title: "Error loading settings",
        description: "Could not load localization settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await tenantSettingsAPI.updateLocalization(localization);
      toast({
        title: "Settings saved",
        description: "Localization settings have been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error saving settings",
        description: "Could not save localization settings. Please try again.",
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

  // Check permissions before showing content
  if (!canViewSettings) {
    return (
      <div className="p-6 max-w-4xl">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 mx-auto text-amber-500 mb-4" />
          <h3 className="text-lg font-medium">Access Denied</h3>
          <p className="text-gray-600">You don't have permission to view localization settings.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <Globe className="mr-2 h-6 w-6" />
          Localization Settings
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Configure regional preferences and formats for your organization
        </p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
        <fieldset disabled={!canEditSettings} className="p-6 space-y-6">
          {/* Timezone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Timezone
            </label>
            <select
              value={localization.timezone}
              onChange={(e) => setLocalization({ ...localization, timezone: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {timezones.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Date Format */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Date Format
              </label>
              <select
                value={localization.date_format}
                onChange={(e) => setLocalization({ ...localization, date_format: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="MM/DD/YYYY">MM/DD/YYYY (12/31/2024)</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY (31/12/2024)</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD (2024-12-31)</option>
              </select>
            </div>

            {/* Time Format */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Time Format
              </label>
              <select
                value={localization.time_format}
                onChange={(e) => setLocalization({ ...localization, time_format: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="12h">12-hour (3:30 PM)</option>
                <option value="24h">24-hour (15:30)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Currency */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Currency
              </label>
              <select
                value={localization.currency}
                onChange={(e) => setLocalization({ ...localization, currency: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {currencies.map((curr) => (
                  <option key={curr.code} value={curr.code}>
                    {curr.code} - {curr.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Language */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Language
              </label>
              <select
                value={localization.language}
                onChange={(e) => setLocalization({ ...localization, language: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Week Start Day */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Week Starts On
            </label>
            <select
              value={localization.week_start_day}
              onChange={(e) => setLocalization({ ...localization, week_start_day: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="sunday">Sunday</option>
              <option value="monday">Monday</option>
            </select>
          </div>

          {/* Format Preview */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Format Preview
            </label>
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800/50">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Date:</span>
                  <span className="ml-2 text-gray-900 dark:text-white font-medium">
                    {localization.date_format === "MM/DD/YYYY" && "12/31/2024"}
                    {localization.date_format === "DD/MM/YYYY" && "31/12/2024"}
                    {localization.date_format === "YYYY-MM-DD" && "2024-12-31"}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Time:</span>
                  <span className="ml-2 text-gray-900 dark:text-white font-medium">
                    {localization.time_format === "12h" ? "3:30 PM" : "15:30"}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Currency:</span>
                  <span className="ml-2 text-gray-900 dark:text-white font-medium">
                    {localization.currency} 1,234.56
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Week starts:</span>
                  <span className="ml-2 text-gray-900 dark:text-white font-medium capitalize">
                    {localization.week_start_day}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </fieldset>

        {/* Save Button */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving || !canEditSettings}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            title={!canEditSettings ? "You don't have permission to edit settings" : ""}
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