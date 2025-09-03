"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { tenantSettingsAPI, type SecurityPolicies, type PasswordComplexity } from "@/lib/api/tenant-settings";
import { Shield, Loader2, Info } from "lucide-react";

export default function SecuritySettingsPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [security, setSecurity] = useState<SecurityPolicies>({
    password_min_length: 8,
    password_complexity: {
      require_uppercase: true,
      require_lowercase: true,
      require_numbers: true,
      require_special: false,
    },
    session_timeout_minutes: 60,
    require_2fa: false,
    ip_whitelist: [],
  });

  const [ipInput, setIpInput] = useState("");

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await tenantSettingsAPI.getSettings();
      if (data.security_policies) {
        setSecurity({
          ...data.security_policies,
          password_complexity: data.security_policies.password_complexity || {
            require_uppercase: true,
            require_lowercase: true,
            require_numbers: true,
            require_special: false,
          },
          ip_whitelist: data.security_policies.ip_whitelist || [],
        });
      }
    } catch (error) {
      toast({
        title: "Error loading settings",
        description: "Could not load security settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    // Validate settings
    if (security.password_min_length < 8 || security.password_min_length > 32) {
      toast({
        title: "Invalid password length",
        description: "Password minimum length must be between 8 and 32 characters.",
        variant: "destructive",
      });
      return;
    }

    if (security.session_timeout_minutes < 15 || security.session_timeout_minutes > 480) {
      toast({
        title: "Invalid session timeout",
        description: "Session timeout must be between 15 and 480 minutes.",
        variant: "destructive",
      });
      return;
    }

    setSaving(true);
    try {
      await tenantSettingsAPI.updateSecurity(security);
      toast({
        title: "Settings saved",
        description: "Security settings have been updated successfully.",
      });
    } catch (error) {
      toast({
        title: "Error saving settings",
        description: "Could not save security settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const addIpAddress = () => {
    // Basic IP validation
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    if (!ipRegex.test(ipInput)) {
      toast({
        title: "Invalid IP address",
        description: "Please enter a valid IPv4 address.",
        variant: "destructive",
      });
      return;
    }

    if (!security.ip_whitelist?.includes(ipInput)) {
      setSecurity({
        ...security,
        ip_whitelist: [...(security.ip_whitelist || []), ipInput],
      });
      setIpInput("");
    }
  };

  const removeIpAddress = (ip: string) => {
    setSecurity({
      ...security,
      ip_whitelist: security.ip_whitelist?.filter((item) => item !== ip) || [],
    });
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
          <Shield className="mr-2 h-6 w-6" />
          Security Settings
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Configure security policies and access controls for your organization
        </p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
        <div className="p-6 space-y-6">
          {/* Password Policy */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Password Policy
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Minimum Password Length
                </label>
                <input
                  type="number"
                  min={8}
                  max={32}
                  value={security.password_min_length}
                  onChange={(e) => setSecurity({ ...security, password_min_length: parseInt(e.target.value) })}
                  className="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Between 8 and 32 characters
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Password Complexity Requirements
                </label>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={security.password_complexity?.require_uppercase || false}
                      onChange={(e) => setSecurity({
                        ...security,
                        password_complexity: {
                          ...security.password_complexity!,
                          require_uppercase: e.target.checked,
                        },
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Require uppercase letters (A-Z)
                    </span>
                  </label>
                  
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={security.password_complexity?.require_lowercase || false}
                      onChange={(e) => setSecurity({
                        ...security,
                        password_complexity: {
                          ...security.password_complexity!,
                          require_lowercase: e.target.checked,
                        },
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Require lowercase letters (a-z)
                    </span>
                  </label>
                  
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={security.password_complexity?.require_numbers || false}
                      onChange={(e) => setSecurity({
                        ...security,
                        password_complexity: {
                          ...security.password_complexity!,
                          require_numbers: e.target.checked,
                        },
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Require numbers (0-9)
                    </span>
                  </label>
                  
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={security.password_complexity?.require_special || false}
                      onChange={(e) => setSecurity({
                        ...security,
                        password_complexity: {
                          ...security.password_complexity!,
                          require_special: e.target.checked,
                        },
                      })}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Require special characters (!@#$%^&*)
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Session Management
            </h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Session Timeout (minutes)
              </label>
              <input
                type="number"
                min={15}
                max={480}
                value={security.session_timeout_minutes}
                onChange={(e) => setSecurity({ ...security, session_timeout_minutes: parseInt(e.target.value) })}
                className="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Automatically log out users after this period of inactivity (15-480 minutes)
              </p>
            </div>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Additional Security
            </h3>
            
            <div className="space-y-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={security.require_2fa}
                  onChange={(e) => setSecurity({ ...security, require_2fa: e.target.checked })}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  Require two-factor authentication for all users
                </span>
              </label>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  IP Whitelist
                </label>
                <div className="flex items-center space-x-2 mb-2">
                  <input
                    type="text"
                    value={ipInput}
                    onChange={(e) => setIpInput(e.target.value)}
                    placeholder="192.168.1.1"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                  />
                  <button
                    onClick={addIpAddress}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
                  >
                    Add IP
                  </button>
                </div>
                
                {security.ip_whitelist && security.ip_whitelist.length > 0 ? (
                  <div className="space-y-1">
                    {security.ip_whitelist.map((ip) => (
                      <div key={ip} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                        <span className="text-sm text-gray-700 dark:text-gray-300 font-mono">{ip}</span>
                        <button
                          onClick={() => removeIpAddress(ip)}
                          className="text-red-600 hover:text-red-700 text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
                    <Info className="h-3 w-3 mr-1" />
                    No IP restrictions. Access allowed from any IP address.
                  </p>
                )}
              </div>
            </div>
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