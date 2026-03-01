# Configuration Guide

Vectorless RAG is configured through environment variables, typically stored in a `.env` file (for local development) or `.env.docker` (for Docker deployment).

---

## Configuration File

The configuration is managed by Pydantic Settings (`config/settings.py`), which automatically reads from environment variables and `.env` files.

### Creating Your Configuration

=== "Docker Deployment"

    Create `.env.docker` in the project root:
    ```bash
    cp .env.example .env.docker
    ```

=== "Local Development"

    Create `.env` in the project root:
    ```bash
    cp .env.example .env
    ```

---

## All Configuration Options

### LLM Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | Which LLM to use: `anthropic` or `openai` |

### Anthropic (Claude)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(empty)* | Your Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5-20250929` | Claude model to use |

### OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(empty)* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model to use |

### LLM Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_TEMPERATURE` | `0.1` | Default sampling temperature (0.0 = deterministic, 1.0 = creative) |
| `LLM_MAX_TOKENS` | `4096` | Maximum tokens in LLM responses |
| `SEARCH_MAX_TOKENS` | `2048` | Maximum tokens for tree search responses |

### Indexing

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CHUNK_CHARS` | `3000` | Maximum characters per parsed section |
| `INDEX_SUMMARY_MAX_WORDS` | `50` | Maximum words in LLM-generated node summaries |

### Image Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `EXTRACT_IMAGES` | `true` | Whether to extract images from documents |
| `IMAGE_MAX_EDGE` | `1568` | Maximum image dimension (pixels) -- images are resized to fit |
| `MAX_IMAGES_PER_SECTION` | `5` | Maximum images attached to a single tree node |
| `MAX_CONTEXT_IMAGES` | `10` | Maximum images included in the answer-generation context |

### Storage Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_DIR` | `{PROJECT_ROOT}/data/uploads` | Directory for uploaded files |
| `INDEX_DIR` | `{PROJECT_ROOT}/data/indices` | Directory for cached tree indices |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/pageindex.db` | Database connection string |

!!! info
    In Docker, `DATABASE_URL` is automatically set by `docker-compose.yml` to point to the PostgreSQL container. The SQLite default is only used for standalone/Streamlit mode.

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_API_KEY` | `pageindex-secret-key` | Bearer token for API authentication |

### Docker-Specific (PostgreSQL)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `pageindex` | Database name |
| `POSTGRES_USER` | `pageindex` | Database username |
| `POSTGRES_PASSWORD` | `changeme` | Database password |

---

## Example Configurations

### Minimal (Anthropic)

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### Minimal (OpenAI)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
```

### Full Production Configuration

```env
# LLM Provider
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Fallback / Alternative LLM
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o

# LLM Tuning
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
SEARCH_MAX_TOKENS=2048

# Indexing
MAX_CHUNK_CHARS=3000
INDEX_SUMMARY_MAX_WORDS=50

# Image Processing
EXTRACT_IMAGES=true
IMAGE_MAX_EDGE=1568
MAX_IMAGES_PER_SECTION=5
MAX_CONTEXT_IMAGES=10

# Database (PostgreSQL)
POSTGRES_DB=vectorless_rag
POSTGRES_USER=vectorless
POSTGRES_PASSWORD=strong-random-password-here

# API Security
RAG_API_KEY=strong-random-api-key-here
```

---

## Switching LLM Providers

You can switch between Anthropic and OpenAI at any time:

### Via Environment Variable

Edit your `.env` file:
```env
LLM_PROVIDER=openai  # Change from 'anthropic' to 'openai'
```

Then restart the backend (or Docker container).

### Via Frontend Settings

The React UI's Settings panel allows switching providers at runtime. Note: this affects the frontend's request headers but the backend still uses the `.env` configuration for actual LLM calls.

---

## Context Budget Tuning

The most impactful configuration for answer quality:

| Scenario | Recommended Settings |
|----------|---------------------|
| **Short documents** (< 20 pages) | Default settings work well |
| **Long documents** (> 100 pages) | Consider `INDEX_SUMMARY_MAX_WORDS=75` for richer summaries |
| **Image-heavy PDFs** | Set `MAX_CONTEXT_IMAGES=15` and `IMAGE_MAX_EDGE=2048` |
| **Cost-conscious** | Use `EXTRACT_IMAGES=false` and Quick Index mode |
| **Maximum accuracy** | Full Index with `INDEX_SUMMARY_MAX_WORDS=75`, `LLM_TEMPERATURE=0.05` |
