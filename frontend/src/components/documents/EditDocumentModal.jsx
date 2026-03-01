import React, { useState, useEffect, useRef } from 'react';
import { Upload, RefreshCw, Loader2 } from 'lucide-react';
import Modal from '../common/Modal';
import useAppStore from '../../stores/useAppStore';
import { formatFileSize, formatDate } from '../../utils/formatters';
import { ACCEPT_STRING } from '../../utils/constants';

export default function EditDocumentModal({ isOpen, onClose, document }) {
  const [docTitle, setDocTitle] = useState('');
  const [fileName, setFileName] = useState('');
  const [saving, setSaving] = useState(false);
  const [replacing, setReplacing] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);
  const { updateDocument, replaceDocument, uploadStatus } = useAppStore();

  useEffect(() => {
    if (isOpen && document) {
      setDocTitle(document.doc_title || '');
      setFileName(document.file_name || '');
      setError('');
      setReplacing(false);
    }
  }, [isOpen, document]);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!fileName.trim()) return;

    setSaving(true);
    setError('');
    try {
      await updateDocument(document.id, {
        file_name: fileName.trim(),
        doc_title: docTitle.trim(),
      });
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to update document');
    } finally {
      setSaving(false);
    }
  };

  const handleReplace = async (file) => {
    if (!file) return;
    setReplacing(true);
    setError('');
    try {
      await replaceDocument(document.id, file);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to replace document');
    } finally {
      setReplacing(false);
    }
  };

  const isProcessing = replacing || uploadStatus === 'uploading' || uploadStatus === 'indexing';

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Document" maxWidth="max-w-lg">
      <form onSubmit={handleSave}>
        <div className="space-y-4">
          {/* Document title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Document Title
            </label>
            <input
              type="text"
              value={docTitle}
              onChange={(e) => setDocTitle(e.target.value)}
              placeholder="Title extracted from document"
              className="input-field"
              autoFocus
            />
          </div>

          {/* File name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              File Name
            </label>
            <input
              type="text"
              value={fileName}
              onChange={(e) => setFileName(e.target.value)}
              placeholder="Display file name"
              className="input-field"
            />
          </div>

          {/* Current metadata (read-only) */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
              Current Version
            </p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-400">Size:</span>{' '}
                <span className="text-gray-700 dark:text-gray-300">{formatFileSize(document?.file_size)}</span>
              </div>
              <div>
                <span className="text-gray-400">Pages:</span>{' '}
                <span className="text-gray-700 dark:text-gray-300">{document?.page_count || 0}</span>
              </div>
              <div>
                <span className="text-gray-400">Nodes:</span>{' '}
                <span className="text-gray-700 dark:text-gray-300">{document?.node_count || 0}</span>
              </div>
              <div>
                <span className="text-gray-400">Images:</span>{' '}
                <span className="text-gray-700 dark:text-gray-300">{document?.image_count || 0}</span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-400">Uploaded:</span>{' '}
                <span className="text-gray-700 dark:text-gray-300">{formatDate(document?.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Replace file section */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Replace with New Version
            </p>
            <p className="text-xs text-gray-400 mb-3">
              Upload a new file to replace the current document. The document will be re-indexed.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPT_STRING}
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleReplace(file);
                e.target.value = '';
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isProcessing}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:border-brand-400 hover:text-brand-600 dark:hover:border-brand-500 dark:hover:text-brand-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  {uploadStatus === 'indexing' ? 'Indexing new version...' : 'Uploading...'}
                </>
              ) : (
                <>
                  <RefreshCw size={16} />
                  Choose replacement file
                </>
              )}
            </button>
          </div>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" disabled={!fileName.trim() || saving || isProcessing} className="btn-primary">
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
