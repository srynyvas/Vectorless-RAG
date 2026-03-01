import React, { useState } from 'react';
import { TreePine, Brain, FileText, Image, PanelRightClose, PanelRight } from 'lucide-react';
import useChatStore from '../../stores/useChatStore';
import useAppStore from '../../stores/useAppStore';
import TreeViewer from './TreeViewer';
import ReasoningCard from './ReasoningCard';
import ContextPreview from './ContextPreview';
import ImageGallery from './ImageGallery';

const tabs = [
  { id: 'tree', label: 'Tree', icon: TreePine },
  { id: 'reasoning', label: 'Reasoning', icon: Brain },
  { id: 'context', label: 'Context', icon: FileText },
  { id: 'images', label: 'Images', icon: Image },
];

export default function RAGPanel() {
  const [activeTab, setActiveTab] = useState('tree');
  const [collapsed, setCollapsed] = useState(false);
  const { currentRAGMetadata } = useChatStore();
  const { settings } = useAppStore();

  if (!settings.showRAGPanel) return null;

  if (collapsed) {
    return (
      <div className="flex flex-col items-center py-3 px-1 border-l border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950">
        <button onClick={() => setCollapsed(false)} className="btn-ghost p-2" title="Expand RAG panel">
          <PanelRight size={18} />
        </button>
      </div>
    );
  }

  return (
    <div className="w-96 flex flex-col border-l border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 dark:border-gray-800">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">RAG Explorer</h3>
        <button onClick={() => setCollapsed(true)} className="btn-ghost p-1.5" title="Collapse">
          <PanelRightClose size={16} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 px-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === id
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {!currentRAGMetadata ? (
          <div className="flex flex-col items-center justify-center h-full py-12 px-4 text-center">
            <TreePine size={32} className="text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Ask a question to see the RAG pipeline in action
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              Tree navigation, LLM reasoning, and context assembly will appear here
            </p>
          </div>
        ) : (
          <>
            {activeTab === 'tree' && <TreeViewer metadata={currentRAGMetadata} />}
            {activeTab === 'reasoning' && <ReasoningCard metadata={currentRAGMetadata} />}
            {activeTab === 'context' && <ContextPreview metadata={currentRAGMetadata} />}
            {activeTab === 'images' && <ImageGallery metadata={currentRAGMetadata} />}
          </>
        )}
      </div>
    </div>
  );
}
