import React, { useState, useEffect } from 'react';
import { Search, TreePine } from 'lucide-react';
import TreeNodeRow from './TreeNodeRow';
import useChatStore from '../../stores/useChatStore';
import useAppStore from '../../stores/useAppStore';
import { getDocumentTree } from '../../api/documents';
import LoadingSpinner from '../common/LoadingSpinner';

export default function TreeViewer({ metadata }) {
  const [tree, setTree] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const { selectedNodeId, setSelectedNode, treesCache, cacheTree } = useChatStore();
  const { documents } = useAppStore();

  // Get highlighted node IDs from RAG metadata
  const highlightedNodeIds = new Set(
    (metadata?.documents_queried || []).flatMap((d) => d.node_ids || [])
  );

  // Load tree for first document
  useEffect(() => {
    if (documents.length === 0) return;
    const docId = documents[0].id;

    if (treesCache[docId]) {
      setTree(treesCache[docId]);
      return;
    }

    setLoading(true);
    getDocumentTree(docId)
      .then((data) => {
        setTree(data);
        cacheTree(docId, data);
      })
      .catch((err) => console.error('Failed to load tree:', err))
      .finally(() => setLoading(false));
  }, [documents, treesCache, cacheTree]);

  // Auto-expand highlighted nodes
  useEffect(() => {
    if (highlightedNodeIds.size > 0) {
      const toExpand = new Set(expandedNodes);
      toExpand.add('root');
      highlightedNodeIds.forEach((nid) => {
        const parts = nid.split('.');
        let path = '';
        for (const p of parts) {
          path = path ? `${path}.${p}` : p;
          toExpand.add(path);
        }
      });
      setExpandedNodes(toExpand);
    }
  }, [metadata]);

  const toggleExpand = (nodeId) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner />
      </div>
    );
  }

  if (!tree) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <TreePine size={28} className="text-gray-300 dark:text-gray-600 mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Upload a document to see its tree structure
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-800">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Filter tree nodes..."
            className="input-field pl-8 py-1.5 text-xs"
          />
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto p-2">
        <TreeNodeRow
          node={tree}
          depth={0}
          highlightedNodeIds={highlightedNodeIds}
          selectedNodeId={selectedNodeId}
          expandedNodes={expandedNodes}
          onToggle={toggleExpand}
          onClick={setSelectedNode}
          searchFilter={searchFilter.toLowerCase()}
        />
      </div>
    </div>
  );
}
