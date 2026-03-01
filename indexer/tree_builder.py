"""Convert a flat list of ParsedSection objects into a hierarchical TreeNode tree.

The primary entry points are :meth:`TreeBuilder.build_tree` (structure only)
and :meth:`TreeBuilder.build_tree_with_summaries` (structure + LLM-generated
summaries for every node).

All public methods are **synchronous**.
"""

from __future__ import annotations

import logging
from typing import Optional

from config.settings import settings
from indexer.node import TreeNode
from llm.base import LLMProvider
from llm.factory import get_llm_provider
from parsers.base import ParsedSection

logger = logging.getLogger(__name__)

# Maximum number of characters sent to the LLM for a single summarisation
# call.  Keeps token usage bounded even when sections are very long.
_MAX_INPUT_CHARS = 2000


class TreeBuilder:
    """Builds a hierarchical :class:`TreeNode` tree from parsed document sections.

    Parameters
    ----------
    llm_provider:
        An optional :class:`LLMProvider` instance.  When *None* **and** a
        summary-generating method is called, the default provider is resolved
        via :func:`get_llm_provider`.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None) -> None:
        self._llm: Optional[LLMProvider] = llm_provider

    # ------------------------------------------------------------------
    # Lazy LLM accessor
    # ------------------------------------------------------------------

    @property
    def llm(self) -> LLMProvider:
        """Return the LLM provider, creating one on first access."""
        if self._llm is None:
            self._llm = get_llm_provider()
        return self._llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_tree(
        self,
        sections: list[ParsedSection],
        doc_title: str = "Document",
    ) -> TreeNode:
        """Convert a flat section list into a tree rooted at a synthetic root node.

        The algorithm uses an explicit stack so that each section becomes a
        child of the most recent section whose heading level is strictly
        *lower* (i.e. a higher-level heading).

        Node IDs follow dotted notation relative to their parent:
        ``"1"``, ``"1.1"``, ``"1.2"``, ``"2"``, ``"2.1.1"``, etc.

        Parameters
        ----------
        sections:
            Flat, document-order list of sections produced by a parser.
        doc_title:
            Human-readable title used for the synthetic root node.

        Returns
        -------
        TreeNode
            The root of the constructed tree with page ranges propagated.
        """
        root = TreeNode(
            node_id="root",
            title=doc_title,
            level=0,
        )

        if not sections:
            return root

        # Stack of (TreeNode, heading_level) pairs.  The root is always at
        # the bottom so every real section has a parent.
        stack: list[tuple[TreeNode, int]] = [(root, 0)]

        for section in sections:
            current_level = section.level

            # Pop until we find a node whose level is strictly less than the
            # current section (i.e. a proper ancestor).
            while len(stack) > 1 and stack[-1][1] >= current_level:
                stack.pop()

            parent_node, _ = stack[-1]

            # Build a dotted node ID based on sibling count under the parent.
            child_index = len(parent_node.children) + 1
            if parent_node.node_id == "root":
                node_id = str(child_index)
            else:
                node_id = f"{parent_node.node_id}.{child_index}"

            child = TreeNode(
                node_id=node_id,
                title=section.title,
                level=section.level,
                text=section.text,
                images=section.images,
                start_page=section.page_number,
                end_page=section.page_number,
            )

            parent_node.children.append(child)
            stack.append((child, current_level))

        # Propagate page ranges so that every parent spans all its children.
        self._fix_page_ranges(root)

        return root

    def build_tree_with_summaries(
        self,
        sections: list[ParsedSection],
        doc_title: str = "Document",
    ) -> TreeNode:
        """Build the tree **and** populate every node with an LLM summary.

        Summaries are generated bottom-up so that parent summaries can be
        synthesised from their children's summaries rather than from raw text.

        Parameters
        ----------
        sections:
            Flat, document-order list of sections produced by a parser.
        doc_title:
            Human-readable title used for the synthetic root node.

        Returns
        -------
        TreeNode
            The fully-summarised tree.
        """
        root = self.build_tree(sections, doc_title=doc_title)
        self._generate_summaries(root)
        return root

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fix_page_ranges(self, node: TreeNode) -> None:
        """Recursively propagate page ranges upward.

        After this pass every parent node's ``start_page`` / ``end_page``
        spans the full range of its descendants.
        """
        if not node.children:
            return

        for child in node.children:
            self._fix_page_ranges(child)

        child_starts = [
            c.start_page for c in node.children if c.start_page is not None
        ]
        child_ends = [
            c.end_page for c in node.children if c.end_page is not None
        ]

        if child_starts:
            min_start = min(child_starts)
            if node.start_page is None:
                node.start_page = min_start
            else:
                node.start_page = min(node.start_page, min_start)

        if child_ends:
            max_end = max(child_ends)
            if node.end_page is None:
                node.end_page = max_end
            else:
                node.end_page = max(node.end_page, max_end)

    def _generate_summaries(self, node: TreeNode) -> None:
        """Recursively generate summaries for *node* and all descendants.

        Children are processed **first** (bottom-up) so that parent summaries
        can incorporate the already-generated child summaries.
        """
        # Recurse into children first (bottom-up ordering).
        for child in node.children:
            self._generate_summaries(child)

        if node.children:
            # Parent node: synthesise from children's summaries.
            children_text = "\n".join(
                f"- {child.title}: {child.summary}" for child in node.children
            )
            node.summary = self._summarize_text(
                title=node.title,
                text=f"This section contains the following sub-sections:\n{children_text}",
            )
            logger.debug("Generated parent summary for node %s", node.node_id)
        elif node.text:
            # Leaf node with body text -- use image-aware summary if available.
            if node.images:
                node.summary = self._summarize_with_images(
                    title=node.title,
                    text=node.text,
                    images=node.images[:3],  # limit images for summary
                )
            else:
                node.summary = self._summarize_text(
                    title=node.title,
                    text=node.text,
                )
            logger.debug("Generated leaf summary for node %s", node.node_id)
        else:
            # Leaf with no text -- nothing useful to summarise.
            node.summary = ""

    def _summarize_text(self, title: str, text: str) -> str:
        """Ask the LLM for a concise 1--2 sentence summary.

        The input *text* is truncated to :data:`_MAX_INPUT_CHARS` to keep
        token usage predictable.

        Parameters
        ----------
        title:
            Section title -- provides context for the LLM.
        text:
            Body text or aggregated child summaries.

        Returns
        -------
        str
            A short summary string, or an empty string if generation fails.
        """
        max_words = settings.INDEX_SUMMARY_MAX_WORDS
        truncated = text[:_MAX_INPUT_CHARS]

        system_prompt = (
            "You are a precise document summarizer. "
            f"Produce a concise summary of no more than {max_words} words. "
            "Output ONLY the summary text with no preamble or extra formatting."
        )
        user_message = (
            f"Section title: {title}\n\n"
            f"Content:\n{truncated}"
        )

        try:
            summary = self.llm.generate(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.1,
                max_tokens=256,
            )
            return summary.strip()
        except Exception:
            logger.exception(
                "LLM summarisation failed for section '%s'", title
            )
            return ""

    def _summarize_with_images(
        self, title: str, text: str, images: list[dict]
    ) -> str:
        """Ask the LLM for a summary that accounts for both text and images.

        Uses :meth:`generate_multimodal` to send the text together with a
        small number of images so the summary can reference visual content
        (charts, diagrams, tables, etc.).

        Falls back to text-only summarisation if the multimodal call fails.

        Parameters
        ----------
        title:
            Section title -- provides context for the LLM.
        text:
            Body text of the section.
        images:
            A list of image dicts (each with ``data``, ``media_type``,
            ``caption`` keys).  Should already be limited to 2-3 items.

        Returns
        -------
        str
            A short summary string, or an empty string if generation fails.
        """
        max_words = settings.INDEX_SUMMARY_MAX_WORDS
        truncated = text[:_MAX_INPUT_CHARS]

        system_prompt = (
            "You are a precise document summarizer. "
            f"Produce a concise summary of no more than {max_words} words. "
            "If images are provided, incorporate key visual information "
            "(charts, diagrams, tables) into the summary. "
            "Output ONLY the summary text with no preamble or extra formatting."
        )

        user_text = (
            f"Section title: {title}\n\n"
            f"Content:\n{truncated}"
        )

        # Build multimodal content blocks: text first, then images.
        content_blocks: list[dict] = [{"type": "text", "text": user_text}]
        for img in images:
            content_blocks.append({
                "type": "image",
                "data": img["data"],
                "media_type": img["media_type"],
            })

        try:
            summary = self.llm.generate_multimodal(
                system_prompt=system_prompt,
                content_blocks=content_blocks,
                temperature=0.1,
                max_tokens=256,
            )
            return summary.strip()
        except Exception:
            logger.warning(
                "Multimodal summarisation failed for section '%s'; "
                "falling back to text-only.",
                title,
            )
            # Fall back to text-only summarisation.
            return self._summarize_text(title=title, text=text)
