"""POST /api/chat/query -- Rich chat endpoint with RAG metadata.

Returns the full RAG pipeline result (answer + reasoning + context + images)
so the React frontend can display tree visualization, search reasoning, and
assembled context alongside the answer.

This is the primary endpoint for the custom React UI.  The existing
``/v1/chat/completions`` endpoint is retained for backward compatibility
with OpenAI-compatible clients.
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.document_manager import load_cached_tree
from backend.core.multi_doc_pipeline import MultiDocPipeline
from backend.db.database import get_db
from backend.db.repos import DocumentRepo, WorkspaceRepo
from indexer.node import TreeNode
from llm.factory import get_llm_provider
from retriever.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class RichChatRequest(BaseModel):
    workspace_id: int
    query: str
    conversation_history: list[ChatHistoryMessage] = []
    stream: bool = True
    temperature: float = 0.2
    max_tokens: int = 4096


class DocumentQueryResult(BaseModel):
    doc_id: int
    file_name: str
    node_ids: list[str] = []
    reasoning: str = ""
    context_preview: str = ""
    image_count: int = 0
    images: list[dict] = []


class RAGMetadata(BaseModel):
    mode: str = "native"
    documents_queried: list[DocumentQueryResult] = []
    routing_reasoning: str = ""
    total_nodes_selected: int = 0
    total_images: int = 0


class RichChatResponse(BaseModel):
    id: str
    answer: str
    rag_metadata: RAGMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_single_doc_rag(
    pipeline: RAGPipeline,
    tree: TreeNode,
    user_query: str,
    doc_id: int,
    file_name: str,
) -> tuple[str, DocumentQueryResult]:
    """Run RAG on a single document and return answer + metadata."""
    try:
        result = pipeline.query(tree, user_query)
        answer = result["answer"]
        doc_result = DocumentQueryResult(
            doc_id=doc_id,
            file_name=file_name,
            node_ids=result.get("node_ids", []),
            reasoning=result.get("reasoning", ""),
            context_preview=result.get("context", "")[:3000],
            image_count=result.get("image_count", 0),
            images=result.get("images", []),
        )
        return answer, doc_result
    except Exception as exc:
        logger.error("RAG pipeline failed for doc %s: %s", file_name, exc, exc_info=True)
        return (
            f"An error occurred while processing '{file_name}': {exc}",
            DocumentQueryResult(doc_id=doc_id, file_name=file_name),
        )


def _split_into_chunks(text: str, chunk_size: int = 50) -> list[str]:
    """Split text for simulated streaming."""
    if not text:
        return []
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break
        split_pos = remaining.rfind(" ", 0, chunk_size)
        if split_pos == -1:
            split_pos = chunk_size
        chunks.append(remaining[:split_pos])
        remaining = remaining[split_pos:].lstrip()
    return chunks


async def _stream_rich_response(
    answer: str,
    rag_metadata: RAGMetadata,
    completion_id: str,
    model: str,
) -> AsyncGenerator[str, None]:
    """SSE stream: text chunks + final RAG metadata event."""
    created = int(time.time())

    # Stream text chunks
    text_chunks = _split_into_chunks(answer)
    for piece in text_chunks:
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"

    # Done sentinel
    yield "data: [DONE]\n\n"

    # RAG metadata as final event (custom extension)
    metadata_event = {
        "type": "rag_metadata",
        "data": rag_metadata.model_dump(),
    }
    yield f"data: {json.dumps(metadata_event)}\n\n"


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("/chat/query")
async def rich_chat_query(
    request: RichChatRequest,
    db: Session = Depends(get_db),
):
    """Rich chat endpoint returning answer + full RAG metadata.

    Unlike ``/v1/chat/completions``, this endpoint returns the complete
    RAG pipeline output: selected node IDs, LLM reasoning, assembled
    context preview, and retrieved images.
    """
    completion_id = f"chatcmpl-{uuid4().hex[:12]}"

    logger.info(
        "Rich chat request: workspace=%d, query_len=%d, stream=%s",
        request.workspace_id,
        len(request.query),
        request.stream,
    )

    # 1. Validate workspace
    workspace = WorkspaceRepo.get_by_id(db, request.workspace_id)
    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workspace {request.workspace_id} not found.",
        )

    # 2. Load documents
    documents = DocumentRepo.list_for_workspace(db, request.workspace_id)
    if not documents:
        answer = (
            f"The workspace **{workspace.name}** has no documents uploaded yet. "
            "Please upload documents before asking questions."
        )
        rag_meta = RAGMetadata(mode="none")

        if request.stream:
            return StreamingResponse(
                _stream_rich_response(answer, rag_meta, completion_id, f"pageindex-ws-{workspace.id}"),
                media_type="text/event-stream",
            )
        return RichChatResponse(id=completion_id, answer=answer, rag_metadata=rag_meta)

    # 3. Load cached trees
    loaded_docs = []
    for doc in documents:
        tree = load_cached_tree(doc.username, doc.file_hash)
        if tree is not None:
            loaded_docs.append((doc, tree))
        else:
            logger.warning("Could not load tree for doc %d (%s)", doc.id, doc.file_name)

    if not loaded_docs:
        answer = "Document indices could not be loaded. Please try re-uploading."
        rag_meta = RAGMetadata(mode="error")
        if request.stream:
            return StreamingResponse(
                _stream_rich_response(answer, rag_meta, completion_id, f"pageindex-ws-{workspace.id}"),
                media_type="text/event-stream",
            )
        return RichChatResponse(id=completion_id, answer=answer, rag_metadata=rag_meta)

    # 4. Run RAG pipeline
    llm = get_llm_provider()
    pipeline = RAGPipeline(llm)
    model_id = f"pageindex-ws-{workspace.id}"

    if len(loaded_docs) == 1:
        # Single document
        doc, tree = loaded_docs[0]
        answer, doc_result = _run_single_doc_rag(pipeline, tree, request.query, doc.id, doc.file_name)

        rag_meta = RAGMetadata(
            mode="native",
            documents_queried=[doc_result],
            total_nodes_selected=len(doc_result.node_ids),
            total_images=doc_result.image_count,
        )

        logger.info(
            "Single-doc RAG complete: %d nodes, %d images, %d char answer",
            len(doc_result.node_ids),
            doc_result.image_count,
            len(answer),
        )
    else:
        # Multi-document routing
        logger.info("Multi-doc RAG: routing across %d documents", len(loaded_docs))
        multi_pipeline = MultiDocPipeline(llm)
        doc_records = [
            {
                "id": doc.id,
                "file_name": doc.file_name,
                "doc_title": doc.doc_title or doc.file_name,
                "root_summary": doc.root_summary or "",
            }
            for doc, _ in loaded_docs
        ]
        trees_map = {doc.id: tree for doc, tree in loaded_docs}

        try:
            multi_result = multi_pipeline.query(doc_records, trees_map, request.query)
            answer = multi_result["answer"]

            # Build per-doc metadata
            doc_results = []
            for per_doc in multi_result.get("per_doc_results", []):
                doc_results.append(DocumentQueryResult(
                    doc_id=per_doc.get("doc_id", 0),
                    file_name=per_doc.get("file_name", ""),
                    node_ids=per_doc.get("node_ids", []),
                    reasoning=per_doc.get("reasoning", ""),
                    context_preview=per_doc.get("context", "")[:3000],
                    image_count=per_doc.get("image_count", 0),
                    images=per_doc.get("images", []),
                ))

            total_nodes = sum(len(d.node_ids) for d in doc_results)
            total_images = sum(d.image_count for d in doc_results)

            rag_meta = RAGMetadata(
                mode="native",
                documents_queried=doc_results,
                routing_reasoning=multi_result.get("routing_reasoning", ""),
                total_nodes_selected=total_nodes,
                total_images=total_images,
            )
        except Exception as exc:
            logger.error("Multi-doc RAG failed: %s", exc, exc_info=True)
            answer = f"Error processing your question: {exc}"
            rag_meta = RAGMetadata(mode="error")

    # 5. Return response
    if request.stream:
        return StreamingResponse(
            _stream_rich_response(answer, rag_meta, completion_id, model_id),
            media_type="text/event-stream",
        )

    return RichChatResponse(id=completion_id, answer=answer, rag_metadata=rag_meta)
