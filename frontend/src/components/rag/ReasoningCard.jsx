import React from 'react';
import { Brain, Route, FileText } from 'lucide-react';
import Badge from '../common/Badge';

export default function ReasoningCard({ metadata }) {
  if (!metadata) return null;

  const docs = metadata.documents_queried || [];

  return (
    <div className="p-4 space-y-4">
      {/* Mode indicator */}
      <div className="flex items-center gap-2">
        <Badge variant={metadata.mode === 'native' ? 'primary' : 'success'}>
          {metadata.mode === 'native' ? 'Tree-based RAG' : 'Context Passthrough'}
        </Badge>
        {metadata.total_nodes_selected > 0 && (
          <Badge variant="default">{metadata.total_nodes_selected} nodes selected</Badge>
        )}
      </div>

      {/* Routing reasoning (multi-doc) */}
      {metadata.routing_reasoning && (
        <div className="card p-3">
          <div className="flex items-center gap-2 mb-2">
            <Route size={14} className="text-brand-600" />
            <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
              Document Routing
            </h4>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
            {metadata.routing_reasoning}
          </p>
        </div>
      )}

      {/* Per-document reasoning */}
      {docs.map((doc, i) => (
        <div key={i} className="card p-3">
          <div className="flex items-center gap-2 mb-2">
            <FileText size={14} className="text-brand-600" />
            <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300">
              {doc.file_name}
            </h4>
          </div>

          {/* Selected nodes */}
          {doc.node_ids && doc.node_ids.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {doc.node_ids.map((nid) => (
                <Badge key={nid} variant="primary">
                  {nid}
                </Badge>
              ))}
            </div>
          )}

          {/* Reasoning text */}
          {doc.reasoning && (
            <div className="mt-2">
              <div className="flex items-center gap-1.5 mb-1">
                <Brain size={12} className="text-gray-400" />
                <span className="text-xs text-gray-500 font-medium">Search Reasoning</span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed bg-gray-50 dark:bg-gray-800/50 rounded-lg p-2">
                {doc.reasoning}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
