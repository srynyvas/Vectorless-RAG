import React, { useState, useEffect } from 'react';
import { FileText, X } from 'lucide-react';
import { getTreeNodeDetail } from '../../api/documents';
import useAppStore from '../../stores/useAppStore';
import useChatStore from '../../stores/useChatStore';
import LoadingSpinner from '../common/LoadingSpinner';

export default function NodeDetail() {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const { selectedNodeId, setSelectedNode } = useChatStore();
  const { documents } = useAppStore();

  useEffect(() => {
    if (!selectedNodeId || documents.length === 0) {
      setDetail(null);
      return;
    }

    const docId = documents[0].id;
    setLoading(true);
    getTreeNodeDetail(docId, selectedNodeId)
      .then(setDetail)
      .catch((err) => console.error('Failed to load node detail:', err))
      .finally(() => setLoading(false));
  }, [selectedNodeId, documents]);

  if (!selectedNodeId) return null;

  return (
    <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-brand-600" />
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
            Node: {selectedNodeId}
          </span>
        </div>
        <button onClick={() => setSelectedNode(null)} className="btn-ghost p-1">
          <X size={14} />
        </button>
      </div>
      <div className="p-4 max-h-48 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center py-4">
            <LoadingSpinner size={16} />
          </div>
        ) : detail ? (
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
              {detail.title}
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">
              {detail.text || 'No text content for this node.'}
            </p>
          </div>
        ) : (
          <p className="text-xs text-gray-400">Could not load node details.</p>
        )}
      </div>
    </div>
  );
}
