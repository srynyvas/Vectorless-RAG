"""End-to-end RAG pipeline: search -> assemble context -> generate answer.

The ``RAGPipeline`` orchestrates the three stages of retrieval-augmented
generation for the PageIndex system:

1. **Tree Search** -- an LLM examines the hierarchical document index and
   selects the most relevant section nodes.
2. **Context Assembly** -- the full text of those sections is extracted and
   formatted into a context window.
3. **Answer Generation** -- a second LLM call synthesizes a grounded answer
   from the retrieved content.

All operations are synchronous.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from retriever.context_assembler import ContextAssembler
from retriever.prompts import (
    ANSWER_GENERATION_SYSTEM_PROMPT,
    ANSWER_GENERATION_USER_TEMPLATE,
)
from retriever.tree_searcher import TreeSearcher

if TYPE_CHECKING:
    from indexer.node import TreeNode
    from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Orchestrates the full retrieval-augmented generation workflow.

    Usage::

        from llm.base import LLMProvider
        from indexer.node import TreeNode

        llm: LLMProvider = ...       # some concrete provider
        tree: TreeNode   = ...       # the pre-built document index

        pipeline = RAGPipeline(llm)
        result = pipeline.query(tree, "What encryption algorithm is used?")

        print(result["answer"])
        print(result["node_ids"])
    """

    def __init__(
        self,
        llm: LLMProvider,
        max_context_chars: int = 15_000,
    ) -> None:
        self.llm = llm
        self.searcher = TreeSearcher(llm)
        self.assembler = ContextAssembler(max_context_chars)

    # ── Public API ────────────────────────────────────────────────────────

    def query(self, tree: TreeNode, user_query: str) -> dict:
        """Run the full RAG pipeline for a user question.

        Args:
            tree:       The root ``TreeNode`` of the document index.
            user_query: The user's natural-language question.

        Returns:
            A dictionary with the following keys:

            - **answer** (str): The LLM-generated answer grounded in the
              retrieved content, or an error/fallback message.
            - **node_ids** (list[str]): The IDs of the tree nodes selected
              by the search step.
            - **reasoning** (str): The LLM's explanation for why those
              nodes were chosen.
            - **context** (str): The assembled section text that was sent
              to the answer-generation prompt.
        """
        t_start = time.monotonic()

        # ── Stage 1: Tree Search ──────────────────────────────────────────
        logger.info("Stage 1 -- Tree search for query: %s", user_query)
        t_search = time.monotonic()

        node_ids, reasoning = self.searcher.search(tree, user_query)

        logger.info(
            "Tree search completed in %.2fs -- %d node(s) selected.",
            time.monotonic() - t_search,
            len(node_ids),
        )

        if not node_ids:
            return {
                "answer": (
                    "I was unable to identify relevant sections in the document "
                    "for your question. Please try rephrasing your query or "
                    "asking about a topic covered by the document."
                ),
                "node_ids": [],
                "reasoning": reasoning,
                "context": "",
                "image_count": 0,
            }

        # ── Stage 2: Context Assembly (multimodal) ─────────────────────────
        logger.info("Stage 2 -- Assembling context from nodes: %s", node_ids)
        t_assemble = time.monotonic()

        context, images = self.assembler.assemble_multimodal(tree, node_ids)

        logger.info(
            "Context assembled in %.2fs -- %d chars, %d image(s).",
            time.monotonic() - t_assemble,
            len(context),
            len(images),
        )

        if not context.strip():
            return {
                "answer": (
                    "The relevant sections were identified but contain no "
                    "extractable text. The document index may be incomplete."
                ),
                "node_ids": node_ids,
                "reasoning": reasoning,
                "context": "",
                "image_count": 0,
            }

        # ── Stage 3: Answer Generation ────────────────────────────────────
        logger.info("Stage 3 -- Generating answer.")
        t_answer = time.monotonic()

        answer = self._generate_answer(
            context, user_query, images=images if images else None
        )

        logger.info(
            "Answer generated in %.2fs.", time.monotonic() - t_answer
        )
        logger.info(
            "Full pipeline completed in %.2fs.", time.monotonic() - t_start
        )

        return {
            "answer": answer,
            "node_ids": node_ids,
            "reasoning": reasoning,
            "context": context,
            "image_count": len(images),
            "images": images,
        }

    # ── Internal helpers ──────────────────────────────────────────────────

    def _generate_answer(
        self,
        context: str,
        user_query: str,
        images: list[dict] | None = None,
    ) -> str:
        """Call the LLM to produce a grounded answer, optionally with images.

        When *images* is provided and non-empty, the answer is generated via
        :meth:`generate_multimodal` so the LLM can see the document images.
        Otherwise the regular text-only path is used.

        If the LLM call fails for any reason, returns a user-friendly
        fallback message rather than propagating the exception.
        """
        user_message = ANSWER_GENERATION_USER_TEMPLATE.format(
            context=context,
            query=user_query,
        )

        try:
            if images:
                # Build multimodal content blocks: text first, then images.
                content_blocks: list[dict] = [
                    {"type": "text", "text": user_message}
                ]
                for img in images:
                    content_blocks.append({
                        "type": "image",
                        "data": img["data"],
                        "media_type": img["media_type"],
                    })
                answer = self.llm.generate_multimodal(
                    system_prompt=ANSWER_GENERATION_SYSTEM_PROMPT,
                    content_blocks=content_blocks,
                    temperature=0.2,
                    max_tokens=4096,
                )
            else:
                answer = self.llm.generate(
                    system_prompt=ANSWER_GENERATION_SYSTEM_PROMPT,
                    user_message=user_message,
                    temperature=0.2,
                    max_tokens=4096,
                )
        except Exception as exc:
            logger.error("Answer generation failed: %s", exc, exc_info=True)
            return (
                "An error occurred while generating the answer. "
                "The relevant document sections were retrieved successfully -- "
                "please review the context directly or try again."
            )

        return answer.strip()
