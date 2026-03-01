"""LLM-guided tree search for identifying relevant document sections.

The TreeSearcher sends the lightweight (no full text) tree index and the
user's query to an LLM, which reasons over the hierarchical structure and
returns the node IDs most likely to contain relevant content.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from retriever.prompts import TREE_SEARCH_SYSTEM_PROMPT, TREE_SEARCH_USER_TEMPLATE

if TYPE_CHECKING:
    from indexer.node import TreeNode
    from llm.base import LLMProvider

logger = logging.getLogger(__name__)

# Regex for dotted node IDs such as "1", "1.2", "1.2.3", or "root".
_NODE_ID_PATTERN = re.compile(r"\b(root|\d+(?:\.\d+)*)\b")


class TreeSearcher:
    """Selects relevant document sections by asking the LLM to reason over
    the hierarchical index.

    The full section text is deliberately excluded from the search payload so
    that the LLM focuses on the structural metadata (titles, summaries, page
    ranges) and the token budget stays small regardless of document size.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    # ── Public API ────────────────────────────────────────────────────────

    def search(self, tree: TreeNode, query: str) -> tuple[list[str], str]:
        """Identify relevant node IDs for a query using the LLM.

        Args:
            tree:  The root ``TreeNode`` of the document index.
            query: The user's natural-language question.

        Returns:
            A tuple of (node_ids, reasoning) where *node_ids* is a list of
            1-5 dot-notation node ID strings and *reasoning* is the LLM's
            brief explanation for why those sections were selected.
        """
        # Build the lightweight tree JSON (titles + summaries, no full text).
        tree_json = tree.to_json(include_text=False)

        user_message = TREE_SEARCH_USER_TEMPLATE.format(
            tree_json=tree_json,
            query=query,
        )

        # Primary path: structured JSON response from the LLM.
        node_ids, reasoning = self._try_json_search(user_message)

        if node_ids:
            logger.info(
                "Tree search selected %d node(s): %s", len(node_ids), node_ids
            )
            return node_ids, reasoning

        # Fallback: ask for raw text and extract node IDs via regex.
        logger.warning(
            "JSON parsing failed; falling back to regex extraction."
        )
        node_ids, reasoning = self._fallback_regex_search(user_message, tree)

        if node_ids:
            logger.info(
                "Regex fallback selected %d node(s): %s", len(node_ids), node_ids
            )
        else:
            logger.warning("Tree search returned no node IDs for query: %s", query)

        return node_ids, reasoning

    # ── Internal helpers ──────────────────────────────────────────────────

    def _try_json_search(self, user_message: str) -> tuple[list[str], str]:
        """Attempt to get a structured JSON response from the LLM.

        Returns:
            (node_ids, reasoning) on success, or ([], "") if parsing fails.
        """
        try:
            result = self.llm.generate_json(
                system_prompt=TREE_SEARCH_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.1,
                max_tokens=1024,
            )
        except (ValueError, Exception) as exc:
            logger.debug("generate_json raised %s: %s", type(exc).__name__, exc)
            return [], ""

        node_ids = result.get("node_ids", [])
        reasoning = result.get("reasoning", "")

        # Validate: node_ids must be a list of strings.
        if not isinstance(node_ids, list):
            logger.debug("node_ids is not a list: %r", node_ids)
            return [], ""

        node_ids = [str(nid) for nid in node_ids if nid]

        # Enforce the 1-5 node cap.
        if len(node_ids) > 5:
            logger.debug("Trimming node_ids from %d to 5.", len(node_ids))
            node_ids = node_ids[:5]

        return node_ids, str(reasoning)

    def _fallback_regex_search(
        self, user_message: str, tree: TreeNode
    ) -> tuple[list[str], str]:
        """Fall back to raw text generation and regex-extract node IDs.

        To avoid hallucinated IDs, only IDs that actually exist in the tree
        are kept.

        Returns:
            (node_ids, reasoning) -- reasoning is the full raw LLM text.
        """
        try:
            raw_text = self.llm.generate(
                system_prompt=TREE_SEARCH_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception as exc:
            logger.error("Fallback generate also failed: %s", exc)
            return [], ""

        # Extract all candidate node IDs from the raw text.
        candidates = _NODE_ID_PATTERN.findall(raw_text)

        # Build a set of valid IDs that actually exist in the tree so we
        # don't pass hallucinated IDs downstream.
        valid_ids = {node.node_id for node in tree.all_nodes_flat()}

        seen: set[str] = set()
        node_ids: list[str] = []
        for candidate in candidates:
            if candidate in valid_ids and candidate not in seen:
                seen.add(candidate)
                node_ids.append(candidate)
            if len(node_ids) >= 5:
                break

        return node_ids, raw_text
