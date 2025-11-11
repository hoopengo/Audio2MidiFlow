import { format } from 'date-fns';
import { CheckCircle, Clock, Download, FileAudio, HardDrive, Loader, X, XCircle } from 'lucide-react';
import { useEffect } from 'react';
import { useCancelTask, useDownloadMidi, useTaskWithEffects } from '../hooks/useTasks';
import { useUIStore } from '../store/useUIStore';
import { TaskStatus } from '../types';
import { cn } from '../utils/cn';

export function TaskDetailModal() {
  const { 
    taskDetailModalOpen, 
    selectedTaskId, 
    closeTaskDetail 
  } = useUIStore((state) => ({
    taskDetailModalOpen: state.taskDetailModalOpen,
    selectedTaskId: state.selectedTaskId,
    closeTaskDetail: state.closeTaskDetail,
  }));

  const { data, isLoading, error } = useTaskWithEffects(selectedTaskId || '');
  const cancelTask = useCancelTask();
  const downloadMidi = useDownloadMidi();

  const task = data?.data;

  const handleDownload = () => {
    if (!task) return;
    const filename = `${task.original_filename.replace(/\.[^/.]+$/, '')}.mid`;
    downloadMidi.mutate({ taskId: task.task_id, filename });
  };

  const handleCancel = () => {
    if (!task) return;
    cancelTask.mutate(task.task_id);
  };

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'processing':
        return <Loader className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'cancelled':
        return <X className="h-5 w-5 text-gray-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400';
      case 'processing':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400';
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const canCancel = task && (task.status === 'pending' || task.status === 'processing');
  const canDownload = task && task.status === 'completed' && task.download_url;

  // Close modal on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeTaskDetail();
      }
    };

    if (taskDetailModalOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [taskDetailModalOpen, closeTaskDetail]);

  if (!taskDetailModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={closeTaskDetail}
        />

        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Task Details
            </h2>
            <button
              onClick={closeTaskDetail}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {isLoading ? (
              <div className="flex justify-center items-center py-12">
                <Loader className="h-8 w-8 animate-spin text-blue-500" />
                <span className="ml-2 text-gray-600 dark:text-gray-400">
                  Loading task details...
                </span>
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                <p className="text-red-600 dark:text-red-400 mb-4">
                  Failed to load task details
                </p>
              </div>
            ) : task ? (
              <div className="space-y-6">
                {/* Task header */}
                <div className="flex items-center space-x-4">
                  <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-full">
                    <FileAudio className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 truncate">
                      {task.original_filename}
                    </h3>
                    <div className="flex items-center space-x-2 mt-1">
                      <span
                        className={cn(
                          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                          getStatusColor(task.status)
                        )}
                      >
                        {getStatusIcon(task.status)}
                        <span className="ml-1">{task.status}</span>
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ID: {task.task_id}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Progress for processing tasks */}
                {task.status === 'processing' && (
                  <div>
                    <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                      <span>Processing Progress</span>
                      <span>{task.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                    {task.processing_stage && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                        Current stage: {task.processing_stage.replace(/_/g, ' ')}
                      </p>
                    )}
                  </div>
                )}

                {/* Task information grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                        File Information
                      </h4>
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <FileAudio className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            Size: {formatFileSize(task.file_size)}
                          </span>
                        </div>
                        {task.output_size && (
                          <div className="flex items-center space-x-2">
                            <HardDrive className="h-4 w-4 text-gray-400" />
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              Output: {formatFileSize(task.output_size)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                        Timeline
                      </h4>
                      <div className="space-y-2">
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          Created: {format(new Date(task.created_at), 'MMM d, yyyy HH:mm:ss')}
                        </div>
                        {task.started_at && (
                          <div className="text-sm text-gray-600 dark:text-gray-400">
                            Started: {format(new Date(task.started_at), 'MMM d, yyyy HH:mm:ss')}
                          </div>
                        )}
                        {task.completed_at && (
                          <div className="text-sm text-gray-600 dark:text-gray-400">
                            Completed: {format(new Date(task.completed_at), 'MMM d, yyyy HH:mm:ss')}
                          </div>
                        )}
                        {task.processing_time && (
                          <div className="text-sm text-gray-600 dark:text-gray-400">
                            Processing time: {task.processing_time} seconds
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Error message */}
                {task.error_message && (
                  <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                    <h4 className="text-sm font-medium text-red-800 dark:text-red-400 mb-2">
                      Error Details
                    </h4>
                    <p className="text-sm text-red-600 dark:text-red-400">
                      {task.error_message}
                    </p>
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  {canDownload && (
                    <button
                      onClick={handleDownload}
                      className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      <Download className="h-4 w-4" />
                      <span>Download MIDI</span>
                    </button>
                  )}

                  {canCancel && (
                    <button
                      onClick={handleCancel}
                      className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <X className="h-4 w-4" />
                      <span>Cancel Task</span>
                    </button>
                  )}

                  <button
                    onClick={closeTaskDetail}
                    className="px-4 py-2 bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}