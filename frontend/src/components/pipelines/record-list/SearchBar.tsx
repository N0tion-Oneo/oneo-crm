// SearchBar - Search input with debouncing
import React, { useState, useEffect, useRef } from 'react'
import { Search } from 'lucide-react'

export interface SearchBarProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  placeholder?: string
  debounceMs?: number
  className?: string
}

export function SearchBar({
  searchQuery,
  onSearchChange,
  placeholder = "Search records...",
  debounceMs = 500,
  className = "w-80"
}: SearchBarProps) {
  const [localQuery, setLocalQuery] = useState(searchQuery)
  const timeoutRef = useRef<NodeJS.Timeout>()

  // Sync local state with prop changes
  useEffect(() => {
    setLocalQuery(searchQuery)
  }, [searchQuery])

  // Debounced search effect
  useEffect(() => {
    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      onSearchChange(localQuery)
    }, debounceMs)

    // Cleanup function
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [localQuery, debounceMs, onSearchChange])

  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
      <input
        type="text"
        placeholder={placeholder}
        value={localQuery}
        onChange={(e) => setLocalQuery(e.target.value)}
        className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white w-full"
      />
    </div>
  )
}