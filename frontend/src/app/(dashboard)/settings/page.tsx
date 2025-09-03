"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { tenantSettingsAPI, type TenantSettings } from "@/lib/api/tenant-settings";
import { Building2, Upload, Loader2 } from "lucide-react";

export default function OrganizationSettingsPage() {
  const { toast } = useToast();
  const [settings, setSettings] = useState<TenantSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);

  const [formData, setFormData] = useState({
    organization_description: "",
    support_email: "",
    support_phone: "",
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await tenantSettingsAPI.getSettings();
      setSettings(data);
      setFormData({
        organization_description: data.organization_description || "",
        support_email: data.support_email || "",
        support_phone: data.support_phone || "",
      });
    } catch (error) {
      toast({
        title: "Error loading settings",
        description: "Could not load organization settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await tenantSettingsAPI.updateOrganizationProfile(formData);
      setSettings(updated);
      toast({
        title: "Settings saved",
        description: "Organization settings have been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error saving settings",
        description: "Could not save organization settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml'];
    if (!validTypes.includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload a JPEG, PNG, GIF, or SVG image.",
        variant: "destructive",
      });
      return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Logo file size cannot exceed 5MB.",
        variant: "destructive",
      });
      return;
    }

    setUploadingLogo(true);
    try {
      const result = await tenantSettingsAPI.uploadLogo(file);
      
      // Reload settings to get the updated logo URL
      await loadSettings();
      
      toast({
        title: "Logo uploaded",
        description: "Organization logo has been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error uploading logo",
        description: "Could not upload logo. Please try again.",
        variant: "destructive",
      });
    } finally {
      setUploadingLogo(false);
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
          <Building2 className="mr-2 h-6 w-6" />
          Organization Settings
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage your organization's profile and contact information
        </p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
        <div className="p-6 space-y-6">
          {/* Organization Name (Read-only) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Organization Name
            </label>
            <input
              type="text"
              value={settings?.name || ""}
              disabled
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 cursor-not-allowed"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Organization name cannot be changed. Contact support if needed.
            </p>
          </div>

          {/* Organization Logo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Organization Logo
            </label>
            <div className="flex items-center space-x-4">
              {settings?.organization_logo ? (
                <img
                  src={settings.organization_logo}
                  alt="Organization logo"
                  className="h-20 w-20 rounded-lg object-cover border border-gray-200 dark:border-gray-700"
                />
              ) : (
                <div className="h-20 w-20 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                  <Building2 className="h-8 w-8 text-gray-400" />
                </div>
              )}
              <div>
                <input
                  type="file"
                  id="logo-upload"
                  className="hidden"
                  accept="image/*"
                  onChange={handleLogoUpload}
                  disabled={uploadingLogo}
                />
                <label
                  htmlFor="logo-upload"
                  className={`inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer ${
                    uploadingLogo ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                >
                  {uploadingLogo ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      Upload Logo
                    </>
                  )}
                </label>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  JPG, PNG, GIF or SVG. Max 5MB.
                </p>
              </div>
            </div>
          </div>

          {/* Organization Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Organization Description
            </label>
            <textarea
              value={formData.organization_description}
              onChange={(e) => setFormData({ ...formData, organization_description: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
              placeholder="Describe your organization..."
            />
          </div>

          {/* Support Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Support Email
            </label>
            <input
              type="email"
              value={formData.support_email}
              onChange={(e) => setFormData({ ...formData, support_email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
              placeholder="support@yourcompany.com"
            />
          </div>

          {/* Support Phone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Support Phone
            </label>
            <input
              type="tel"
              value={formData.support_phone}
              onChange={(e) => setFormData({ ...formData, support_phone: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
              placeholder="+1 (555) 123-4567"
            />
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