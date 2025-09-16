'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Zap,
  Timer,
  Users,
  Target,
  Layers
} from 'lucide-react';
import { workflowsApi } from '@/lib/api';

interface WorkflowAnalyticsProps {
  workflowId?: string;
}

export function WorkflowAnalytics({ workflowId }: WorkflowAnalyticsProps) {
  const [timeRange, setTimeRange] = useState('7d');
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, [workflowId, timeRange]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      // This would call the actual API endpoint
      // const response = await workflowsApi.getAnalytics(workflowId, { timeRange });
      // For now, using mock data
      setAnalytics(getMockAnalytics());
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMockAnalytics = () => ({
    overview: {
      totalExecutions: 1234,
      successRate: 92.5,
      averageDuration: 45.2,
      activeWorkflows: 28,
      failedExecutions: 93,
      pendingApprovals: 7
    },
    executionTrend: [
      { date: '2024-01-01', success: 45, failed: 3, total: 48 },
      { date: '2024-01-02', success: 52, failed: 5, total: 57 },
      { date: '2024-01-03', success: 38, failed: 2, total: 40 },
      { date: '2024-01-04', success: 61, failed: 4, total: 65 },
      { date: '2024-01-05', success: 55, failed: 6, total: 61 },
      { date: '2024-01-06', success: 49, failed: 3, total: 52 },
      { date: '2024-01-07', success: 58, failed: 5, total: 63 }
    ],
    performanceByNode: [
      { node: 'Email Send', avgDuration: 2.3, executions: 456, successRate: 98 },
      { node: 'AI Analysis', avgDuration: 8.7, executions: 234, successRate: 95 },
      { node: 'Record Update', avgDuration: 1.2, executions: 678, successRate: 99 },
      { node: 'HTTP Request', avgDuration: 5.4, executions: 123, successRate: 87 },
      { node: 'Condition Check', avgDuration: 0.3, executions: 890, successRate: 100 }
    ],
    triggerDistribution: [
      { name: 'Manual', value: 30, color: '#3b82f6' },
      { name: 'Schedule', value: 25, color: '#10b981' },
      { name: 'Webhook', value: 20, color: '#f59e0b' },
      { name: 'Record Event', value: 15, color: '#8b5cf6' },
      { name: 'Email Received', value: 10, color: '#ef4444' }
    ],
    topWorkflows: [
      { name: 'Customer Onboarding', executions: 234, successRate: 95, avgDuration: 32 },
      { name: 'Lead Qualification', executions: 189, successRate: 92, avgDuration: 18 },
      { name: 'Support Escalation', executions: 156, successRate: 88, avgDuration: 45 },
      { name: 'Document Approval', executions: 98, successRate: 94, avgDuration: 120 },
      { name: 'Data Sync', executions: 456, successRate: 99, avgDuration: 5 }
    ],
    errorPatterns: [
      { error: 'API Rate Limit', count: 23, trend: 'increasing' },
      { error: 'Timeout', count: 18, trend: 'stable' },
      { error: 'Invalid Data', count: 12, trend: 'decreasing' },
      { error: 'Permission Denied', count: 8, trend: 'stable' },
      { error: 'Network Error', count: 5, trend: 'decreasing' }
    ]
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const { overview, executionTrend, performanceByNode, triggerDistribution, topWorkflows, errorPatterns } = analytics;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Workflow Analytics</h2>
          <p className="text-muted-foreground">
            Monitor performance and identify optimization opportunities
          </p>
        </div>
        <Select value={timeRange} onValueChange={setTimeRange}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="24h">Last 24 Hours</SelectItem>
            <SelectItem value="7d">Last 7 Days</SelectItem>
            <SelectItem value="30d">Last 30 Days</SelectItem>
            <SelectItem value="90d">Last 90 Days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Executions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.totalExecutions.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="inline h-3 w-3 mr-1 text-green-500" />
              +12% from last period
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.successRate}%</div>
            <Progress value={overview.successRate} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.averageDuration}s</div>
            <p className="text-xs text-muted-foreground">
              <TrendingDown className="inline h-3 w-3 mr-1 text-green-500" />
              -8% faster
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Workflows</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.activeWorkflows}</div>
            <p className="text-xs text-muted-foreground">Currently enabled</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{overview.failedExecutions}</div>
            <p className="text-xs text-muted-foreground">Requires attention</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{overview.pendingApprovals}</div>
            <p className="text-xs text-muted-foreground">Awaiting approval</p>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Tabs */}
      <Tabs defaultValue="execution" className="space-y-4">
        <TabsList>
          <TabsTrigger value="execution">Execution Trends</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="triggers">Triggers</TabsTrigger>
          <TabsTrigger value="errors">Error Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="execution" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Execution Trend</CardTitle>
              <CardDescription>Daily workflow executions over time</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={executionTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="success" stackId="1" stroke="#10b981" fill="#10b981" />
                  <Area type="monotone" dataKey="failed" stackId="1" stroke="#ef4444" fill="#ef4444" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top Workflows</CardTitle>
              <CardDescription>Most frequently executed workflows</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {topWorkflows.map((workflow: any, index: number) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{workflow.name}</p>
                        <Badge variant="secondary">{workflow.executions} runs</Badge>
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <CheckCircle className="h-3 w-3" />
                          {workflow.successRate}% success
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {workflow.avgDuration}s avg
                        </span>
                      </div>
                    </div>
                    <Progress value={workflow.successRate} className="w-[100px]" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Node Performance</CardTitle>
              <CardDescription>Average execution time by node type</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={performanceByNode}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="node" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="avgDuration" fill="#3b82f6" name="Avg Duration (s)" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Node Statistics</CardTitle>
              <CardDescription>Detailed performance metrics by node</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {performanceByNode.map((node: any, index: number) => (
                  <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex-1">
                      <p className="font-medium">{node.node}</p>
                      <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                        <span>{node.executions} executions</span>
                        <span>{node.avgDuration}s avg</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={node.successRate >= 95 ? 'default' : 'secondary'}>
                        {node.successRate}% success
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="triggers" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Trigger Distribution</CardTitle>
              <CardDescription>Breakdown of workflow triggers</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={triggerDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: ${entry.value}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {triggerDistribution.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="errors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Error Patterns</CardTitle>
              <CardDescription>Common errors and their trends</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {errorPatterns.map((error: any, index: number) => (
                  <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex-1">
                      <p className="font-medium">{error.error}</p>
                      <p className="text-sm text-muted-foreground">{error.count} occurrences</p>
                    </div>
                    <Badge
                      variant={
                        error.trend === 'increasing' ? 'destructive' :
                        error.trend === 'decreasing' ? 'default' :
                        'secondary'
                      }
                    >
                      {error.trend === 'increasing' && <TrendingUp className="h-3 w-3 mr-1" />}
                      {error.trend === 'decreasing' && <TrendingDown className="h-3 w-3 mr-1" />}
                      {error.trend}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}