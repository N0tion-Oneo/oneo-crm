'use client'

import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CalendarIcon, ClockIcon, CalendarDaysIcon, UsersIcon } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { useToast } from '@/hooks/use-toast'
import AvailabilitySettings from './components/AvailabilitySettings'
import { UnifiedSchedulingSettings } from '@/components/communications/scheduling/UnifiedSchedulingSettings'
import ScheduledMeetings from './components/ScheduledMeetings'

export default function SchedulingPage() {
  const { hasPermission, user } = useAuth()
  const [activeTab, setActiveTab] = useState('availability')
  const [isLoading, setIsLoading] = useState(false)
  
  // Check if user can manage all users' scheduling (admin)
  const canManageAll = hasPermission('communication_settings', 'scheduling_all')

  return (
    <div className="p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Scheduling</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage your availability and meeting types with calendar integration
          </p>
        </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Week</CardTitle>
            <CalendarIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">Meetings scheduled</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Meeting Types</CardTitle>
            <ClockIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
            <p className="text-xs text-muted-foreground">Active types</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
            <UsersIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">68%</div>
            <p className="text-xs text-muted-foreground">View to booking</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="availability" className="flex items-center gap-2">
            <CalendarDaysIcon className="h-4 w-4" />
            Availability
          </TabsTrigger>
          <TabsTrigger value="meeting-types" className="flex items-center gap-2">
            <ClockIcon className="h-4 w-4" />
            Meeting Types
          </TabsTrigger>
          <TabsTrigger value="meetings" className="flex items-center gap-2">
            <CalendarIcon className="h-4 w-4" />
            Scheduled
          </TabsTrigger>
        </TabsList>

        <TabsContent value="availability" className="space-y-4">
          {activeTab === 'availability' && <AvailabilitySettings canManageAll={canManageAll} />}
        </TabsContent>

        <TabsContent value="meeting-types" className="space-y-4">
          {activeTab === 'meeting-types' && <UnifiedSchedulingSettings canManageAll={canManageAll} />}
        </TabsContent>

        <TabsContent value="meetings" className="space-y-4">
          {activeTab === 'meetings' && <ScheduledMeetings canManageAll={canManageAll} />}
        </TabsContent>
      </Tabs>
      </div>
    </div>
  )
}