export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

export type ProcessingStage = 
  | 'queued'
  | 'audio_loading'
  | 'feature_extraction'
  | 'pitch_detection'
  | 'midi_generation'
  | 'finalization';

export interface Task {
  id: number;
  task_id: string;
  original_filename: string;
  status: TaskStatus;
  progress: number;
  processing_stage?: ProcessingStage;
  error_message?: string;
  file_size?: number;
  output_size?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  estimated_completion?: string;
  processing_time?: number;
  download_url?: string;
}

export interface TaskListResponse {
  success: boolean;
  data: {
    tasks: Task[];
    pagination: {
      total: number;
      limit: number;
      offset: number;
      has_more: boolean;
    };
  };
}

export interface UploadResponse {
  success: boolean;
  data: {
    task_id?: string;
    status?: string;
    original_filename?: string;
    file_size?: number;
    created_at?: string;
    estimated_processing_time?: number;
    tasks?: Array<{
      task_id?: string;
      status?: string;
      original_filename?: string;
      file_size?: number;
      error?: string;
      filename?: string;
    }>;
    total_files?: number;
    successful_uploads?: number;
    failed_uploads?: number;
  };
  message: string;
}

export type OperationType = 
  | 'file_upload'
  | 'task_processing'
  | 'task_completion'
  | 'task_cancellation'
  | 'error'
  | 'cleanup';

export type OperationStatus = 'success' | 'error' | 'pending';

export interface OperationHistory {
  id: number;
  task_id?: string;
  user_id?: string;
  operation: string; // Changed from operation_type to match backend
  status: string; // Changed from OperationStatus to match backend
  details?: string;
  operation_metadata?: Record<string, any>;
  duration_ms?: number;
  timestamp: string;
  task_info?: {
    status: TaskStatus;
    progress: number;
    original_filename: string;
  };
  related_operations?: Array<{
    id: number;
    operation: string; // Changed from operation_type to match backend
    status: string; // Changed from OperationStatus to match backend
    timestamp: string;
    duration_ms?: number;
  }>;
}

export interface HistoryListResponse {
  success: boolean;
  data: {
    history: OperationHistory[];
    pagination: {
      total: number;
      limit: number;
      offset: number;
      has_more: boolean;
    };
    filters_applied: {
      operation_type?: string;
      task_id?: string;
      user_id?: string;
      status?: string;
      start_date?: string;
      end_date?: string;
    };
  };
}

export interface TaskStatistics {
  period?: {
    start_date: string;
    end_date: string;
    days: number;
  };
  total_operations?: number;
  operations_by_type?: Record<string, number>;
  operations_by_status?: Record<string, number>;
  avg_duration_by_type_ms?: Record<string, number>;
  daily_operations?: Array<{
    date: string;
    count: number;
  }>;
  error_rate_percent?: number;
  recent_operations?: Array<{
    id: number;
    operation_type: OperationType;
    status: OperationStatus;
    timestamp: string;
    duration_ms?: number;
    task_id?: string;
  }>;
  total_tasks?: number;
  recent_tasks_24h?: number;
  active_processing?: number;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface HistoryFilters extends PaginationParams {
  operation_type?: string;
  task_id?: string;
  user_id?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

export interface TaskFilters extends PaginationParams {
  status?: TaskStatus;
}