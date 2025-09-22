'use client';

import { useState, useEffect, useRef } from 'react';
import { pipelinesApi, usersApi, permissionsApi } from '@/lib/api';

interface Pipeline {
  id: string;
  name: string;
  slug: string;
  description?: string;
}

interface PipelineField {
  id: string;
  name: string;
  label: string;
  field_type: string;
  is_required: boolean;
  config?: any;
}

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  user_type?: any;
}

interface UserType {
  id: string;
  name: string;
  description?: string;
}

interface WorkflowData {
  pipelines: Pipeline[];
  users: User[];
  userTypes: UserType[];
  pipelineFields: Record<string, PipelineField[]>; // Keyed by pipeline ID
  loading: {
    pipelines: boolean;
    users: boolean;
    userTypes: boolean;
    fields: boolean;
  };
  error: {
    pipelines: string | null;
    users: string | null;
    userTypes: string | null;
    fields: string | null;
  };
  fetchPipelineFields: (pipelineId: string) => Promise<void>;
  refetchAll: () => Promise<void>;
}

export function useWorkflowData(): WorkflowData {
  console.log('[useWorkflowData] Hook called/rendered', {
    timestamp: new Date().toISOString()
  });

  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [userTypes, setUserTypes] = useState<UserType[]>([]);
  const [pipelineFields, setPipelineFields] = useState<Record<string, PipelineField[]>>({});

  const [loading, setLoading] = useState({
    pipelines: false,
    users: false,
    userTypes: false,
    fields: false
  });

  const [error, setError] = useState({
    pipelines: null as string | null,
    users: null as string | null,
    userTypes: null as string | null,
    fields: null as string | null
  });

  // Fetch pipelines
  const fetchPipelines = async () => {
    setLoading(prev => ({ ...prev, pipelines: true }));
    setError(prev => ({ ...prev, pipelines: null }));

    try {
      const response = await pipelinesApi.list();
      const pipelineData = response.data;

      // Handle both array and paginated response
      const pipelineList = Array.isArray(pipelineData)
        ? pipelineData
        : pipelineData.results || [];

      setPipelines(pipelineList);
    } catch (err: any) {
      console.error('Failed to fetch pipelines:', err);
      setError(prev => ({
        ...prev,
        pipelines: err.response?.data?.detail || err.message || 'Failed to fetch pipelines'
      }));
    } finally {
      setLoading(prev => ({ ...prev, pipelines: false }));
    }
  };

  // Fetch users
  const fetchUsers = async () => {
    setLoading(prev => ({ ...prev, users: true }));
    setError(prev => ({ ...prev, users: null }));

    try {
      const response = await usersApi.list();
      const userData = response.data;

      // Handle both array and paginated response
      const userList = Array.isArray(userData)
        ? userData
        : userData.results || [];

      // Add full_name if not present
      const usersWithFullName = userList.map((user: any) => ({
        ...user,
        full_name: user.full_name || `${user.first_name} ${user.last_name}`.trim() || user.email
      }));

      setUsers(usersWithFullName);
    } catch (err: any) {
      console.error('Failed to fetch users:', err);
      setError(prev => ({
        ...prev,
        users: err.response?.data?.detail || err.message || 'Failed to fetch users'
      }));
    } finally {
      setLoading(prev => ({ ...prev, users: false }));
    }
  };

  // Fetch user types
  const fetchUserTypes = async () => {
    setLoading(prev => ({ ...prev, userTypes: true }));
    setError(prev => ({ ...prev, userTypes: null }));

    try {
      const response = await permissionsApi.getUserTypes();
      const userTypeData = response.data;

      // Handle both array and paginated response
      const userTypeList = Array.isArray(userTypeData)
        ? userTypeData
        : userTypeData.results || [];

      setUserTypes(userTypeList);
    } catch (err: any) {
      console.error('Failed to fetch user types:', err);
      setError(prev => ({
        ...prev,
        userTypes: err.response?.data?.detail || err.message || 'Failed to fetch user types'
      }));
    } finally {
      setLoading(prev => ({ ...prev, userTypes: false }));
    }
  };

  // Track ongoing requests to prevent duplicates
  const fieldRequestsRef = useRef<Set<string>>(new Set());

  // Fetch fields for a specific pipeline
  const fetchPipelineFields = async (pipelineId: string) => {
    console.log('[useWorkflowData] fetchPipelineFields called', {
      pipelineId,
      alreadyCached: !!pipelineFields[pipelineId],
      requestInProgress: fieldRequestsRef.current.has(pipelineId),
      timestamp: new Date().toISOString()
    });

    // Don't fetch if we already have the fields cached
    if (pipelineFields[pipelineId]) {
      console.log('[useWorkflowData] Fields already cached for pipeline:', pipelineId);
      return;
    }

    // Don't fetch if a request is already in progress
    if (fieldRequestsRef.current.has(pipelineId)) {
      console.log('[useWorkflowData] Request already in progress for pipeline:', pipelineId);
      return;
    }

    console.log('[useWorkflowData] Starting fetch for pipeline fields:', pipelineId);
    fieldRequestsRef.current.add(pipelineId);
    setLoading(prev => ({ ...prev, fields: true }));
    setError(prev => ({ ...prev, fields: null }));

    try {
      const response = await pipelinesApi.getFields(pipelineId);
      const fieldsData = response.data;

      // Handle both array and paginated response
      const fieldList = Array.isArray(fieldsData)
        ? fieldsData
        : fieldsData.results || [];


      setPipelineFields(prev => ({
        ...prev,
        [pipelineId]: fieldList
      }));
    } catch (err: any) {
      console.error(`Failed to fetch fields for pipeline ${pipelineId}:`, err);
      setError(prev => ({
        ...prev,
        fields: err.response?.data?.detail || err.message || 'Failed to fetch pipeline fields'
      }));
    } finally {
      fieldRequestsRef.current.delete(pipelineId);
      setLoading(prev => ({ ...prev, fields: false }));
    }
  };

  // Refetch all data
  const refetchAll = async () => {
    await Promise.all([
      fetchPipelines(),
      fetchUsers(),
      fetchUserTypes()
    ]);
  };

  // Initial data fetch
  useEffect(() => {
    fetchPipelines();
    fetchUsers();
    fetchUserTypes();
  }, []);

  return {
    pipelines,
    users,
    userTypes,
    pipelineFields,
    loading,
    error,
    fetchPipelineFields,
    refetchAll
  };
}

// Helper function to get field options from a pipeline field
export function getFieldOptions(field: PipelineField): Array<{ label: string; value: any }> {
  if (!field.config) return [];

  // For select/multiselect fields
  if (field.field_type === 'select' || field.field_type === 'multiselect') {
    if (Array.isArray(field.config.options)) {
      return field.config.options.map((opt: any) => {
        if (typeof opt === 'string') {
          return { label: opt, value: opt };
        }
        return { label: opt.label || opt.value, value: opt.value };
      });
    }
  }

  // For radio fields
  if (field.field_type === 'radio' && Array.isArray(field.config.choices)) {
    return field.config.choices.map((choice: any) => {
      if (typeof choice === 'string') {
        return { label: choice, value: choice };
      }
      return { label: choice.label || choice.value, value: choice.value };
    });
  }

  return [];
}