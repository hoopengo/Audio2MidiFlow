import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React from 'react';
import apiService from '../lib/api';
import { useTaskStore } from '../store/useTaskStore';
import { useUIStore } from '../store/useUIStore';

// Query keys
export const uploadKeys = {
  all: ['upload'] as const,
  status: () => [...uploadKeys.all, 'status'] as const,
};

// Hook for upload status
export function useUploadStatus() {
  return useQuery({
    queryKey: uploadKeys.status(),
    queryFn: () => apiService.getUploadStatus(),
  });
}

// Hook for single file upload
export function useUploadFile() {
  const queryClient = useQueryClient();
  const addTask = useTaskStore((state) => state.addTask);
  const addNotification = useUIStore((state) => state.addNotification);
  const setUploading = useUIStore((state) => state.setUploading);
  const setUploadProgress = useUIStore((state) => state.setUploadProgress);

  return useMutation({
    mutationFn: (file: File) => apiService.uploadFile(file),
    onMutate: () => {
      setUploading(true);
      setUploadProgress(0);
      addNotification({
        type: 'info',
        title: 'Upload started',
        message: 'Your file is being uploaded...',
      });
    },
    onSuccess: (data) => {
      if (data.data.task_id) {
        // Create a task object from the upload response
        const newTask = {
          id: 0, // Will be updated when we fetch the full task
          task_id: data.data.task_id,
          original_filename: data.data.original_filename || 'Unknown',
          status: data.data.status as any,
          progress: 0,
          file_size: data.data.file_size,
          created_at: data.data.created_at || new Date().toISOString(),
        };
        addTask(newTask);
      }

      addNotification({
        type: 'success',
        title: 'Upload successful',
        message: data.message,
      });

      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Upload failed',
        message: error.response?.data?.error?.message || error.message,
      });
    },
    onSettled: () => {
      setUploading(false);
      setUploadProgress(0);
    },
  });
}

// Hook for multiple file upload
export function useUploadMultipleFiles() {
  const queryClient = useQueryClient();
  const addTask = useTaskStore((state) => state.addTask);
  const addNotification = useUIStore((state) => state.addNotification);
  const setUploading = useUIStore((state) => state.setUploading);
  const setUploadProgress = useUIStore((state) => state.setUploadProgress);

  return useMutation({
    mutationFn: (files: File[]) => apiService.uploadMultipleFiles(files),
    onMutate: () => {
      setUploading(true);
      setUploadProgress(0);
      addNotification({
        type: 'info',
        title: 'Batch upload started',
        message: 'Your files are being uploaded...',
      });
    },
    onSuccess: (data) => {
      // Add successful tasks to the store
      if (data.data.tasks) {
        data.data.tasks.forEach((taskData: any) => {
          if (taskData.task_id) {
            const newTask = {
              id: 0, // Will be updated when we fetch the full task
              task_id: taskData.task_id,
              original_filename: taskData.original_filename || 'Unknown',
              status: taskData.status as any,
              progress: 0,
              file_size: taskData.file_size,
              created_at: new Date().toISOString(),
            };
            addTask(newTask);
          }
        });
      }

      addNotification({
        type: 'success',
        title: 'Batch upload completed',
        message: `${data.data.successful_uploads || 0} of ${data.data.total_files || 0} files uploaded successfully.`,
      });

      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: any) => {
      addNotification({
        type: 'error',
        title: 'Batch upload failed',
        message: error.response?.data?.error?.message || error.message,
      });
    },
    onSettled: () => {
      setUploading(false);
      setUploadProgress(0);
    },
  });
}

// Hook for simulating upload progress (since we don't have real progress from the API)
export function useUploadProgress() {
  const setUploadProgress = useUIStore((state) => state.setUploadProgress);

  const simulateProgress = React.useCallback((duration: number = 3000) => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15;
      if (progress >= 95) {
        progress = 95;
        clearInterval(interval);
      }
      setUploadProgress(Math.round(progress));
    }, duration / 20);

    return () => clearInterval(interval);
  }, [setUploadProgress]);

  return { simulateProgress };
}