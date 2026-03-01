import client from './client';

export async function listWorkspaces(ownerUsername) {
  const params = ownerUsername ? { owner_username: ownerUsername } : {};
  const { data } = await client.get('/api/workspaces', { params });
  return data;
}

export async function createWorkspace(name, description = '', ownerUsername = 'default') {
  const { data } = await client.post('/api/workspaces', {
    name,
    description,
    owner_username: ownerUsername,
  });
  return data;
}

export async function updateWorkspace(id, patch) {
  const { data } = await client.patch(`/api/workspaces/${id}`, patch);
  return data;
}

export async function deleteWorkspace(id) {
  const { data } = await client.delete(`/api/workspaces/${id}`);
  return data;
}
