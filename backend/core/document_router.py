"""LLM-based document router for multi-document workspaces.

When a workspace has multiple documents, the router examines each
document's title and root summary to determine which documents are
most likely to contain the answer. This avoids running the full
RAG pipeline on every document.
"""

from __future__ import annotations
import json
import logging
import re
from llm.base import LLMProvider

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """\
You are a document routing specialist. Given a list of documents with their \
titles and summaries, select the 1-3 documents most likely to contain \
information relevant to the user's question.

## Output format
Return ONLY a JSON object with exactly two keys:
{
  "doc_ids": [1, 3],
  "reasoning": "Brief explanation of why these documents were selected."
}

Do NOT include any text outside the JSON object. Do NOT wrap in markdown \
code fences."""

ROUTER_USER_TEMPLATE = """\
## Available Documents

{doc_summaries_json}

## Question

{query}

Select the 1-3 most relevant documents. Return JSON with "doc_ids" (list of \
document ID integers) and "reasoning"."""


class DocumentRouter:
    """Selects relevant documents from a workspace for a given query."""

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    def route(
        self,
        doc_summaries: list[dict],
        query: str,
    ) -> tuple[list[int], str]:
        """Select 1-3 relevant documents for a query.

        Parameters
        ----------
        doc_summaries:
            List of dicts with keys: "id", "title", "summary", "file_name"
        query:
            The user's question.

        Returns
        -------
        tuple[list[int], str]
            (doc_ids, reasoning) — doc_ids are the database IDs of selected docs.
        """
        if len(doc_summaries) <= 1:
            # Only one document — always select it
            return [d["id"] for d in doc_summaries], "Single document in workspace."

        summaries_json = json.dumps(doc_summaries, indent=2)
        user_message = ROUTER_USER_TEMPLATE.format(
            doc_summaries_json=summaries_json,
            query=query,
        )

        # Try structured JSON first
        try:
            result = self.llm.generate_json(
                system_prompt=ROUTER_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.1,
                max_tokens=512,
            )
            doc_ids = result.get("doc_ids", [])
            reasoning = result.get("reasoning", "")

            if isinstance(doc_ids, list) and doc_ids:
                # Validate IDs exist in our list
                valid_ids = {d["id"] for d in doc_summaries}
                doc_ids = [int(did) for did in doc_ids if int(did) in valid_ids]
                if doc_ids:
                    return doc_ids[:3], str(reasoning)
        except Exception:
            logger.warning("Document router JSON parsing failed; using fallback.")

        # Fallback: try raw text and extract integers
        try:
            raw = self.llm.generate(
                system_prompt=ROUTER_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.1,
                max_tokens=512,
            )
            valid_ids = {d["id"] for d in doc_summaries}
            found = re.findall(r'\b(\d+)\b', raw)
            doc_ids = [int(x) for x in found if int(x) in valid_ids]
            if doc_ids:
                return doc_ids[:3], raw
        except Exception:
            logger.error("Document router fallback also failed.")

        # Ultimate fallback: return all documents (up to 3)
        return [d["id"] for d in doc_summaries[:3]], "Fallback: all documents selected."
