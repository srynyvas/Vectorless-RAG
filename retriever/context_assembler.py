"""Assembles the retrieval context from selected tree nodes.

Given a set of node IDs chosen by the TreeSearcher, the ContextAssembler
extracts the full text from those nodes (and their children) and formats
it into a single string suitable for the LLM answer-generation step.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config.settings import settings

if TYPE_CHECKING:
    from indexer.node import TreeNode

logger = logging.getLogger(__name__)

_SECTION_SEPARATOR = "\n\n---\n\n"


class ContextAssembler:
    """Collects and formats section text for the answer-generation prompt.

    The assembler resolves node IDs to actual ``TreeNode`` objects, gathers
    their text (including child text recursively), and concatenates
    everything into a single context string while respecting a character
    budget.
    """

    def __init__(self, max_context_chars: int = 15_000) -> None:
        self.max_context_chars = max_context_chars

    # ── Public API ────────────────────────────────────────────────────────

    def assemble(self, tree: TreeNode, node_ids: list[str]) -> str:
        """Build a formatted context string from selected nodes.

        Args:
            tree:     The root ``TreeNode`` of the document index.
            node_ids: IDs of nodes selected by the tree searcher.

        Returns:
            A formatted string containing the section headers and full text
            of the selected nodes, separated by horizontal rules. Respects
            ``max_context_chars``; later sections are truncated or omitted
            if the budget is exceeded.
        """
        if not node_ids:
            logger.warning("No node IDs provided; returning empty context.")
            return ""

        selected_nodes = tree.find_nodes_by_ids(node_ids)

        if not selected_nodes:
            logger.warning(
                "None of the requested node IDs were found in the tree: %s",
                node_ids,
            )
            return ""

        logger.info(
            "Assembling context from %d node(s): %s",
            len(selected_nodes),
            [n.node_id for n in selected_nodes],
        )

        sections: list[str] = []
        total_chars = 0

        for node in selected_nodes:
            section_text = self._format_section(node)

            # Check whether adding this section would exceed the budget.
            addition_cost = len(section_text)
            if sections:
                addition_cost += len(_SECTION_SEPARATOR)

            if total_chars + addition_cost > self.max_context_chars:
                remaining = self.max_context_chars - total_chars
                if sections:
                    remaining -= len(_SECTION_SEPARATOR)

                if remaining > 200:
                    # Worth including a truncated version.
                    truncated = section_text[:remaining].rsplit(" ", 1)[0]
                    truncated += "\n\n[... section truncated due to length limit]"
                    sections.append(truncated)
                    logger.info(
                        "Truncated section '%s' to fit context budget.", node.title
                    )
                else:
                    logger.info(
                        "Skipping section '%s' -- context budget exhausted.",
                        node.title,
                    )
                break

            sections.append(section_text)
            total_chars += addition_cost

        context = _SECTION_SEPARATOR.join(sections)
        logger.info(
            "Assembled context: %d chars across %d section(s).",
            len(context),
            len(sections),
        )
        return context

    def assemble_multimodal(
        self,
        tree: "TreeNode",
        node_ids: list[str],
        max_images: int | None = None,
    ) -> tuple[str, list[dict]]:
        """Build context text AND collect images from selected nodes.

        Args:
            tree:       The root ``TreeNode`` of the document index.
            node_ids:   IDs of nodes selected by the tree searcher.
            max_images: Maximum number of images to include.  Defaults to
                        ``settings.MAX_CONTEXT_IMAGES``.

        Returns:
            A ``(context_text, images_list)`` tuple where *images_list* is a
            list of ``{"data": base64_str, "media_type": str, "caption": str}``
            dicts, capped at *max_images*.
        """
        if max_images is None:
            max_images = settings.MAX_CONTEXT_IMAGES

        context_text = self.assemble(tree, node_ids)

        # Collect images from the selected nodes.
        selected_nodes = tree.find_nodes_by_ids(node_ids)
        images: list[dict] = []
        for node in selected_nodes:
            images.extend(self._collect_images(node))
            if len(images) >= max_images:
                images = images[:max_images]
                break

        logger.info(
            "Multimodal assembly: %d chars of text, %d image(s).",
            len(context_text),
            len(images),
        )
        return context_text, images

    @staticmethod
    def _collect_images(node: "TreeNode") -> list[dict]:
        """Recursively collect images from a node and its children."""
        images = list(node.images)  # copy
        for child in node.children:
            images.extend(ContextAssembler._collect_images(child))
        return images

    # ── Internal helpers ──────────────────────────────────────────────────

    def _format_section(self, node: TreeNode) -> str:
        """Format a single node (and its descendants) into a readable block.

        The output looks like::

            ### Chapter 3: Security Architecture (Pages 45-62)

            <full text of node and children>
        """
        header = self._build_header(node)
        body = self._collect_text(node)

        if not body.strip():
            return f"{header}\n\n[No text content available for this section.]"

        return f"{header}\n\n{body}"

    @staticmethod
    def _build_header(node: TreeNode) -> str:
        """Construct a Markdown-style section header with page info."""
        header = f"### {node.title}"
        if node.start_page is not None and node.end_page is not None:
            if node.start_page == node.end_page:
                header += f" (Page {node.start_page})"
            else:
                header += f" (Pages {node.start_page}-{node.end_page})"
        return header

    @staticmethod
    def _collect_text(node: TreeNode) -> str:
        """Recursively gather text from a node and all its children.

        Text is collected depth-first so that the natural reading order
        (parent first, then children in order) is preserved.
        """
        parts: list[str] = []

        if node.text and node.text.strip():
            parts.append(node.text.strip())

        for child in node.children:
            child_text = ContextAssembler._collect_text(child)
            if child_text:
                parts.append(child_text)

        return "\n\n".join(parts)
