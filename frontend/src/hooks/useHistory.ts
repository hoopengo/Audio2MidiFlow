import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React from 'react';
import apiService from '../lib/api';
import { useUIStore } from '../store/useUIStore';
import { HistoryFilters } from '../types';

// Query keys
export const historyKeys = {
  all: ['history'] as const,
  lists: () => [...historyKeys.all, 'list'] as const,
  list: (filters: HistoryFilters) => [...historyKeys.lists(), filters] as const,
  details: () => [...historyKeys.all, 'detail'] as const,
  detail: (id: string) => [...historyKeys.details(), id] as const,
  statistics: () => [...historyKeys.all, 'statistics'] as const,
};

// Hook for fetching history
export function useHistory(filters: HistoryFilters = {}) {
  const addNotification = useUIStore((state) => state.addNotification);

  return useQuery({
    queryKey: historyKeys.list(filters),
    queryFn: () => apiService.getHistory(filters),
  });
}

// Hook for fetching history with side effects
export function useHistoryWithEffects(filters: HistoryFilters = {}) {
  const addNotification = useUIStore((state) => state.addNotification);

  const query = useQuery({
    queryKey: historyKeys.list(filters),
    queryFn: () => apiService.getHistory(filters),
  });

  // Handle side effects
  React.useEffect(() => {
    if (query.error) {
      addNotification({
        type: 'error',
        title: 'Failed to fetch history',
        message: (query.error as any)?.response?.data?.error?.message || (query.error as any)?.message,
      });
    }
  }, [query.error, addNotification]);

  return query;
}

// Hook for fetching a single history item
export function useHistoryItem(itemId: string) {
  const addNotification = useUIStore((state) => state.addNotification);

  return useQuery({
    queryKey: historyKeys.detail(itemId),
    queryFn: () => apiService.getHistoryItem(itemId),
    enabled: !!itemId,
  });
}

// Hook for fetching history statistics
export function useHistoryStatistics(days?: number, operationType?: string) {
  const addNotification = useUIStore((state) => state.addNotification);

  return useQuery({
    queryKey: [...historyKeys.statistics(), days, operationType],
    queryFn: () => apiService.getHistoryStatistics(days, operationType),
  });
}

// Hook for exporting history
export function useExportHistory() {
  const queryClient = useQueryClient();
  const addNotification = useUIStore((state) => state.addNotification);

  return useMutation({
    mutationFn: ({ 
      format = 'json', 
      days, 
      operationType 
    }: { 
      format?: 'json' | 'csv'; 
      days?: number; 
      operationType?: string; 
    }) => apiService.exportHistory(format, days, operationType),
    onSuccess: (data, variables) => {
      addNotification({
        type: 'success',
        title: 'Export completed',
        message: `History exported successfully in ${variables.format || 'json'} format`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Export failed',
        message: error.response?.data?.error?.message || error.message,
      });
    },
  });
}

// Hook for cleaning up history
export function useCleanupHistory() {
  const queryClient = useQueryClient();
  const addNotification = useUIStore((state) => state.addNotification);

  return useMutation({
    mutationFn: ({ 
      days = 30, 
      operationType, 
      status 
    }: { 
      days?: number; 
      operationType?: string; 
      status?: string; 
    }) => apiService.cleanupHistory(days, operationType, status),
    onSuccess: (data, variables) => {
      // Invalidate history queries to refresh data
      queryClient.invalidateQueries({ queryKey: historyKeys.lists() });
      queryClient.invalidateQueries({ queryKey: historyKeys.statistics() });
      
      addNotification({
        type: 'success',
        title: 'Cleanup completed',
        message: `History cleanup completed successfully`,
      });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Cleanup failed',
        message: error.response?.data?.error?.message || error.message,
      });
    },
  });
}