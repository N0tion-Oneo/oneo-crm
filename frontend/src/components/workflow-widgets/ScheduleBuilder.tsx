'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Calendar, Clock, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ScheduleBuilderProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

type ScheduleType = 'simple' | 'advanced' | 'presets';

const SCHEDULE_PRESETS = [
  { label: 'Every minute', value: '* * * * *', description: 'Runs every minute' },
  { label: 'Every 5 minutes', value: '*/5 * * * *', description: 'Runs every 5 minutes' },
  { label: 'Every 15 minutes', value: '*/15 * * * *', description: 'Runs every 15 minutes' },
  { label: 'Every 30 minutes', value: '*/30 * * * *', description: 'Runs every 30 minutes' },
  { label: 'Every hour', value: '0 * * * *', description: 'Runs at the start of every hour' },
  { label: 'Every day at 9am', value: '0 9 * * *', description: 'Runs daily at 9:00 AM' },
  { label: 'Every day at noon', value: '0 12 * * *', description: 'Runs daily at 12:00 PM' },
  { label: 'Every day at 5pm', value: '0 17 * * *', description: 'Runs daily at 5:00 PM' },
  { label: 'Every Monday at 9am', value: '0 9 * * 1', description: 'Runs every Monday at 9:00 AM' },
  { label: 'Every weekday at 9am', value: '0 9 * * 1-5', description: 'Runs Monday-Friday at 9:00 AM' },
  { label: 'Every Sunday at midnight', value: '0 0 * * 0', description: 'Runs every Sunday at midnight' },
  { label: 'First day of month at 9am', value: '0 9 1 * *', description: 'Runs on the 1st of each month at 9:00 AM' },
  { label: 'Last day of month at 5pm', value: '0 17 L * *', description: 'Runs on the last day of each month at 5:00 PM' },
];

const WEEKDAYS = [
  { label: 'Sunday', value: '0' },
  { label: 'Monday', value: '1' },
  { label: 'Tuesday', value: '2' },
  { label: 'Wednesday', value: '3' },
  { label: 'Thursday', value: '4' },
  { label: 'Friday', value: '5' },
  { label: 'Saturday', value: '6' },
];

export function ScheduleBuilder({
  value,
  onChange,
  placeholder = '0 9 * * *',
  disabled = false
}: ScheduleBuilderProps) {
  const [scheduleType, setScheduleType] = useState<ScheduleType>('simple');
  const [simpleSchedule, setSimpleSchedule] = useState({
    frequency: 'daily',
    time: '09:00',
    dayOfWeek: '1',
    dayOfMonth: '1',
    hour: '9',
    minute: '0'
  });

  // Parse existing cron expression to simple schedule if possible
  useEffect(() => {
    if (value && value !== placeholder) {
      parseCronExpression(value);
    }
  }, [value]);

  const parseCronExpression = (cron: string) => {
    const parts = cron.split(' ');
    if (parts.length !== 5) return;

    const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;

    // Try to detect common patterns
    if (minute === '0' && hour !== '*' && dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
      // Daily at specific time
      setSimpleSchedule(prev => ({
        ...prev,
        frequency: 'daily',
        hour: hour,
        minute: '0',
        time: `${hour.padStart(2, '0')}:00`
      }));
    } else if (minute !== '*' && hour !== '*' && dayOfWeek !== '*' && dayOfWeek !== '1-5') {
      // Weekly on specific day
      setSimpleSchedule(prev => ({
        ...prev,
        frequency: 'weekly',
        dayOfWeek: dayOfWeek,
        hour: hour,
        minute: minute,
        time: `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`
      }));
    }
  };

  const generateCronExpression = () => {
    const { frequency, time, dayOfWeek, dayOfMonth } = simpleSchedule;
    const [hour, minute] = time.split(':');

    switch (frequency) {
      case 'hourly':
        return `${minute} * * * *`;
      case 'daily':
        return `${minute} ${hour} * * *`;
      case 'weekly':
        return `${minute} ${hour} * * ${dayOfWeek}`;
      case 'monthly':
        return `${minute} ${hour} ${dayOfMonth} * *`;
      case 'weekdays':
        return `${minute} ${hour} * * 1-5`;
      case 'weekends':
        return `${minute} ${hour} * * 0,6`;
      default:
        return '0 9 * * *';
    }
  };

  const handleSimpleChange = (field: string, value: string) => {
    const newSchedule = { ...simpleSchedule, [field]: value };
    setSimpleSchedule(newSchedule);

    // Generate and update cron expression
    const tempSchedule = simpleSchedule;
    simpleSchedule[field as keyof typeof simpleSchedule] = value;
    const cronExp = generateCronExpression();
    simpleSchedule[field as keyof typeof simpleSchedule] = tempSchedule[field as keyof typeof simpleSchedule];
    setSimpleSchedule(newSchedule);
    onChange(cronExp);
  };

  const getHumanReadableSchedule = (cron: string) => {
    // Find matching preset
    const preset = SCHEDULE_PRESETS.find(p => p.value === cron);
    if (preset) return preset.description;

    // Parse cron for common patterns
    const parts = cron.split(' ');
    if (parts.length !== 5) return 'Invalid schedule';

    const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;

    if (minute === '*' && hour === '*') return 'Every minute';
    if (minute === '0' && hour === '*') return 'Every hour';
    if (dayOfWeek === '1-5' && hour !== '*') return `Weekdays at ${hour}:${minute.padStart(2, '0')}`;
    if (dayOfWeek !== '*' && hour !== '*') {
      const day = WEEKDAYS.find(d => d.value === dayOfWeek);
      return `Every ${day?.label || 'day'} at ${hour}:${minute.padStart(2, '0')}`;
    }
    if (hour !== '*' && minute !== '*' && dayOfMonth === '*' && dayOfWeek === '*') {
      return `Daily at ${hour}:${minute.padStart(2, '0')}`;
    }

    return cron;
  };

  return (
    <div className="space-y-4">
      <Tabs value={scheduleType} onValueChange={(v) => setScheduleType(v as ScheduleType)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="simple">Simple</TabsTrigger>
          <TabsTrigger value="presets">Presets</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="simple" className="space-y-4">
          <div className="space-y-3">
            <div>
              <Label>Frequency</Label>
              <Select
                value={simpleSchedule.frequency}
                onValueChange={(v) => handleSimpleChange('frequency', v)}
                disabled={disabled}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hourly">Every hour</SelectItem>
                  <SelectItem value="daily">Every day</SelectItem>
                  <SelectItem value="weekly">Every week</SelectItem>
                  <SelectItem value="monthly">Every month</SelectItem>
                  <SelectItem value="weekdays">Weekdays only</SelectItem>
                  <SelectItem value="weekends">Weekends only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {simpleSchedule.frequency !== 'hourly' && (
              <div>
                <Label>Time</Label>
                <Input
                  type="time"
                  value={simpleSchedule.time}
                  onChange={(e) => handleSimpleChange('time', e.target.value)}
                  disabled={disabled}
                />
              </div>
            )}

            {simpleSchedule.frequency === 'weekly' && (
              <div>
                <Label>Day of Week</Label>
                <Select
                  value={simpleSchedule.dayOfWeek}
                  onValueChange={(v) => handleSimpleChange('dayOfWeek', v)}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WEEKDAYS.map(day => (
                      <SelectItem key={day.value} value={day.value}>
                        {day.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {simpleSchedule.frequency === 'monthly' && (
              <div>
                <Label>Day of Month</Label>
                <Select
                  value={simpleSchedule.dayOfMonth}
                  onValueChange={(v) => handleSimpleChange('dayOfMonth', v)}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
                      <SelectItem key={day} value={String(day)}>
                        {day}{day === 1 ? 'st' : day === 2 ? 'nd' : day === 3 ? 'rd' : 'th'}
                      </SelectItem>
                    ))}
                    <SelectItem value="L">Last day</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="presets" className="space-y-2">
          <div className="grid gap-2">
            {SCHEDULE_PRESETS.map(preset => (
              <Button
                key={preset.value}
                variant={value === preset.value ? 'default' : 'outline'}
                className="justify-start h-auto py-2 px-3"
                onClick={() => onChange(preset.value)}
                disabled={disabled}
              >
                <div className="flex flex-col items-start">
                  <span className="font-medium">{preset.label}</span>
                  <span className="text-xs text-muted-foreground">{preset.description}</span>
                </div>
              </Button>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4">
          <div>
            <Label>Cron Expression</Label>
            <Input
              value={value || ''}
              onChange={(e) => onChange(e.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              className="font-mono"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Format: minute hour day month weekday
            </p>
          </div>

          <div className="bg-muted rounded-lg p-3">
            <div className="text-sm space-y-1">
              <div className="font-medium">Quick Reference:</div>
              <div className="font-mono text-xs space-y-0.5">
                <div>* = any value</div>
                <div>*/5 = every 5 units</div>
                <div>1,3,5 = specific values</div>
                <div>1-5 = range of values</div>
                <div>L = last (day of month)</div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Current schedule display */}
      <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">
          <span className="text-muted-foreground">Schedule: </span>
          <span className="font-medium">{getHumanReadableSchedule(value || placeholder)}</span>
        </span>
      </div>

      {/* Cron value display */}
      {value && (
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="font-mono text-xs">
            {value}
          </Badge>
        </div>
      )}
    </div>
  );
}