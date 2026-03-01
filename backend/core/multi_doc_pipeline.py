"""Multi-document RAG pipeline: routes to relevant docs, runs per-doc RAG, merges.

Flow:
1. DocumentRouter selects 1-3 relevant documents from workspace
2. RAGPipeline.query() on each selected document
3. If single doc selected: return its answer directly
4. If multiple docs: merge answers with a final LLM call citing document names
"""

from __future__ import annotations
import logging
from indexer.node import TreeNode
from llm.base import LLMProvider
from retriever.pipeline import RAGPipeline
from backend.core.document_router import DocumentRouter

logger = logging.getLogger(__name__)

MERGE_SYSTEM_PROMPT = """\
You are a knowledgeable assistant. You have been given answers from multiple \
documents in response to a user's question. Your job is to synthesize these \
into a single coherent answer.

Rules:
1. Combine information from all provided answers into one clear response.
2. Cite which document each piece of information comes from using \
   (Document: "filename") format.
3. Remove redundant information — don't repeat the same fact from multiple docs.
4. If documents provide contradictory information, note the discrepancy.
5. Maintain the depth and detail of the original answers.
6. If all documents say the information is not available, say so clearly."""

MERGE_USER_TEMPLATE = """\
## User's Question
{query}

## Answers from Individual Documents

{per_doc_answers}

---

Synthesize these into a single coherent answer. Cite document names when \
referencing specific information."""


class MultiDocPipeline:
    """Orchestrates multi-document RAG with routing and answer merging."""

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm
        self.router = DocumentRouter(llm)
        self.pipeline = RAGPipeline(llm)

    def query(
        self,
        doc_records: list[dict],
        trees: dict[int, TreeNode],
        user_query: str,
    ) -> dict:
        """Run multi-document RAG pipeline.

        Parameters
        ----------
        doc_records:
            List of dicts with keys: "id", "file_name", "doc_title",
            "root_summary". One per document in the workspace.
        trees:
            Mapping of document ID -> TreeNode root.
        user_query:
            The user's question.

        Returns
        -------
        dict with keys:
            answer, per_doc_results, routed_doc_ids, routing_reasoning
        """
        # Build summaries for router
        doc_summaries = [
            {
                "id": d["id"],
                "title": d.get("doc_title") or d["file_name"],
                "summary": d.get("root_summary", ""),
                "file_name": d["file_name"],
            }
            for d in doc_records
        ]

        # Stage 0: Route to relevant documents
        logger.info("Multi-doc routing for query: %s", user_query[:100])
        routed_ids, routing_reasoning = self.router.route(doc_summaries, user_query)
        logger.info("Router selected doc IDs: %s — %s", routed_ids, routing_reasoning)

        # Stage 1-3: Run RAG on each selected document
        per_doc_results = []
        for doc_id in routed_ids:
            if doc_id not in trees:
                logger.warning("Tree not found for doc_id=%d, skipping.", doc_id)
                continue

            tree = trees[doc_id]
            # Find the doc record for this ID
            doc_info = next((d for d in doc_records if d["id"] == doc_id), {})
            file_name = doc_info.get("file_name", f"Document {doc_id}")

            try:
                result = self.pipeline.query(tree, user_query)
                per_doc_results.append({
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "answer": result.get("answer", ""),
                    "node_ids": result.get("node_ids", []),
                    "reasoning": result.get("reasoning", ""),
                    "context": result.get("context", ""),
                })
            except Exception as exc:
                logger.error("RAG failed for doc %d (%s): %s", doc_id, file_name, exc)
                per_doc_results.append({
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "answer": f"Error processing this document: {exc}",
                    "node_ids": [],
                    "reasoning": "",
                    "context": "",
                })

        if not per_doc_results:
            return {
                "answer": "No relevant documents could be processed for your question.",
                "per_doc_results": [],
                "routed_doc_ids": routed_ids,
                "routing_reasoning": routing_reasoning,
            }

        # If only one doc had results, return directly
        useful_results = [r for r in per_doc_results if r["node_ids"]]
        if len(useful_results) == 1:
            return {
                "answer": useful_results[0]["answer"],
                "per_doc_results": per_doc_results,
                "routed_doc_ids": routed_ids,
                "routing_reasoning": routing_reasoning,
            }

        # If no docs had useful results, combine error messages
        if not useful_results:
            combined = "\n\n".join(
                f"**{r['file_name']}**: {r['answer']}" for r in per_doc_results
            )
            return {
                "answer": combined,
                "per_doc_results": per_doc_results,
                "routed_doc_ids": routed_ids,
                "routing_reasoning": routing_reasoning,
            }

        # Multiple docs with results — merge with LLM
        merged_answer = self._merge_answers(per_doc_results, user_query)
        return {
            "answer": merged_answer,
            "per_doc_results": per_doc_results,
            "routed_doc_ids": routed_ids,
            "routing_reasoning": routing_reasoning,
        }

    def _merge_answers(self, per_doc_results: list[dict], query: str) -> str:
        """Merge answers from multiple documents using the LLM."""
        per_doc_text = ""
        for r in per_doc_results:
            per_doc_text += f"### Document: {r['file_name']}\n{r['answer']}\n\n"

        user_message = MERGE_USER_TEMPLATE.format(
            query=query,
            per_doc_answers=per_doc_text.strip(),
        )

        try:
            merged = self.llm.generate(
                system_prompt=MERGE_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.2,
                max_tokens=4096,
            )
            return merged.strip()
        except Exception as exc:
            logger.error("Answer merging failed: %s", exc)
            # Fallback: concatenate with headers
            parts = []
            for r in per_doc_results:
                if r["answer"]:
                    parts.append(f"## From: {r['file_name']}\n\n{r['answer']}")
            return "\n\n---\n\n".join(parts)
