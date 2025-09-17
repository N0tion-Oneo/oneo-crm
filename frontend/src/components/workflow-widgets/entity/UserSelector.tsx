/**
 * User and user type selection widgets
 */

import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { User, X, Loader2 } from 'lucide-react';
import { WidgetProps } from '../core/types';
import { BaseWidgetWrapper } from '../basic/BaseWidget';
import { useEntityData } from './useEntityData';

export const UserSelector: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {} } = props;
  const isMultiple = uiHints.widget === 'user_multiselect' || uiHints.multiple;

  // Use users from props if available, otherwise fetch
  const shouldFetch = !props.users || props.users.length === 0;
  const { data: fetchedUsers, isLoading } = useEntityData('users', {
    enabled: shouldFetch
  });

  const users = props.users || fetchedUsers;
  const placeholder = props.placeholder || uiHints.placeholder || 'Select user(s)';

  if (isMultiple) {
    return <UserMultiSelect {...props} users={users} isLoading={isLoading} />;
  }

  return (
    <BaseWidgetWrapper {...props}>
      <Select
        value={value || ''}
        onValueChange={onChange}
        disabled={props.disabled || props.readonly || isLoading}
      >
        <SelectTrigger>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading users...</span>
            </div>
          ) : (
            <SelectValue placeholder={placeholder} />
          )}
        </SelectTrigger>
        <SelectContent>
          {users.map((user: any) => {
            const userId = user.id || user.value;
            const userName = user.full_name || user.name || user.email || user.label || userId;
            const userEmail = user.email;

            return (
              <SelectItem key={userId} value={userId}>
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-gray-400" />
                  <div className="flex flex-col">
                    <span>{userName}</span>
                    {userEmail && userEmail !== userName && (
                      <span className="text-xs text-gray-500">{userEmail}</span>
                    )}
                  </div>
                </div>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </BaseWidgetWrapper>
  );
};

const UserMultiSelect: React.FC<WidgetProps & { users: any[]; isLoading: boolean }> = ({
  value = [],
  onChange,
  users,
  isLoading,
  ...props
}) => {
  const selectedValues = Array.isArray(value) ? value : [];
  const placeholder = props.placeholder || props.uiHints?.placeholder || 'Select users';

  const handleToggle = (userId: string) => {
    const newValues = selectedValues.includes(userId)
      ? selectedValues.filter(v => v !== userId)
      : [...selectedValues, userId];
    onChange(newValues);
  };

  const handleRemove = (userId: string) => {
    onChange(selectedValues.filter(v => v !== userId));
  };

  return (
    <BaseWidgetWrapper {...props}>
      <div className="space-y-2">
        <Select
          value=""
          onValueChange={handleToggle}
          disabled={props.disabled || props.readonly || isLoading}
        >
          <SelectTrigger>
            {isLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading users...</span>
              </div>
            ) : (
              <SelectValue placeholder={placeholder} />
            )}
          </SelectTrigger>
          <SelectContent>
            {users.map((user: any) => {
              const userId = user.id || user.value;
              const userName = user.full_name || user.name || user.email || user.label || userId;
              const isSelected = selectedValues.includes(userId);

              return (
                <SelectItem
                  key={userId}
                  value={userId}
                  className={isSelected ? 'bg-blue-50' : ''}
                >
                  <div className="flex items-center gap-2">
                    {isSelected && <span className="text-blue-600">✓</span>}
                    <User className="w-4 h-4 text-gray-400" />
                    {userName}
                  </div>
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>

        {selectedValues.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedValues.map((userId) => {
              const user = users.find(u => (u.id || u.value) === userId);
              const userName = user?.full_name || user?.name || user?.email || user?.label || userId;

              return (
                <Badge
                  key={userId}
                  variant="secondary"
                  className="flex items-center gap-1"
                >
                  <User className="w-3 h-3" />
                  {userName}
                  {!props.disabled && !props.readonly && (
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
};

/**
 * User Type selector widget
 */
export const UserTypeSelector: React.FC<WidgetProps> = (props) => {
  const { value, onChange, uiHints = {} } = props;
  const isMultiple = uiHints.widget === 'user_type_multiselect' || uiHints.multiple;

  // Use userTypes from props if available, otherwise fetch
  const shouldFetch = !props.userTypes || props.userTypes.length === 0;
  const { data: fetchedUserTypes, isLoading } = useEntityData('userTypes', {
    enabled: shouldFetch
  });

  const userTypes = props.userTypes || fetchedUserTypes;
  const selectedValues = isMultiple
    ? (Array.isArray(value) ? value : [])
    : [value].filter(Boolean);

  const handleChange = (typeId: string) => {
    if (isMultiple) {
      const newValues = selectedValues.includes(typeId)
        ? selectedValues.filter(v => v !== typeId)
        : [...selectedValues, typeId];
      onChange(newValues);
    } else {
      onChange(typeId);
    }
  };

  return (
    <BaseWidgetWrapper {...props}>
      <Select
        value={isMultiple ? '' : (value || '')}
        onValueChange={handleChange}
        disabled={props.disabled || props.readonly || isLoading}
      >
        <SelectTrigger>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading user types...</span>
            </div>
          ) : (
            <SelectValue placeholder={props.placeholder || 'Select user type(s)'} />
          )}
        </SelectTrigger>
        <SelectContent>
          {userTypes.map((userType: any) => {
            const typeId = userType.id || userType.value;
            const typeName = userType.name || userType.label || typeId;

            return (
              <SelectItem key={typeId} value={typeId}>
                {typeName}
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>

      {isMultiple && selectedValues.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {selectedValues.map((typeId) => {
            const userType = userTypes.find((t: any) => (t.id || t.value) === typeId);
            const typeName = userType?.name || userType?.label || typeId;

            return (
              <Badge key={typeId} variant="secondary">
                {typeName}
              </Badge>
            );
          })}
        </div>
      )}
    </BaseWidgetWrapper>
  );
};