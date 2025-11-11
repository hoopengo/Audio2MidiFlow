import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Task, TaskStatus } from '../types';

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  setCurrentTask: (task: Task | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // Computed
  getTasksByStatus: (status: TaskStatus) => Task[];
  getTaskById: (taskId: string) => Task | undefined;
  getActiveTasks: () => Task[];
  getCompletedTasks: () => Task[];
}

export const useTaskStore = create<TaskState>()(
  devtools(
    (set, get) => ({
      // Initial state
      tasks: [],
      currentTask: null,
      isLoading: false,
      error: null,

      // Actions
      setTasks: (tasks) => set({ tasks }),

      addTask: (task) => set((state) => ({ 
        tasks: [task, ...state.tasks] 
      })),

      updateTask: (taskId, updates) => set((state) => ({
        tasks: state.tasks.map(task => 
          task.task_id === taskId 
            ? { ...task, ...updates }
            : task
        ),
        currentTask: state.currentTask?.task_id === taskId 
          ? { ...state.currentTask, ...updates }
          : state.currentTask
      })),

      setCurrentTask: (task) => set({ currentTask: task }),

      setLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error }),

      clearError: () => set({ error: null }),

      // Computed getters
      getTasksByStatus: (status) => {
        return get().tasks.filter(task => task.status === status);
      },

      getTaskById: (taskId) => {
        return get().tasks.find(task => task.task_id === taskId);
      },

      getActiveTasks: () => {
        return get().tasks.filter(task => 
          task.status === 'pending' || task.status === 'processing'
        );
      },

      getCompletedTasks: () => {
        return get().tasks.filter(task => task.status === 'completed');
      },
    }),
    {
      name: 'task-store',
    }
  )
);