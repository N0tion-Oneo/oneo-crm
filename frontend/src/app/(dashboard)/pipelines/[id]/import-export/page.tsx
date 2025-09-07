'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { 
  Download,
  Upload,
  FileJson,
  FileText,
  FileSpreadsheet,
  CheckCircle,
  AlertCircle,
  Clock
} from 'lucide-react'
import { pipelinesApi } from '@/lib/api'

export default function ImportExportPage() {
  const params = useParams()
  const pipelineId = params.id as string
  const [pipeline, setPipeline] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [exportOptions, setExportOptions] = useState({
    includeSettings: true,
    includeFields: true,
    includeRules: true,
    includeSampleData: false,
    format: 'json'
  })
  const [importFile, setImportFile] = useState<File | null>(null)

  useEffect(() => {
    const loadPipeline = async () => {
      try {
        setLoading(true)
        const response = await pipelinesApi.get(pipelineId)
        setPipeline(response.data)
      } catch (error) {
        console.error('Failed to load pipeline:', error)
      } finally {
        setLoading(false)
      }
    }

    if (pipelineId) {
      loadPipeline()
    }
  }, [pipelineId])

  const handleExport = async () => {
    console.log('Exporting with options:', exportOptions)
    // TODO: Implement export functionality
  }

  const handleImport = async () => {
    if (!importFile) return
    console.log('Importing file:', importFile.name)
    // TODO: Implement import functionality
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImportFile(e.target.files[0])
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/3 mb-8"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Import/Export
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Export pipeline configuration or import data for {pipeline?.name}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Export Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <Download className="w-5 h-5 mr-2" />
              Export Configuration
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeSettings}
                    onChange={(e) => setExportOptions({...exportOptions, includeSettings: e.target.checked})}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                    Pipeline settings
                  </span>
                </label>
              </div>
              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeFields}
                    onChange={(e) => setExportOptions({...exportOptions, includeFields: e.target.checked})}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                    Field definitions
                  </span>
                </label>
              </div>
              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeRules}
                    onChange={(e) => setExportOptions({...exportOptions, includeRules: e.target.checked})}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                    Business rules
                  </span>
                </label>
              </div>
              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeSampleData}
                    onChange={(e) => setExportOptions({...exportOptions, includeSampleData: e.target.checked})}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                    Sample data (10 records)
                  </span>
                </label>
              </div>
              
              <div className="pt-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Format
                </label>
                <select
                  value={exportOptions.format}
                  onChange={(e) => setExportOptions({...exportOptions, format: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md"
                >
                  <option value="json">JSON</option>
                  <option value="csv">CSV</option>
                  <option value="excel">Excel</option>
                </select>
              </div>
              
              <button
                onClick={handleExport}
                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md"
              >
                Export Configuration
              </button>
            </div>
          </div>
        </div>

        {/* Import Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <Upload className="w-5 h-5 mr-2" />
              Import Configuration
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center">
                <input
                  type="file"
                  onChange={handleFileSelect}
                  accept=".json,.csv,.xlsx"
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <Upload className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {importFile ? importFile.name : 'Drop file or click to browse'}
                  </p>
                </label>
              </div>
              
              <div className="space-y-2">
                <label className="flex items-center">
                  <input type="checkbox" className="w-4 h-4 text-blue-600 rounded" />
                  <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                    Override existing settings
                  </span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" className="w-4 h-4 text-blue-600 rounded" />
                  <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                    Merge with current configuration
                  </span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" className="w-4 h-4 text-blue-600 rounded" />
                  <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                    Create as new pipeline
                  </span>
                </label>
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={handleImport}
                  disabled={!importFile}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-md"
                >
                  Import
                </button>
                <button className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                  Preview
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Import History */}
      <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Import History
          </h2>
        </div>
        <div className="p-6">
          <div className="space-y-3">
            <ImportHistoryItem
              filename="config_backup_2024.json"
              date="Jan 10, 2024"
              status="success"
              records={150}
            />
            <ImportHistoryItem
              filename="fields_template.json"
              date="Jan 5, 2024"
              status="success"
              records={0}
            />
            <ImportHistoryItem
              filename="data_migration.csv"
              date="Dec 28, 2023"
              status="warning"
              records={248}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function ImportHistoryItem({ filename, date, status, records }: any) {
  const statusIcons: any = {
    success: <CheckCircle className="w-4 h-4 text-green-500" />,
    warning: <AlertCircle className="w-4 h-4 text-yellow-500" />,
    pending: <Clock className="w-4 h-4 text-gray-400" />
  }

  return (
    <div className="flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-700 rounded">
      <div className="flex items-center">
        {statusIcons[status]}
        <div className="ml-3">
          <div className="text-sm font-medium text-gray-900 dark:text-white">{filename}</div>
          <div className="text-xs text-gray-500">{date} • {records} records</div>
        </div>
      </div>
      <button className="text-sm text-blue-600 hover:underline">Download</button>
    </div>
  )
}