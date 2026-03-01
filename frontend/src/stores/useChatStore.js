import { create } from 'zustand';
import { sendChatCompletions, sendRichQuery } from '../api/chat';

const useChatStore = create((set, get) => ({
  // Conversation
  messages: [],
  isStreaming: false,
  streamingContent: '',
  abortController: null,

  // RAG visualization
  currentRAGMetadata: null,
  selectedNodeId: null,

  // Trees cache (docId -> treeData)
  treesCache: {},

  // Actions
  sendMessage: async (query, workspaceId, modelId) => {
    const { messages } = get();

    // Add user message
    const userMsg = { id: Date.now(), role: 'user', content: query };
    set({ messages: [...messages, userMsg], isStreaming: true, streamingContent: '', currentRAGMetadata: null });

    const abortController = new AbortController();
    set({ abortController });

    const history = messages.map(({ role, content }) => ({ role, content }));

    // Try rich endpoint first, fall back to OpenAI-compatible
    const useRichEndpoint = true; // Will be toggled based on backend availability

    if (useRichEndpoint) {
      try {
        await sendRichQuery({
          workspaceId,
          query,
          history,
          stream: true,
          onChunk: (chunk) => {
            set((s) => ({ streamingContent: s.streamingContent + chunk }));
          },
          onMetadata: (metadata) => {
            set({ currentRAGMetadata: metadata });
          },
          onDone: (fullContent) => {
            set((s) => ({
              messages: [
                ...s.messages,
                {
                  id: Date.now(),
                  role: 'assistant',
                  content: fullContent,
                  ragMetadata: s.currentRAGMetadata,
                },
              ],
              isStreaming: false,
              streamingContent: '',
              abortController: null,
            }));
          },
          onError: async (err) => {
            // If rich endpoint fails (404), fall back to OpenAI endpoint
            if (err.message?.includes('404') || err.message?.includes('Not Found')) {
              await get()._fallbackSend(query, modelId, history, abortController.signal);
            } else {
              set((s) => ({
                messages: [
                  ...s.messages,
                  {
                    id: Date.now(),
                    role: 'assistant',
                    content: `Error: ${err.message}`,
                  },
                ],
                isStreaming: false,
                streamingContent: '',
                abortController: null,
              }));
            }
          },
          signal: abortController.signal,
        });
      } catch {
        // Fallback
        await get()._fallbackSend(query, modelId, history, abortController.signal);
      }
    }
  },

  _fallbackSend: async (query, modelId, history, signal) => {
    const allMessages = [
      ...history,
      { role: 'user', content: query },
    ];

    await sendChatCompletions({
      model: modelId || 'pageindex-ws-1',
      messages: allMessages,
      stream: true,
      onChunk: (chunk) => {
        set((s) => ({ streamingContent: s.streamingContent + chunk }));
      },
      onDone: (fullContent) => {
        set((s) => ({
          messages: [
            ...s.messages,
            { id: Date.now(), role: 'assistant', content: fullContent },
          ],
          isStreaming: false,
          streamingContent: '',
          abortController: null,
        }));
      },
      onError: (err) => {
        set((s) => ({
          messages: [
            ...s.messages,
            { id: Date.now(), role: 'assistant', content: `Error: ${err.message}` },
          ],
          isStreaming: false,
          streamingContent: '',
          abortController: null,
        }));
      },
      signal,
    });
  },

  stopStreaming: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
      set((s) => ({
        messages: s.streamingContent
          ? [
              ...s.messages,
              { id: Date.now(), role: 'assistant', content: s.streamingContent },
            ]
          : s.messages,
        isStreaming: false,
        streamingContent: '',
        abortController: null,
      }));
    }
  },

  clearChat: () =>
    set({
      messages: [],
      isStreaming: false,
      streamingContent: '',
      currentRAGMetadata: null,
      selectedNodeId: null,
    }),

  setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId }),

  cacheTree: (docId, tree) =>
    set((s) => ({ treesCache: { ...s.treesCache, [docId]: tree } })),
}));

export default useChatStore;
