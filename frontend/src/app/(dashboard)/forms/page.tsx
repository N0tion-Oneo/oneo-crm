import FormsManager from '@/components/forms/FormsManager'

export default function FormsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <FormsManager />
      </div>
    </div>
  )
}

export const dynamic = 'force-dynamic'