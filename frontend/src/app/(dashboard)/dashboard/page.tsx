'use client'

import { useAuth } from '@/features/auth/context'
import { Users, Database, Activity, TrendingUp, ArrowUpRight, ArrowDownRight } from 'lucide-react'

export default function DashboardPage() {
  const { user, tenant } = useAuth()

  const stats = [
    {
      name: 'Total Users',
      value: '12',
      change: '+2.5%',
      changeType: 'increase' as const,
      icon: Users,
    },
    {
      name: 'Active Pipelines',
      value: '8',
      change: '+12%',
      changeType: 'increase' as const,
      icon: Database,
    },
    {
      name: 'Workflows Running',
      value: '24',
      change: '+4.2%',
      changeType: 'increase' as const,
      icon: Activity,
    },
    {
      name: 'System Performance',
      value: '98.5%',
      change: '-0.3%',
      changeType: 'decrease' as const,
      icon: TrendingUp,
    },
  ]

  const recentActivity = [
    {
      id: 1,
      user: 'John Doe',
      action: 'Created new pipeline',
      target: 'Customer Onboarding',
      time: '2 minutes ago',
    },
    {
      id: 2,
      user: 'Sarah Smith',
      action: 'Updated user permissions',
      target: 'Marketing Team',
      time: '15 minutes ago',
    },
    {
      id: 3,
      user: 'Mike Johnson',
      action: 'Completed workflow',
      target: 'Lead Processing',
      time: '1 hour ago',
    },
    {
      id: 4,
      user: 'Emily Brown',
      action: 'Added new user',
      target: 'Sales Department',
      time: '2 hours ago',
    },
  ]

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Welcome back, {user?.firstName}! Here's what's happening with{' '}
          <span className="capitalize font-medium">{tenant?.name || 'your organization'}</span>.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  {stat.name}
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
                  {stat.value}
                </p>
              </div>
              <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
                <stat.icon className="w-6 h-6 text-gray-600 dark:text-gray-400" />
              </div>
            </div>
            <div className="flex items-center mt-4">
              {stat.changeType === 'increase' ? (
                <ArrowUpRight className="w-4 h-4 text-green-500 mr-1" />
              ) : (
                <ArrowDownRight className="w-4 h-4 text-red-500 mr-1" />
              )}
              <span
                className={`text-sm font-medium ${
                  stat.changeType === 'increase' ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {stat.change}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">
                from last month
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Activity
            </h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                        {activity.user.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 dark:text-white">
                      <span className="font-medium">{activity.user}</span>{' '}
                      {activity.action}{' '}
                      <span className="font-medium">{activity.target}</span>
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {activity.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Quick Actions
            </h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 gap-4">
              <button className="p-4 text-left border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <Users className="w-6 h-6 text-primary mb-2" />
                <h4 className="font-medium text-gray-900 dark:text-white">
                  Add User
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Invite new team members
                </p>
              </button>
              <button className="p-4 text-left border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <Database className="w-6 h-6 text-primary mb-2" />
                <h4 className="font-medium text-gray-900 dark:text-white">
                  New Pipeline
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Create data pipeline
                </p>
              </button>
              <button className="p-4 text-left border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <Activity className="w-6 h-6 text-primary mb-2" />
                <h4 className="font-medium text-gray-900 dark:text-white">
                  Run Workflow
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Execute automation
                </p>
              </button>
              <button className="p-4 text-left border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <TrendingUp className="w-6 h-6 text-primary mb-2" />
                <h4 className="font-medium text-gray-900 dark:text-white">
                  View Reports
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Analytics dashboard
                </p>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}