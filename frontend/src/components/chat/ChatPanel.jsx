import React from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import useChatStore from '../../stores/useChatStore';
import useAppStore from '../../stores/useAppStore';
import EmptyState from '../common/EmptyState';
import { MessageSquare } from 'lucide-react';

export default function ChatPanel() {
  const { messages, isStreaming, streamingContent } = useChatStore();
  const { activeWorkspaceId, documents } = useAppStore();

  const hasDocuments = documents.length > 0;

  return (
    <div className="flex-1 flex flex-col min-w-0 border-r border-gray-200 dark:border-gray-800">
      {messages.length === 0 && !isStreaming ? (
        <div className="flex-1 flex items-center justify-center">
          <EmptyState
            icon={MessageSquare}
            title={hasDocuments ? 'Ask a Question' : 'Upload Documents First'}
            description={
              hasDocuments
                ? 'Ask questions about your uploaded documents. The RAG pipeline will find relevant sections and generate grounded answers.'
                : 'Upload documents to this workspace, then ask questions about them.'
            }
          />
        </div>
      ) : (
        <MessageList messages={messages} isStreaming={isStreaming} streamingContent={streamingContent} />
      )}
      <ChatInput />
    </div>
  );
}
