"""Pydantic request/response schemas for the OpenAI-compatible API.

These models mirror the OpenAI chat-completions API surface so that
clients such as Open WebUI can talk to PageIndex RAG as if it were an
OpenAI-compatible provider.  Additional schemas for workspace and
document management are included at the bottom.
"""

from pydantic import BaseModel, Field
from typing import Optional
import time


# ===================================================================
# Chat Completions — request / response
# ===================================================================

class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: str  # "system", "user", "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request body.

    The ``metadata`` field is used by Open WebUI to pass file references and
    other per-request metadata.  It is accepted but not validated here so
    that FastAPI does not reject the request.
    """
    model: str  # workspace model ID like "pageindex-ws-1"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    # Accept any extra fields Open WebUI sends (metadata, user, etc.)
    model_config = {"extra": "allow"}


class ChatChoice(BaseModel):
    """A single completion choice (non-streaming)."""
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """Full (non-streaming) chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatChoice]
    usage: UsageInfo = Field(default_factory=UsageInfo)


# ===================================================================
# Chat Completions — streaming
# ===================================================================

class DeltaContent(BaseModel):
    """Incremental content for a streaming chunk."""
    role: Optional[str] = None
    content: Optional[str] = None


class StreamChoice(BaseModel):
    """A single streaming choice delta."""
    index: int = 0
    delta: DeltaContent
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """One chunk of a streaming chat completion response."""
    id: str
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[StreamChoice]


# ===================================================================
# Models list
# ===================================================================

class ModelInfo(BaseModel):
    """Metadata for a single model (workspace) exposed via /v1/models.

    The ``name`` field provides a human-friendly display name for Open WebUI
    while the ``id`` remains the canonical machine-readable identifier.  This
    prevents users from needing to rename models and avoids ID-mismatch errors.
    """
    id: str
    name: str = ""
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "pageindex-rag"


class ModelListResponse(BaseModel):
    """Response body for GET /v1/models."""
    object: str = "list"
    data: list[ModelInfo]


# ===================================================================
# Workspace management
# ===================================================================

class WorkspaceCreate(BaseModel):
    """Request body for creating a new workspace."""
    name: str
    description: str = ""
    owner_username: str


class WorkspaceUpdate(BaseModel):
    """Request body for updating an existing workspace."""
    name: Optional[str] = None
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Response body representing a workspace."""
    id: int
    name: str
    description: str
    owner_username: str
    doc_count: int = 0
    created_at: str


# ===================================================================
# Document management
# ===================================================================

class DocumentUpdate(BaseModel):
    """Request body for updating document metadata."""
    file_name: Optional[str] = None
    doc_title: Optional[str] = None


class DocumentResponse(BaseModel):
    """Response body representing a processed document."""
    id: int
    workspace_id: int
    file_name: str
    doc_title: str
    root_summary: str
    node_count: int
    image_count: int
    page_count: int
    file_size: int
    created_at: str
