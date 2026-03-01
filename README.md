<p align="center">
  <h1 align="center">Vectorless RAG</h1>
  <p align="center">
    <strong>Retrieval-Augmented Generation Without Vector Embeddings</strong>
  </p>
  <p align="center">
    <a href="https://srynyvas.github.io/Vectorless-RAG/">Documentation</a> &bull;
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#how-it-works">How It Works</a> &bull;
    <a href="#features">Features</a>
  </p>
</p>

---

**Vectorless RAG** is a document question-answering system that replaces traditional vector embeddings with **hierarchical tree indexing and LLM reasoning**. Instead of encoding documents into high-dimensional vector spaces and performing similarity searches, it builds a structured tree of document sections and lets an LLM intelligently navigate that tree to find relevant content.

## The Core Idea

Traditional RAG systems work like this:

> *"Turn everything into numbers, then find similar numbers."*

Vectorless RAG works like this:

> *"Build a table of contents, then ask an LLM to read it and pick the right sections."*

This seemingly simple shift eliminates entire categories of problems — embedding model selection, vector database management, chunk size tuning, and semantic drift. The result is a system that is **simpler to understand, easier to debug, and often more accurate** for structured documents.

## How It Works

```
  Upload Document ──> Parse & Build Tree ──> User Asks Question
                                                     │
                                              LLM Reads Tree
                                              Metadata (only
                                              titles & summaries)
                                                     │
                                              Selects Relevant
                                              Sections by ID
                                                     │
                                              Full Text Retrieved
                                                     │
                                              LLM Generates
                                              Grounded Answer
```

1. **Parse** the document into sections (respecting headings, chapters, sub-sections)
2. **Build a tree** where each node has a title, summary, and page range
3. When a user asks a question, send **only the lightweight tree metadata** (no full text) to the LLM
4. The LLM **reasons about which sections are relevant** and returns node IDs
5. **Retrieve the full text** of selected sections
6. **Generate a grounded answer** with citations

> The key insight: **documents already have structure. Traditional RAG destroys it during chunking. Vectorless RAG preserves and leverages it.**

## How It Differs from Traditional RAG

| Aspect | Traditional Vector RAG | Vectorless RAG |
|--------|----------------------|----------------|
| **Retrieval** | Cosine similarity in embedding space | LLM reasoning over document structure |
| **Infrastructure** | Vector DB (Pinecone, Chroma, etc.) | Just a filesystem or any DB |
| **Chunking** | Critical decision, domain-dependent | Natural document structure (headings) |
| **Context** | Lost at chunk boundaries | Preserved in tree hierarchy |
| **Explainability** | "Cosine similarity = 0.87" | "Selected Section 2.1 because it discusses revenue by segment" |
| **Negation** | Poor (embeddings are symmetric) | Good (LLM understands negation) |
| **Debugging** | Opaque | Transparent (see tree, reasoning, context) |

## Features

- **Vectorless Retrieval** — No embeddings, no vector DB. Pure LLM reasoning over document structure.
- **Multi-Document Support** — Routes queries across multiple documents, merges answers with citations.
- **Multimodal** — Extracts images from PDFs and includes them in the LLM context.
- **Multi-LLM** — Pluggable support for Claude (Anthropic) and GPT-4o (OpenAI).
- **OpenAI-Compatible API** — Drop-in replacement for any OpenAI-compatible client.
- **React UI** — Modern chat interface with a RAG Explorer panel showing tree, reasoning, context, and images.
- **Document Management** — Upload, edit metadata, replace (version), and delete documents within workspaces.
- **Streaming** — Token-by-token responses via Server-Sent Events.
- **Docker Ready** — Full stack (PostgreSQL + FastAPI + React/Nginx) in containers.
- **CI/CD** — GitHub Actions pipelines for automated Docker image builds and docs deployment.
- **5 File Types** — PDF, Markdown, DOCX, PPTX, and TXT.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An API key from [Anthropic](https://console.anthropic.com/) (Claude) or [OpenAI](https://platform.openai.com/) (GPT-4o)

### 1. Clone

```bash
git clone https://github.com/srynyvas/Vectorless-RAG.git
cd Vectorless-RAG
```

### 2. Configure

Create a `.env.docker` file:

```env
# Choose your LLM provider
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Or use OpenAI:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key-here

# Database (change in production)
POSTGRES_DB=pageindex
POSTGRES_USER=pageindex
POSTGRES_PASSWORD=changeme

# API auth (change in production)
RAG_API_KEY=pageindex-secret-key
```

### 3. Launch

```bash
docker compose up --build
```

### 4. Open

Navigate to **[http://localhost:3000](http://localhost:3000)** — create a workspace, upload a document, and start asking questions.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Docker Compose                     │
│                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ Frontend  │    │   Backend    │    │ PostgreSQL│ │
│  │ React +   │───>│   FastAPI    │───>│   :5433   │ │
│  │ Nginx     │    │   :8100      │    │           │ │
│  │ :3000     │    │              │    └───────────┘ │
│  └──────────┘    │  ┌────────┐  │                   │
│                  │  │Parsers │  │    ┌───────────┐  │
│                  │  ├────────┤  │───>│ Anthropic │  │
│                  │  │Indexer │  │    │ / OpenAI  │  │
│                  │  ├────────┤  │    │   API     │  │
│                  │  │Retriever│ │    └───────────┘  │
│                  │  ├────────┤  │                   │
│                  │  │  LLM   │  │                   │
│                  │  └────────┘  │                   │
│                  └──────────────┘                    │
└─────────────────────────────────────────────────────┘
```

| Service | Technology | Port |
|---------|-----------|------|
| **Frontend** | React 18, Vite, Tailwind, Zustand, Nginx | 3000 |
| **Backend** | FastAPI, SQLAlchemy 2.0, Pydantic v2 | 8100 |
| **Database** | PostgreSQL 16 | 5433 |

## Project Structure

```
Vectorless-RAG/
├── backend/                 # FastAPI server
│   ├── api/                # REST endpoints (chat, documents, workspaces)
│   ├── core/               # Document manager, routing, multi-doc pipeline
│   └── db/                 # SQLAlchemy models & repository pattern
├── frontend/                # React SPA
│   ├── src/components/     # Chat, RAG panel, documents, workspaces
│   ├── src/stores/         # Zustand state management
│   └── src/api/            # API clients (Axios)
├── indexer/                 # Tree builder (ParsedSection → TreeNode)
├── retriever/               # 3-stage RAG pipeline
│   ├── tree_searcher.py    # Stage 1: LLM-guided tree search
│   ├── context_assembler.py # Stage 2: Context extraction
│   └── pipeline.py         # Stage 3: Answer generation
├── parsers/                 # PDF, Markdown, DOCX, PPTX, TXT
├── llm/                     # Provider abstraction (Anthropic, OpenAI)
├── config/                  # Pydantic settings (.env)
├── docker-compose.yml
├── .github/workflows/       # CI/CD pipelines
│   ├── backend-docker.yml  # Backend image build
│   ├── frontend-docker.yml # Frontend image build
│   └── docs.yml            # Documentation deployment
└── docs/                    # MkDocs documentation
```

## The RAG Pipeline

The three-stage pipeline is the heart of the system:

**Stage 1 — Tree Search:** The lightweight tree (titles, summaries, page ranges — no full text) is sent to the LLM along with the user's question. The LLM reasons about which sections are relevant and returns 1-5 node IDs.

**Stage 2 — Context Assembly:** The full text of selected nodes (and their children) is extracted, formatted with section headers and page numbers, and assembled within a 15,000-character budget.

**Stage 3 — Answer Generation:** The assembled context and the user's question are sent to the LLM, which generates a grounded answer with section citations.

For **multi-document** workspaces, a routing step first selects the 1-3 most relevant documents before running the per-document pipeline, and a merge step synthesizes per-document answers into a single response.

## API Usage

The backend exposes an **OpenAI-compatible API**, so you can use it with any compatible client:

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

## Documentation

Full documentation is available at **[srynyvas.github.io/Vectorless-RAG](https://srynyvas.github.io/Vectorless-RAG/)**

| Page | Description |
|------|-------------|
| [The Intuition](https://srynyvas.github.io/Vectorless-RAG/intuition/) | Why vectorless works and how it compares to traditional RAG |
| [Architecture](https://srynyvas.github.io/Vectorless-RAG/architecture/) | System design, components, database schema, request flow |
| [RAG Pipeline](https://srynyvas.github.io/Vectorless-RAG/pipeline/) | Deep dive into the three-stage retrieval pipeline |
| [Features](https://srynyvas.github.io/Vectorless-RAG/features/) | Complete feature list and capabilities |
| [Getting Started](https://srynyvas.github.io/Vectorless-RAG/getting-started/) | Setup options (Docker, Streamlit, local dev) |
| [Configuration](https://srynyvas.github.io/Vectorless-RAG/configuration/) | All environment variables and tuning options |
| [Deployment](https://srynyvas.github.io/Vectorless-RAG/deployment/) | Docker, Nginx, CI/CD pipelines, production checklist |
| [API Reference](https://srynyvas.github.io/Vectorless-RAG/api-reference/) | Complete endpoint documentation |

## License

This project is for personal and educational use.
