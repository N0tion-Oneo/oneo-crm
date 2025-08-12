'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/app-shell'
import { useAuth } from '@/features/auth/context'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    // Only redirect if we're not loading and not authenticated
    if (!isLoading && !isAuthenticated) {
      const currentPath = window.location.pathname
      router.push(`/login?redirect=${encodeURIComponent(currentPath)}`)
    }
  }, [isAuthenticated, isLoading, router])

  // Don't show dashboard loading - let individual pages handle their own loading
  // This eliminates the dashboard loading spinner that cascades with page loading
  if (isLoading) {
    // Still redirect if needed, but don't show loading UI
    return null
  }

  // Don't render dashboard if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null
  }

  return <AppShell>{children}</AppShell>
}