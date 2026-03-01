import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import useAppStore from '../../stores/useAppStore';
import DocumentCard from './DocumentCard';
import UploadZone from './UploadZone';
import LoadingSpinner from '../common/LoadingSpinner';

export default function DocumentList() {
  const [expanded, setExpanded] = useState(true);
  const { documents, documentsLoading } = useAppStore();

  return (
    <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-6 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        <span>Documents ({documents.length})</span>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {expanded && (
        <div className="px-6 pb-4">
          <UploadZone />
          {documentsLoading ? (
            <div className="flex justify-center py-4">
              <LoadingSpinner />
            </div>
          ) : documents.length > 0 ? (
            <div className="mt-3 space-y-2">
              {documents.map((doc) => (
                <DocumentCard key={doc.id} document={doc} />
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
