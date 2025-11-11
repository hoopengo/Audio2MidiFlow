import { AlertCircle, CheckCircle, Info, X, XCircle } from 'lucide-react';
import { useUIStore } from '../store/useUIStore';
import { cn } from '../utils/cn';

export function Notifications() {
  const { notifications, removeNotification } = useUIStore((state) => ({
    notifications: state.notifications,
    removeNotification: state.removeNotification,
  }));

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'info':
      default:
        return <Info className="h-5 w-5 text-blue-500" />;
    }
  };

  const getBackgroundColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800';
      case 'error':
        return 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800';
      case 'info':
      default:
        return 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800';
    }
  };

  const getTextColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'text-green-800 dark:text-green-200';
      case 'error':
        return 'text-red-800 dark:text-red-200';
      case 'warning':
        return 'text-yellow-800 dark:text-yellow-200';
      case 'info':
      default:
        return 'text-blue-800 dark:text-blue-200';
    }
  };

  if (notifications.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={cn(
            'p-4 rounded-lg shadow-lg border transition-all duration-300 transform',
            'animate-in slide-in-from-right-full',
            getBackgroundColor(notification.type)
          )}
        >
          <div className="flex items-start">
            <div className="flex-shrink-0">
              {getIcon(notification.type)}
            </div>
            <div className="ml-3 flex-1 min-w-0">
              <p className={cn(
                'text-sm font-medium',
                getTextColor(notification.type)
              )}>
                {notification.title}
              </p>
              {notification.message && (
                <p className={cn(
                  'mt-1 text-sm',
                  getTextColor(notification.type)
                )}>
                  {notification.message}
                </p>
              )}
            </div>
            <div className="ml-4 flex-shrink-0">
              <button
                onClick={() => removeNotification(notification.id)}
                className={cn(
                  'inline-flex rounded-md p-1.5 hover:bg-opacity-20 transition-colors',
                  notification.type === 'success' && 'hover:bg-green-600',
                  notification.type === 'error' && 'hover:bg-red-600',
                  notification.type === 'warning' && 'hover:bg-yellow-600',
                  (notification.type === 'info' || !notification.type) && 'hover:bg-blue-600'
                )}
              >
                <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}