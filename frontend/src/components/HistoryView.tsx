import { format } from 'date-fns';
import {
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  FileAudio,
  Filter,
  History as HistoryIcon,
  Trash2,
  XCircle
} from 'lucide-react';
import { useState } from 'react';
import { useCleanupHistory, useExportHistory, useHistoryWithEffects } from '../hooks/useHistory';
import { useUIStore } from '../store/useUIStore';
import { HistoryFilters, OperationHistory } from '../types';
import { cn } from '../utils/cn';

export function HistoryView() {
  const [expandedItems, setExpandedItems] = useState<number[]>([]);
  const [filters, setFilters] = useState({
    operation_type: '',
    status: '',
    date_range: 'all',
  });
  const [showFilters, setShowFilters] = useState(false);
  const addNotification = useUIStore((state) => state.addNotification);
  
  // Convert UI filters to API filters
  const getApiFilters = (): HistoryFilters => {
    const apiFilters: HistoryFilters = {};
    
    if (filters.operation_type) {
      apiFilters.operation_type = filters.operation_type;
    }
    
    if (filters.status) {
      apiFilters.status = filters.status;
    }
    
    // Handle date range conversion
    if (filters.date_range !== 'all') {
      const now = new Date();
      let startDate: Date | null = null;
      
      switch (filters.date_range) {
        case 'today':
          startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          break;
        case 'week':
          startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        case 'month':
          startDate = new Date(now.getFullYear(), now.getMonth(), 1);
          break;
      }
      
      if (startDate) {
        apiFilters.start_date = startDate.toISOString();
        apiFilters.end_date = now.toISOString();
      }
    }
    
    return apiFilters;
  };
  
  // Fetch history data
  const { data: historyData, isLoading, error } = useHistoryWithEffects(getApiFilters());
  
  // Export and cleanup mutations
  const exportMutation = useExportHistory();
  const cleanupMutation = useCleanupHistory();
  
  // Extract history list from response
  const history = historyData?.data?.history || [];

  const getOperationIcon = (type: string) => {
    switch (type) {
      case 'file_upload':
        return <FileAudio className="h-4 w-4 text-blue-500" />;
      case 'task_processing':
      case 'task_started':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'task_completion':
      case 'task_completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'task_cancellation':
      case 'task_cancelled':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'error':
      case 'error_occurred':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'audio_loading':
      case 'feature_extraction':
      case 'pitch_detection':
      case 'midi_generation':
        return <Clock className="h-4 w-4 text-purple-500" />;
      case 'file_cleanup':
        return <Trash2 className="h-4 w-4 text-orange-500" />;
      default:
        return <HistoryIcon className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
      case 'info':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'warning':
        return <Clock className="h-4 w-4 text-orange-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
      case 'failed':
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
      case 'pending':
      case 'info':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400';
      case 'warning':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return 'Unknown';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const toggleExpanded = (id: number) => {
    setExpandedItems((prev) =>
      prev.includes(id)
        ? prev.filter((item) => item !== id)
        : [...prev, id]
    );
  };

  const handleExport = () => {
    exportMutation.mutate({
      format: 'json',
      days: filters.date_range === 'all' ? undefined :
            filters.date_range === 'today' ? 1 :
            filters.date_range === 'week' ? 7 :
            filters.date_range === 'month' ? 30 : undefined,
      operationType: filters.operation_type || undefined,
    });
  };

  const handleCleanup = () => {
    cleanupMutation.mutate({
      days: 30, // Default to 30 days
      operationType: filters.operation_type || undefined,
      status: filters.status || undefined,
    });
  };

  // The filtering is now handled by the API, but we'll keep this for any client-side filtering
  const filteredHistory = history.filter((item: OperationHistory) => {
    if (filters.operation_type && item.operation !== filters.operation_type) {
      return false;
    }
    if (filters.status && item.status !== filters.status) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Operation History
        </h2>
        <div className="flex space-x-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center space-x-2 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <Filter className="h-4 w-4" />
            <span>Filters</span>
          </button>
          <button
            onClick={handleExport}
            className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Download className="h-4 w-4" />
            <span>Export</span>
          </button>
          <button
            onClick={handleCleanup}
            className="flex items-center space-x-2 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
            <span>Cleanup</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Operation Type
              </label>
              <select
                value={filters.operation_type}
                onChange={(e) => setFilters({ ...filters, operation_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="">All Types</option>
                <option value="file_upload">File Upload</option>
                <option value="task_started">Task Started</option>
                <option value="audio_loading">Audio Loading</option>
                <option value="feature_extraction">Feature Extraction</option>
                <option value="pitch_detection">Pitch Detection</option>
                <option value="midi_generation">MIDI Generation</option>
                <option value="task_completed">Task Completed</option>
                <option value="task_failed">Task Failed</option>
                <option value="task_cancelled">Task Cancelled</option>
                <option value="error_occurred">Error Occurred</option>
                <option value="file_cleanup">File Cleanup</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Status
              </label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="">All Statuses</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Date Range
              </label>
              <select
                value={filters.date_range}
                onChange={(e) => setFilters({ ...filters, date_range: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* History list */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">
              Loading history...
            </p>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              Failed to load history records
            </p>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="text-center py-12">
            <HistoryIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              No history records found
            </p>
          </div>
        ) : (
          filteredHistory.map((item: OperationHistory) => (
            <div
              key={item.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
            >
              <div
                className="p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                onClick={() => toggleExpanded(item.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getOperationIcon(item.operation)}
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {item.operation.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {format(new Date(item.timestamp), 'MMM d, yyyy HH:mm:ss')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span
                      className={cn(
                        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                        getStatusColor(item.status)
                      )}
                    >
                      {getStatusIcon(item.status)}
                      <span className="ml-1">{item.status}</span>
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {formatDuration(item.duration_ms)}
                    </span>
                    {expandedItems.includes(item.id) ? (
                      <ChevronUp className="h-4 w-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-gray-400" />
                    )}
                  </div>
                </div>
              </div>

              {/* Expanded details */}
              {expandedItems.includes(item.id) && (
                <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="pt-4 space-y-3">
                    {item.details && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                          Details
                        </h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {item.details}
                        </p>
                      </div>
                    )}

                    {item.task_id && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                          Task ID
                        </h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {item.task_id}
                        </p>
                      </div>
                    )}

                    {item.task_info && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                          Task Information
                        </h4>
                        <div className="space-y-1">
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            File: {item.task_info.original_filename}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Status: {item.task_info.status}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Progress: {item.task_info.progress}%
                          </p>
                        </div>
                      </div>
                    )}

                    {item.operation_metadata && Object.keys(item.operation_metadata).length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                          Metadata
                        </h4>
                        <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 p-2 rounded overflow-x-auto">
                          {JSON.stringify(item.operation_metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}