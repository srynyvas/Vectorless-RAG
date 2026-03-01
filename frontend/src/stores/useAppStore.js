import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import * as workspacesApi from '../api/workspaces';
import * as documentsApi from '../api/documents';

const useAppStore = create(
  persist(
    (set, get) => ({
      // Auth
      apiKey: 'pageindex-secret-key',
      username: 'default',

      // Workspaces
      workspaces: [],
      activeWorkspaceId: null,
      workspacesLoading: false,

      // Documents for active workspace
      documents: [],
      documentsLoading: false,

      // Upload state
      uploadProgress: 0,
      uploadStatus: 'idle', // idle | uploading | indexing | complete | error
      uploadError: null,

      // Settings
      settings: {
        llmProvider: 'anthropic',
        temperature: 0.2,
        maxTokens: 4096,
        showRAGPanel: true,
        quickIndex: false,
      },

      // UI state
      sidebarOpen: true,
      settingsOpen: false,

      // Actions
      setApiKey: (key) => {
        localStorage.setItem('pageindex_api_key', key);
        set({ apiKey: key });
      },

      setUsername: (username) => set({ username }),

      fetchWorkspaces: async () => {
        set({ workspacesLoading: true });
        try {
          const data = await workspacesApi.listWorkspaces();
          set({ workspaces: data, workspacesLoading: false });
        } catch (err) {
          console.error('Failed to fetch workspaces:', err);
          set({ workspacesLoading: false });
        }
      },

      createWorkspace: async (name, description) => {
        const { username } = get();
        try {
          const ws = await workspacesApi.createWorkspace(name, description, username);
          set((s) => ({ workspaces: [ws, ...s.workspaces] }));
          return ws;
        } catch (err) {
          console.error('Failed to create workspace:', err);
          throw err;
        }
      },

      deleteWorkspace: async (id) => {
        try {
          await workspacesApi.deleteWorkspace(id);
          set((s) => ({
            workspaces: s.workspaces.filter((w) => w.id !== id),
            activeWorkspaceId: s.activeWorkspaceId === id ? null : s.activeWorkspaceId,
            documents: s.activeWorkspaceId === id ? [] : s.documents,
          }));
        } catch (err) {
          console.error('Failed to delete workspace:', err);
          throw err;
        }
      },

      setActiveWorkspace: (id) => {
        set({ activeWorkspaceId: id, documents: [] });
        if (id) get().fetchDocuments(id);
      },

      fetchDocuments: async (workspaceId) => {
        set({ documentsLoading: true });
        try {
          const data = await documentsApi.listDocuments(workspaceId);
          set({ documents: data, documentsLoading: false });
        } catch (err) {
          console.error('Failed to fetch documents:', err);
          set({ documentsLoading: false });
        }
      },

      uploadDocument: async (file) => {
        const { activeWorkspaceId, username, settings } = get();
        if (!activeWorkspaceId) return;

        set({ uploadStatus: 'uploading', uploadProgress: 0, uploadError: null });
        try {
          const doc = await documentsApi.uploadDocument(
            activeWorkspaceId,
            file,
            username,
            settings.quickIndex,
            (progress) => {
              set({ uploadProgress: progress });
              // Once upload bytes are sent, server is indexing
              if (progress >= 100) {
                set({ uploadStatus: 'indexing' });
              }
            }
          );
          set((s) => ({
            documents: [doc, ...s.documents],
            uploadStatus: 'complete',
            uploadProgress: 100,
          }));
          // Auto-clear upload status after 3 seconds
          setTimeout(() => set({ uploadStatus: 'idle', uploadProgress: 0 }), 3000);
          return doc;
        } catch (err) {
          console.error('Failed to upload document:', err);
          set({
            uploadStatus: 'error',
            uploadError: err.response?.data?.detail || err.message,
          });
          throw err;
        }
      },

      updateWorkspace: async (id, patch) => {
        try {
          const updated = await workspacesApi.updateWorkspace(id, patch);
          set((s) => ({
            workspaces: s.workspaces.map((w) => (w.id === id ? updated : w)),
          }));
          return updated;
        } catch (err) {
          console.error('Failed to update workspace:', err);
          throw err;
        }
      },

      updateDocument: async (id, patch) => {
        try {
          const updated = await documentsApi.updateDocument(id, patch);
          set((s) => ({
            documents: s.documents.map((d) => (d.id === id ? updated : d)),
          }));
          return updated;
        } catch (err) {
          console.error('Failed to update document:', err);
          throw err;
        }
      },

      replaceDocument: async (docId, file) => {
        const { username, settings } = get();
        set({ uploadStatus: 'uploading', uploadProgress: 0, uploadError: null });
        try {
          const updated = await documentsApi.replaceDocument(
            docId,
            file,
            username,
            settings.quickIndex,
            (progress) => {
              set({ uploadProgress: progress });
              if (progress >= 100) {
                set({ uploadStatus: 'indexing' });
              }
            }
          );
          set((s) => ({
            documents: s.documents.map((d) => (d.id === docId ? updated : d)),
            uploadStatus: 'complete',
            uploadProgress: 100,
          }));
          setTimeout(() => set({ uploadStatus: 'idle', uploadProgress: 0 }), 3000);
          return updated;
        } catch (err) {
          console.error('Failed to replace document:', err);
          set({
            uploadStatus: 'error',
            uploadError: err.response?.data?.detail || err.message,
          });
          throw err;
        }
      },

      deleteDocument: async (id) => {
        try {
          await documentsApi.deleteDocument(id);
          set((s) => ({
            documents: s.documents.filter((d) => d.id !== id),
          }));
        } catch (err) {
          console.error('Failed to delete document:', err);
          throw err;
        }
      },

      updateSettings: (patch) =>
        set((s) => ({ settings: { ...s.settings, ...patch } })),

      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      toggleSettings: () => set((s) => ({ settingsOpen: !s.settingsOpen })),
    }),
    {
      name: 'pageindex-app-store',
      partialize: (state) => ({
        apiKey: state.apiKey,
        username: state.username,
        activeWorkspaceId: state.activeWorkspaceId,
        settings: state.settings,
      }),
      onRehydrateStorage: () => (state) => {
        // Always reset transient upload state after hydration
        if (state) {
          state.uploadStatus = 'idle';
          state.uploadProgress = 0;
          state.uploadError = null;
        }
      },
    }
  )
);

export default useAppStore;
