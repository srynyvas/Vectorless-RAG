import React, { useState } from 'react';
import { FolderOpen, Pencil, Trash2 } from 'lucide-react';
import useAppStore from '../../stores/useAppStore';
import ConfirmDialog from '../common/ConfirmDialog';
import EditWorkspaceModal from './EditWorkspaceModal';

export default function WorkspaceCard({ workspace, isActive, onClick }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const { deleteWorkspace } = useAppStore();

  return (
    <>
      <div
        onClick={onClick}
        className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
          isActive
            ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
      >
        <FolderOpen size={16} className={isActive ? 'text-brand-600' : 'text-gray-400'} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{workspace.name}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            {workspace.doc_count || 0} doc{(workspace.doc_count || 0) !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowEdit(true);
            }}
            className="p-1 text-gray-400 hover:text-brand-600 rounded transition-colors"
            title="Edit workspace"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowConfirm(true);
            }}
            className="p-1 text-gray-400 hover:text-red-500 rounded transition-colors"
            title="Delete workspace"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      <EditWorkspaceModal
        isOpen={showEdit}
        onClose={() => setShowEdit(false)}
        workspace={workspace}
      />

      <ConfirmDialog
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={() => deleteWorkspace(workspace.id)}
        title="Delete Workspace"
        message={`Delete "${workspace.name}" and all its documents? This cannot be undone.`}
      />
    </>
  );
}
