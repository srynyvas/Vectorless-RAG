# Getting Started

## Prerequisites

Before you begin, ensure you have:

- **Docker** and **Docker Compose** (for containerized deployment)
- **Python 3.11+** (for local/standalone development)
- **Node.js 20+** (for frontend development)
- An API key from **Anthropic** (Claude) or **OpenAI** (GPT-4o)

---

## Option 1: Docker Compose (Recommended)

The fastest way to get the complete stack running.

### Step 1: Clone the Repository

```bash
git clone https://github.com/srynyvas/Vectorless-RAG.git
cd Vectorless-RAG
```

### Step 2: Configure Environment

Create a `.env.docker` file in the project root:

```bash
# LLM Configuration
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Or use OpenAI instead:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key-here
# OPENAI_MODEL=gpt-4o

# Database (change in production!)
POSTGRES_DB=pageindex
POSTGRES_USER=pageindex
POSTGRES_PASSWORD=changeme

# API Authentication (change in production!)
RAG_API_KEY=pageindex-secret-key
```

!!! warning "Security"
    Always change `POSTGRES_PASSWORD` and `RAG_API_KEY` for production deployments. The defaults are for development only.

### Step 3: Launch

```bash
docker compose up --build
```

This will:

1. Start **PostgreSQL** on port `5433`
2. Build and start the **FastAPI backend** on port `8100`
3. Build and start the **React frontend** on port `3000`

### Step 4: Open the UI

Navigate to [http://localhost:3000](http://localhost:3000) in your browser.

---

## Option 2: Streamlit Standalone

For quick experimentation without Docker or a database.

### Step 1: Clone and Install

```bash
git clone https://github.com/srynyvas/Vectorless-RAG.git
cd Vectorless-RAG
pip install -r requirements.txt
```

### Step 2: Configure

```bash
cp .env.example .env
```

Edit `.env` with your API key:

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Step 3: Run

```bash
streamlit run app.py
```

The Streamlit UI will open at [http://localhost:8501](http://localhost:8501).

!!! note
    The Streamlit version is the original interface. It doesn't include the database, workspace management, or the RAG Explorer panel. For the full experience, use Docker Compose.

---

## Option 3: Local Development (Full Stack)

For active development with hot-reload on both frontend and backend.

### Backend Setup

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Start PostgreSQL (using Docker for the database only)
docker run -d \
  --name vectorless-pg \
  -e POSTGRES_DB=pageindex \
  -e POSTGRES_USER=pageindex \
  -e POSTGRES_PASSWORD=changeme \
  -p 5433:5432 \
  postgres:16-alpine

# Configure environment
cp .env.example .env
# Edit .env with your API key and database URL:
# DATABASE_URL=postgresql://pageindex:changeme@localhost:5433/pageindex

# Start the backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8100 --reload
```

### Frontend Setup

```bash
# In a separate terminal
cd frontend
npm install
npm run dev
```

The frontend dev server runs at [http://localhost:5173](http://localhost:5173) with hot module replacement.

!!! tip "API Proxy in Development"
    The Vite dev server should be configured to proxy `/api/` and `/v1/` requests to `localhost:8100`. Check `frontend/vite.config.js` for proxy configuration.

---

## Your First Query

Once the system is running:

### 1. Create a Workspace

Click **"New Workspace"** in the sidebar and give it a name (e.g., "Research Papers").

### 2. Upload a Document

Click the upload zone or drag-and-drop a file. Supported formats:

- PDF (`.pdf`)
- Markdown (`.md`)
- Word (`.docx`)
- PowerPoint (`.pptx`)
- Plain Text (`.txt`)

!!! info "Indexing Time"
    - **Quick Index** (toggle in Settings): Nearly instant -- uses text snippets as summaries
    - **Full Index**: 30 seconds to several minutes, depending on document size -- generates LLM summaries for every section

### 3. Ask a Question

Type your question in the chat input and press Enter. The system will:

1. Route your question to the most relevant document(s)
2. Search the document tree for relevant sections
3. Assemble context from selected sections
4. Generate a grounded answer with citations

### 4. Explore the RAG Process

Toggle the **RAG Explorer** panel (eye icon in the header) to see:

- **Tree**: The document's hierarchical structure with highlighted selected nodes
- **Reasoning**: Why those sections were chosen
- **Context**: The exact text sent to the LLM
- **Images**: Any visual content from selected sections

---

## Verifying the Installation

### Health Check

```bash
curl http://localhost:8100/health
```

Expected response:
```json
{"status": "healthy"}
```

### List Models (Workspaces)

```bash
curl http://localhost:8100/v1/models \
  -H "Authorization: Bearer pageindex-secret-key"
```

### Upload via API

```bash
# Create a workspace
curl -X POST http://localhost:8100/api/workspaces \
  -H "Authorization: Bearer pageindex-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workspace", "owner_username": "default"}'

# Upload a document (replace workspace_id and file path)
curl -X POST http://localhost:8100/api/documents/upload \
  -H "Authorization: Bearer pageindex-secret-key" \
  -F "file=@/path/to/your/document.pdf" \
  -F "workspace_id=1" \
  -F "username=default"
```

### Query via API

```bash
curl -X POST http://localhost:8100/api/chat/query \
  -H "Authorization: Bearer pageindex-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "query": "What is the main topic of this document?",
    "username": "default"
  }'
```

---

## Troubleshooting

??? question "Docker build fails with memory errors"
    The frontend build (Vite/React) can be memory-intensive. Ensure Docker has at least **4GB of memory** allocated. On Docker Desktop, go to Settings > Resources > Memory.

??? question "Backend can't connect to PostgreSQL"
    Ensure PostgreSQL is healthy before the backend starts. Docker Compose handles this with `depends_on: condition: service_healthy`, but if running manually, wait for the database to be ready:
    ```bash
    pg_isready -h localhost -p 5433 -U pageindex
    ```

??? question "LLM API errors during upload/chat"
    - Verify your API key is correct in `.env` or `.env.docker`
    - Check that `LLM_PROVIDER` matches your API key (e.g., `anthropic` for Anthropic keys)
    - Ensure you have API credits available

??? question "Frontend shows blank page"
    - Check browser console for errors (F12 > Console)
    - Verify the backend is running: `curl http://localhost:8100/health`
    - Ensure Nginx is correctly proxying -- check `frontend/nginx.conf`

??? question "Documents upload but chat gives empty answers"
    - Check backend logs for tree search errors
    - Try re-uploading with Quick Index disabled (full summaries improve search)
    - Verify the document has extractable text (scanned PDFs without OCR won't work)
