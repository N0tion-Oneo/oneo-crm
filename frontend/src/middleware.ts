import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  // Extract subdomain from hostname
  const hostname = request.nextUrl.hostname
  const isLocalhost = hostname === 'localhost' || hostname.startsWith('127.0.0.1')
  
  let subdomain = ''
  
  if (isLocalhost) {
    // For localhost development, check for subdomain patterns like demo.localhost
    const parts = hostname.split('.')
    if (parts.length > 1 && parts[0] !== 'www') {
      subdomain = parts[0]
    }
  } else {
    // For production, extract subdomain from domain
    const parts = hostname.split('.')
    if (parts.length > 2) {
      subdomain = parts[0]
    }
  }

  // Handle auth routes - redirect authenticated users away from auth pages
  const authRoutes = ['/login', '/register']
  const isAuthRoute = authRoutes.some(route => request.nextUrl.pathname === route)
  
  if (isAuthRoute) {
    // Check for Django session cookie instead of JWT token
    const sessionCookie = request.cookies.get('sessionid')?.value
    
    if (sessionCookie) {
      // User might be authenticated, redirect to dashboard
      return NextResponse.redirect(new URL('/dashboard', request.url))
    }
    
    // Add tenant header for auth pages
    const response = NextResponse.next()
    if (subdomain) {
      response.headers.set('x-tenant-subdomain', subdomain)
    }
    return response
  }

  // Protect authenticated routes - but let the auth context handle the actual authentication check
  // The middleware shouldn't block access since we're using session-based auth that needs server verification
  const protectedRoutes = ['/dashboard', '/users', '/permissions', '/pipelines', '/workflows']
  const isProtectedRoute = protectedRoutes.some(route => 
    request.nextUrl.pathname.startsWith(route)
  )

  if (isProtectedRoute) {
    // Don't block access here - let the auth context handle authentication
    // The auth context will redirect to login if the session is invalid
  }

  // Add tenant and user context headers for all requests
  const response = NextResponse.next()
  
  if (subdomain) {
    response.headers.set('x-tenant-subdomain', subdomain)
  }
  
  // Add tenant context if available
  const tenantCookie = request.cookies.get('oneo_tenant')?.value
  if (tenantCookie) {
    response.headers.set('x-tenant-schema', tenantCookie)
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}