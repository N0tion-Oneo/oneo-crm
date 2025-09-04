"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { tenantSettingsAPI, type BrandingSettings, type EmailSignatureVariables } from "@/lib/api/tenant-settings";
import { Palette, Loader2, Mail, Copy, Eye, EyeOff, Info, User, Building, Briefcase, Globe } from "lucide-react";

export default function BrandingSettingsPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showSignaturePreview, setShowSignaturePreview] = useState(false);
  const [signaturePreviewHtml, setSignaturePreviewHtml] = useState("");
  const [availableVariables, setAvailableVariables] = useState<EmailSignatureVariables | null>(null);
  const [activeVariableCategory, setActiveVariableCategory] = useState<keyof EmailSignatureVariables>("user_basic");
  
  // Template definitions with professional icons
  const templates = [
    {
      name: "🏢 Professional Corporate",
      template: `<!--[if mso]>
<table cellpadding="0" cellspacing="0" border="0" width="450" style="width: 450px;">
<tr><td>
<![endif]-->
<table cellpadding="0" cellspacing="0" border="0" width="450" style="font-family: Arial, Verdana, sans-serif; font-size: 14px; color: #333333; mso-line-height-rule: exactly; line-height: 1.4; width: 450px; max-width: 450px;">
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 16px; font-weight: bold; color: #003E49; mso-line-height-rule: exactly; line-height: 20px; padding: 0;">
      {user_full_name}
    </td>
  </tr>
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 14px; color: #666666; mso-line-height-rule: exactly; line-height: 18px; padding: 2px 0 0 0;">
      {user_job_title}
    </td>
  </tr>
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #999999; mso-line-height-rule: exactly; line-height: 16px; padding: 2px 0 12px 0;">
      {user_department}
    </td>
  </tr>
  <tr>
    <td style="padding: 8px 0;">
      <table cellpadding="0" cellspacing="0" border="0" width="50" style="width: 50px;">
        <tr>
          <td style="font-size: 0; line-height: 0; border-top: 2px solid #003E49;">&nbsp;</td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding: 8px 0 0 0;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="20" style="width: 20px; padding: 0 8px 4px 0;" valign="middle">
            <img src="https://img.icons8.com/material-outlined/24/003E49/new-post.png" width="14" height="14" alt="Email" style="display: block; border: 0;" />
          </td>
          <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; padding: 0 0 4px 0;" valign="middle">
            <a href="mailto:{user_email}" style="color: #003E49; text-decoration: none;">{user_email}</a>
          </td>
        </tr>
        <tr>
          <td width="20" style="width: 20px; padding: 0 8px 4px 0;" valign="middle">
            <img src="https://img.icons8.com/material-outlined/24/003E49/phone.png" width="14" height="14" alt="Phone" style="display: block; border: 0;" />
          </td>
          <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #666666; padding: 0 0 4px 0;" valign="middle">
            {user_phone}
          </td>
        </tr>
        <tr>
          <td width="20" style="width: 20px; padding: 0 8px 4px 0;" valign="middle">
            <img src="https://img.icons8.com/material-outlined/24/003E49/smartphone.png" width="14" height="14" alt="Mobile" style="display: block; border: 0;" />
          </td>
          <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #666666; padding: 0 0 4px 0;" valign="middle">
            {user_mobile_phone}
          </td>
        </tr>
        <tr>
          <td width="20" style="width: 20px; padding: 0 8px 4px 0;" valign="middle">
            <img src="https://img.icons8.com/material-outlined/24/003E49/marker.png" width="14" height="14" alt="Location" style="display: block; border: 0;" />
          </td>
          <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #666666; padding: 0 0 4px 0;" valign="middle">
            {user_office_location}
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding: 12px 0 8px 0;">
      <table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-top: 1px solid #e0e0e0;">
        <tr>
          <td style="font-size: 0; line-height: 0; height: 1px;">&nbsp;</td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding: 0;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding: 0 15px 0 0;" valign="middle">
            <img src="{organization_logo_url}" width="100" height="40" alt="{organization_name}" style="display: block; border: 0; width: 100px; height: 40px;" />
          </td>
          <td style="border-left: 1px solid #e0e0e0; padding: 0 0 0 15px;" valign="middle">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 12px; font-weight: bold; color: #003E49; padding: 0 0 2px 0;">
                  {organization_name}
                </td>
              </tr>
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 11px; padding: 0;">
                  <a href="https://{organization_website}" style="color: #003E49; text-decoration: none;">{organization_website}</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding: 10px 0 0 0;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding: 0 5px 0 0;">
            <a href="{user_linkedin_profile}" style="text-decoration: none;">
              <img src="https://img.icons8.com/color/48/000000/linkedin.png" width="20" height="20" alt="LinkedIn" style="display: block; border: 0;" />
            </a>
          </td>
          <td style="padding: 0 5px 0 0;">
            <a href="https://twitter.com/{organization_twitter}" style="text-decoration: none;">
              <img src="https://img.icons8.com/color/48/000000/twitter.png" width="20" height="20" alt="Twitter" style="display: block; border: 0;" />
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr>
</table>
<![endif]-->`
    },
    {
      name: "✨ Modern Minimal",
      template: `<table cellpadding="0" cellspacing="0" border="0" width="400" style="font-family: Arial, Verdana, sans-serif; width: 400px; max-width: 400px;">
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 16px; font-weight: bold; color: #1a1a1a; mso-line-height-rule: exactly; line-height: 20px; padding: 0;">
      {user_full_name}
    </td>
  </tr>
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #666666; mso-line-height-rule: exactly; line-height: 18px; padding: 3px 0 0 0;">
      {user_job_title}
    </td>
  </tr>
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 12px; color: #999999; mso-line-height-rule: exactly; line-height: 16px; padding: 2px 0 10px 0;">
      {user_department}
    </td>
  </tr>
  <tr>
    <td style="padding: 8px 0;">
      <!--[if mso]>
      <table cellpadding="0" cellspacing="0" border="0" width="40" style="width: 40px;">
        <tr>
          <td style="font-size: 0; line-height: 0; border-top: 1px solid #3B82F6;">&nbsp;</td>
        </tr>
      </table>
      <![endif]-->
      <!--[if !mso]><!-->
      <table cellpadding="0" cellspacing="0" border="0" width="40" style="width: 40px;">
        <tr>
          <td style="font-size: 0; line-height: 0; border-top: 1px solid #3B82F6;">&nbsp;</td>
        </tr>
      </table>
      <!--<![endif]-->
    </td>
  </tr>
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #333333; mso-line-height-rule: exactly; line-height: 20px; padding: 0;">
      <a href="mailto:{user_email}" style="color: #3B82F6; text-decoration: none;">{user_email}</a><br />
      {user_phone}<br />
      {user_office_location}
    </td>
  </tr>
  <tr>
    <td style="padding: 12px 0 0 0;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding: 0 12px 0 0;" valign="middle">
            <img src="{organization_logo_url}" width="80" height="30" alt="{organization_name}" style="display: block; border: 0; width: 80px; height: 30px;" />
          </td>
          <td style="border-left: 1px solid #e0e0e0; padding: 0 0 0 12px;" valign="middle">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 11px; font-weight: bold; color: #999999; padding: 0;">
                  {organization_name}
                </td>
              </tr>
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 11px; color: #999999; padding: 2px 0 0 0;">
                  <a href="https://{organization_website}" style="color: #3B82F6; text-decoration: none;">{organization_website}</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>`
    },
    {
      name: "💼 Corporate Professional",
      template: `<!--[if mso]>
<table cellpadding="0" cellspacing="0" border="0" width="500" style="width: 500px;">
<tr><td>
<![endif]-->
<table cellpadding="0" cellspacing="0" border="0" width="500" style="font-family: Arial, Verdana, sans-serif; width: 500px; max-width: 500px;">
  <tr>
    <td>
      <table cellpadding="0" cellspacing="0" border="0" width="100%">
        <tr>
          <td width="90" style="width: 90px; padding: 0 15px 0 0;" valign="top">
            <img src="{organization_logo_url}" width="90" height="50" alt="{organization_name}" style="display: block; border: 0; width: 90px; height: 50px;" />
          </td>
          <td style="border-left: 2px solid #0066CC; padding: 0 0 0 15px;" valign="top">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 18px; font-weight: bold; color: #0066CC; mso-line-height-rule: exactly; line-height: 22px; padding: 0;">
                  {user_full_name}
                </td>
              </tr>
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 14px; color: #666666; mso-line-height-rule: exactly; line-height: 18px; padding: 3px 0 0 0;">
                  {user_job_title}
                </td>
              </tr>
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #999999; mso-line-height-rule: exactly; line-height: 16px; padding: 2px 0 0 0;">
                  {user_department}
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding: 15px 0 0 0;">
      <table cellpadding="0" cellspacing="0" border="0" width="100%">
        <tr>
          <td width="50%" style="width: 50%; padding: 0 10px 0 0;" valign="top">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 10px; color: #999999; text-transform: uppercase; letter-spacing: 1px; mso-line-height-rule: exactly; line-height: 14px; padding: 0 0 3px 0;">
                  CONTACT
                </td>
              </tr>
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; mso-line-height-rule: exactly; line-height: 18px; padding: 0;">
                  <a href="mailto:{user_email}" style="color: #0066CC; text-decoration: none;">{user_email}</a><br />
                  <span style="color: #666666;">{user_phone}</span><br />
                  <span style="color: #666666;">{user_mobile_phone}</span>
                </td>
              </tr>
            </table>
          </td>
          <td width="50%" style="width: 50%; border-left: 1px solid #e0e0e0; padding: 0 0 0 10px;" valign="top">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 10px; color: #999999; text-transform: uppercase; letter-spacing: 1px; mso-line-height-rule: exactly; line-height: 14px; padding: 0 0 3px 0;">
                  LOCATION
                </td>
              </tr>
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #666666; mso-line-height-rule: exactly; line-height: 18px; padding: 0;">
                  {user_office_location}<br />
                  <a href="https://{organization_website}" style="color: #0066CC; text-decoration: none;">{organization_website}</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding: 12px 0 0 0;">
      <a href="{user_linkedin_profile}" style="text-decoration: none;">
        <img src="https://img.icons8.com/fluency/48/000000/linkedin.png" width="20" height="20" alt="LinkedIn" style="display: block; border: 0;" />
      </a>
    </td>
  </tr>
</table>
<!--[if mso]>
</td></tr>
</table>
<![endif]-->`
    },
    {
      name: "🎨 Creative Bold",
      template: `<table cellpadding="0" cellspacing="0" border="0" style="font-family: 'Segoe UI', Arial, sans-serif;">
  <tbody>
    <tr>
      <td style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px 10px 0 0;">
        <table cellpadding="0" cellspacing="0" border="0">
          <tbody>
            <tr>
              <td valign="middle">
                <div style="font-size: 20px; font-weight: bold; color: #ffffff; margin: 0;">{user_full_name}</div>
                <div style="font-size: 14px; color: rgba(255,255,255,0.95); margin: 4px 0 0 0;">{user_job_title}</div>
                <div style="font-size: 13px; color: rgba(255,255,255,0.85);">{organization_name}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
    <tr>
      <td style="padding: 15px 20px; background: #ffffff; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
        <table cellpadding="0" cellspacing="0" border="0">
          <tbody>
            <tr>
              <td style="padding-bottom: 8px;">
                <table cellpadding="0" cellspacing="0" border="0">
                  <tbody>
                    <tr>
                      <td width="16" valign="middle" style="padding-right: 8px;">
                        <img src="https://img.icons8.com/material-rounded/24/667eea/new-post.png" width="14" height="14" alt="Email">
                      </td>
                      <td valign="middle">
                        <a href="mailto:{user_email}" style="color: #667eea; text-decoration: none; font-size: 13px;">{user_email}</a>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding-bottom: 8px;">
                <table cellpadding="0" cellspacing="0" border="0">
                  <tbody>
                    <tr>
                      <td width="16" valign="middle" style="padding-right: 8px;">
                        <img src="https://img.icons8.com/material-rounded/24/667eea/phone.png" width="14" height="14" alt="Phone">
                      </td>
                      <td valign="middle">
                        <span style="color: #555555; font-size: 13px;">{user_phone} • {user_mobile_phone}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding-bottom: 10px;">
                <table cellpadding="0" cellspacing="0" border="0">
                  <tbody>
                    <tr>
                      <td width="16" valign="middle" style="padding-right: 8px;">
                        <img src="https://img.icons8.com/material-rounded/24/667eea/marker.png" width="14" height="14" alt="Location">
                      </td>
                      <td valign="middle">
                        <span style="color: #555555; font-size: 13px;">{user_office_location}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding-top: 10px; border-top: 1px solid #e0e0e0;">
                <table cellpadding="0" cellspacing="0" border="0">
                  <tbody>
                    <tr>
                      <td style="padding-right: 10px;" valign="middle">
                        <img src="{organization_logo_url}" alt="{organization_name}" style="max-height: 30px; max-width: 80px;">
                      </td>
                      <td valign="middle" style="padding-left: 10px; border-left: 1px solid #e0e0e0;">
                        <div style="font-size: 11px; color: #999999;">
                          <a href="https://{organization_website}" style="color: #667eea; text-decoration: none;">{organization_website}</a>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
  </tbody>
</table>`
    },
    {
      name: "🚀 Tech Modern",
      template: `<table cellpadding="0" cellspacing="0" border="0" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
  <tbody>
    <tr>
      <td style="background: #f8f9fa; padding: 16px; border-radius: 8px; border: 1px solid #e1e4e8;">
        <table cellpadding="0" cellspacing="0" border="0">
          <tbody>
            <tr>
              <td width="50" valign="top">
                <div style="width: 44px; height: 44px; background: linear-gradient(135deg, #0969da 0%, #1f883d 100%); border-radius: 8px; text-align: center; line-height: 44px; color: white; font-size: 16px; font-weight: 600;">
                  {user_first_name[0]}{user_last_name[0]}
                </div>
              </td>
              <td style="padding-left: 12px;" valign="top">
                <div style="font-size: 16px; font-weight: 600; color: #24292f;">{user_full_name}</div>
                <div style="font-size: 13px; color: #0969da; margin-top: 2px;">{user_job_title}</div>
                <div style="font-size: 12px; color: #656d76; margin-top: 1px;">{user_department}</div>
              </td>
            </tr>
            <tr>
              <td colspan="2" style="padding-top: 12px;">
                <div style="font-size: 12px; line-height: 1.6; color: #424a53;">
                  <div style="margin-bottom: 3px;">
                    <a href="mailto:{user_email}" style="color: #0969da; text-decoration: none;">{user_email}</a>
                  </div>
                  <div style="margin-bottom: 3px;">{user_phone}</div>
                  <div>{user_office_location}</div>
                </div>
              </td>
            </tr>
            <tr>
              <td colspan="2" style="padding-top: 12px;">
                <table cellpadding="0" cellspacing="0" border="0">
                  <tbody>
                    <tr>
                      <td valign="middle" style="padding-right: 10px;">
                        <img src="{organization_logo_url}" alt="{organization_name}" style="max-height: 24px; max-width: 80px;">
                      </td>
                      <td valign="middle" style="border-left: 1px solid #d1d9e0; padding-left: 10px;">
                        <div style="font-size: 11px; color: #656d76;">
                          <strong>{organization_name}</strong><br>
                          <a href="https://{organization_website}" style="color: #0969da; text-decoration: none;">{organization_website}</a>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            <tr>
              <td colspan="2" style="padding-top: 10px;">
                <a href="{user_linkedin_profile}" style="text-decoration: none; margin-right: 5px;">
                  <img src="https://img.icons8.com/color/48/000000/linkedin.png" width="20" height="20" alt="LinkedIn">
                </a>
                <a href="https://github.com/{user_github_username}" style="text-decoration: none; margin-right: 5px;">
                  <img src="https://img.icons8.com/material-outlined/48/000000/github.png" width="20" height="20" alt="GitHub">
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
  </tbody>
</table>`
    },
    {
      name: "💎 Elegant Classic",
      template: `<table cellpadding="0" cellspacing="0" border="0" style="font-family: Georgia, 'Times New Roman', serif;">
  <tbody>
    <tr>
      <td>
        <table cellpadding="0" cellspacing="0" border="0">
          <tbody>
            <tr>
              <td width="3" style="background-color: #d4af37;"></td>
              <td style="padding-left: 15px;">
                <!-- Name and Title -->
                <div style="font-size: 18px; color: #2c3e50; margin: 0;">{user_full_name}</div>
                <div style="font-size: 13px; color: #d4af37; font-style: italic; margin: 3px 0;">{user_job_title}</div>
                <div style="font-size: 12px; color: #7f8c8d; margin: 2px 0 15px 0;">{organization_name}</div>
                
                <!-- Contact Info -->
                <div style="font-size: 12px; line-height: 1.5; color: #2c3e50;">
                  <div style="margin-bottom: 2px;">{user_email}</div>
                  <div style="margin-bottom: 2px;">{user_phone}</div>
                  <div style="margin-bottom: 2px;">{user_mobile_phone}</div>
                  <div>{user_office_location}</div>
                </div>
                
                <!-- Logo and Website -->
                <table cellpadding="0" cellspacing="0" border="0" style="margin-top: 12px;">
                  <tbody>
                    <tr>
                      <td style="padding-right: 12px;" valign="middle">
                        <img src="{organization_logo_url}" alt="{organization_name}" style="max-height: 35px; max-width: 100px;">
                      </td>
                      <td style="border-left: 1px solid #ecf0f1; padding-left: 12px;" valign="middle">
                        <div style="font-size: 11px; color: #95a5a6;">
                          <a href="https://{organization_website}" style="color: #d4af37; text-decoration: none;">{organization_website}</a>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
  </tbody>
</table>`
    },
    {
      name: "📱 Social Connected",
      template: `<table cellpadding="0" cellspacing="0" border="0" style="font-family: 'Helvetica Neue', Arial, sans-serif;">
  <tbody>
    <tr>
      <td>
        <table cellpadding="0" cellspacing="0" border="0">
          <tbody>
            <!-- Header with Logo and Name -->
            <tr>
              <td width="65" style="padding-right: 12px;" valign="top">
                <img src="{organization_logo_url}" alt="{organization_name}" style="width: 60px; height: 60px; border-radius: 6px; object-fit: contain;">
              </td>
              <td valign="top">
                <div style="font-size: 17px; font-weight: 600; color: #1a1a1a; margin: 0;">{user_full_name}</div>
                <div style="font-size: 14px; color: #0066cc; margin: 3px 0;">{user_job_title}</div>
                <div style="font-size: 13px; color: #666666;">{organization_name}</div>
              </td>
            </tr>
            <!-- Contact Details -->
            <tr>
              <td colspan="2" style="padding-top: 15px;">
                <table cellpadding="0" cellspacing="0" border="0">
                  <tbody>
                    <tr>
                      <td style="font-size: 13px; line-height: 1.6; color: #333333;">
                        <div style="margin-bottom: 3px;">
                          <a href="mailto:{user_email}" style="color: #0066cc; text-decoration: none;">{user_email}</a>
                        </div>
                        <div style="margin-bottom: 3px;">{user_phone} • {user_mobile_phone}</div>
                        <div style="margin-bottom: 3px;">{user_office_location}</div>
                        <div>
                          <a href="https://{organization_website}" style="color: #0066cc; text-decoration: none;">{organization_website}</a>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            <!-- Social Media Buttons -->
            <tr>
              <td colspan="2" style="padding-top: 12px;">
                <table cellpadding="0" cellspacing="0" border="0">
                  <tbody>
                    <tr>
                      <td style="padding-right: 4px;">
                        <a href="{user_linkedin_profile}" style="text-decoration: none;">
                          <div style="background: #0077B5; color: white; padding: 4px 8px; border-radius: 3px; font-size: 11px; font-weight: 500; display: inline-block;">in</div>
                        </a>
                      </td>
                      <td style="padding-right: 4px;">
                        <a href="https://twitter.com/{organization_twitter}" style="text-decoration: none;">
                          <div style="background: #1DA1F2; color: white; padding: 4px 8px; border-radius: 3px; font-size: 11px; font-weight: 500; display: inline-block;">tw</div>
                        </a>
                      </td>
                      <td style="padding-right: 4px;">
                        <a href="https://facebook.com/{organization_facebook}" style="text-decoration: none;">
                          <div style="background: #4267B2; color: white; padding: 4px 8px; border-radius: 3px; font-size: 11px; font-weight: 500; display: inline-block;">fb</div>
                        </a>
                      </td>
                      <td>
                        <a href="https://instagram.com/{organization_instagram}" style="text-decoration: none;">
                          <div style="background: #E4405F; color: white; padding: 4px 8px; border-radius: 3px; font-size: 11px; font-weight: 500; display: inline-block;">ig</div>
                        </a>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
  </tbody>
</table>`
    }
  ];
  
  const [branding, setBranding] = useState<BrandingSettings>({
    primary_color: "#3B82F6",
    secondary_color: "#10B981",
    email_header_html: "",
    login_message: "",
    email_signature_template: "",
    email_signature_enabled: false,
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await tenantSettingsAPI.getSettings();
      const signaturePreview = await tenantSettingsAPI.getEmailSignaturePreview();
      
      if (data.branding_settings) {
        setBranding({
          primary_color: data.branding_settings.primary_color || "#3B82F6",
          secondary_color: data.branding_settings.secondary_color || "#10B981",
          email_header_html: data.branding_settings.email_header_html || "",
          login_message: data.branding_settings.login_message || "",
          email_signature_template: data.branding_settings.email_signature_template || "",
          email_signature_enabled: data.branding_settings.email_signature_enabled || false,
        });
      }
      
      setSignaturePreviewHtml(signaturePreview.preview_html);
      setAvailableVariables(signaturePreview.available_variables);
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

  const updateSignaturePreview = async (template?: string) => {
    try {
      // Pass the current template for preview
      const preview = await tenantSettingsAPI.getEmailSignaturePreview(
        template !== undefined ? template : branding.email_signature_template
      );
      setSignaturePreviewHtml(preview.preview_html);
    } catch (error) {
      console.error("Error updating preview:", error);
    }
  };

  // Update preview when template changes
  useEffect(() => {
    if (branding.email_signature_template && showSignaturePreview) {
      const timeoutId = setTimeout(() => {
        updateSignaturePreview(branding.email_signature_template);
      }, 500); // Debounce for 500ms
      
      return () => clearTimeout(timeoutId);
    }
  }, [branding.email_signature_template, showSignaturePreview]);

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
      
      // Update preview after save with the saved template
      await updateSignaturePreview(branding.email_signature_template);
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

  const useTemplate = (template: string) => {
    setBranding({ ...branding, email_signature_template: template, email_signature_enabled: true });
    toast({
      title: "Template applied",
      description: "The template has been applied to your signature. Remember to save your changes.",
    });
    // Scroll to the signature section
    document.getElementById("signature-template")?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const insertVariable = (variable: string) => {
    const textarea = document.getElementById("signature-template") as HTMLTextAreaElement;
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const newTemplate = (branding.email_signature_template || "").substring(0, start) + 
                       variable + 
                       (branding.email_signature_template || "").substring(end);
    setBranding({ ...branding, email_signature_template: newTemplate });
    
    // Reset cursor position
    setTimeout(() => {
      textarea.focus();
      textarea.selectionStart = start + variable.length;
      textarea.selectionEnd = start + variable.length;
    }, 0);
  };

  const copyVariable = (variable: string) => {
    navigator.clipboard.writeText(variable);
    toast({
      title: "Copied to clipboard",
      description: `Variable ${variable} copied to clipboard.`,
    });
  };

  const getVariableCategoryIcon = (category: keyof EmailSignatureVariables) => {
    switch (category) {
      case "user_basic":
        return <User className="h-4 w-4" />;
      case "user_preferences":
        return <Globe className="h-4 w-4" />;
      case "staff_profile":
        return <Briefcase className="h-4 w-4" />;
      case "organization":
        return <Building className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const getCategoryLabel = (category: keyof EmailSignatureVariables) => {
    switch (category) {
      case "user_basic":
        return "User Information";
      case "user_preferences":
        return "User Preferences";
      case "staff_profile":
        return "Staff Profile";
      case "organization":
        return "Organization";
      default:
        return category;
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
    <div className="p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <Palette className="mr-2 h-6 w-6" />
          Branding Settings
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Customize your organization's branding, colors, and email signatures
        </p>
      </div>

      <div className="space-y-6">
        {/* Colors Section */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
          <div className="p-6 space-y-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">Brand Colors</h2>
            
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
          </div>
        </div>

        {/* Messaging Section */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
          <div className="p-6 space-y-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">Messaging & Content</h2>
            
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
        </div>

        {/* Email Signature Section */}
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Mail className="mr-2 h-5 w-5 text-gray-700 dark:text-gray-300" />
                <h2 className="text-lg font-medium text-gray-900 dark:text-white">Email Signature</h2>
              </div>
              <button
                onClick={() => setBranding({ ...branding, email_signature_enabled: !branding.email_signature_enabled })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  branding.email_signature_enabled ? "bg-blue-600" : "bg-gray-200 dark:bg-gray-700"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    branding.email_signature_enabled ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
            
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Create a standardized email signature template for your organization
            </p>

            {/* Template Editor */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Signature Template
              </label>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Template Input */}
                <div className="lg:col-span-2">
                  <textarea
                    id="signature-template"
                    value={branding.email_signature_template || ""}
                    onChange={(e) => setBranding({ ...branding, email_signature_template: e.target.value })}
                    rows={12}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                    placeholder="Enter your HTML email signature template here..."
                    disabled={!branding.email_signature_enabled}
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Use HTML to format your signature. Insert variables by clicking them from the list.
                  </p>
                </div>

                {/* Variables Panel */}
                <div className="space-y-2">
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Available Variables
                  </div>
                  
                  {/* Category Tabs */}
                  <div className="flex flex-wrap gap-1">
                    {availableVariables && Object.keys(availableVariables).map((category) => (
                      <button
                        key={category}
                        onClick={() => setActiveVariableCategory(category as keyof EmailSignatureVariables)}
                        className={`inline-flex items-center px-2 py-1 text-xs rounded-md transition-colors ${
                          activeVariableCategory === category
                            ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                        }`}
                        disabled={!branding.email_signature_enabled}
                      >
                        {getVariableCategoryIcon(category as keyof EmailSignatureVariables)}
                        <span className="ml-1">{getCategoryLabel(category as keyof EmailSignatureVariables)}</span>
                      </button>
                    ))}
                  </div>
                  
                  {/* Variable List */}
                  <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-2 max-h-64 overflow-y-auto bg-gray-50 dark:bg-gray-800/50">
                    {availableVariables && availableVariables[activeVariableCategory] && (
                      <div className="space-y-1">
                        {availableVariables[activeVariableCategory].map((variable) => (
                          <div
                            key={variable}
                            className="flex items-center justify-between group hover:bg-gray-100 dark:hover:bg-gray-700 rounded px-2 py-1 cursor-pointer"
                            onClick={() => branding.email_signature_enabled && insertVariable(variable)}
                          >
                            <span className="text-xs font-mono text-gray-600 dark:text-gray-400">
                              {variable}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                copyVariable(variable);
                              }}
                              className="opacity-0 group-hover:opacity-100 transition-opacity"
                              disabled={!branding.email_signature_enabled}
                            >
                              <Copy className="h-3 w-3 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Preview Toggle */}
            <div>
              <button
                onClick={() => setShowSignaturePreview(!showSignaturePreview)}
                className="inline-flex items-center text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
              >
                {showSignaturePreview ? (
                  <>
                    <EyeOff className="mr-1 h-4 w-4" />
                    Hide Preview
                  </>
                ) : (
                  <>
                    <Eye className="mr-1 h-4 w-4" />
                    Show Preview
                  </>
                )}
              </button>
            </div>

            {/* Preview */}
            {showSignaturePreview && (
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Preview (with sample data)
                </div>
                <div className="bg-white dark:bg-gray-900 p-4 rounded border border-gray-200 dark:border-gray-700">
                  {signaturePreviewHtml ? (
                    <div dangerouslySetInnerHTML={{ __html: signaturePreviewHtml }} />
                  ) : branding.email_signature_template ? (
                    <div className="text-gray-500 dark:text-gray-400 italic">
                      Processing preview...
                    </div>
                  ) : (
                    <div className="text-gray-500 dark:text-gray-400 italic">
                      No signature template. Add content above to see a preview.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Template Selector */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="flex items-start">
            <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 mr-2 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800 dark:text-blue-300 w-full">
              <p className="font-medium mb-3">Quick Start Templates</p>
              
              <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-blue-200 dark:border-blue-700">
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Choose a professional template:
                </label>
                <select 
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                  onChange={(e) => {
                    const selectedTemplate = templates[parseInt(e.target.value)];
                    if (selectedTemplate) {
                      useTemplate(selectedTemplate.template);
                    }
                  }}
                  defaultValue=""
                >
                  <option value="" disabled>Select a template...</option>
                  {templates.map((t, index) => (
                    <option key={index} value={index}>{t.name}</option>
                  ))}
                </select>
                
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-medium">🏢 Logo-First</span> - Company branding focus
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-medium">✨ Modern Minimal</span> - Clean & simple
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-medium">💼 Corporate</span> - With logo placement
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-medium">🎨 Creative</span> - Gradient design
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-medium">🚀 Tech Startup</span> - Modern avatar
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-medium">💎 Elegant</span> - Logo & classic style
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-medium">📱 Social Rich</span> - With social links
                  </div>
                </div>
              </div>
              
              <div className="mt-4 p-3 bg-blue-100 dark:bg-blue-900/50 rounded">
                <p className="text-xs font-medium">💡 Pro Tips:</p>
                <ul className="text-xs mt-1 space-y-1">
                  <li>• Select a template to instantly apply it</li>
                  <li>• Customize the template to match your brand</li>
                  <li>• Preview shows how it looks with sample data</li>
                  <li>• All user variables will be automatically replaced</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
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