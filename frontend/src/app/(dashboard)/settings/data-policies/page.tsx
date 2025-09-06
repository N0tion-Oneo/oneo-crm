"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/features/auth/context";
import { tenantSettingsAPI, type DataPolicies } from "@/lib/api/tenant-settings";
import { Database, Loader2, FileDown, AlertCircle } from "lucide-react";

export default function DataPoliciesPage() {
  const { toast } = useToast();
  const { hasPermission } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Check page-based permission - having permission means both view and edit
  const hasPageAccess = hasPermission('settings', 'data_policies');
  const canViewSettings = hasPageAccess;
  const canEditSettings = hasPageAccess;
  
  const [dataPolicies, setDataPolicies] = useState<DataPolicies>({
    retention_days: 365,
    backup_frequency: "daily",
    auto_archive_days: 90,
    export_formats: ["csv", "json", "excel"],
  });

  const exportFormats = [
    { value: "csv", label: "CSV" },
    { value: "json", label: "JSON" },
    { value: "excel", label: "Excel" },
    { value: "pdf", label: "PDF" },
  ];

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
      if (data.data_policies) {
        setDataPolicies(data.data_policies);
      }
    } catch (error) {
      toast({
        title: "Error loading settings",
        description: "Could not load data policies. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    // Validate settings
    if (dataPolicies.retention_days < 30 || dataPolicies.retention_days > 3650) {
      toast({
        title: "Invalid retention period",
        description: "Data retention must be between 30 days and 10 years.",
        variant: "destructive",
      });
      return;
    }

    if (dataPolicies.auto_archive_days < 30 || dataPolicies.auto_archive_days > 365) {
      toast({
        title: "Invalid archive period",
        description: "Auto-archive must be between 30 and 365 days.",
        variant: "destructive",
      });
      return;
    }

    if (dataPolicies.export_formats.length === 0) {
      toast({
        title: "Export formats required",
        description: "Please select at least one export format.",
        variant: "destructive",
      });
      return;
    }

    setSaving(true);
    try {
      await tenantSettingsAPI.updateDataPolicies(dataPolicies);
      toast({
        title: "Settings saved",
        description: "Data policies have been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error saving settings",
        description: "Could not save data policies. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const toggleExportFormat = (format: string) => {
    if (dataPolicies.export_formats.includes(format as any)) {
      setDataPolicies({
        ...dataPolicies,
        export_formats: dataPolicies.export_formats.filter((f) => f !== format) as any[],
      });
    } else {
      setDataPolicies({
        ...dataPolicies,
        export_formats: [...dataPolicies.export_formats, format as any],
      });
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
          <p className="text-gray-600">You don't have permission to view data policies.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <Database className="mr-2 h-6 w-6" />
          Data Policies
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Configure data retention, backup, and export policies for your organization
        </p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
        <fieldset disabled={!canEditSettings} className="p-6 space-y-6">
          {/* Data Retention */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Data Retention
            </h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Data Retention Period (days)
              </label>
              <div className="flex items-center space-x-4">
                <input
                  type="number"
                  min={30}
                  max={3650}
                  value={dataPolicies.retention_days}
                  onChange={(e) => setDataPolicies({ ...dataPolicies, retention_days: parseInt(e.target.value) })}
                  className="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                />
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  ({Math.floor(dataPolicies.retention_days / 365)} years, {dataPolicies.retention_days % 365} days)
                </span>
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                How long to keep deleted records and data. Minimum 30 days, maximum 10 years (3650 days).
              </p>
            </div>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Backup & Archive
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Backup Frequency
                </label>
                <select
                  value={dataPolicies.backup_frequency}
                  onChange={(e) => setDataPolicies({ ...dataPolicies, backup_frequency: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                >
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  How often to create automatic backups of your data
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Auto-Archive After (days)
                </label>
                <input
                  type="number"
                  min={30}
                  max={365}
                  value={dataPolicies.auto_archive_days}
                  onChange={(e) => setDataPolicies({ ...dataPolicies, auto_archive_days: parseInt(e.target.value) })}
                  className="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Automatically archive inactive records after this period (30-365 days)
                </p>
              </div>
            </div>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Export Settings
            </h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Allowed Export Formats
              </label>
              <div className="space-y-2">
                {exportFormats.map((format) => (
                  <label key={format.value} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={dataPolicies.export_formats.includes(format.value as any)}
                      onChange={() => toggleExportFormat(format.value)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300 flex items-center">
                      <FileDown className="h-4 w-4 mr-1" />
                      {format.label}
                    </span>
                  </label>
                ))}
              </div>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Select which formats users can export data to
              </p>
            </div>
          </div>

          {/* Data Policy Summary */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Policy Summary
            </h3>
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
              <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
                <li className="flex items-start">
                  <span className="text-gray-500 dark:text-gray-400 mr-2">•</span>
                  Deleted data will be retained for <strong>{dataPolicies.retention_days} days</strong> before permanent deletion
                </li>
                <li className="flex items-start">
                  <span className="text-gray-500 dark:text-gray-400 mr-2">•</span>
                  Automatic backups will be created <strong>{dataPolicies.backup_frequency}</strong>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-500 dark:text-gray-400 mr-2">•</span>
                  Inactive records will be archived after <strong>{dataPolicies.auto_archive_days} days</strong>
                </li>
                <li className="flex items-start">
                  <span className="text-gray-500 dark:text-gray-400 mr-2">•</span>
                  Users can export data in: <strong>{dataPolicies.export_formats.map(f => f.toUpperCase()).join(", ")}</strong>
                </li>
              </ul>
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