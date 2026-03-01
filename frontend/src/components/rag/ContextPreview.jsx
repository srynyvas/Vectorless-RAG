import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import Badge from '../common/Badge';

export default function ContextPreview({ metadata }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!metadata) return null;

  const docs = metadata.documents_queried || [];
  const allContext = docs.map((d) => d.context_preview || '').filter(Boolean).join('\n\n---\n\n');

  if (!allContext) {
    return (
      <div className="p-4 text-sm text-gray-500 dark:text-gray-400 text-center">
        No context available for this query.
      </div>
    );
  }

  const preview = expanded ? allContext : allContext.slice(0, 500);
  const isLong = allContext.length > 500;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(allContext);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-brand-600" />
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
            Assembled Context
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="default">{allContext.length.toLocaleString()} chars</Badge>
          <button
            onClick={handleCopy}
            className="btn-ghost p-1"
            title="Copy context"
          >
            {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
          </button>
        </div>
      </div>

      <div className="card p-3">
        <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono leading-relaxed overflow-y-auto max-h-[60vh]">
          {preview}
          {!expanded && isLong && '...'}
        </pre>
        {isLong && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 mt-2 text-xs text-brand-600 hover:text-brand-700 font-medium"
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {expanded ? 'Show less' : `Show all (${allContext.length.toLocaleString()} chars)`}
          </button>
        )}
      </div>
    </div>
  );
}
