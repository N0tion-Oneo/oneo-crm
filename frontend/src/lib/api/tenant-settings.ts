import { api } from '../api';

export interface LocalizationSettings {
  timezone: string;
  date_format: 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD';
  time_format: '12h' | '24h';
  currency: string;
  language: string;
  week_start_day: 'sunday' | 'monday';
}

export interface EmailSignatureVariables {
  user_basic: string[];
  user_preferences: string[];
  staff_profile: string[];
  organization: string[];
}

export interface BrandingSettings {
  primary_color: string;
  secondary_color: string;
  email_header_html?: string;
  login_message?: string;
  email_signature_template?: string;
  email_signature_enabled?: boolean;
  email_signature_variables?: EmailSignatureVariables;
}

export interface PasswordComplexity {
  require_uppercase: boolean;
  require_lowercase: boolean;
  require_numbers: boolean;
  require_special: boolean;
}

export interface SecurityPolicies {
  password_min_length: number;
  password_complexity?: PasswordComplexity;
  session_timeout_minutes: number;
  require_2fa: boolean;
  ip_whitelist?: string[];
}

export interface DataPolicies {
  retention_days: number;
  backup_frequency: 'hourly' | 'daily' | 'weekly' | 'monthly';
  auto_archive_days: number;
  export_formats: ('csv' | 'json' | 'excel' | 'pdf')[];
}

export interface TenantSettings {
  id: string;
  name: string;
  created_on: string;
  
  // Organization profile
  organization_logo?: string;
  organization_description?: string;
  organization_website?: string;
  support_email?: string;
  support_phone?: string;
  business_hours?: Record<string, any>;
  
  // Settings
  localization_settings?: LocalizationSettings;
  branding_settings?: BrandingSettings;
  security_policies?: SecurityPolicies;
  data_policies?: DataPolicies;
  
  // Limits and usage
  max_users: number;
  current_users: number;
  features_enabled?: Record<string, boolean>;
  billing_settings?: Record<string, any>;
  ai_enabled: boolean;
  ai_usage_limit: number;
  ai_current_usage: number;
  storage_usage_mb?: number;
  api_calls_this_month?: number;
}

export interface TenantUsage {
  current_users: number;
  max_users: number;
  user_percentage: number;
  storage_used_mb: number;
  storage_limit_mb: number;
  storage_percentage: number;
  ai_usage_current: number;
  ai_usage_limit: number;
  ai_usage_percentage: number;
  api_calls_today: number;
  api_calls_this_month: number;
  api_calls_limit_monthly: number;
  plan_name: string;
  plan_tier: string;
  billing_cycle: string;
  next_billing_date: string;
}

class TenantSettingsAPI {
  private basePath = '/api/v1/tenant-settings';

  async getSettings(): Promise<TenantSettings> {
    const response = await api.get(`${this.basePath}/current/`);
    return response.data;
  }

  async updateSettings(settings: Partial<TenantSettings>): Promise<TenantSettings> {
    const response = await api.patch(`${this.basePath}/current/`, settings);
    return response.data;
  }

  async uploadLogo(file: File): Promise<{ message: string; logo_url?: string }> {
    const formData = new FormData();
    formData.append('organization_logo', file);
    
    const response = await api.post(`${this.basePath}/current/upload_logo/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getUsage(): Promise<TenantUsage> {
    const response = await api.get(`${this.basePath}/current/usage/`);
    return response.data;
  }

  async updateLocalization(settings: LocalizationSettings): Promise<TenantSettings> {
    return this.updateSettings({ localization_settings: settings });
  }

  async updateBranding(settings: BrandingSettings): Promise<TenantSettings> {
    return this.updateSettings({ branding_settings: settings });
  }

  async updateSecurity(settings: SecurityPolicies): Promise<TenantSettings> {
    return this.updateSettings({ security_policies: settings });
  }

  async updateDataPolicies(settings: DataPolicies): Promise<TenantSettings> {
    return this.updateSettings({ data_policies: settings });
  }

  async updateOrganizationProfile(profile: {
    organization_description?: string;
    support_email?: string;
    support_phone?: string;
    business_hours?: Record<string, any>;
  }): Promise<TenantSettings> {
    return this.updateSettings(profile);
  }

  async getEmailSignaturePreview(template?: string): Promise<{
    preview_html: string;
    available_variables: EmailSignatureVariables;
  }> {
    if (template !== undefined) {
      // Use POST to preview a specific template
      const response = await api.post(`${this.basePath}/current/email_signature_preview/`, {
        template: template
      });
      return response.data;
    } else {
      // Use GET for saved template preview
      const response = await api.get(`${this.basePath}/current/email_signature_preview/`);
      return response.data;
    }
  }

  async renderEmailSignature(userId?: string): Promise<{
    signature_html: string;
    enabled: boolean;
  }> {
    const response = await api.post(`${this.basePath}/current/render_email_signature/`, {
      user_id: userId,
    });
    return response.data;
  }
}

export const tenantSettingsAPI = new TenantSettingsAPI();