import React, { useState } from 'react';
import { FileText, Pencil, Trash2, TreePine, Image, BookOpen } from 'lucide-react';
import { formatFileSize, formatDate } from '../../utils/formatters';
import useAppStore from '../../stores/useAppStore';
import ConfirmDialog from '../common/ConfirmDialog';
import EditDocumentModal from './EditDocumentModal';
import Badge from '../common/Badge';

export default function DocumentCard({ document }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const { deleteDocument } = useAppStore();

  return (
    <>
      <div className="group flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 transition-colors">
        <div className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center flex-shrink-0">
          <FileText size={16} className="text-brand-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {document.doc_title || document.file_name}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <Badge variant="default">
              <BookOpen size={10} />
              {document.page_count} pg
            </Badge>
            <Badge variant="primary">
              <TreePine size={10} />
              {document.node_count} nodes
            </Badge>
            {document.image_count > 0 && (
              <Badge variant="success">
                <Image size={10} />
                {document.image_count}
              </Badge>
            )}
            <span className="text-xs text-gray-400">{formatFileSize(document.file_size)}</span>
            <span className="text-xs text-gray-400">{formatDate(document.created_at)}</span>
          </div>
        </div>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
          <button
            onClick={() => setShowEdit(true)}
            className="p-1.5 text-gray-400 hover:text-brand-600 rounded-lg transition-colors"
            title="Edit document"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => setShowConfirm(true)}
            className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"
            title="Delete document"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <EditDocumentModal
        isOpen={showEdit}
        onClose={() => setShowEdit(false)}
        document={document}
      />

      <ConfirmDialog
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={() => deleteDocument(document.id)}
        title="Delete Document"
        message={`Delete "${document.file_name}"? The document index will be removed.`}
      />
    </>
  );
}
