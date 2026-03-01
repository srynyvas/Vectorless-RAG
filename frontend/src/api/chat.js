/**
 * Send a rich chat query with RAG metadata.
 * Uses fetch + ReadableStream for SSE POST streaming.
 *
 * @param {Object} params
 * @param {number} params.workspaceId
 * @param {string} params.query
 * @param {Array} params.history - conversation history [{role, content}]
 * @param {boolean} params.stream
 * @param {number} params.temperature
 * @param {number} params.maxTokens
 * @param {Function} params.onChunk - called with each text chunk
 * @param {Function} params.onMetadata - called with RAG metadata object
 * @param {Function} params.onDone - called when stream completes
 * @param {Function} params.onError - called on error
 * @param {AbortSignal} params.signal - for cancellation
 * @returns {Promise<void>}
 */
export async function sendRichQuery({
  workspaceId,
  query,
  history = [],
  stream = true,
  temperature = 0.2,
  maxTokens = 4096,
  onChunk,
  onMetadata,
  onDone,
  onError,
  signal,
}) {
  const apiKey = localStorage.getItem('pageindex_api_key') || 'pageindex-secret-key';

  try {
    const response = await fetch('/api/chat/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        workspace_id: workspaceId,
        query,
        conversation_history: history,
        stream,
        temperature,
        max_tokens: maxTokens,
      }),
      signal,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    if (!stream) {
      const data = await response.json();
      onChunk?.(data.answer);
      onMetadata?.(data.rag_metadata);
      onDone?.(data.answer);
      return;
    }

    // Parse SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();

        if (payload === '[DONE]') {
          continue;
        }

        try {
          const parsed = JSON.parse(payload);

          // Check if this is RAG metadata (sent after [DONE])
          if (parsed.type === 'rag_metadata') {
            onMetadata?.(parsed.data);
            continue;
          }

          // Normal chunk
          const delta = parsed.choices?.[0]?.delta;
          if (delta?.content) {
            fullContent += delta.content;
            onChunk?.(delta.content);
          }
        } catch {
          // Skip unparseable lines
        }
      }
    }

    onDone?.(fullContent);
  } catch (err) {
    if (err.name !== 'AbortError') {
      onError?.(err);
    }
  }
}

/**
 * Fallback: send chat via OpenAI-compatible endpoint.
 * Used before the rich chat endpoint is available.
 */
export async function sendChatCompletions({
  model,
  messages,
  stream = true,
  onChunk,
  onDone,
  onError,
  signal,
}) {
  const apiKey = localStorage.getItem('pageindex_api_key') || 'pageindex-secret-key';

  try {
    const response = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ model, messages, stream }),
      signal,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    if (!stream) {
      const data = await response.json();
      const content = data.choices?.[0]?.message?.content || '';
      onChunk?.(content);
      onDone?.(content);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        if (payload === '[DONE]') continue;

        try {
          const parsed = JSON.parse(payload);
          const delta = parsed.choices?.[0]?.delta;
          if (delta?.content) {
            fullContent += delta.content;
            onChunk?.(delta.content);
          }
        } catch {
          // skip
        }
      }
    }

    onDone?.(fullContent);
  } catch (err) {
    if (err.name !== 'AbortError') {
      onError?.(err);
    }
  }
}
