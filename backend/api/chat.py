"""POST /v1/chat/completions -- OpenAI-compatible chat endpoint.

Receives chat requests from Open WebUI (or any OpenAI-compatible client),
routes them through the PageIndex RAG pipeline, and returns either a full
response or an SSE stream of token chunks.

Each workspace is exposed as a model with ID ``pageindex-ws-{id}``.  The
endpoint extracts the workspace ID from the model name, loads the cached
document trees, runs the RAG pipeline, and formats the result as an
OpenAI-compatible chat completion.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatChoice,
    ChatMessage,
    DeltaContent,
    StreamChoice,
    UsageInfo,
)
from backend.core.document_manager import load_cached_tree
from backend.core.multi_doc_pipeline import MultiDocPipeline
from backend.db.database import get_db
from backend.db.repos import DocumentRepo, WorkspaceRepo
from indexer.node import TreeNode
from llm.factory import get_llm_provider
from retriever.pipeline import RAGPipeline
from retriever.prompts import (
    ANSWER_GENERATION_SYSTEM_PROMPT,
    ANSWER_GENERATION_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# Regex for detecting Open WebUI's injected <source> tags.
_SOURCE_TAG_RE = re.compile(r"<source[^>]*>(.*?)</source>", re.DOTALL)


# ---------------------------------------------------------------------------
# Helper: detect and extract Open WebUI injected RAG context
# ---------------------------------------------------------------------------

def _extract_owui_rag_context(user_message: str) -> tuple[str, str] | None:
    """Detect and extract Open WebUI's pre-injected RAG context.

    When Open WebUI performs its own RAG retrieval, it modifies the user
    message to include ``<source>`` tags with retrieved document chunks
    and wraps the original query in a template.

    Parameters
    ----------
    user_message:
        The raw user message content from the chat request.

    Returns
    -------
    tuple[str, str] | None
        A ``(context_text, clean_query)`` tuple if source tags are found,
        or ``None`` if the message is a plain query without injected context.
    """
    source_matches = _SOURCE_TAG_RE.findall(user_message)
    if not source_matches:
        return None

    # Extract all source content
    context_parts = [match.strip() for match in source_matches if match.strip()]
    context_text = "\n\n---\n\n".join(context_parts)

    # Extract the user's actual query from the template.
    # Open WebUI uses patterns like "### User Query:\n..." or "[query]..."
    # or the query appears after all source tags.
    clean_query = user_message

    # Try common Open WebUI RAG template patterns:
    # Pattern 1: "### User Query:\n<query>"
    query_match = re.search(
        r"(?:###\s*User\s*Query|###\s*Query|User(?:'s)?\s*Query)\s*[:\-]?\s*\n(.+)",
        user_message, re.DOTALL | re.IGNORECASE,
    )
    if query_match:
        clean_query = query_match.group(1).strip()
    else:
        # Pattern 2: everything after the last </source> tag
        last_source_end = user_message.rfind("</source>")
        if last_source_end != -1:
            after_sources = user_message[last_source_end + len("</source>"):].strip()
            # Remove common template wrappers
            after_sources = re.sub(
                r"^(?:---\s*\n?|Based on.*?context.*?answer.*?\n)",
                "", after_sources, flags=re.IGNORECASE,
            ).strip()
            if after_sources and len(after_sources) > 5:
                clean_query = after_sources

    # If still contains source tags, strip them out as last resort
    clean_query = _SOURCE_TAG_RE.sub("", clean_query).strip()
    # Remove common RAG template boilerplate
    clean_query = re.sub(
        r"^### Task:.*?\n", "", clean_query, flags=re.DOTALL
    ).strip()

    logger.info(
        "Detected Open WebUI RAG context: %d source(s), %d chars context, "
        "query='%s'",
        len(source_matches),
        len(context_text),
        clean_query[:100],
    )
    return context_text, clean_query


# ---------------------------------------------------------------------------
# Helper: generate answer from pre-assembled context (Mode 1)
# ---------------------------------------------------------------------------

def _generate_from_context(context: str, query: str) -> str:
    """Generate an answer from pre-assembled RAG context.

    Used when Open WebUI has already performed retrieval and injected
    document chunks into the user message.  Reuses the same answer
    generation prompts as the native PageIndex pipeline.

    Parameters
    ----------
    context:
        The assembled document context text (from Open WebUI's retrieval).
    query:
        The user's clean question (source tags stripped).

    Returns
    -------
    str
        The LLM-generated answer.
    """
    llm = get_llm_provider()

    user_message = ANSWER_GENERATION_USER_TEMPLATE.format(
        context=context,
        query=query,
    )

    try:
        answer = llm.generate(
            system_prompt=ANSWER_GENERATION_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.2,
            max_tokens=4096,
        )
        return answer.strip()
    except Exception as exc:
        logger.error("Context-based answer generation failed: %s", exc, exc_info=True)
        return (
            "An error occurred while generating the answer from the provided "
            "document context. Please try again."
        )


# ---------------------------------------------------------------------------
# Helper: split text into streamable chunks
# ---------------------------------------------------------------------------

def _split_into_chunks(text: str, chunk_size: int = 50) -> list[str]:
    """Split text into small chunks for streaming simulation.

    Attempts to split on word boundaries near *chunk_size* characters.
    If no space is found, falls back to a hard split at *chunk_size*.

    Parameters
    ----------
    text:
        The full answer text to split.
    chunk_size:
        Target maximum number of characters per chunk.

    Returns
    -------
    list[str]
        Ordered list of text fragments whose concatenation equals *text*.
    """
    if not text:
        return []

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break
        # Try to split at a space near chunk_size
        split_pos = remaining.rfind(" ", 0, chunk_size)
        if split_pos == -1:
            split_pos = chunk_size
        chunks.append(remaining[:split_pos])
        remaining = remaining[split_pos:].lstrip()
    return chunks


# ---------------------------------------------------------------------------
# Helper: build a non-streaming response
# ---------------------------------------------------------------------------

def _make_response(
    model: str,
    content: str,
    completion_id: str | None = None,
) -> ChatCompletionResponse:
    """Build a complete (non-streaming) ``ChatCompletionResponse``.

    Parameters
    ----------
    model:
        Model identifier to echo back (e.g. ``"pageindex-ws-1"``).
    content:
        The assistant's answer text.
    completion_id:
        Optional custom completion ID.  A random one is generated when
        not provided.
    """
    cid = completion_id or f"chatcmpl-{uuid4().hex[:12]}"
    return ChatCompletionResponse(
        id=cid,
        model=model,
        choices=[
            ChatChoice(
                message=ChatMessage(role="assistant", content=content),
            )
        ],
        usage=UsageInfo(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        ),
    )


# ---------------------------------------------------------------------------
# Helper: SSE streaming generator
# ---------------------------------------------------------------------------

async def _stream_response(
    model: str,
    content: str,
    completion_id: str,
) -> AsyncGenerator[str, None]:
    """Yield Server-Sent-Event lines that stream *content* as token chunks.

    The SSE format follows the OpenAI specification exactly so that
    Open WebUI and other compatible clients can consume the stream.

    Yields
    ------
    str
        Individual ``data: {json}\\n\\n`` lines including the final
        ``data: [DONE]\\n\\n`` sentinel.
    """
    created = int(time.time())

    # 1. Initial chunk: send the assistant role
    initial_chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            StreamChoice(
                delta=DeltaContent(role="assistant"),
                finish_reason=None,
            )
        ],
    )
    yield f"data: {initial_chunk.model_dump_json()}\n\n"

    # 2. Content chunks
    text_chunks = _split_into_chunks(content)
    for piece in text_chunks:
        chunk = ChatCompletionChunk(
            id=completion_id,
            created=created,
            model=model,
            choices=[
                StreamChoice(
                    delta=DeltaContent(content=piece),
                    finish_reason=None,
                )
            ],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"

    # 3. Final chunk: signal stop
    final_chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            StreamChoice(
                delta=DeltaContent(),
                finish_reason="stop",
            )
        ],
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"

    # 4. Done sentinel
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Helper: run RAG on a single document
# ---------------------------------------------------------------------------

def _query_single_document(
    pipeline: RAGPipeline,
    tree: TreeNode,
    user_query: str,
) -> dict:
    """Run the RAG pipeline against a single document tree.

    Wraps ``pipeline.query`` in a try/except so that individual document
    failures don't crash the entire request.

    Returns
    -------
    dict
        The pipeline result dict (keys: answer, node_ids, reasoning, context,
        image_count), or a dict with an error answer on failure.
    """
    try:
        return pipeline.query(tree, user_query)
    except Exception as exc:
        logger.error(
            "RAG pipeline failed for tree '%s': %s",
            tree.title,
            exc,
            exc_info=True,
        )
        return {
            "answer": (
                f"An error occurred while processing '{tree.title}': {exc}"
            ),
            "node_ids": [],
            "reasoning": "",
            "context": "",
            "image_count": 0,
        }


# ---------------------------------------------------------------------------
# Helper: merge answers from multiple documents
# ---------------------------------------------------------------------------

def _merge_multi_doc_answers(
    results: list[tuple[str, dict]],
) -> str:
    """Merge RAG results from multiple documents into a single answer.

    Parameters
    ----------
    results:
        A list of ``(doc_file_name, pipeline_result_dict)`` tuples.

    Returns
    -------
    str
        A single merged answer string.  If only one document produced a
        non-trivial answer, its answer is returned without section headers.
    """
    # Filter out results that look like error/fallback messages
    substantive: list[tuple[str, str]] = []
    for doc_name, result in results:
        answer = result.get("answer", "").strip()
        if answer and not answer.startswith("I was unable to identify"):
            substantive.append((doc_name, answer))

    if not substantive:
        return (
            "I was unable to find relevant information in any of the "
            "workspace documents for your question. Please try rephrasing "
            "your query or asking about a topic covered by the documents."
        )

    if len(substantive) == 1:
        # Single useful answer -- return it without headers
        return substantive[0][1]

    # Multiple useful answers -- add document name headers
    parts: list[str] = []
    for doc_name, answer in substantive:
        parts.append(f"## From: {doc_name}\n\n{answer}")
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    db: Session = Depends(get_db),
):
    """OpenAI-compatible chat completions endpoint.

    Accepts a chat request with a model ID of the form
    ``pageindex-ws-{id}``, runs the RAG pipeline against the documents
    in that workspace, and returns the answer either as a complete
    response or as an SSE stream.
    """
    completion_id = f"chatcmpl-{uuid4().hex[:12]}"

    logger.info(
        "Incoming chat request: model='%s', messages=%d, stream=%s",
        request.model,
        len(request.messages),
        request.stream,
    )

    # ------------------------------------------------------------------
    # 1. Resolve workspace from model identifier
    #    Supports both canonical "pageindex-ws-{id}" format and
    #    user-renamed model names from Open WebUI.
    # ------------------------------------------------------------------
    workspace = WorkspaceRepo.resolve_from_model_string(db, request.model)
    if workspace is None:
        logger.warning(
            "Could not resolve workspace from model string: '%s'",
            request.model,
        )
        raise HTTPException(
            status_code=404,
            detail=(
                f"Could not find a workspace matching model '{request.model}'. "
                f"Expected format: 'pageindex-ws-{{id}}' or a workspace name."
            ),
        )
    workspace_id = workspace.id

    # ------------------------------------------------------------------
    # 3. Extract the user query (last user message)
    # ------------------------------------------------------------------
    user_query: str | None = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_query = msg.content
            break

    if not user_query:
        raise HTTPException(
            status_code=400,
            detail="No user message found in the request.",
        )

    logger.info(
        "Chat request: workspace=%d (%s), query_len=%d, stream=%s",
        workspace_id,
        workspace.name,
        len(user_query),
        request.stream,
    )

    # ------------------------------------------------------------------
    # 4. MODE 1: Check for Open WebUI injected RAG context
    #    If Open WebUI has already performed retrieval and injected
    #    <source> tags, use that context directly for answer generation.
    # ------------------------------------------------------------------
    owui_context = _extract_owui_rag_context(user_query)

    if owui_context is not None:
        context_text, clean_query = owui_context
        logger.info(
            "MODE 1: Using Open WebUI injected RAG context "
            "(%d chars context, query='%s')",
            len(context_text),
            clean_query[:80],
        )
        try:
            answer = _generate_from_context(context_text, clean_query)
        except Exception as exc:
            logger.error("Mode 1 answer generation failed: %s", exc, exc_info=True)
            answer = (
                "An error occurred while generating an answer from the "
                "document context. Please try again."
            )
    else:
        # ---------------------------------------------------------------
        # 5. MODE 2: Native PageIndex tree-based RAG
        #    No Open WebUI context found — use our own pipeline.
        # ---------------------------------------------------------------
        documents = DocumentRepo.list_for_workspace(db, workspace_id)
        if not documents:
            content = (
                f"The workspace **{workspace.name}** has no documents "
                "uploaded yet. Please upload documents either through "
                "Open WebUI (attach files to chat) or via the document "
                "management API before asking questions."
            )
            if request.stream:
                return StreamingResponse(
                    _stream_response(request.model, content, completion_id),
                    media_type="text/event-stream",
                )
            return _make_response(request.model, content, completion_id)

        logger.info(
            "MODE 2: Using PageIndex tree-based RAG (%d documents)",
            len(documents),
        )

        # 5a. Load cached trees for each document
        loaded_docs: list[tuple] = []  # (document_orm, tree)
        for doc in documents:
            tree = load_cached_tree(doc.username, doc.file_hash)
            if tree is not None:
                loaded_docs.append((doc, tree))
            else:
                logger.warning(
                    "Could not load cached tree for doc %d (%s), hash=%s",
                    doc.id,
                    doc.file_name,
                    doc.file_hash,
                )

        if not loaded_docs:
            content = (
                "The document indices for this workspace could not be loaded. "
                "The cached index files may be missing or corrupted. Please try "
                "re-uploading the documents."
            )
            if request.stream:
                return StreamingResponse(
                    _stream_response(request.model, content, completion_id),
                    media_type="text/event-stream",
                )
            return _make_response(request.model, content, completion_id)

        # 5b. Run RAG pipeline
        try:
            llm = get_llm_provider()
            pipeline = RAGPipeline(llm)

            if len(loaded_docs) == 1:
                doc, tree = loaded_docs[0]
                result = _query_single_document(pipeline, tree, user_query)
                answer = result["answer"]
                logger.info(
                    "Single-doc RAG complete: %d node(s) selected, %d char answer.",
                    len(result.get("node_ids", [])),
                    len(answer),
                )
            else:
                logger.info(
                    "Multi-doc RAG: routing across %d document(s).",
                    len(loaded_docs),
                )
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
                trees_map: dict[int, TreeNode] = {
                    doc.id: tree for doc, tree in loaded_docs
                }
                multi_result = multi_pipeline.query(
                    doc_records, trees_map, user_query
                )
                answer = multi_result["answer"]
                logger.info(
                    "Multi-doc RAG complete: routed to %s, %d char answer.",
                    multi_result.get("routed_doc_ids", []),
                    len(answer),
                )

        except Exception as exc:
            logger.error("RAG pipeline failed: %s", exc, exc_info=True)
            answer = (
                "I encountered an error while processing your question. "
                f"Error details: {exc}\n\n"
                "Please try again. If the issue persists, the workspace "
                "documents may need to be re-indexed."
            )

    # ------------------------------------------------------------------
    # 7. Return response (streaming or non-streaming)
    # ------------------------------------------------------------------
    if request.stream:
        return StreamingResponse(
            _stream_response(request.model, answer, completion_id),
            media_type="text/event-stream",
        )

    return _make_response(request.model, answer, completion_id)
