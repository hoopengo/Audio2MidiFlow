import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React from 'react';
import apiService from '../lib/api';
import { useTaskStore } from '../store/useTaskStore';
import { useUIStore } from '../store/useUIStore';
import { TaskFilters } from '../types';

// Query keys
export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters: TaskFilters) => [...taskKeys.lists(), filters] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
  statistics: () => [...taskKeys.all, 'statistics'] as const,
};

// Hook for fetching tasks
export function useTasks(filters: TaskFilters = {}) {
  const setTasks = useTaskStore((state) => state.setTasks);
  const setLoading = useTaskStore((state) => state.setLoading);
  const addNotification = useUIStore((state) => state.addNotification);

  return useQuery({
    queryKey: taskKeys.list(filters),
    queryFn: () => apiService.getTasks(filters),
  });
}

// Hook for fetching tasks with side effects
export function useTasksWithEffects(filters: TaskFilters = {}) {
  const setTasks = useTaskStore((state) => state.setTasks);
  const setLoading = useTaskStore((state) => state.setLoading);
  const addNotification = useUIStore((state) => state.addNotification);

  const query = useQuery({
    queryKey: taskKeys.list(filters),
    queryFn: () => apiService.getTasks(filters),
    refetchInterval: (query) => {
      // Auto-refresh every 2 seconds if there are active tasks
      const data = query.state.data;
      if (data?.data?.tasks) {
        const hasActiveTasks = data.data.tasks.some((task: any) =>
          task.status === 'pending' || task.status === 'processing'
        );
        return hasActiveTasks ? 2000 : false; // 2 seconds for active tasks, no refresh otherwise
      }
      return false;
    },
  });

  // Handle side effects
  React.useEffect(() => {
    if (query.data) {
      setTasks(query.data.data.tasks);
      setLoading(false);
    }
  }, [query.data, setTasks, setLoading]);

  React.useEffect(() => {
    if (query.error) {
      addNotification({
        type: 'error',
        title: 'Failed to fetch tasks',
        message: (query.error as any)?.response?.data?.error?.message || (query.error as any)?.message,
      });
      setLoading(false);
    }
  }, [query.error, addNotification, setLoading]);

  // Determine if auto-refresh is active
  const hasActiveTasks = query.data?.data?.tasks?.some((task: any) =>
    task.status === 'pending' || task.status === 'processing'
  ) || false;

  return {
    ...query,
    hasActiveTasks,
  };
}

// Hook for fetching a single task
export function useTask(taskId: string) {
  const setCurrentTask = useTaskStore((state) => state.setCurrentTask);
  const updateTask = useTaskStore((state) => state.updateTask);
  const addNotification = useUIStore((state) => state.addNotification);

  return useQuery({
    queryKey: taskKeys.detail(taskId),
    queryFn: () => apiService.getTask(taskId),
    enabled: !!taskId,
    refetchInterval: (query) => {
      // Poll more frequently for active tasks
      const data = query.state.data;
      if (data?.data?.status === 'processing' || data?.data?.status === 'pending') {
        return 2000; // 2 seconds
      }
      return false; // Don't refetch for completed/failed tasks
    },
  });
}

// Hook for fetching a single task with side effects
export function useTaskWithEffects(taskId: string) {
  const setCurrentTask = useTaskStore((state) => state.setCurrentTask);
  const updateTask = useTaskStore((state) => state.updateTask);
  const addNotification = useUIStore((state) => state.addNotification);

  const query = useQuery({
    queryKey: taskKeys.detail(taskId),
    queryFn: () => apiService.getTask(taskId),
    enabled: !!taskId,
    refetchInterval: (query) => {
      // Poll more frequently for active tasks
      const data = query.state.data;
      if (data?.data?.status === 'processing' || data?.data?.status === 'pending') {
        return 2000; // 2 seconds
      }
      return false; // Don't refetch for completed/failed tasks
    },
  });

  // Handle side effects
  React.useEffect(() => {
    if (query.data?.data) {
      setCurrentTask(query.data.data);
      updateTask(taskId, query.data.data);
    }
  }, [query.data, taskId, setCurrentTask, updateTask]);

  React.useEffect(() => {
    if (query.error) {
      addNotification({
        type: 'error',
        title: 'Failed to fetch task',
        message: (query.error as any)?.response?.data?.error?.message || (query.error as any)?.message,
      });
    }
  }, [query.error, addNotification]);

  return query;
}

// Hook for task statistics
export function useTaskStatistics() {
  const addNotification = useUIStore((state) => state.addNotification);

  return useQuery({
    queryKey: taskKeys.statistics(),
    queryFn: () => apiService.getTaskStatistics(),
  });
}

// Hook for cancelling a task
export function useCancelTask() {
  const queryClient = useQueryClient();
  const updateTask = useTaskStore((state) => state.updateTask);
  const addNotification = useUIStore((state) => state.addNotification);

  return useMutation({
    mutationFn: (taskId: string) => apiService.cancelTask(taskId),
    onSuccess: (data, taskId) => {
      updateTask(taskId, { status: 'cancelled' });
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      
      addNotification({
        type: 'success',
        title: 'Task cancelled',
        message: `Task ${taskId} has been cancelled successfully.`,
      });
    },
    onError: (error: any, taskId) => {
      addNotification({
        type: 'error',
        title: 'Failed to cancel task',
        message: error.response?.data?.error?.message || error.message,
      });
    },
  });
}

// Hook for cleaning up old tasks
export function useCleanupTasks() {
  const queryClient = useQueryClient();
  const addNotification = useUIStore((state) => state.addNotification);

  return useMutation({
    mutationFn: (hours: number = 24) => apiService.cleanupOldTasks(hours),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
      queryClient.invalidateQueries({ queryKey: taskKeys.statistics() });
      
      addNotification({
        type: 'success',
        title: 'Cleanup initiated',
        message: 'Old tasks cleanup has been initiated.',
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Failed to cleanup tasks',
        message: error.response?.data?.error?.message || error.message,
      });
    },
  });
}

// Hook for downloading MIDI files
export function useDownloadMidi() {
  const addNotification = useUIStore((state) => state.addNotification);

  return useMutation({
    mutationFn: ({ taskId, filename }: { taskId: string; filename: string }) => 
      apiService.downloadMidiFile(taskId).then((blob) => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }),
    onSuccess: (_, { filename }) => {
      addNotification({
        type: 'success',
        title: 'Download started',
        message: `Downloading ${filename}...`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Download failed',
        message: error.response?.data?.error?.message || error.message,
      });
    },
  });
}