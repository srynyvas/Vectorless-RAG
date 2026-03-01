# API Reference

The Vectorless RAG backend exposes two sets of endpoints:

1. **OpenAI-Compatible API** (`/v1/`) -- for integration with any OpenAI-compatible client
2. **Management API** (`/api/`) -- for workspace/document management and rich chat

All endpoints (except `/health` and `/`) require authentication:

```
Authorization: Bearer <RAG_API_KEY>
```

Default key: `pageindex-secret-key`

---

## OpenAI-Compatible Endpoints

### List Models

Returns all workspaces as selectable "models."

```
GET /v1/models
```

**Response:**

```json
{
  "object": "list",
  "data": [
    {
      "id": "pageindex-ws-1",
      "object": "model",
      "created": 1709251200,
      "owned_by": "pageindex",
      "name": "Research Papers"
    },
    {
      "id": "pageindex-ws-2",
      "object": "model",
      "created": 1709337600,
      "owned_by": "pageindex",
      "name": "Technical Docs"
    }
  ]
}
```

### Chat Completions

OpenAI-compatible chat endpoint. Use the workspace model ID from `/v1/models`.

```
POST /v1/chat/completions
```

**Request Body:**

```json
{
  "model": "pageindex-ws-1",
  "messages": [
    {"role": "user", "content": "What is the main finding?"}
  ],
  "stream": true,
  "temperature": 0.2
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | Workspace model ID (e.g., `pageindex-ws-1`) |
| `messages` | array | Yes | Array of message objects with `role` and `content` |
| `stream` | boolean | No | Enable SSE streaming (default: `false`) |
| `temperature` | float | No | Override default temperature |

**Response (non-streaming):**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1709251200,
  "model": "pageindex-ws-1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Based on Section 2.1, the main finding is..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

**Response (streaming):**

Server-Sent Events with chunks:

```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Based"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" on"},"finish_reason":null}]}

data: [DONE]
```

---

## Workspace Endpoints

### Create Workspace

```
POST /api/workspaces
```

**Request Body:**

```json
{
  "name": "Research Papers",
  "description": "Collection of ML research papers",
  "owner_username": "default"
}
```

**Response:** `201 Created`

```json
{
  "id": 1,
  "name": "Research Papers",
  "description": "Collection of ML research papers",
  "owner_username": "default",
  "created_at": "2024-03-01T10:00:00Z",
  "updated_at": "2024-03-01T10:00:00Z"
}
```

### List Workspaces

```
GET /api/workspaces
GET /api/workspaces?owner_username=default
```

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "name": "Research Papers",
    "description": "Collection of ML research papers",
    "owner_username": "default",
    "created_at": "2024-03-01T10:00:00Z",
    "updated_at": "2024-03-01T10:00:00Z"
  }
]
```

### Update Workspace

```
PATCH /api/workspaces/{workspace_id}
```

**Request Body** (all fields optional):

```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

**Response:** `200 OK` -- Updated workspace object

### Delete Workspace

Deletes the workspace, all its documents, and all cached tree indices.

```
DELETE /api/workspaces/{workspace_id}
```

**Response:** `200 OK`

```json
{"status": "deleted", "workspace_id": 1}
```

---

## Document Endpoints

### Upload Document

Parse, index, and store a document in a workspace.

```
POST /api/documents/upload
Content-Type: multipart/form-data
```

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Document file (PDF, MD, DOCX, PPTX, TXT) |
| `workspace_id` | integer | Yes | Target workspace ID |
| `username` | string | Yes | Uploading user |
| `quick_index` | boolean | No | Skip LLM summaries (default: `false`) |

**Response:** `201 Created`

```json
{
  "id": 1,
  "workspace_id": 1,
  "username": "default",
  "file_name": "research_paper.pdf",
  "file_hash": "a1b2c3d4e5f6...",
  "file_size": 1048576,
  "doc_title": "Research Paper Title",
  "root_summary": "This paper discusses...",
  "node_count": 24,
  "image_count": 5,
  "page_count": 15,
  "created_at": "2024-03-01T10:00:00Z"
}
```

!!! info "Deduplication"
    If a file with the same MD5 hash already exists in the workspace, the upload returns the existing document instead of re-indexing.

### List Documents

```
GET /api/documents?workspace_id=1
```

**Response:** `200 OK` -- Array of document objects

### Get Document

```
GET /api/documents/{doc_id}
```

**Response:** `200 OK` -- Single document object

### Update Document Metadata

```
PATCH /api/documents/{doc_id}
```

**Request Body** (all fields optional):

```json
{
  "file_name": "renamed_paper.pdf",
  "doc_title": "Updated Title"
}
```

**Response:** `200 OK` -- Updated document object

### Replace Document (Version)

Upload a new version of a document. Re-indexes the file while keeping the same document ID.

```
POST /api/documents/{doc_id}/replace
Content-Type: multipart/form-data
```

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | New version of the document |
| `username` | string | Yes | Uploading user |
| `quick_index` | boolean | No | Skip LLM summaries (default: `false`) |

**Response:** `200 OK` -- Updated document object with new metadata

### Delete Document

```
DELETE /api/documents/{doc_id}
```

**Response:** `200 OK`

```json
{"status": "deleted", "doc_id": 1}
```

---

## Tree Endpoints

### Get Document Tree

Returns the lightweight tree structure (titles, summaries, page ranges -- no full text).

```
GET /api/documents/{doc_id}/tree
```

**Response:** `200 OK`

```json
{
  "node_id": "root",
  "title": "Document Title",
  "summary": "Overview of the document...",
  "children": [
    {
      "node_id": "1",
      "title": "Introduction",
      "summary": "Background and motivation...",
      "pages": "1-3",
      "children": [
        {
          "node_id": "1.1",
          "title": "Problem Statement",
          "summary": "Describes the core challenge...",
          "pages": "2-3"
        }
      ]
    }
  ]
}
```

### Get Tree Node Detail

Returns full details for a specific node, including text and images.

```
GET /api/documents/{doc_id}/tree/{node_id}
```

**Response:** `200 OK`

```json
{
  "node_id": "1.1",
  "title": "Problem Statement",
  "summary": "Describes the core challenge...",
  "level": 2,
  "start_page": 2,
  "end_page": 3,
  "text": "The full text content of this section...",
  "images": [
    {
      "data": "base64-encoded-image-data...",
      "media_type": "image/png",
      "caption": "Page 2 visual content"
    }
  ],
  "children": []
}
```

---

## Rich Chat Endpoint

The React frontend uses this endpoint instead of the OpenAI-compatible one, because it returns full RAG metadata.

```
POST /api/chat/query
```

**Request Body:**

```json
{
  "workspace_id": 1,
  "query": "What encryption algorithm is used?",
  "username": "default"
}
```

**Response:** `200 OK`

```json
{
  "answer": "According to Section 3.2 (Security Architecture), the system uses AES-256 encryption...",
  "node_ids": ["3.2", "3.2.1"],
  "reasoning": "The question asks about encryption, which is directly addressed in the Security Architecture section and its sub-section on cryptographic protocols.",
  "context": "### Security Architecture (Pages 45-52)\n\nThe system implements AES-256...",
  "image_count": 1,
  "images": [...],
  "routed_docs": [
    {"doc_id": 2, "doc_title": "Architecture Guide"}
  ],
  "routing_reasoning": "The question about encryption is relevant to the Architecture Guide."
}
```

---

## Utility Endpoints

### Health Check

```
GET /health
```

No authentication required.

**Response:** `200 OK`

```json
{"status": "healthy"}
```

### Service Info

```
GET /
```

No authentication required.

**Response:** `200 OK`

```json
{
  "name": "Vectorless RAG Backend",
  "version": "1.1.0"
}
```

---

## Error Responses

All endpoints return standard HTTP error codes:

| Code | Meaning |
|------|---------|
| `400` | Bad request (missing required fields, invalid file type) |
| `401` | Unauthorized (missing or invalid API key) |
| `404` | Resource not found (workspace, document, or node) |
| `409` | Conflict (duplicate file hash in workspace) |
| `500` | Internal server error |

**Error Response Format:**

```json
{
  "detail": "Human-readable error message"
}
```
