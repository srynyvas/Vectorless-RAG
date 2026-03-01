import React, { useState } from 'react';
import { Image, X, ZoomIn } from 'lucide-react';

export default function ImageGallery({ metadata }) {
  const [selectedImage, setSelectedImage] = useState(null);

  if (!metadata) return null;

  const docs = metadata.documents_queried || [];
  const allImages = docs.flatMap((d) =>
    (d.images || []).map((img, idx) => ({
      ...img,
      docName: d.file_name,
      key: `${d.doc_id}-${idx}`,
    }))
  );

  if (allImages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <Image size={28} className="text-gray-300 dark:text-gray-600 mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No images retrieved</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-3">
        <Image size={14} className="text-brand-600" />
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
          Retrieved Images ({allImages.length})
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {allImages.map((img) => (
          <div
            key={img.key}
            onClick={() => setSelectedImage(img)}
            className="group relative aspect-square rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 cursor-pointer hover:border-brand-400 transition-colors"
          >
            <img
              src={`data:${img.media_type};base64,${img.data}`}
              alt={img.caption || 'Document image'}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
              <ZoomIn size={20} className="text-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            {img.caption && (
              <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1">
                <p className="text-xs text-white truncate">{img.caption}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-8" onClick={() => setSelectedImage(null)}>
          <button className="absolute top-4 right-4 p-2 text-white/80 hover:text-white" onClick={() => setSelectedImage(null)}>
            <X size={24} />
          </button>
          <img
            src={`data:${selectedImage.media_type};base64,${selectedImage.data}`}
            alt={selectedImage.caption || 'Document image'}
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
          {selectedImage.caption && (
            <p className="absolute bottom-8 text-white text-sm bg-black/60 px-4 py-2 rounded-lg">
              {selectedImage.caption}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
