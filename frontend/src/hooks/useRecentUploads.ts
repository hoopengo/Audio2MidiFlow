import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import apiService from '../lib/api';
import { useTaskStore } from '../store/useTaskStore';
import { Task, TaskStatus } from '../types';

// Query keys
export const recentUploadsKeys = {
  all: ['recentUploads'] as const,
  lists: () => [...recentUploadsKeys.all, 'list'] as const,
  list: (hours: number) => [...recentUploadsKeys.lists(), hours] as const,
};

// Hook for fetching recent uploads
export function useRecentUploads(hours: number = 24) {
  const [activeTasks, setActiveTasks] = useState<string[]>([]);
  
  // Subscribe to Zustand store for local tasks
  const localTasks = useTaskStore((state) => state.tasks);
  
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: recentUploadsKeys.list(hours),
    queryFn: () => apiService.getTasks({
      limit: 50, // Get last 50 tasks
      sort: 'created_at',
      order: 'desc'
    }),
    refetchInterval: (query) => {
      // Auto-refresh every 2 seconds if there are active tasks
      if (activeTasks.length > 0) {
        return 2000;
      }
      return false; // Don't refetch if no active tasks
    },
  });

  // Merge local tasks with API data
  const mergedTasks = useMemo(() => {
    const apiTasks = data?.data?.tasks || [];
    
    // Create a map of API tasks by task_id for quick lookup
    const apiTaskMap = new Map(apiTasks.map((task: Task) => [task.task_id, task]));
    
    // Filter local tasks that don't exist in API (new uploads)
    const localOnlyTasks = localTasks.filter(
      localTask => !apiTaskMap.has(localTask.task_id)
    );
    
    // Combine local-only tasks with API tasks
    const allTasks = [...localOnlyTasks, ...apiTasks];
    
    // Sort by creation date (newest first)
    return allTasks.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [data, localTasks]);

  // Update active tasks based on merged data
  useEffect(() => {
    const active = mergedTasks
      .filter((task: Task) => task.status === 'pending' || task.status === 'processing')
      .map((task: Task) => task.task_id);
    setActiveTasks(active);
  }, [mergedTasks]);

  // Filter tasks from the last N hours
  const recentTasks = mergedTasks.filter((task: Task) => {
    const taskDate = new Date(task.created_at);
    const now = new Date();
    const hoursDiff = (now.getTime() - taskDate.getTime()) / (1000 * 60 * 60);
    return hoursDiff <= hours;
  });

  // Group tasks by status
  const tasksByStatus = recentTasks.reduce((acc: Record<TaskStatus, Task[]>, task: Task) => {
    if (!acc[task.status]) {
      acc[task.status] = [];
    }
    acc[task.status].push(task);
    return acc;
  }, {} as Record<TaskStatus, Task[]>);

  return {
    data: recentTasks,
    tasksByStatus,
    isLoading,
    error,
    refetch,
    activeTasks,
    hasActiveTasks: activeTasks.length > 0,
  };
}