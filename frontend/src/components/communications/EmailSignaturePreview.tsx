import React, { useEffect, useRef } from 'react'

interface EmailSignaturePreviewProps {
  html: string
  className?: string
}

export function EmailSignaturePreview({ html, className = '' }: EmailSignaturePreviewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    if (iframeRef.current && html) {
      const iframe = iframeRef.current
      const doc = iframe.contentDocument || iframe.contentWindow?.document
      
      if (doc) {
        // Create a complete HTML document with the signature
        const fullHtml = `
          <!DOCTYPE html>
          <html>
          <head>
            <meta charset="utf-8">
            <style>
              body {
                margin: 0;
                padding: 10px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                line-height: 1.4;
                color: #333;
                background: white;
              }
              /* Reset any inherited styles */
              * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
              }
              /* Ensure tables render as intended */
              table {
                border-collapse: collapse;
                mso-table-lspace: 0pt;
                mso-table-rspace: 0pt;
              }
              /* Ensure images display properly */
              img {
                border: 0;
                outline: none;
                text-decoration: none;
                display: block;
              }
              /* Links should use their inline styles */
              a {
                text-decoration: none;
              }
            </style>
          </head>
          <body>
            ${html}
          </body>
          </html>
        `
        
        doc.open()
        doc.write(fullHtml)
        doc.close()
        
        // Adjust iframe height to content
        const adjustHeight = () => {
          const contentHeight = doc.body.scrollHeight
          iframe.style.height = `${contentHeight + 20}px`
        }
        
        // Wait for images to load before adjusting height
        const images = doc.getElementsByTagName('img')
        if (images.length > 0) {
          let loadedImages = 0
          const checkAllLoaded = () => {
            loadedImages++
            if (loadedImages === images.length) {
              adjustHeight()
            }
          }
          
          Array.from(images).forEach(img => {
            if (img.complete) {
              checkAllLoaded()
            } else {
              img.addEventListener('load', checkAllLoaded)
              img.addEventListener('error', checkAllLoaded)
            }
          })
        } else {
          // No images, adjust height immediately
          adjustHeight()
        }
        
        // Also adjust on window resize
        iframe.contentWindow?.addEventListener('resize', adjustHeight)
      }
    }
  }, [html])

  return (
    <iframe
      ref={iframeRef}
      className={`w-full border-0 ${className}`}
      style={{ minHeight: '100px' }}
      title="Email Signature Preview"
      sandbox="allow-same-origin"
    />
  )
}