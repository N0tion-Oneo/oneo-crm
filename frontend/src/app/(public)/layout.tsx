import type { Metadata } from 'next'

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
    <div className="bg-gray-50 min-h-screen antialiased">
      {children}
    </div>
  )
}