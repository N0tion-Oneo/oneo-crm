'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  ArrowLeft,
  BarChart3,
  TrendingUp,
  Users
} from 'lucide-react'
import Link from 'next/link'
import PortfolioAnalytics from '@/components/communications/portfolio-analytics'

export default function CommunicationAnalyticsPage() {
  const [activeTab, setActiveTab] = useState('portfolio')

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/communications">
              <Button variant="outline" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Communications
              </Button>
            </Link>
            
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Communication Analytics</h1>
              <p className="text-gray-600 dark:text-gray-400">Analyze your communication performance and relationship health</p>
            </div>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 max-w-md">
            <TabsTrigger value="portfolio" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Portfolio
            </TabsTrigger>
            <TabsTrigger value="trends" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Trends
            </TabsTrigger>
            <TabsTrigger value="insights" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Insights
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="portfolio">
            <PortfolioAnalytics />
          </TabsContent>
          
          <TabsContent value="trends">
            <div className="text-center py-12 text-gray-500">
              <TrendingUp className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Communication trends analysis coming soon!</p>
            </div>
          </TabsContent>
          
          <TabsContent value="insights">
            <div className="text-center py-12 text-gray-500">
              <Users className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Advanced insights and recommendations coming soon!</p>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}