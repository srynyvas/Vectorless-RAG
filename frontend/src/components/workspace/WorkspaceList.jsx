import React from 'react';
import useAppStore from '../../stores/useAppStore';
import WorkspaceCard from './WorkspaceCard';
import LoadingSpinner from '../common/LoadingSpinner';

export default function WorkspaceList() {
  const { workspaces, workspacesLoading, activeWorkspaceId, setActiveWorkspace } = useAppStore();

  if (workspacesLoading && workspaces.length === 0) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner />
      </div>
    );
  }

  if (workspaces.length === 0) {
    return (
      <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-6">
        No workspaces yet
      </p>
    );
  }

  return (
    <div className="space-y-1">
      {workspaces.map((ws) => (
        <WorkspaceCard
          key={ws.id}
          workspace={ws}
          isActive={ws.id === activeWorkspaceId}
          onClick={() => setActiveWorkspace(ws.id)}
        />
      ))}
    </div>
  );
}
