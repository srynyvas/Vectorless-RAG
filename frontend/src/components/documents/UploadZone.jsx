import React, { useRef, useState, useCallback } from 'react';
import { Upload, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import useAppStore from '../../stores/useAppStore';
import { ACCEPT_STRING } from '../../utils/constants';

export default function UploadZone() {
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const { uploadDocument, uploadStatus, uploadProgress, uploadError } = useAppStore();

  const handleFiles = useCallback(
    (files) => {
      if (files.length === 0) return;
      // Upload first file (could be extended for multi-file)
      uploadDocument(files[0]);
    },
    [uploadDocument]
  );

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const isUploading = uploadStatus === 'uploading' || uploadStatus === 'indexing';

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => !isUploading && fileInputRef.current?.click()}
      className={`relative flex items-center justify-center gap-3 px-4 py-3 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
        isDragging
          ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
          : uploadStatus === 'complete'
          ? 'border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20'
          : uploadStatus === 'error'
          ? 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/20'
          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800/50'
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPT_STRING}
        onChange={(e) => handleFiles(e.target.files)}
        className="hidden"
      />

      {isUploading ? (
        <>
          <Loader2 size={18} className="animate-spin text-brand-600" />
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {uploadStatus === 'indexing' ? 'Indexing document...' : 'Uploading...'}
            </p>
            <div className="mt-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-600 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        </>
      ) : uploadStatus === 'complete' ? (
        <>
          <CheckCircle size={18} className="text-green-600" />
          <p className="text-sm font-medium text-green-700 dark:text-green-400">
            Document uploaded and indexed
          </p>
        </>
      ) : uploadStatus === 'error' ? (
        <>
          <AlertCircle size={18} className="text-red-600" />
          <p className="text-sm font-medium text-red-700 dark:text-red-400">
            {uploadError || 'Upload failed'}
          </p>
        </>
      ) : (
        <>
          <Upload size={18} className="text-gray-400" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Drop a file here or <span className="text-brand-600 font-medium">browse</span>
            <span className="text-xs ml-2 text-gray-400">PDF, DOCX, PPTX, MD, TXT</span>
          </p>
        </>
      )}
    </div>
  );
}
