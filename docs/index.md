# Vectorless RAG

## Retrieval-Augmented Generation Without Vector Embeddings

**Vectorless RAG** is a document question-answering system that replaces traditional vector embeddings with **hierarchical tree indexing and LLM reasoning**. Instead of encoding documents into high-dimensional vector spaces and performing similarity searches, it builds a structured tree of document sections and lets an LLM intelligently navigate that tree to find relevant content.

---

## The Core Idea

Traditional RAG systems work like this:

> *"Turn everything into numbers, then find similar numbers."*

Vectorless RAG works like this:

> *"Build a table of contents, then ask an LLM to read it and pick the right sections."*

This seemingly simple shift eliminates entire categories of problems: embedding model selection, vector database management, chunk size tuning, and semantic drift. The result is a system that is **simpler to understand, easier to debug, and often more accurate** for structured documents.

---

## How It Works (30-Second Version)

```mermaid
graph LR
    A[Upload Document] --> B[Parse & Build Tree]
    B --> C[User Asks Question]
    C --> D[LLM Reads Tree Metadata]
    D --> E[Selects Relevant Sections]
    E --> F[Full Text Retrieved]
    F --> G[LLM Generates Answer]
```

1. **Parse** the document into sections (respecting headings, chapters, etc.)
2. **Build a tree** where each node is a section with a title, summary, and page range
3. When a user asks a question, send **only the tree metadata** (no full text) to the LLM
4. The LLM **reasons about which sections are relevant** and returns node IDs
5. **Retrieve the full text** of selected sections
6. **Generate a grounded answer** with citations

---

## Key Highlights

| Feature | Description |
|---------|-------------|
| :material-tree:{ .lg } **Vectorless Retrieval** | No embeddings, no vector DB. Pure LLM reasoning over document structure. |
| :material-file-multiple:{ .lg } **Multi-Document** | Routes queries across multiple documents, merges answers with citations. |
| :material-image:{ .lg } **Multimodal** | Extracts images from PDFs and includes them in the LLM context. |
| :material-swap-horizontal:{ .lg } **Multi-LLM** | Pluggable support for Claude (Anthropic) and GPT-4o (OpenAI). |
| :material-api:{ .lg } **OpenAI-Compatible API** | Drop-in replacement for any OpenAI-compatible client. |
| :material-docker:{ .lg } **Docker Ready** | Full stack in containers with CI/CD pipelines. |
| :material-file-document-multiple:{ .lg } **5 File Types** | PDF, Markdown, DOCX, PPTX, and TXT. |

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/srynyvas/Vectorless-RAG.git
cd Vectorless-RAG

# Configure your API key
cp .env.example .env
# Edit .env with your Anthropic or OpenAI API key

# Launch with Docker
docker compose up --build

# Open the UI
open http://localhost:3000
```

That's it. Upload a document, ask a question, and explore the RAG reasoning panel to see exactly how the system found your answer.

---

## Project Structure

```
Vectorless-RAG/
├── backend/            # FastAPI server (API, database, core logic)
├── frontend/           # React + Vite web UI
├── indexer/            # Tree index construction
├── retriever/          # 3-stage RAG pipeline
├── parsers/            # Document parsers (PDF, MD, DOCX, PPTX, TXT)
├── llm/                # LLM abstraction (Anthropic, OpenAI)
├── config/             # Configuration management
├── docker-compose.yml  # Container orchestration
└── docs/               # This documentation
```

---

## Who Is This For?

- **Developers** building RAG systems who want a simpler, more transparent alternative to vector search
- **Researchers** exploring non-embedding approaches to information retrieval
- **Teams** who need document Q&A without the operational overhead of vector databases
- **Anyone** frustrated by the "black box" nature of embedding-based retrieval

---

<div class="grid cards" markdown>

-   :material-lightbulb-on:{ .lg .middle } **Read the Intuition**

    ---

    Understand *why* vectorless works and how it compares to traditional RAG

    [:octicons-arrow-right-24: The Intuition](intuition.md)

-   :material-rocket-launch:{ .lg .middle } **Get Started**

    ---

    Set up the project locally or with Docker in under 5 minutes

    [:octicons-arrow-right-24: Getting Started](getting-started.md)

-   :material-cog:{ .lg .middle } **Architecture**

    ---

    Dive deep into the system design and component interactions

    [:octicons-arrow-right-24: Architecture](architecture.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Complete endpoint documentation for integration

    [:octicons-arrow-right-24: API Reference](api-reference.md)

</div>
