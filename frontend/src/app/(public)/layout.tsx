import type { Metadata } from 'next'
import '../globals.css'

export const metadata: Metadata = {
  title: 'Public Forms - Oneo CRM',
  description: 'Public forms for data collection and collaboration',
  robots: 'noindex, nofollow', // Prevent search engine indexing of public forms
}

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-gray-50 antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  )
}