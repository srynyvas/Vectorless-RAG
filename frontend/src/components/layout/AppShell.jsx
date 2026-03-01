import React, { useState, useEffect } from 'react';
import useAppStore from '../../stores/useAppStore';
import Sidebar from './Sidebar';
import Header from './Header';
import CreateWorkspaceModal from '../workspace/CreateWorkspaceModal';
import SettingsPanel from '../settings/SettingsPanel';
import DocumentList from '../documents/DocumentList';
import ChatPanel from '../chat/ChatPanel';
import RAGPanel from '../rag/RAGPanel';
import EmptyState from '../common/EmptyState';
import { FolderOpen } from 'lucide-react';

export default function AppShell() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { activeWorkspaceId, fetchWorkspaces, settingsOpen, settings } = useAppStore();

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar onCreateWorkspace={() => setShowCreateModal(true)} />

      <div className="flex-1 flex flex-col overflow-hidden">
        {activeWorkspaceId ? (
          <>
            <Header />
            <div className="flex-1 flex overflow-hidden">
              {/* Main content area */}
              <div className="flex-1 flex flex-col overflow-hidden">
                <DocumentList />
                <div className="flex-1 flex overflow-hidden">
                  <ChatPanel />
                  {settings.showRAGPanel && <RAGPanel />}
                </div>
              </div>
            </div>
          </>
        ) : (
          <EmptyState
            icon={FolderOpen}
            title="Select a Workspace"
            description="Choose a workspace from the sidebar or create a new one to get started."
            action={
              <button onClick={() => setShowCreateModal(true)} className="btn-primary">
                Create Workspace
              </button>
            }
          />
        )}
      </div>

      <CreateWorkspaceModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
      <SettingsPanel />
    </div>
  );
}
