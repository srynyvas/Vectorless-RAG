import React, { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import StreamingIndicator from './StreamingIndicator';

export default function MessageList({ messages, isStreaming, streamingContent }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isStreaming && streamingContent && (
        <MessageBubble
          message={{ role: 'assistant', content: streamingContent }}
          isStreaming
        />
      )}
      {isStreaming && !streamingContent && <StreamingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
