import {
    BarChart3,
    History,
    List,
    Menu,
    Music,
    Settings,
    X
} from 'lucide-react';
import React from 'react';
import { useUIStore } from '../store/useUIStore';
import { cn } from '../utils/cn';

interface SidebarItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}

function SidebarItem({ icon, label, active, onClick }: SidebarItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
        'hover:bg-gray-100 dark:hover:bg-gray-700',
        active 
          ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' 
          : 'text-gray-700 dark:text-gray-300'
      )}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

interface SidebarProps {
  activeView: 'upload' | 'tasks' | 'history' | 'statistics';
  onViewChange: (view: 'upload' | 'tasks' | 'history' | 'statistics') => void;
}

export function Sidebar({ activeView, onViewChange }: SidebarProps) {
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);

  return (
    <>
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-900 shadow-lg transform transition-transform duration-300 ease-in-out',
          'lg:translate-x-0 lg:static lg:inset-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-2">
              <Music className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <span className="text-xl font-bold text-gray-900 dark:text-gray-100">
                Audio2Midi
              </span>
            </div>
            <button
              onClick={toggleSidebar}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 lg:hidden"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 p-4">
            <SidebarItem
              icon={<Music className="h-5 w-5" />}
              label="Upload"
              active={activeView === 'upload'}
              onClick={() => onViewChange('upload')}
            />
            <SidebarItem
              icon={<List className="h-5 w-5" />}
              label="Tasks"
              active={activeView === 'tasks'}
              onClick={() => onViewChange('tasks')}
            />
            <SidebarItem
              icon={<History className="h-5 w-5" />}
              label="History"
              active={activeView === 'history'}
              onClick={() => onViewChange('history')}
            />
            <SidebarItem
              icon={<BarChart3 className="h-5 w-5" />}
              label="Statistics"
              active={activeView === 'statistics'}
              onClick={() => onViewChange('statistics')}
            />
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <SidebarItem
              icon={<Settings className="h-5 w-5" />}
              label="Settings"
              onClick={() => {
                // TODO: Implement settings
                console.log('Settings clicked');
              }}
            />
          </div>
        </div>
      </div>

      {/* Mobile menu button */}
      <button
        onClick={toggleSidebar}
        className={cn(
          'fixed top-4 left-4 z-30 p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg',
          'lg:hidden',
          sidebarOpen && 'hidden'
        )}
      >
        <Menu className="h-5 w-5 text-gray-700 dark:text-gray-300" />
      </button>
    </>
  );
}