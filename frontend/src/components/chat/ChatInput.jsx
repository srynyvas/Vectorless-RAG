import React, { useState, useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';
import useChatStore from '../../stores/useChatStore';
import useAppStore from '../../stores/useAppStore';

export default function ChatInput() {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);
  const { sendMessage, isStreaming, stopStreaming } = useChatStore();
  const { activeWorkspaceId } = useAppStore();

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  }, [query]);

  const handleSend = () => {
    if (!query.trim() || isStreaming) return;
    const modelId = `pageindex-ws-${activeWorkspaceId}`;
    sendMessage(query.trim(), activeWorkspaceId, modelId);
    setQuery('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-6 py-3">
      <div className="flex items-end gap-3">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents..."
          rows={1}
          className="input-field resize-none min-h-[40px]"
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button
            onClick={stopStreaming}
            className="flex-shrink-0 p-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            title="Stop generating"
          >
            <Square size={18} />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!query.trim()}
            className="flex-shrink-0 p-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white rounded-lg transition-colors"
            title="Send (Ctrl+Enter)"
          >
            <Send size={18} />
          </button>
        )}
      </div>
      <p className="text-xs text-gray-400 mt-1.5 text-center">
        Press Ctrl+Enter to send
      </p>
    </div>
  );
}
