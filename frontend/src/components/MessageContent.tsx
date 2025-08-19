'use client'

import { useMemo } from 'react'
import DOMPurify from 'isomorphic-dompurify'

interface MessageContentProps {
  content: string
  isEmail?: boolean
  className?: string
  metadata?: any // Add metadata prop to access raw HTML
}

export function MessageContent({ content, isEmail = false, className = '', metadata }: MessageContentProps) {
  // Safely sanitize HTML content
  const sanitizedContent = useMemo(() => {
    if (!content) return ''
    
    let htmlContent = content
    
    // Debug logging (disabled - enable only for troubleshooting)
    // if (isEmail && process.env.NODE_ENV === 'development') {
    //   console.log('🔍 MessageContent Debug:', {
    //     isEmail,
    //     contentHasHtml: content.includes('<'),
    //     contentPreview: content.substring(0, 100),
    //     metadataExists: !!metadata,
    //     metadataKeys: metadata ? Object.keys(metadata) : null,
    //   })
    // }
    
    // For emails, check if we have HTML content in metadata
    if (isEmail && metadata) {
      // Check various locations where HTML might be stored
      const rawHtml = metadata.raw_webhook_data?.body?.html || 
                     metadata.raw_webhook_data?.body ||
                     metadata.formatted_content?.html
      
      if (rawHtml && typeof rawHtml === 'string' && rawHtml.includes('<')) {
        htmlContent = rawHtml
      } else if (!content.includes('<') && rawHtml) {
        // Even if no HTML tags detected, use the raw content if main content is plain
        htmlContent = String(rawHtml)
      }
    }
    
    // If it looks like HTML content and this is an email, sanitize and render as HTML
    if (isEmail && (htmlContent.includes('<') && htmlContent.includes('>'))) {
      return DOMPurify.sanitize(htmlContent, {
        ALLOWED_TAGS: [
          'p', 'br', 'div', 'span', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li',
          'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'a', 'img', 'table',
          'thead', 'tbody', 'tr', 'th', 'td', 'code', 'pre'
        ],
        ALLOWED_ATTR: [
          'href', 'src', 'alt', 'title', 'style', 'class', 'target', 'rel',
          'width', 'height', 'align', 'valign', 'cellpadding', 'cellspacing',
          'border', 'colspan', 'rowspan'
        ],
        ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i
      })
    }
    
    // Otherwise return as plain text
    return htmlContent
  }, [content, isEmail, metadata])

  // Render HTML content if it's an email and contains HTML
  if (isEmail && sanitizedContent !== content && sanitizedContent.includes('<')) {
    return (
      <div 
        className={`${className}`}
        dangerouslySetInnerHTML={{ __html: sanitizedContent }}
        style={{
          // Email-friendly styling
          lineHeight: '1.6',
          color: 'inherit',
          wordWrap: 'break-word',
          maxWidth: '100%'
        }}
      />
    )
  }

  // Render as plain text
  return <div className={className}>{content}</div>
}