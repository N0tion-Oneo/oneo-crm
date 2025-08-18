"use client"

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { 
  TrendingUp, 
  TrendingDown,
  BarChart3,
  Users,
  MessageSquare,
  Target,
  Activity,
  Star,
  AlertTriangle,
  CheckCircle2,
  Heart,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Mail,
  Phone,
  MessageCircle,
  Linkedin,
  Instagram,
  ExternalLink
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

// Types
interface PortfolioRecord {
  record_id: number
  record_title: string
  total_messages: number
  health_score: number
  response_rate: number
  last_contact: string | null
}

interface PortfolioAnalytics {
  total_active_records: number
  top_records_by_health: PortfolioRecord[]
  records_needing_attention: PortfolioRecord[]
  portfolio_summary: {
    avg_health_score: number
    avg_response_rate: number
    total_messages: number
  }
}

interface InsightData {
  portfolio_health: {
    total_active_records: number
    avg_health_score: number
    avg_response_rate: number
    total_messages: number
  }
  top_performers: PortfolioRecord[]
  needs_attention: PortfolioRecord[]
  key_insights: Array<{
    type: 'positive' | 'warning' | 'action'
    title: string
    description: string
  }>
}

interface PortfolioAnalyticsProps {
  className?: string
}

export default function PortfolioAnalytics({ className = "" }: PortfolioAnalyticsProps) {
  const [portfolioData, setPortfolioData] = useState<PortfolioAnalytics | null>(null)
  const [insightData, setInsightData] = useState<InsightData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'insights'>('overview')

  // Fetch portfolio analytics
  useEffect(() => {
    fetchPortfolioData()
    fetchInsightData()
  }, [])

  const fetchPortfolioData = async () => {
    try {
      const response = await fetch('/api/v1/communications/analytics/portfolio_overview/')
      if (response.ok) {
        const result = await response.json()
        setPortfolioData(result.data)
      }
    } catch (error) {
      console.error('Error fetching portfolio analytics:', error)
    }
  }

  const fetchInsightData = async () => {
    try {
      const response = await fetch('/api/v1/communications/analytics/insights_dashboard/')
      if (response.ok) {
        const result = await response.json()
        setInsightData(result.data)
      }
    } catch (error) {
      console.error('Error fetching insights:', error)
    } finally {
      setLoading(false)
    }
  }

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-50 border-green-200'
    if (score >= 60) return 'text-blue-600 bg-blue-50 border-blue-200'
    if (score >= 40) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    if (score >= 20) return 'text-orange-600 bg-orange-50 border-orange-200'
    return 'text-red-600 bg-red-50 border-red-200'
  }

  const getHealthIcon = (score: number) => {
    if (score >= 80) return <Award className="h-4 w-4 text-green-600" />
    if (score >= 60) return <CheckCircle2 className="h-4 w-4 text-blue-600" />
    if (score >= 40) return <Clock className="h-4 w-4 text-yellow-600" />
    return <AlertTriangle className="h-4 w-4 text-red-600" />
  }

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'positive': return <CheckCircle2 className="h-4 w-4 text-green-600" />
      case 'warning': return <AlertTriangle className="h-4 w-4 text-yellow-600" />
      case 'action': return <Target className="h-4 w-4 text-red-600" />
      default: return <CheckCircle2 className="h-4 w-4 text-blue-600" />
    }
  }

  const getInsightColor = (type: string) => {
    switch (type) {
      case 'positive': return 'bg-green-50 border-green-200'
      case 'warning': return 'bg-yellow-50 border-yellow-200'
      case 'action': return 'bg-red-50 border-red-200'
      default: return 'bg-blue-50 border-blue-200'
    }
  }

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

  return (
    <Card className={className}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Portfolio Analytics
          </CardTitle>
          
          <div className="flex gap-1">
            <Button
              variant={activeTab === 'overview' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('overview')}
            >
              Overview
            </Button>
            <Button
              variant={activeTab === 'insights' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('insights')}
            >
              Insights
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {activeTab === 'overview' && portfolioData && (
          <div className="space-y-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium">Active Records</span>
                  </div>
                  <p className="text-2xl font-bold mt-1">{portfolioData.total_active_records}</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <Heart className="h-4 w-4 text-red-600" />
                    <span className="text-sm font-medium">Avg Health Score</span>
                  </div>
                  <p className="text-2xl font-bold mt-1">{portfolioData.portfolio_summary.avg_health_score.toFixed(1)}</p>
                  <Progress value={portfolioData.portfolio_summary.avg_health_score} className="mt-2" />
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium">Avg Response Rate</span>
                  </div>
                  <p className="text-2xl font-bold mt-1">{portfolioData.portfolio_summary.avg_response_rate.toFixed(1)}%</p>
                  <Progress value={portfolioData.portfolio_summary.avg_response_rate} className="mt-2" />
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-purple-600" />
                    <span className="text-sm font-medium">Total Messages</span>
                  </div>
                  <p className="text-2xl font-bold mt-1">{portfolioData.portfolio_summary.total_messages.toLocaleString()}</p>
                </CardContent>
              </Card>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Performers */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Star className="h-5 w-5 text-yellow-500" />
                    Top Performers
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-80">
                    <div className="space-y-3">
                      {portfolioData.top_records_by_health.slice(0, 10).map((record, index) => (
                        <div key={record.record_id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-sm font-medium">
                              {index + 1}
                            </div>
                            <div>
                              <p className="font-medium text-sm">{record.record_title}</p>
                              <p className="text-xs text-gray-500">
                                {record.total_messages} messages • {record.response_rate.toFixed(1)}% response
                              </p>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            {getHealthIcon(record.health_score)}
                            <Badge className={getHealthColor(record.health_score)}>
                              {record.health_score.toFixed(1)}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
              
              {/* Records Needing Attention */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                    Needs Attention
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-80">
                    {portfolioData.records_needing_attention.length > 0 ? (
                      <div className="space-y-3">
                        {portfolioData.records_needing_attention.map((record) => (
                          <div key={record.record_id} className="flex items-center justify-between p-3 border border-red-200 rounded-lg bg-red-50">
                            <div>
                              <p className="font-medium text-sm">{record.record_title}</p>
                              <p className="text-xs text-gray-600">
                                {record.total_messages} messages • {record.response_rate.toFixed(1)}% response
                              </p>
                              {record.last_contact && (
                                <p className="text-xs text-gray-500">
                                  Last contact: {formatDistanceToNow(new Date(record.last_contact), { addSuffix: true })}
                                </p>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4 text-red-600" />
                              <Badge className={getHealthColor(record.health_score)}>
                                {record.health_score.toFixed(1)}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-500" />
                        <p className="text-sm">All relationships are healthy!</p>
                        <p className="text-xs">No records require immediate attention.</p>
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
        
        {activeTab === 'insights' && insightData && (
          <div className="space-y-6">
            {/* Key Insights */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Key Insights</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {insightData.key_insights.length > 0 ? (
                    insightData.key_insights.map((insight, index) => (
                      <div key={index} className={`border rounded-lg p-4 ${getInsightColor(insight.type)}`}>
                        <div className="flex items-start gap-3">
                          {getInsightIcon(insight.type)}
                          <div className="flex-1">
                            <h4 className="font-medium text-sm">{insight.title}</h4>
                            <p className="text-sm text-gray-600 mt-1">{insight.description}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <BarChart3 className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                      <p className="text-sm">No insights available</p>
                      <p className="text-xs">Insights will appear as you accumulate more communication data.</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
            
            {/* Portfolio Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Portfolio Health Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[
                      { range: '80-100', label: 'Excellent', color: 'bg-green-500', count: insightData.top_performers.filter(r => r.health_score >= 80).length },
                      { range: '60-79', label: 'Good', color: 'bg-blue-500', count: insightData.top_performers.filter(r => r.health_score >= 60 && r.health_score < 80).length },
                      { range: '40-59', label: 'Fair', color: 'bg-yellow-500', count: insightData.top_performers.filter(r => r.health_score >= 40 && r.health_score < 60).length },
                      { range: '20-39', label: 'Poor', color: 'bg-orange-500', count: insightData.top_performers.filter(r => r.health_score >= 20 && r.health_score < 40).length },
                      { range: '0-19', label: 'Critical', color: 'bg-red-500', count: insightData.needs_attention.filter(r => r.health_score < 20).length }
                    ].map((item) => (
                      <div key={item.range} className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded ${item.color}`}></div>
                        <span className="text-sm flex-1">{item.label} ({item.range})</span>
                        <span className="text-sm font-medium">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Quick Actions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <Button variant="outline" className="w-full justify-start" size="sm">
                      <TrendingUp className="h-4 w-4 mr-2" />
                      View Detailed Analytics
                    </Button>
                    
                    <Button variant="outline" className="w-full justify-start" size="sm">
                      <MessageSquare className="h-4 w-4 mr-2" />
                      Bulk Message Campaign
                    </Button>
                    
                    <Button variant="outline" className="w-full justify-start" size="sm">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Export Portfolio Report
                    </Button>
                    
                    <Button variant="outline" className="w-full justify-start" size="sm">
                      <Target className="h-4 w-4 mr-2" />
                      Review Priority Records
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}