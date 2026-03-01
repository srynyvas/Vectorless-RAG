import React from 'react';
import { ChevronRight, ChevronDown, FileText, Image } from 'lucide-react';

export default function TreeNodeRow({
  node,
  depth,
  highlightedNodeIds,
  selectedNodeId,
  expandedNodes,
  onToggle,
  onClick,
  searchFilter,
}) {
  if (!node) return null;

  const isHighlighted = highlightedNodeIds.has(node.node_id);
  const isSelected = selectedNodeId === node.node_id;
  const isExpanded = expandedNodes.has(node.node_id);
  const hasChildren = node.children && node.children.length > 0;
  const hasImages = node.images && node.images.length > 0;

  // Filter by search
  const matchesFilter = !searchFilter || node.title?.toLowerCase().includes(searchFilter);
  const childMatches = hasChildren && node.children.some(
    (c) => c.title?.toLowerCase().includes(searchFilter) || !searchFilter
  );
  if (!matchesFilter && !childMatches) return null;

  return (
    <div>
      <div
        onClick={() => onClick(node.node_id)}
        className={`flex items-start gap-1 px-2 py-1 rounded-md cursor-pointer text-xs transition-colors ${
          isSelected
            ? 'bg-brand-100 dark:bg-brand-900/30 ring-1 ring-brand-400'
            : isHighlighted
            ? 'bg-amber-50 dark:bg-amber-900/20 ring-1 ring-amber-300 dark:ring-amber-700'
            : 'hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        {/* Expand toggle */}
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle(node.node_id);
            }}
            className="p-0.5 mt-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex-shrink-0"
          >
            {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        ) : (
          <span className="w-4 flex-shrink-0" />
        )}

        <FileText size={12} className={`mt-0.5 flex-shrink-0 ${isHighlighted ? 'text-amber-600' : 'text-gray-400'}`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1">
            <span
              className={`font-medium truncate ${
                isHighlighted ? 'text-amber-800 dark:text-amber-300' : 'text-gray-700 dark:text-gray-300'
              }`}
            >
              {node.title || node.node_id}
            </span>
            {node.pages && (
              <span className="text-gray-400 text-[10px] flex-shrink-0">p.{node.pages}</span>
            )}
            {hasImages && (
              <Image size={10} className="text-green-500 flex-shrink-0" />
            )}
          </div>
          {node.summary && (
            <p className="text-[10px] text-gray-400 dark:text-gray-500 line-clamp-1 mt-0.5">
              {node.summary}
            </p>
          )}
        </div>
      </div>

      {/* Children */}
      {isExpanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <TreeNodeRow
              key={child.node_id}
              node={child}
              depth={depth + 1}
              highlightedNodeIds={highlightedNodeIds}
              selectedNodeId={selectedNodeId}
              expandedNodes={expandedNodes}
              onToggle={onToggle}
              onClick={onClick}
              searchFilter={searchFilter}
            />
          ))}
        </div>
      )}
    </div>
  );
}
