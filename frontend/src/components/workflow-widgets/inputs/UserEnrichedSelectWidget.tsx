/**
 * UserEnrichedSelectWidget - Widget for selecting users with their enriched data
 * Provides access to user profile, staff info, channel connections, and scheduling data
 */

import React, { useState, useEffect } from 'react';
import { User, Mail, MessageSquare, Phone, Calendar, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectSeparator,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { BaseWidgetWrapper } from '../core/BaseWidgetWrapper';
import { BaseWidgetProps } from '../types';
import { api } from '@/lib/api';

// Types for channel connections
type ChannelType = 'email' | 'linkedin' | 'whatsapp' | 'instagram' | 'messenger' | 'telegram' | 'twitter';

interface UserChannelConnection {
  id: string;
  channel_type: string;
  channel_type_display: string;
  account_name: string;
  unipile_account_id: string;
  account_status: string;
  is_active: boolean;
  status_info: {
    status: string;
    display: string;
    can_send: boolean;
    needs_action: boolean;
    message: string;
  };
}

interface StaffProfile {
  id: string;
  job_title: string;
  department: string;
  work_location: string;
  reporting_manager_name: string;
}

interface SchedulingProfile {
  id: string;
  timezone: string;
  buffer_minutes: number;
  calendar_account: string;
  is_active: boolean;
}

interface MeetingType {
  id: string;
  name: string;
  slug: string;
  duration_minutes: number;
  booking_url: string;
}

interface EnrichedUser {
  id: string;
  email: string;
  username: string;
  full_name: string;
  phone?: string;
  user_type: string;
  user_type_name: string;
  avatar_url?: string;
  staff_profile?: StaffProfile;
  channel_connections: Record<string, UserChannelConnection[]>;
  scheduling_profiles: SchedulingProfile[];
  meeting_types: MeetingType[];
  has_email_connection: boolean;
  has_linkedin_connection: boolean;
  has_whatsapp_connection: boolean;
  primary_email_account: string;
  is_active: boolean;
}

interface UserEnrichedSelectWidgetProps extends Omit<BaseWidgetProps, 'key'> {
  value: string | string[] | { user_id: string; account_id?: string } | Array<{ user_id: string; account_id?: string }> | null;
  onChange: (value: any) => void;
  channel_filter?: ChannelType;
  multiple?: boolean;
  show_all_option?: boolean;
  show_accounts?: boolean;
  display_format?: 'user_only' | 'user_with_accounts' | 'account_primary';
  allow_variable?: boolean;
}

const getChannelIcon = (channel: string) => {
  switch (channel.toLowerCase()) {
    case 'gmail':
    case 'outlook':
    case 'mail':
    case 'email':
      return <Mail className="h-3 w-3" />;
    case 'linkedin':
      return <MessageSquare className="h-3 w-3 text-blue-600" />;
    case 'whatsapp':
      return <Phone className="h-3 w-3 text-green-600" />;
    default:
      return <MessageSquare className="h-3 w-3" />;
  }
};

const getChannelColor = (channel: string) => {
  switch (channel.toLowerCase()) {
    case 'gmail':
    case 'email':
      return 'bg-red-100 text-red-700';
    case 'outlook':
      return 'bg-blue-100 text-blue-700';
    case 'linkedin':
      return 'bg-blue-100 text-blue-700';
    case 'whatsapp':
      return 'bg-green-100 text-green-700';
    default:
      return 'bg-gray-100 text-gray-700';
  }
};

export function UserEnrichedSelectWidget(props: UserEnrichedSelectWidgetProps) {
  // Extract ui_hints from props
  const uiHints = (props as any).uiHints || {};

  // Merge props with uiHints for backward compatibility
  const {
    value,
    onChange,
    placeholder = uiHints.placeholder || 'Select user...',
    disabled,
    required,
    error,
    helpText,
    label,
    channel_filter = uiHints.channel_filter,
    multiple = uiHints.multiple || false,
    show_all_option = uiHints.show_all_option || false,
    show_accounts = uiHints.show_accounts || false,
    display_format = uiHints.display_format || 'user_with_accounts',
    allow_variable = uiHints.allow_variable || false,
    config,
    ...rest
  } = props;
  const [users, setUsers] = useState<EnrichedUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);

  // Parse initial value
  useEffect(() => {
    console.log('UserEnrichedSelectWidget value changed:', value);

    if (!value) {
      setSelectedUsers([]);
      return;
    }

    let selected: string[] = [];

    if (value === 'all') {
      selected = ['all'];
    } else if (Array.isArray(value)) {
      selected = value.map(v => {
        // Handle both string and number IDs
        if (typeof v === 'string' || typeof v === 'number') return String(v);
        if (v?.user_id) return String(v.user_id);
        return '';
      }).filter(Boolean);
    } else if (typeof value === 'string') {
      selected = [value];
    } else if (typeof value === 'number') {
      // Handle number IDs
      selected = [String(value)];
    } else if (value && typeof value === 'object' && 'user_id' in value) {
      selected = [String(value.user_id)];
    }

    console.log('Parsed selected users:', selected);
    setSelectedUsers(selected);
  }, [value]);

  // Load users
  useEffect(() => {
    loadUsers();
  }, [channel_filter]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      let params: any = {};
      if (channel_filter) {
        params.channel_filter = channel_filter;
      }

      const response = await api.get('/api/v1/users-enriched/', { params });
      const userData = response.data.results || response.data || [];
      setUsers(userData);
    } catch (error: any) {
      console.error('Failed to load enriched users:', error);
      // Set mock data for testing if API fails
      setUsers([
        {
          id: 'mock1',
          email: 'john.doe@example.com',
          username: 'johndoe',
          full_name: 'John Doe',
          user_type: 'admin',
          user_type_name: 'Admin',
          channel_connections: {
            email: [{
              id: 'conn1',
              channel_type: 'email',
              channel_type_display: 'Email',
              account_name: 'john.doe@example.com',
              unipile_account_id: 'unipile_1',
              account_status: 'active',
              is_active: true,
              status_info: {
                status: 'active',
                display: 'Active',
                can_send: true,
                needs_action: false,
                message: ''
              }
            }]
          },
          scheduling_profiles: [],
          meeting_types: [],
          has_email_connection: true,
          has_linkedin_connection: false,
          has_whatsapp_connection: false,
          primary_email_account: 'john.doe@example.com',
          is_active: true
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (userId: string) => {
    console.log('handleToggle called with userId:', userId);

    // Ensure userId is a string
    const userIdStr = String(userId);

    if (userIdStr === 'all') {
      // Toggle all users
      const newSelected = selectedUsers.includes('all') ? [] : ['all'];
      setSelectedUsers(newSelected);
      onChange(newSelected.length ? 'all' : null);
      return;
    }

    // Toggle individual user
    let newSelected = [...selectedUsers];

    // Remove 'all' if selecting individual users
    const allIndex = newSelected.indexOf('all');
    if (allIndex > -1) {
      newSelected.splice(allIndex, 1);
    }

    const index = newSelected.indexOf(userIdStr);
    if (index > -1) {
      newSelected.splice(index, 1);
    } else {
      newSelected.push(userIdStr);
    }

    console.log('New selected users:', newSelected);
    setSelectedUsers(newSelected);

    if (newSelected.length === 0) {
      onChange(null);
    } else {
      const values = newSelected.map(uid => {
        if (show_accounts) {
          const user = users.find(u => String(u.id) === uid);
          const primaryAccount = user ? getFirstAccountForUser(user) : null;
          return primaryAccount
            ? { user_id: Number(uid), account_id: primaryAccount.id }
            : { user_id: Number(uid) };
        }
        // Convert back to number for consistency with backend
        return Number(uid);
      });
      console.log('Calling onChange with values:', values);
      onChange(values);
    }
  };

  const handleUserSelect = (userId: string) => {
    if (!multiple) {
      // Single selection
      if (userId === 'all') {
        onChange('all');
      } else {
        const user = users.find(u => u.id === userId);
        if (show_accounts && user) {
          const primaryAccount = getFirstAccountForUser(user);
          if (primaryAccount) {
            onChange({ user_id: userId, account_id: primaryAccount.id });
          } else {
            onChange({ user_id: userId });
          }
        } else {
          onChange(userId);
        }
      }
    } else {
      handleToggle(userId);
    }
  };

  const handleRemove = (userId: string) => {
    const newSelected = selectedUsers.filter(id => id !== userId);
    setSelectedUsers(newSelected);

    if (newSelected.length === 0) {
      onChange(null);
    } else {
      const values = newSelected.map(uid => {
        if (uid === 'all') return 'all';
        if (show_accounts) {
          const user = users.find(u => u.id === uid);
          const primaryAccount = user ? getFirstAccountForUser(user) : null;
          return primaryAccount
            ? { user_id: uid, account_id: primaryAccount.id }
            : { user_id: uid };
        }
        return uid;
      });
      onChange(values.length === 1 && values[0] === 'all' ? 'all' : values);
    }
  };

  const getFirstAccountForUser = (user: EnrichedUser): UserChannelConnection | null => {
    if (!channel_filter) return null;
    const channelConnections = user.channel_connections[channel_filter] || [];
    return channelConnections.find(conn => conn.is_active && conn.account_status === 'active') || null;
  };

  const getDisplayValue = () => {
    if (!selectedUsers.length) return undefined;

    if (selectedUsers.includes('all')) {
      return 'all';
    }

    if (!multiple && selectedUsers.length === 1) {
      return selectedUsers[0];
    }

    return '';
  };

  const getDisplayText = (userId: string) => {
    if (userId === 'all') {
      return 'All Users';
    }

    // Handle both string and number comparison for user IDs
    const user = users.find(u => String(u.id) === String(userId));
    console.log('Looking for userId:', userId, 'in users:', users.map(u => ({ id: u.id, name: u.full_name })), 'found:', user);

    if (!user) {
      console.log('User not found, returning userId:', userId);
      return userId;
    }

    const displayText = user.full_name || user.email;
    console.log('Returning display text:', displayText);
    return displayText;
  };

  const renderUserItem = (user: EnrichedUser | 'all') => {
    if (user === 'all') {
      return (
        <div className="flex items-center gap-2">
          <User className="h-4 w-4" />
          <span className="font-medium">All Users</span>
          {channel_filter && (
            <Badge variant="secondary" className="text-xs ml-auto">
              with {channel_filter}
            </Badge>
          )}
        </div>
      );
    }

    const connections = channel_filter
      ? user.channel_connections[channel_filter] || []
      : Object.values(user.channel_connections).flat();

    return (
      <div className="flex items-start gap-2 py-1">
        <Avatar className="h-6 w-6">
          <AvatarImage src={user.avatar_url} />
          <AvatarFallback className="text-xs">
            {user.full_name.split(' ').map(n => n[0]).join('').toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{user.full_name}</span>
            {user.staff_profile?.job_title && (
              <span className="text-xs text-muted-foreground truncate">
                {user.staff_profile.job_title}
              </span>
            )}
          </div>
          <div className="text-xs text-muted-foreground truncate">
            {user.email}
            {user.staff_profile?.department && (
              <span> • {user.staff_profile.department}</span>
            )}
          </div>
          {connections.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {connections.slice(0, 2).map((conn) => (
                <Badge
                  key={conn.id}
                  variant="outline"
                  className={cn('text-xs', getChannelColor(conn.channel_type))}
                >
                  {getChannelIcon(conn.channel_type)}
                  <span className="ml-1 truncate max-w-[100px]">{conn.account_name}</span>
                </Badge>
              ))}
              {connections.length > 2 && (
                <Badge variant="outline" className="text-xs">
                  +{connections.length - 2} more
                </Badge>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (multiple) {
    return (
      <BaseWidgetWrapper
        label={label}
        helpText={helpText}
        error={error}
        required={required}
      >
        <div className="space-y-2">
          <Select
            value=""
            onValueChange={handleToggle}
            disabled={disabled || loading}
          >
            <SelectTrigger>
              {loading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Loading users...</span>
                </div>
              ) : (
                <SelectValue placeholder={placeholder} />
              )}
            </SelectTrigger>
            <SelectContent>
              {show_all_option && (
                <>
                  <SelectItem
                    value="all"
                    className={selectedUsers.includes('all') ? 'bg-blue-50' : ''}
                  >
                    <div className="flex items-center gap-2">
                      {selectedUsers.includes('all') && <span className="text-blue-600">✓</span>}
                      <User className="h-4 w-4" />
                      <span className="font-medium">All Users</span>
                      {channel_filter && (
                        <Badge variant="secondary" className="text-xs ml-auto">
                          with {channel_filter}
                        </Badge>
                      )}
                    </div>
                  </SelectItem>
                  <SelectSeparator />
                </>
              )}
              <SelectGroup>
                {users.map((user) => {
                  const userIdStr = String(user.id);
                  const isSelected = selectedUsers.includes(userIdStr);
                  return (
                    <SelectItem
                      key={user.id}
                      value={userIdStr}
                      className={isSelected ? 'bg-blue-50' : ''}
                    >
                      <div className="flex items-center gap-2">
                        {isSelected && <span className="text-blue-600">✓</span>}
                        {renderUserItem(user)}
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectGroup>
            </SelectContent>
          </Select>

          {selectedUsers.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {selectedUsers.map((userId) => {
                console.log('Rendering badge for userId:', userId, 'displayText:', getDisplayText(userId));
                return (
                  <Badge
                    key={userId}
                    variant="secondary"
                    className="flex items-center gap-1"
                  >
                    {getDisplayText(userId)}
                    {!disabled && (
                      <X
                        className="w-3 h-3 cursor-pointer hover:text-red-600"
                        onClick={() => handleRemove(userId)}
                      />
                    )}
                  </Badge>
                );
              })}
            </div>
          )}
        </div>
      </BaseWidgetWrapper>
    );
  }

  return (
    <BaseWidgetWrapper
      label={label}
      helpText={helpText}
      error={error}
      required={required}
    >
      <Select
        value={getDisplayValue()}
        onValueChange={handleUserSelect}
        disabled={disabled || loading}
      >
        <SelectTrigger className={cn(error && 'border-destructive')}>
          {loading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading users...</span>
            </div>
          ) : (
            <SelectValue placeholder={placeholder}>
              {selectedUsers.length > 0 && getDisplayText(selectedUsers[0])}
            </SelectValue>
          )}
        </SelectTrigger>
        <SelectContent>
          {show_all_option && (
            <>
              <SelectItem value="all">
                {renderUserItem('all')}
              </SelectItem>
              <SelectSeparator />
            </>
          )}
          <SelectGroup>
            {users.map((user) => (
              <SelectItem key={user.id} value={String(user.id)}>
                {renderUserItem(user)}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </BaseWidgetWrapper>
  );
}