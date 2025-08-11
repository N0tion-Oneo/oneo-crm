// Pagination - Pagination controls component  
import React from 'react'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

export interface PaginationProps {
  currentPage: number
  totalPages: number
  totalRecords: number
  recordsPerPage: number
  onPageChange: (page: number) => void
  onNextPage: () => void
  onPreviousPage: () => void
  hasNext: boolean
  hasPrevious: boolean
  className?: string
}

export function Pagination({
  currentPage,
  totalPages,
  totalRecords,
  recordsPerPage,
  onPageChange,
  onNextPage,
  onPreviousPage,
  hasNext,
  hasPrevious,
  className = ""
}: PaginationProps) {
  if (totalRecords === 0) {
    return null
  }

  const startRecord = (currentPage - 1) * recordsPerPage + 1
  const endRecord = Math.min(currentPage * recordsPerPage, totalRecords)

  // Generate page numbers to show
  const getVisiblePages = (): number[] => {
    const delta = 2 // Number of pages to show on each side of current page
    const pages: number[] = []
    
    // Always show first page
    if (totalPages > 1) {
      pages.push(1)
    }
    
    // Calculate range around current page
    const start = Math.max(2, currentPage - delta)
    const end = Math.min(totalPages - 1, currentPage + delta)
    
    // Add ellipsis after first page if needed
    if (start > 2) {
      pages.push(-1) // -1 represents ellipsis
    }
    
    // Add pages around current page
    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
    
    // Add ellipsis before last page if needed
    if (end < totalPages - 1) {
      pages.push(-2) // -2 represents ellipsis
    }
    
    // Always show last page
    if (totalPages > 1) {
      pages.push(totalPages)
    }
    
    return pages
  }

  const visiblePages = getVisiblePages()

  return (
    <div className={`flex items-center justify-between ${className}`}>
      {/* Records info */}
      <div className="text-sm text-gray-500 dark:text-gray-400">
        Showing {startRecord} to {endRecord} of {totalRecords} records
      </div>

      {/* Pagination controls */}
      {totalPages > 1 && (
        <div className="flex items-center space-x-1">
          {/* First page button */}
          <button
            onClick={() => onPageChange(1)}
            disabled={currentPage === 1}
            className="p-2 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            title="First page"
          >
            <ChevronsLeft className="w-4 h-4" />
          </button>

          {/* Previous page button */}
          <button
            onClick={onPreviousPage}
            disabled={!hasPrevious}
            className="p-2 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Previous page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          {/* Page numbers */}
          <div className="flex items-center space-x-1">
            {visiblePages.map((page, index) => {
              if (page === -1 || page === -2) {
                return (
                  <span
                    key={`ellipsis-${index}`}
                    className="px-3 py-2 text-gray-400 dark:text-gray-500"
                  >
                    ...
                  </span>
                )
              }

              const isCurrentPage = page === currentPage

              return (
                <button
                  key={page}
                  onClick={() => onPageChange(page)}
                  className={`px-3 py-2 text-sm rounded-md transition-colors ${
                    isCurrentPage
                      ? 'bg-primary text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  {page}
                </button>
              )
            })}
          </div>

          {/* Next page button */}
          <button
            onClick={onNextPage}
            disabled={!hasNext}
            className="p-2 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Next page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          {/* Last page button */}
          <button
            onClick={() => onPageChange(totalPages)}
            disabled={currentPage === totalPages}
            className="p-2 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Last page"
          >
            <ChevronsRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}