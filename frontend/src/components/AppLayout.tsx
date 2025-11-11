'use client';

import { useState } from 'react';
import { FileUpload } from './FileUpload';
import { HistoryView } from './HistoryView';
import { Notifications } from './Notifications';
import { RecentUploads } from './RecentUploads';
import { Sidebar } from './Sidebar';
import { StatisticsView } from './StatisticsView';
import { TaskDetailModal } from './TaskDetailModal';
import { TaskList } from './TaskList';

type ViewType = 'upload' | 'tasks' | 'history' | 'statistics';

export function AppLayout() {
  const [activeView, setActiveView] = useState<ViewType>('upload');

  const renderContent = () => {
    switch (activeView) {
      case 'upload':
        return (
          <div className="max-w-4xl mx-auto">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Upload Audio Files
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Upload MP3 files to convert them to MIDI format. Files are processed asynchronously.
              </p>
            </div>
            <div className="space-y-8">
              <FileUpload multiple={true} maxFiles={10} />
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Recent Uploads
                </h2>
                <RecentUploads hours={24} />
              </div>
            </div>
          </div>
        );
      case 'tasks':
        return (
          <div>
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Task Management
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Monitor and manage your audio to MIDI conversion tasks.
              </p>
            </div>
            <TaskList />
          </div>
        );
      case 'history':
        return (
          <div>
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Operation History
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                View the history of all operations and system events.
              </p>
            </div>
            <HistoryView />
          </div>
        );
      case 'statistics':
        return (
          <div>
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Statistics
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                View system statistics and performance metrics.
              </p>
            </div>
            <StatisticsView />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Sidebar activeView={activeView} onViewChange={setActiveView} />
      
      {/* Main content */}
      <div className="lg:pl-64">
        <main className="py-8 px-4 sm:px-6 lg:px-8">
          {renderContent()}
        </main>
      </div>

      {/* Modals and overlays */}
      <TaskDetailModal />
      <Notifications />
    </div>
  );
}