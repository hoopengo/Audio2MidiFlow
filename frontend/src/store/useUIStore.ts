import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  timestamp: number;
}

interface UIState {
  // Sidebar state
  sidebarOpen: boolean;
  
  // Notifications
  notifications: Notification[];
  
  // Loading states
  isUploading: boolean;
  uploadProgress: number;
  
  // Modal states
  taskDetailModalOpen: boolean;
  selectedTaskId: string | null;
  
  // Theme
  theme: 'light' | 'dark' | 'system';
  
  // Actions
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  
  setUploading: (uploading: boolean) => void;
  setUploadProgress: (progress: number) => void;
  
  openTaskDetail: (taskId: string) => void;
  closeTaskDetail: () => void;
  
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useUIStore = create<UIState>()(
  devtools(
    (set, get) => ({
      // Initial state
      sidebarOpen: true,
      notifications: [],
      isUploading: false,
      uploadProgress: 0,
      taskDetailModalOpen: false,
      selectedTaskId: null,
      theme: 'system',

      // Actions
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      toggleSidebar: () => set((state) => ({ 
        sidebarOpen: !state.sidebarOpen 
      })),

      addNotification: (notification) => {
        const id = Math.random().toString(36).substring(2, 9);
        const timestamp = Date.now();
        const newNotification = { ...notification, id, timestamp };
        
        set((state) => ({
          notifications: [...state.notifications, newNotification]
        }));

        // Auto-remove notification after duration (default 5 seconds)
        const duration = notification.duration ?? 5000;
        if (duration > 0) {
          setTimeout(() => {
            get().removeNotification(id);
          }, duration);
        }
      },

      removeNotification: (id) => set((state) => ({
        notifications: state.notifications.filter(n => n.id !== id)
      })),

      clearNotifications: () => set({ notifications: [] }),

      setUploading: (uploading) => set({ isUploading: uploading }),

      setUploadProgress: (progress) => set({ uploadProgress: progress }),

      openTaskDetail: (taskId) => set({
        taskDetailModalOpen: true,
        selectedTaskId: taskId
      }),

      closeTaskDetail: () => set({
        taskDetailModalOpen: false,
        selectedTaskId: null
      }),

      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'ui-store',
    }
  )
);