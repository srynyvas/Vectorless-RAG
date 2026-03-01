import React from 'react';
import { TreePine } from 'lucide-react';
import useChatStore from '../../stores/useChatStore';

export default function SourceCitations({ metadata }) {
  const { setSelectedNode } = useChatStore();

  if (!metadata) return null;

  const docs = metadata.documents_queried || [];
  const allNodeIds = docs.flatMap((d) => d.node_ids || []);

  if (allNodeIds.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-1.5 flex-wrap">
        <TreePine size={12} className="text-gray-400" />
        <span className="text-xs text-gray-400">Sources:</span>
        {allNodeIds.map((nid) => (
          <button
            key={nid}
            onClick={() => setSelectedNode(nid)}
            className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400 hover:bg-brand-200 dark:hover:bg-brand-900/50 transition-colors cursor-pointer"
          >
            {nid}
          </button>
        ))}
      </div>
    </div>
  );
}
