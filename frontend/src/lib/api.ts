import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiService {
  private client;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000, // 30 seconds timeout
      headers: {

      },
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`, {
          data: config.data,
          params: config.params,
          headers: config.headers,
        });
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for logging and error handling
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
          status: response.status,
          data: response.data,
          headers: response.headers,
        });
        return response;
      },
      (error) => {
        console.error('API Response Error:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message,
          config: error.config,
        });
        return Promise.reject(error);
      }
    );
  }

  // Upload endpoints
  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await this.client.post('/upload', formData);
    
    return response.data;
  }

  async uploadMultipleFiles(files: File[]) {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    
    const response = await this.client.post('/upload/batch', formData);
    
    return response.data;
  }

  async getUploadStatus() {
    const response = await this.client.get('/upload/status');
    return response.data;
  }

  // Task endpoints
  async getTasks(filters?: any) {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await this.client.get(`/tasks?${params.toString()}`);
    return response.data;
  }

  async getTask(taskId: string) {
    const response = await this.client.get(`/tasks/${taskId}`);
    return response.data;
  }

  async cancelTask(taskId: string) {
    const response = await this.client.post(`/tasks/${taskId}/cancel`);
    return response.data;
  }

  async cleanupOldTasks(hours: number = 24) {
    const response = await this.client.delete(`/tasks/cleanup?hours=${hours}`);
    return response.data;
  }

  async getTaskStatistics() {
    const response = await this.client.get('/tasks/statistics');
    return response.data;
  }

  async downloadMidiFile(taskId: string) {
    const response = await this.client.get(`/tasks/${taskId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // History endpoints
  async getHistory(filters?: any) {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await this.client.get(`/history?${params.toString()}`);
    return response.data;
  }

  async getHistoryItem(itemId: string) {
    const response = await this.client.get(`/history/${itemId}`);
    return response.data;
  }

  async getHistoryStatistics(days?: number, operationType?: string) {
    const params = new URLSearchParams();
    if (days) params.append('days', String(days));
    if (operationType) params.append('operation_type', operationType);
    
    const response = await this.client.get(`/history/statistics?${params.toString()}`);
    return response.data;
  }

  async exportHistory(format: 'json' | 'csv' = 'json', days?: number, operationType?: string) {
    const params = new URLSearchParams();
    params.append('format', format);
    if (days) params.append('days', String(days));
    if (operationType) params.append('operation_type', operationType);
    
    const response = await this.client.get(`/history/export?${params.toString()}`);
    return response.data;
  }

  async cleanupHistory(days: number = 30, operationType?: string, status?: string) {
    const params = new URLSearchParams();
    params.append('days', String(days));
    if (operationType) params.append('operation_type', operationType);
    if (status) params.append('status', status);
    
    const response = await this.client.delete(`/history/cleanup?${params.toString()}`);
    return response.data;
  }
}

const apiService = new ApiService();
export default apiService;