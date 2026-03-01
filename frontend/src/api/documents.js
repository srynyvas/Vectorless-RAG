import client from './client';

export async function listDocuments(workspaceId) {
  const { data } = await client.get('/api/documents', {
    params: { workspace_id: workspaceId },
  });
  return data;
}

export async function getDocument(id) {
  const { data } = await client.get(`/api/documents/${id}`);
  return data;
}

export async function uploadDocument(workspaceId, file, username = 'default', quickIndex = false, onProgress) {
  const formData = new FormData();
  formData.append('workspace_id', workspaceId);
  formData.append('username', username);
  formData.append('quick_index', quickIndex);
  formData.append('file', file);

  const { data } = await client.post('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
      ? (evt) => onProgress(Math.round((evt.loaded * 100) / (evt.total || 1)))
      : undefined,
  });
  return data;
}

export async function updateDocument(id, patch) {
  const { data } = await client.patch(`/api/documents/${id}`, patch);
  return data;
}

export async function replaceDocument(docId, file, username = 'default', quickIndex = false, onProgress) {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('quick_index', quickIndex);
  formData.append('file', file);

  const { data } = await client.post(`/api/documents/${docId}/replace`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
      ? (evt) => onProgress(Math.round((evt.loaded * 100) / (evt.total || 1)))
      : undefined,
  });
  return data;
}

export async function deleteDocument(id) {
  const { data } = await client.delete(`/api/documents/${id}`);
  return data;
}

export async function getDocumentTree(id) {
  const { data } = await client.get(`/api/documents/${id}/tree`);
  return data;
}

export async function getTreeNodeDetail(docId, nodeId) {
  const { data } = await client.get(`/api/documents/${docId}/tree/${encodeURIComponent(nodeId)}`);
  return data;
}
