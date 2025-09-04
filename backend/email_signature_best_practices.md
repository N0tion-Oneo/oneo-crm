# Email Signature HTML Best Practices - Implementation Guide

## Key Requirements for Email Signatures (2024)

### 1. HTML Structure Requirements
- **Table-based layout only** - No divs for layout
- **Fixed widths required** - Max 450-600px recommended
- **Inline CSS only** - No external stylesheets or `<style>` blocks
- **MSO conditional comments** for Outlook compatibility

### 2. Image Requirements
- **Fixed dimensions required**: Always set width AND height attributes
- **Formats**: Use .png or .jpg only (no .svg)
- **File size**: Keep under 100KB per image
- **Alt text**: Required for all images
- **Border="0"**: Required to prevent blue borders in some clients

### 3. CSS Best Practices
- **Web-safe fonts only**: Arial, Verdana, Georgia, Times New Roman, sans-serif
- **Font-family on every TD**: Must be repeated in each cell
- **mso-line-height-rule: exactly**: Required before line-height
- **No margins**: Use padding on TD elements only
- **No background images**: Won't work in Outlook

### 4. Link Requirements
- **Full URLs required**: Always include https://
- **text-decoration explicit**: Must set to none or underline
- **Color in style**: Don't rely on default link colors

### 5. Avoid These Elements
- ❌ Bullet points or lists
- ❌ Background gradients (except in MSO conditionals)
- ❌ Float or position CSS
- ❌ JavaScript
- ❌ Forms or input elements
- ❌ SVG images
- ❌ Custom fonts
- ❌ Borders larger than 5px

## Correct Email Signature Template Example

```html
<!--[if mso]>
<table cellpadding="0" cellspacing="0" border="0" width="450" style="width: 450px;">
<tr><td>
<![endif]-->
<table cellpadding="0" cellspacing="0" border="0" width="450" style="font-family: Arial, Verdana, sans-serif; width: 450px; max-width: 450px;">
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 16px; font-weight: bold; color: #333333; mso-line-height-rule: exactly; line-height: 20px; padding: 0;">
      John Smith
    </td>
  </tr>
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 14px; color: #666666; mso-line-height-rule: exactly; line-height: 18px; padding: 2px 0 0 0;">
      Senior Developer
    </td>
  </tr>
  <tr>
    <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #999999; mso-line-height-rule: exactly; line-height: 16px; padding: 2px 0 10px 0;">
      Engineering Department
    </td>
  </tr>
  <!-- Divider Line -->
  <tr>
    <td style="padding: 8px 0;">
      <table cellpadding="0" cellspacing="0" border="0" width="50">
        <tr>
          <td style="font-size: 0; line-height: 0; border-top: 2px solid #0066CC;">&nbsp;</td>
        </tr>
      </table>
    </td>
  </tr>
  <!-- Contact Info -->
  <tr>
    <td style="padding: 0;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; mso-line-height-rule: exactly; line-height: 18px; padding: 0 0 3px 0;">
            <a href="mailto:john.smith@company.com" style="color: #0066CC; text-decoration: none;">john.smith@company.com</a>
          </td>
        </tr>
        <tr>
          <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #666666; mso-line-height-rule: exactly; line-height: 18px; padding: 0 0 3px 0;">
            +1 (555) 123-4567
          </td>
        </tr>
        <tr>
          <td style="font-family: Arial, Verdana, sans-serif; font-size: 13px; color: #666666; mso-line-height-rule: exactly; line-height: 18px; padding: 0 0 10px 0;">
            123 Main Street, City, State 12345
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <!-- Logo and Company -->
  <tr>
    <td style="padding: 10px 0 0 0;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding: 0 12px 0 0;" valign="middle">
            <img src="https://example.com/logo.png" width="100" height="40" alt="Company Logo" style="display: block; border: 0;" />
          </td>
          <td style="border-left: 1px solid #e0e0e0; padding: 0 0 0 12px;" valign="middle">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 12px; font-weight: bold; color: #333333; padding: 0 0 2px 0;">
                  Company Name Inc.
                </td>
              </tr>
              <tr>
                <td style="font-family: Arial, Verdana, sans-serif; font-size: 11px; padding: 0;">
                  <a href="https://www.company.com" style="color: #0066CC; text-decoration: none;">www.company.com</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <!-- Social Icons -->
  <tr>
    <td style="padding: 10px 0 0 0;">
      <table cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding: 0 5px 0 0;">
            <a href="https://linkedin.com/in/username" style="text-decoration: none;">
              <img src="https://img.icons8.com/color/48/000000/linkedin.png" width="20" height="20" alt="LinkedIn" style="display: block; border: 0;" />
            </a>
          </td>
          <td style="padding: 0 5px 0 0;">
            <a href="https://twitter.com/username" style="text-decoration: none;">
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
<![endif]-->
```

## Testing Checklist

1. ✅ Test in Outlook 2016/2019 (Windows)
2. ✅ Test in Outlook 365 (Web)
3. ✅ Test in Gmail (Web and Mobile)
4. ✅ Test in Apple Mail (Mac and iOS)
5. ✅ Test in Yahoo Mail
6. ✅ Test width on mobile devices (should be responsive)
7. ✅ Verify images display with alt text when blocked
8. ✅ Check link colors and underlines
9. ✅ Verify font fallbacks work correctly

## Common Issues and Fixes

### Outlook Issues
- **Images not displaying correctly**: Always set width AND height attributes
- **Spacing issues**: Use padding on TD, never margins
- **Font issues**: Repeat font-family in every TD element
- **Line height issues**: Always use mso-line-height-rule: exactly

### Gmail Issues
- **Styles being stripped**: Use inline styles only
- **Images blocked**: Include meaningful alt text
- **Links not styled**: Explicitly set text-decoration and color

### Mobile Issues
- **Signature too wide**: Keep max-width at 450px
- **Text too small**: Use minimum 13px font size
- **Links too close**: Add adequate padding between clickable elements