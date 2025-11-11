import { format } from 'date-fns';
import {
    CheckCircle,
    Clock,
    Download,
    Loader,
    Music,
    RefreshCw,
    X,
    XCircle
} from 'lucide-react';
import { useRecentUploads } from '../hooks/useRecentUploads';
import { useDownloadMidi } from '../hooks/useTasks';
import { cn } from '../utils/cn';

interface RecentUploadsProps {
  className?: string;
  hours?: number; // How many hours of recent uploads to show
}

export function RecentUploads({ className, hours = 24 }: RecentUploadsProps) {
  const { 
    data: recentTasks, 
    tasksByStatus, 
    isLoading, 
    error, 
    refetch, 
    hasActiveTasks 
  } = useRecentUploads(hours);
  const downloadMidi = useDownloadMidi();

  const handleDownload = (task: any) => {
    const filename = `${task.original_filename.replace(/\.[^/.]+$/, '')}.mid`;
    downloadMidi.mutate({ taskId: task.task_id, filename });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'processing':
        return <Loader className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <X className="h-4 w-4 text-gray-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
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

  const canDownload = (task: any) => {
    return task.status === 'completed' && task.download_url;
  };

  if (isLoading) {
    return (
      <div className={cn('flex justify-center items-center py-8', className)}>
        <Loader className="h-6 w-6 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600 dark:text-gray-400">Loading recent uploads...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('text-center py-8', className)}>
        <XCircle className="h-8 w-8 text-red-500 mx-auto mb-3" />
        <p className="text-red-600 dark:text-red-400 mb-3">
          Failed to load recent uploads
        </p>
        <button
          onClick={() => refetch()}
          className="px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!recentTasks || recentTasks.length === 0) {
    return (
      <div className={cn('text-center py-8', className)}>
        <Music className="h-8 w-8 text-gray-400 mx-auto mb-3" />
        <p className="text-gray-600 dark:text-gray-400">
          No recent uploads found
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header with refresh button and auto-refresh indicator */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Recent Uploads ({recentTasks.length})
        </h3>
        <div className="flex items-center space-x-2">
          {hasActiveTasks && (
            <div className="flex items-center text-xs text-green-600 dark:text-green-400">
              <Loader className="h-3 w-3 animate-spin mr-1" />
              Auto-refreshing
            </div>
          )}
          <button
            onClick={() => refetch()}
            className="p-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 transition-colors"
            title="Refresh recent uploads"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Task list */}
      <div className="space-y-3">
        {recentTasks.map((task: any) => (
          <div
            key={task.task_id}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between">
              {/* Task info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-3 mb-2">
                  <Music className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  <h4
                    className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate"
                    title={task.original_filename}
                  >
                    {task.original_filename}
                  </h4>
                  <span
                    className={cn(
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      getStatusColor(task.status)
                    )}
                  >
                    {getStatusIcon(task.status)}
                    <span className="ml-1">{task.status}</span>
                  </span>
                </div>

                {/* Progress bar for processing tasks */}
                {task.status === 'processing' && (
                  <div className="mb-2">
                    <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                      <span>Progress</span>
                      <span>{task.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700">
                      <div
                        className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                    {task.processing_stage && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Stage: {task.processing_stage.replace(/_/g, ' ')}
                      </p>
                    )}
                  </div>
                )}

                {/* Task details */}
                <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                  <span>Size: {formatFileSize(task.file_size)}</span>
                  <span>Created: {format(new Date(task.created_at), 'MMM d, HH:mm')}</span>
                  {task.processing_time && (
                    <span>Duration: {task.processing_time}s</span>
                  )}
                  {task.error_message && (
                    <span className="text-red-500 truncate max-w-xs">
                      Error: {task.error_message}
                    </span>
                  )}
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center space-x-2 ml-4">
                {canDownload(task) && (
                  <button
                    onClick={() => handleDownload(task)}
                    className="p-2 text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300 transition-colors"
                    title="Download MIDI file"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Status summary */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap gap-4 text-sm">
          {Object.entries(tasksByStatus).map(([status, tasks]) => (
            <div key={status} className="flex items-center space-x-2">
              {getStatusIcon(status)}
              <span className="text-gray-600 dark:text-gray-400">
                {status}: {Array.isArray(tasks) ? tasks.length : 0}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}