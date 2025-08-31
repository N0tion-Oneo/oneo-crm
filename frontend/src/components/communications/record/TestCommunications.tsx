'use client'

import React, { useEffect, useState } from 'react'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'
import Cookies from 'js-cookie'

export function TestCommunications({ recordId }: { recordId: string | number }) {
  // Get access token directly from cookies
  const accessToken = Cookies.get('oneo_access_token')
  const { isAuthenticated } = useAuth()
  const [status, setStatus] = useState<any>({})
  const recordIdStr = recordId ? String(recordId) : ''
  
  useEffect(() => {
    console.log('TestCommunications - Debug', {
      recordId,
      recordIdStr, 
      recordIdType: typeof recordId,
      hasToken: !!accessToken,
      tokenLength: accessToken?.length
    })
    
    if (!accessToken || !recordIdStr) {
      setStatus({ 
        message: 'Missing token or recordId', 
        accessToken: !!accessToken, 
        recordId,
        recordIdStr,
        recordIdType: typeof recordId
      })
      return
    }
    
    const testApi = async () => {
      setStatus({ message: 'Testing API...', recordIdStr })
      
      try {
        // Test without explicit auth header first (axios interceptor should add it)
        const response = await api.get(
          `/api/v1/communications/records/${recordIdStr}/profile/`
        )
        
        setStatus({
          success: true,
          message: 'API Working!',
          data: response.data,
          identifiers: response.data.communication_identifiers
        })
      } catch (error: any) {
        setStatus({
          success: false,
          message: 'API Failed',
          error: error.message,
          response: error.response?.data,
          status: error.response?.status
        })
      }
    }
    
    testApi()
  }, [accessToken, recordIdStr])
  
  return (
    <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded">
      <h3 className="font-bold mb-2">Communication Test Component</h3>
      <pre className="text-xs overflow-auto">
        {JSON.stringify(status, null, 2)}
      </pre>
    </div>
  )
}