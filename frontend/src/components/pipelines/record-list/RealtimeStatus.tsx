// RealtimeStatus - WebSocket connection indicator
import React from 'react'

export interface RealtimeStatusProps {
  isConnected: boolean
  className?: string
}

export function RealtimeStatus({ isConnected, className = "" }: RealtimeStatusProps) {
  return (
    <div className={`flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
      <span>{isConnected ? 'Live' : 'Offline'}</span>
    </div>
  )
}