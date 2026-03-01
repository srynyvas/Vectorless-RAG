import React from 'react';
import { FolderOpen, FileText, MessageSquarePlus } from 'lucide-react';
import useAppStore from '../../stores/useAppStore';
import useChatStore from '../../stores/useChatStore';

export default function Header() {
  const { workspaces, activeWorkspaceId, documents } = useAppStore();
  const { clearChat } = useChatStore();

  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId);

  if (!activeWorkspace) return null;

  return (
    <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <div className="flex items-center gap-3">
        <FolderOpen size={18} className="text-brand-600" />
        <div>
          <h1 className="font-semibold text-gray-900 dark:text-gray-100">{activeWorkspace.name}</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {documents.length} document{documents.length !== 1 ? 's' : ''}
            {activeWorkspace.description && ` \u00B7 ${activeWorkspace.description}`}
          </p>
        </div>
      </div>
      <button
        onClick={clearChat}
        className="btn-ghost flex items-center gap-1.5"
        title="New Chat"
      >
        <MessageSquarePlus size={16} />
        <span className="text-sm">New Chat</span>
      </button>
    </div>
  );
}
