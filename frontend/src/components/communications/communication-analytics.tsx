"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { 
  TrendingUp, 
  TrendingDown,
  Activity,
  MessageSquare,
  Users,
  Calendar,
  Clock,
  Target,
  AlertCircle,
  CheckCircle2,
  BarChart3,
  PieChart,
  LineChart,
  Heart,
  Zap,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Mail,
  Phone,
  MessageCircle,
  Linkedin,
  Instagram,
  Star,
  AlertTriangle,
  Info,
  Lightbulb
} from 'lucide-react'
import { formatDistanceToNow, format, parseISO } from 'date-fns'

// Types
interface AnalyticsData {
  record_id: number
  record_title: string
  period_days: number
  summary: {
    total_messages: number
    outbound_messages: number
    inbound_messages: number
    response_rate: number
    initiation_rate: number
    unique_conversations: number
    active_channels: number
    first_contact: string | null
    last_contact: string | null
  }
  channel_breakdown: Record<string, {
    total_messages: number
    outbound_messages: number
    inbound_messages: number
    response_rate: number
    message_share: number
    avg_response_time_hours: number | null
    last_activity: string | null
  }>
  engagement_metrics: {
    avg_message_length: number
    avg_conversation_depth: number
    subject_line_usage_rate: number
    attachment_usage_rate: number
    engagement_score: number
  }
  response_patterns: {
    weekday_distribution: Record<string, number>
    hourly_distribution: Record<string, number>
    peak_weekday: string
    peak_hour: number
    avg_response_time_hours: number | null
    median_response_time_hours: number | null
    response_consistency: string
  }
  communication_trends: {
    daily_message_counts: Record<string, number>
    daily_outbound_counts: Record<string, number>
    daily_inbound_counts: Record<string, number>
    trend_direction: string
    peak_activity_date: string | null
    total_active_days: number
  }
  relationship_health: {
    health_score: number
    status: string
    communication_balance: number
    response_rate: number
    initiation_balance: number
    recent_activity: number
    relationship_age_days: number
  }
  recommendations: Array<{
    type: string
    priority: string
    title: string
    description: string
    action: string
  }>
}

interface CommunicationAnalyticsProps {
  recordId: number
  recordTitle: string
  className?: string
}

export default function CommunicationAnalytics({ 
  recordId, 
  recordTitle, 
  className = "" 
}: CommunicationAnalyticsProps) {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedPeriod, setSelectedPeriod] = useState(30)

  // Fetch analytics data
  useEffect(() => {
    fetchAnalytics()
  }, [recordId, selectedPeriod])

  const fetchAnalytics = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/communications/analytics/${recordId}/record_analytics/?days=${selectedPeriod}`)
      
      if (response.ok) {
        const result = await response.json()
        setAnalyticsData(result.data)
      }
    } catch (error) {
      console.error('Error fetching analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  // Helper functions
  const getChannelIcon = (channelType: string) => {
    switch (channelType) {
      case 'whatsapp': return <MessageCircle className="h-4 w-4" />
      case 'linkedin': return <Linkedin className="h-4 w-4" />
      case 'gmail':
      case 'outlook':
      case 'mail': return <Mail className="h-4 w-4" />
      case 'phone': return <Phone className="h-4 w-4" />
      case 'instagram': return <Instagram className="h-4 w-4" />
      default: return <MessageSquare className="h-4 w-4" />
    }
  }

  const getChannelColor = (channelType: string) => {
    switch (channelType) {
      case 'whatsapp': return 'bg-green-500'
      case 'linkedin': return 'bg-blue-600'
      case 'gmail': return 'bg-red-500'
      case 'outlook': return 'bg-blue-500'
      case 'instagram': return 'bg-purple-500'
      default: return 'bg-gray-500'
    }
  }

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-50 border-green-200'
    if (score >= 60) return 'text-blue-600 bg-blue-50 border-blue-200'
    if (score >= 40) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    if (score >= 20) return 'text-orange-600 bg-orange-50 border-orange-200'
    return 'text-red-600 bg-red-50 border-red-200'
  }

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'excellent': return <Award className="h-4 w-4 text-green-600" />
      case 'good': return <CheckCircle2 className="h-4 w-4 text-blue-600" />
      case 'fair': return <AlertCircle className="h-4 w-4 text-yellow-600" />
      case 'poor': return <AlertTriangle className="h-4 w-4 text-orange-600" />
      case 'critical': return <AlertCircle className="h-4 w-4 text-red-600" />
      default: return <Info className="h-4 w-4 text-gray-600" />
    }
  }

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case 'increasing': return <ArrowUpRight className="h-4 w-4 text-green-600" />
      case 'decreasing': return <ArrowDownRight className="h-4 w-4 text-red-600" />
      case 'stable': return <Minus className="h-4 w-4 text-gray-600" />
      default: return <Info className="h-4 w-4 text-gray-600" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-50 border-red-200'
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const formatResponseTime = (hours: number | null) => {
    if (!hours) return 'N/A'
    if (hours < 1) return `${Math.round(hours * 60)}m`
    if (hours < 24) return `${Math.round(hours)}h`
    return `${Math.round(hours / 24)}d`
  }

  // Calculate chart data
  const weekdayChartData = useMemo(() => {
    if (!analyticsData) return []
    
    const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return weekdays.map(day => ({
      day: day.slice(0, 3),
      messages: analyticsData.response_patterns.weekday_distribution[day] || 0
    }))
  }, [analyticsData])

  const channelChartData = useMemo(() => {
    if (!analyticsData) return []
    
    return Object.entries(analyticsData.channel_breakdown).map(([channel, data]) => ({
      channel,
      messages: data.total_messages,
      share: data.message_share
    }))
  }, [analyticsData])

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!analyticsData) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            <BarChart3 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No analytics data available</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Communication Analytics
            <Badge variant="outline">{recordTitle}</Badge>
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(parseInt(e.target.value))}
              className="text-sm border rounded px-2 py-1"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="engagement">Engagement</TabsTrigger>
            <TabsTrigger value="patterns">Patterns</TabsTrigger>
            <TabsTrigger value="health">Health</TabsTrigger>
          </TabsList>
          
          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium">Total Messages</span>
                  </div>
                  <p className="text-2xl font-bold mt-1">{analyticsData.summary.total_messages}</p>
                  <p className="text-xs text-gray-500">
                    {analyticsData.summary.outbound_messages} sent • {analyticsData.summary.inbound_messages} received
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium">Response Rate</span>
                  </div>
                  <p className="text-2xl font-bold mt-1">{analyticsData.summary.response_rate.toFixed(1)}%</p>
                  <Progress value={analyticsData.summary.response_rate} className="mt-2" />
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-purple-600" />
                    <span className="text-sm font-medium">Conversations</span>
                  </div>
                  <p className="text-2xl font-bold mt-1">{analyticsData.summary.unique_conversations}</p>
                  <p className="text-xs text-gray-500">
                    Across {analyticsData.summary.active_channels} channels
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-orange-600" />
                    <span className="text-sm font-medium">Active Days</span>
                  </div>
                  <p className="text-2xl font-bold mt-1">{analyticsData.communication_trends.total_active_days}</p>
                  <p className="text-xs text-gray-500">
                    Out of {analyticsData.period_days} days
                  </p>
                </CardContent>
              </Card>
            </div>
            
            {/* Channel Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Channel Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(analyticsData.channel_breakdown).map(([channel, data]) => (
                    <div key={channel} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full text-white ${getChannelColor(channel)}`}>
                          {getChannelIcon(channel)}
                        </div>
                        <div>
                          <p className="font-medium capitalize">{channel}</p>
                          <p className="text-sm text-gray-500">
                            {data.total_messages} messages • {data.message_share.toFixed(1)}% share
                          </p>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <p className="text-sm font-medium">{data.response_rate.toFixed(1)}% response</p>
                        <p className="text-xs text-gray-500">
                          Avg: {formatResponseTime(data.avg_response_time_hours)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Engagement Tab */}
          <TabsContent value="engagement" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Engagement Metrics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Engagement Score</span>
                    <Badge className={getHealthColor(analyticsData.engagement_metrics.engagement_score)}>
                      {analyticsData.engagement_metrics.engagement_score.toFixed(1)}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Avg Message Length</span>
                    <span className="font-medium">{analyticsData.engagement_metrics.avg_message_length} chars</span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Conversation Depth</span>
                    <span className="font-medium">{analyticsData.engagement_metrics.avg_conversation_depth.toFixed(1)} msgs</span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Subject Line Usage</span>
                    <span className="font-medium">{analyticsData.engagement_metrics.subject_line_usage_rate.toFixed(1)}%</span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Attachment Usage</span>
                    <span className="font-medium">{analyticsData.engagement_metrics.attachment_usage_rate.toFixed(1)}%</span>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Communication Trends</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-2">
                    {getTrendIcon(analyticsData.communication_trends.trend_direction)}
                    <span className="font-medium capitalize">
                      {analyticsData.communication_trends.trend_direction.replace('_', ' ')}
                    </span>
                  </div>
                  
                  {analyticsData.communication_trends.peak_activity_date && (
                    <div>
                      <p className="text-sm text-gray-500">Peak Activity</p>
                      <p className="font-medium">
                        {format(parseISO(analyticsData.communication_trends.peak_activity_date), 'MMM d, yyyy')}
                      </p>
                    </div>
                  )}
                  
                  <div className="space-y-2">
                    <p className="text-sm text-gray-500">Recent Activity</p>
                    <div className="grid grid-cols-7 gap-1">
                      {Object.entries(analyticsData.communication_trends.daily_message_counts)
                        .slice(-7)
                        .map(([date, count]) => (
                          <div key={date} className="text-center">
                            <div 
                              className="h-8 bg-blue-100 rounded flex items-end justify-center"
                              style={{ 
                                backgroundColor: count > 0 ? `rgba(59, 130, 246, ${Math.min(count / 10, 1)})` : '#f3f4f6' 
                              }}
                            >
                              <span className="text-xs text-white font-medium">
                                {count > 0 ? count : ''}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              {format(parseISO(date), 'EEE')}
                            </p>
                          </div>
                        ))
                      }
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* Patterns Tab */}
          <TabsContent value="patterns" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Weekly Patterns</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Peak Day</span>
                      <Badge variant="outline">{analyticsData.response_patterns.peak_weekday}</Badge>
                    </div>
                    
                    <div className="space-y-2">
                      {weekdayChartData.map((item) => (
                        <div key={item.day} className="flex items-center gap-3">
                          <span className="text-sm w-8">{item.day}</span>
                          <div className="flex-1 bg-gray-100 rounded-full h-2">
                            <div 
                              className="bg-blue-500 h-2 rounded-full"
                              style={{ 
                                width: `${(item.messages / Math.max(...weekdayChartData.map(d => d.messages))) * 100}%` 
                              }}
                            />
                          </div>
                          <span className="text-sm w-8 text-right">{item.messages}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Response Timing</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Peak Hour</span>
                    <Badge variant="outline">
                      {analyticsData.response_patterns.peak_hour}:00
                    </Badge>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Avg Response Time</span>
                    <span className="font-medium">
                      {formatResponseTime(analyticsData.response_patterns.avg_response_time_hours)}
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Median Response Time</span>
                    <span className="font-medium">
                      {formatResponseTime(analyticsData.response_patterns.median_response_time_hours)}
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Response Consistency</span>
                    <Badge variant="outline" className="capitalize">
                      {analyticsData.response_patterns.response_consistency.replace('_', ' ')}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* Health Tab */}
          <TabsContent value="health" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Heart className="h-5 w-5 text-red-500" />
                    Relationship Health
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      {getHealthIcon(analyticsData.relationship_health.status)}
                      <span className="text-3xl font-bold">
                        {analyticsData.relationship_health.health_score}
                      </span>
                    </div>
                    <Badge className={getHealthColor(analyticsData.relationship_health.health_score)}>
                      {analyticsData.relationship_health.status.charAt(0).toUpperCase() + 
                       analyticsData.relationship_health.status.slice(1)}
                    </Badge>
                  </div>
                  
                  <Separator />
                  
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Communication Balance</span>
                        <span>{analyticsData.relationship_health.communication_balance.toFixed(1)}%</span>
                      </div>
                      <Progress value={analyticsData.relationship_health.communication_balance} />
                    </div>
                    
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Response Rate</span>
                        <span>{analyticsData.relationship_health.response_rate.toFixed(1)}%</span>
                      </div>
                      <Progress value={analyticsData.relationship_health.response_rate} />
                    </div>
                    
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Initiation Balance</span>
                        <span>{analyticsData.relationship_health.initiation_balance.toFixed(1)}%</span>
                      </div>
                      <Progress value={analyticsData.relationship_health.initiation_balance} />
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm">
                    <span>Relationship Age</span>
                    <span className="font-medium">
                      {analyticsData.relationship_health.relationship_age_days} days
                    </span>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Lightbulb className="h-5 w-5 text-yellow-500" />
                    Recommendations
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-64">
                    <div className="space-y-3">
                      {analyticsData.recommendations.length > 0 ? (
                        analyticsData.recommendations.map((rec, index) => (
                          <div key={index} className="border rounded-lg p-3">
                            <div className="flex items-start gap-2 mb-2">
                              <Badge className={getPriorityColor(rec.priority)}>
                                {rec.priority}
                              </Badge>
                              <div className="flex-1">
                                <p className="font-medium text-sm">{rec.title}</p>
                                <p className="text-xs text-gray-600 mt-1">{rec.description}</p>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-8 text-gray-500">
                          <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-500" />
                          <p className="text-sm">No recommendations at this time</p>
                          <p className="text-xs">Your communication is performing well!</p>
                        </div>
                      )}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}