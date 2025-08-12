// RecordTable - Complete table view with header and rows
import React from 'react'
import { Record, RecordField, Sort, FieldGroup } from '@/types/records'
import { RecordTableHeader } from './RecordTableHeader'
import { RecordTableRow } from './RecordTableRow'

export interface RecordTableProps {
  records: Record[]
  fields: RecordField[]
  fieldGroups?: FieldGroup[]
  sort: Sort
  onSort: (fieldName: string) => void
  selectedRecords: Set<string>
  onSelectRecord: (recordId: string) => void
  onSelectAll: () => void
  onEditRecord: (record: Record) => void
  onDeleteRecord?: (recordId: string) => void
  pipelineId: string
  className?: string
}

export function RecordTable({
  records,
  fields,
  fieldGroups,
  sort,
  onSort,
  selectedRecords,
  onSelectRecord,
  onSelectAll,
  onEditRecord,
  onDeleteRecord,
  pipelineId,
  className = ""
}: RecordTableProps) {
  return (
    <table className={`w-full ${className}`}>
      <RecordTableHeader
        fields={fields}
        fieldGroups={fieldGroups}
        sort={sort}
        onSort={onSort}
        selectedRecords={selectedRecords}
        records={records}
        onSelectAll={onSelectAll}
      />
      
      <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
        {records.map((record) => (
          <RecordTableRow
            key={record.id}
            record={record}
            fields={fields}
            isSelected={selectedRecords.has(record.id)}
            onSelectRecord={onSelectRecord}
            onEditRecord={onEditRecord}
            onDeleteRecord={onDeleteRecord}
            pipelineId={pipelineId}
          />
        ))}
      </tbody>
    </table>
  )
}