import {
  BarChart3,
  CheckCircle,
  Clock,
  RefreshCw,
  TrendingUp,
  XCircle
} from 'lucide-react';
import { useTaskStatistics } from '../hooks/useTasks';
import { cn } from '../utils/cn';

export function StatisticsView() {
  const { data, isLoading, error, refetch } = useTaskStatistics();

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '0s';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin">
          <BarChart3 className="h-8 w-8 text-blue-500" />
        </div>
        <span className="ml-2 text-gray-600 dark:text-gray-400">
          Loading statistics...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-600 dark:text-red-400 mb-4">
          Failed to load statistics
        </p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  const stats = data?.data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Statistics
        </h2>
        <button
          onClick={() => refetch()}
          className="p-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 transition-colors"
          title="Refresh statistics"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Tasks */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-full">
              <BarChart3 className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Total Tasks
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats?.total_tasks || 0}
              </p>
            </div>
          </div>
        </div>

        {/* Recent Tasks */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-full">
              <TrendingUp className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Last 24 Hours
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats?.recent_tasks_24h || 0}
              </p>
            </div>
          </div>
        </div>

        {/* Active Processing */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 dark:bg-yellow-900/20 rounded-full">
              <Clock className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Active Now
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats?.active_processing || 0}
              </p>
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-full">
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Success Rate
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats?.error_rate_percent !== undefined
                  ? `${(100 - stats.error_rate_percent).toFixed(1)}%`
                  : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Operations by Type */}
      {stats?.operations_by_type && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Operations by Type
          </h3>
          <div className="space-y-3">
            {Object.entries(stats.operations_by_type).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                  {type.replace(/_/g, ' ')}
                </span>
                <div className="flex items-center space-x-2">
                  <div className="w-32 bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{
                        width: `${(count as number / Math.max(...Object.values(stats.operations_by_type || {}) as number[])) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm text-gray-600 dark:text-gray-400 w-12 text-right">
                    {count as number}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Operations by Status */}
      {stats?.operations_by_status && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Operations by Status
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(stats.operations_by_status).map(([status, count]) => (
              <div key={status} className="text-center">
                <div className={cn(
                  'inline-flex items-center justify-center w-16 h-16 rounded-full mb-2',
                  status === 'success' && 'bg-green-100 dark:bg-green-900/20',
                  status === 'error' && 'bg-red-100 dark:bg-red-900/20',
                  status === 'pending' && 'bg-yellow-100 dark:bg-yellow-900/20'
                )}>
                  {status === 'success' && <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />}
                  {status === 'error' && <XCircle className="h-8 w-8 text-red-600 dark:text-red-400" />}
                  {status === 'pending' && <Clock className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />}
                </div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                  {status}
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {count as number}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Average Processing Times */}
      {stats?.avg_duration_by_type_ms && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Average Processing Times
          </h3>
          <div className="space-y-3">
            {Object.entries(stats.avg_duration_by_type_ms).map(([type, duration]) => (
              <div key={type} className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                  {type.replace(/_/g, ' ')}
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {formatDuration(duration as number / 1000)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Operations */}
      {stats?.recent_operations && stats.recent_operations.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Recent Operations
          </h3>
          <div className="space-y-3">
            {stats.recent_operations.map((operation: any) => (
              <div key={operation.id} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div className="flex items-center space-x-3">
                  <div className={cn(
                    'p-2 rounded-full',
                    operation.status === 'success' && 'bg-green-100 dark:bg-green-900/20',
                    operation.status === 'error' && 'bg-red-100 dark:bg-red-900/20',
                    operation.status === 'pending' && 'bg-yellow-100 dark:bg-yellow-900/20'
                  )}>
                    {operation.status === 'success' && <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />}
                    {operation.status === 'error' && <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />}
                    {operation.status === 'pending' && <Clock className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 capitalize">
                      {operation.operation_type.replace(/_/g, ' ')}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {new Date(operation.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {operation.duration_ms && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {formatDuration(operation.duration_ms / 1000)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}