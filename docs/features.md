# Features

## Core Capabilities

### :material-tree: Vectorless Retrieval

The defining feature. Instead of embedding documents into vector spaces, the system builds a hierarchical tree index and uses LLM reasoning to find relevant sections. This means:

- **No embedding model to choose or manage**
- **No vector database to deploy or scale**
- **No chunk size tuning** -- the document's natural structure is used
- **Full explainability** -- you can read the LLM's reasoning for every retrieval decision

### :material-file-multiple: Multi-Document Support

Upload multiple documents to a workspace and ask questions that span across them:

- **Intelligent routing** -- an LLM examines document summaries and selects 1-3 most relevant documents
- **Per-document RAG** -- each selected document goes through the full tree search pipeline
- **Answer merging** -- multiple per-document answers are synthesized into a single coherent response with cross-document citations

### :material-image: Multimodal Processing

Documents aren't just text. The system extracts and processes images:

- **PDF image extraction** -- pages containing images are rendered and extracted
- **Image-aware summaries** -- tree node summaries can incorporate visual content
- **Multimodal answer generation** -- the LLM receives both text context and images, enabling answers like *"As shown in the diagram on Page 12..."*
- Configurable limits: max images per section, max images in context

### :material-message-text: Streaming Responses

Chat responses stream token-by-token via Server-Sent Events (SSE):

- Real-time feedback as the answer is generated
- Works through the Nginx reverse proxy with buffering disabled
- Supported in both the React UI and the OpenAI-compatible API endpoint

---

## Document Management

### Workspace Organization

- **Create workspaces** to group related documents
- **Rename and describe** workspaces with inline editing
- **Delete workspaces** with cascade cleanup (all documents and cached indices)
- **Per-user isolation** -- workspaces are scoped to usernames

### Document Operations

| Operation | Description |
|-----------|-------------|
| **Upload** | Drag-and-drop or file picker, with real-time progress tracking |
| **Edit Metadata** | Rename documents and update titles without re-indexing |
| **Replace (Version)** | Upload a new version of a document -- re-indexes while keeping the same document ID |
| **Delete** | Remove document and its cached tree index |
| **Deduplication** | MD5 hash check prevents uploading the same file twice to a workspace |

### Supported File Types

| Format | Extensions | Parser | Features |
|--------|-----------|--------|----------|
| **PDF** | `.pdf` | pypdfium2 | Heuristic heading detection, image extraction, page-by-page fallback |
| **Markdown** | `.md`, `.markdown` | Built-in | Section splitting on headings |
| **Word** | `.docx` | python-docx | Paragraphs and tables |
| **PowerPoint** | `.pptx` | python-pptx | Slide-by-slide extraction |
| **Plain Text** | `.txt` | Built-in | Line-by-line parsing |

---

## User Interface

### Chat Interface

- Clean, modern chat UI with message history
- Markdown rendering with GitHub-Flavored Markdown support
- Message timestamps and clear visual distinction between user and AI messages
- Conversation clearing and management

### RAG Explorer Panel

The standout UI feature -- a four-tab panel that shows exactly how the system found each answer:

=== "Tree View"

    Displays the complete hierarchical document structure. Click any node to see its full details including text, images, and metadata. Selected nodes (used for the current answer) are highlighted.

=== "Reasoning"

    Shows the LLM's explanation for why specific sections were selected. This is the key to debugging and understanding retrieval decisions.

=== "Context"

    Displays the exact text that was assembled and sent to the answer-generation LLM. What you see is what the LLM saw -- complete transparency.

=== "Images"

    Shows any images extracted from the selected document sections. Useful for verifying that visual content (charts, diagrams) was included in the LLM's context.

### Settings Panel

- **LLM Provider** toggle (Anthropic / OpenAI)
- **Temperature** control for response creativity
- **Max Tokens** configuration
- **Quick Index** toggle (skip LLM summaries during upload)
- **RAG Panel** visibility toggle

---

## API Compatibility

### OpenAI-Compatible Endpoint

The system exposes an OpenAI-compatible `/v1/chat/completions` endpoint, making it a drop-in replacement for any client that speaks the OpenAI protocol:

```bash
curl http://localhost:8100/v1/chat/completions \
  -H "Authorization: Bearer pageindex-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "pageindex-ws-1",
    "messages": [{"role": "user", "content": "What is the main finding?"}],
    "stream": true
  }'
```

This means you can use Vectorless RAG with:

- **Open WebUI** -- as a custom model backend
- **ChatBox** -- or any OpenAI-compatible desktop client
- **Custom applications** -- any app that uses the OpenAI SDK

### Rich Chat Endpoint

For the React frontend, a dedicated `/api/chat/query` endpoint returns full RAG metadata alongside the answer:

- Selected node IDs
- LLM reasoning for section selection
- Assembled context text
- Extracted images
- Document routing information (for multi-doc queries)

---

## Indexing Options

### Full Index (with LLM Summaries)

- Generates concise (up to 50 words) summaries for every tree node
- **Bottom-up**: leaf nodes summarized from text, parent nodes from children's summaries
- **Multimodal summaries**: nodes with images use `generate_multimodal()` to incorporate visual content
- Produces the highest-quality tree for search
- Takes longer (one LLM call per node)

### Quick Index

- Skips LLM summary generation
- Uses text snippets as node summaries instead
- Nearly instant indexing
- Slightly lower search accuracy (summaries are less informative)
- Great for rapid prototyping or when LLM costs matter

---

## Caching & Performance

### Tree Index Caching

- Built trees are serialized to JSON and stored on disk
- Cache key: `{username}/{file_hash}.json`
- Subsequent queries load the cached tree instantly
- Document replacement clears the old cache and creates a new one
- Docker volume (`index_data`) persists cache across container restarts

### Content Deduplication

- Every uploaded file is MD5 hashed
- If a file with the same hash already exists in a workspace, upload is rejected
- Prevents wasted indexing time and storage

---

## CI/CD & Deployment

### Docker Compose

Full stack deployment with three containers:

- **PostgreSQL 16** -- persistent storage
- **FastAPI Backend** -- Python 3.11, all RAG logic
- **React Frontend** -- Nginx + static build

### GitHub Actions Pipelines

Automated Docker image builds on every push to `main`:

- **Backend pipeline** -- triggered by changes to `backend/`, `config/`, `indexer/`, `llm/`, `parsers/`, `retriever/`
- **Frontend pipeline** -- triggered by changes to `frontend/`
- Images pushed to GitHub Container Registry (`ghcr.io`)
- Pull request builds validate without pushing
- Docker Buildx with GitHub Actions cache for fast builds
