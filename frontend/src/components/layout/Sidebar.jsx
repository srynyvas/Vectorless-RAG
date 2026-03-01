import React from 'react';
import { Plus, Settings, PanelLeftClose, PanelLeft } from 'lucide-react';
import useAppStore from '../../stores/useAppStore';
import WorkspaceList from '../workspace/WorkspaceList';

export default function Sidebar({ onCreateWorkspace }) {
  const { sidebarOpen, toggleSidebar, toggleSettings } = useAppStore();

  if (!sidebarOpen) {
    return (
      <div className="flex flex-col items-center py-3 px-1 border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950">
        <button onClick={toggleSidebar} className="btn-ghost p-2" title="Open sidebar">
          <PanelLeft size={18} />
        </button>
      </div>
    );
  }

  return (
    <div className="w-72 flex flex-col border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">PageIndex RAG</span>
        </div>
        <button onClick={toggleSidebar} className="btn-ghost p-1.5" title="Close sidebar">
          <PanelLeftClose size={16} />
        </button>
      </div>

      {/* Workspace Actions */}
      <div className="px-3 py-2">
        <button
          onClick={onCreateWorkspace}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          <Plus size={16} />
          New Workspace
        </button>
      </div>

      {/* Workspace List */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        <WorkspaceList />
      </div>

      {/* Bottom Settings */}
      <div className="border-t border-gray-200 dark:border-gray-800 px-3 py-2">
        <button
          onClick={toggleSettings}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          <Settings size={16} />
          Settings
        </button>
      </div>
    </div>
  );
}
