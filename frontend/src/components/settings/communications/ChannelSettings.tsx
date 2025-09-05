'use client'

import { MessageCircle, Mail, MessageSquare, Check, X } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface ChannelConfig {
  enabled: boolean
  minMessages: number
  requireTwoWay: boolean
  required: boolean
}

interface ChannelSettingsProps {
  settings: any
  onUpdateSettings: (updates: any) => void
  saving: boolean
  canEdit: boolean
}

const CHANNELS = [
  {
    key: 'email',
    name: 'Email',
    icon: Mail,
    description: 'Email communication through Gmail, Outlook, etc.',
    color: 'blue'
  },
  {
    key: 'whatsapp',
    name: 'WhatsApp',
    icon: MessageCircle,
    description: 'WhatsApp Business messaging',
    color: 'green'
  },
  {
    key: 'linkedin',
    name: 'LinkedIn',
    icon: MessageSquare,
    description: 'LinkedIn messages and InMail',
    color: 'indigo'
  }
]

export function ChannelSettings({
  settings,
  onUpdateSettings,
  saving,
  canEdit
}: ChannelSettingsProps) {
  if (!settings) return null

  const getChannelConfig = (channel: string): ChannelConfig => ({
    enabled: settings[`${channel}_enabled`] ?? true,
    minMessages: settings[`${channel}_min_messages`] ?? 1,
    requireTwoWay: settings[`${channel}_require_two_way`] ?? false,
    required: settings[`${channel}_required`] ?? false
  })

  const updateChannelSetting = (channel: string, key: string, value: any) => {
    onUpdateSettings({ [`${channel}_${key}`]: value })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Channel Configuration</CardTitle>
        <CardDescription>
          Configure auto-creation rules for each communication channel
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {CHANNELS.map((channel) => {
          const config = getChannelConfig(channel.key)
          const Icon = channel.icon
          const isEnabled = config.enabled
          
          return (
            <div
              key={channel.key}
              className={cn(
                "border rounded-lg transition-all",
                isEnabled ? "border-gray-200 dark:border-gray-700" : "border-gray-100 dark:border-gray-800 opacity-60"
              )}
            >
              {/* Channel Header */}
              <div className="p-4 border-b border-gray-100 dark:border-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "p-2 rounded-lg",
                      channel.color === 'blue' && "bg-blue-100 dark:bg-blue-900/30",
                      channel.color === 'green' && "bg-green-100 dark:bg-green-900/30",
                      channel.color === 'indigo' && "bg-indigo-100 dark:bg-indigo-900/30"
                    )}>
                      <Icon className={cn(
                        "h-5 w-5",
                        channel.color === 'blue' && "text-blue-600 dark:text-blue-400",
                        channel.color === 'green' && "text-green-600 dark:text-green-400",
                        channel.color === 'indigo' && "text-indigo-600 dark:text-indigo-400"
                      )} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{channel.name}</h4>
                        {config.required && isEnabled && (
                          <Badge variant="default" className="text-xs">
                            Required
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {channel.description}
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={isEnabled}
                    disabled={saving || !canEdit}
                    onCheckedChange={(checked) => updateChannelSetting(channel.key, 'enabled', checked)}
                  />
                </div>
              </div>

              {/* Channel Settings */}
              {isEnabled && (
                <div className="p-4 space-y-4 bg-gray-50/50 dark:bg-gray-900/20">
                  <div className="grid grid-cols-2 gap-4">
                    {/* Minimum Messages */}
                    <div className="space-y-2">
                      <Label htmlFor={`${channel.key}-min`} className="text-sm">
                        Minimum Messages
                      </Label>
                      <Input
                        id={`${channel.key}-min`}
                        type="number"
                        min="1"
                        value={config.minMessages}
                        disabled={saving || !canEdit}
                        onChange={(e) => updateChannelSetting(channel.key, 'min_messages', parseInt(e.target.value))}
                        className="h-9"
                      />
                      <p className="text-xs text-gray-500">
                        Messages required before creation
                      </p>
                    </div>

                    {/* Two-Way Conversation */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between h-9">
                        <Label htmlFor={`${channel.key}-twoway`} className="text-sm cursor-pointer">
                          Two-Way Required
                        </Label>
                        <Switch
                          id={`${channel.key}-twoway`}
                          checked={config.requireTwoWay}
                          disabled={saving || !canEdit}
                          onCheckedChange={(checked) => updateChannelSetting(channel.key, 'require_two_way', checked)}
                        />
                      </div>
                      <p className="text-xs text-gray-500">
                        Both parties must have messaged
                      </p>
                    </div>
                  </div>

                  {/* Required Channel Setting */}
                  <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label className="text-sm flex items-center gap-2">
                          Required for Auto-Creation
                          {config.required ? (
                            <Check className="h-3.5 w-3.5 text-green-600" />
                          ) : (
                            <X className="h-3.5 w-3.5 text-gray-400" />
                          )}
                        </Label>
                        <p className="text-xs text-gray-500">
                          Participant must have this channel to be eligible
                        </p>
                      </div>
                      <Switch
                        checked={config.required}
                        disabled={saving || !canEdit}
                        onCheckedChange={(checked) => updateChannelSetting(channel.key, 'required', checked)}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {/* Info Alert */}
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>Tip:</strong> When multiple channels are marked as required, participants must have ALL required channels to qualify for auto-creation.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}