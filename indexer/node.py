from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class TreeNode:
    """A node in the hierarchical document index tree.

    Each node represents a section of a document (chapter, sub-section, etc.)
    and stores its title, summary, page range, full text, and child nodes.

    Node IDs follow a dot-separated numbering scheme:
        "root" -> top-level document node
        "1"    -> first chapter
        "1.1"  -> first section of first chapter
        "1.2.3" -> third sub-sub-section of second section of first chapter
    """

    node_id: str                          # "root", "1", "1.1", "1.2.3"
    title: str
    summary: str = ""
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    level: int = 0
    text: str = ""
    images: list[dict] = field(default_factory=list)
    children: list[TreeNode] = field(default_factory=list)

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Full serialization including text."""
        d = {
            "node_id": self.node_id,
            "title": self.title,
            "summary": self.summary,
            "level": self.level,
        }
        if self.start_page is not None:
            d["start_page"] = self.start_page
            d["end_page"] = self.end_page
        if self.text:
            d["text"] = self.text
        if self.images:
            d["images"] = self.images
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> TreeNode:
        """Reconstruct a TreeNode from a dictionary (for loading cached indices)."""
        children = [cls.from_dict(c) for c in d.get("children", [])]
        return cls(
            node_id=d["node_id"],
            title=d["title"],
            summary=d.get("summary", ""),
            start_page=d.get("start_page"),
            end_page=d.get("end_page"),
            level=d.get("level", 0),
            text=d.get("text", ""),
            images=d.get("images", []),
            children=children,
        )

    def to_search_dict(self) -> dict:
        """Lightweight version for LLM search -- NO full text, just metadata."""
        d = {
            "node_id": self.node_id,
            "title": self.title,
            "summary": self.summary,
        }
        if self.start_page is not None:
            d["pages"] = f"{self.start_page}-{self.end_page}"
        if self.children:
            d["children"] = [c.to_search_dict() for c in self.children]
        return d

    def to_json(self, include_text: bool = True) -> str:
        """Serialize to a formatted JSON string.

        Args:
            include_text: If True, include full text in the output.
                          If False, produce the lightweight search-only format.
        """
        if include_text:
            return json.dumps(self.to_dict(), indent=2)
        return json.dumps(self.to_search_dict(), indent=2)

    # ── Traversal helpers ────────────────────────────────────────────

    def find_nodes_by_ids(self, node_ids: list[str]) -> list[TreeNode]:
        """Return the list of nodes whose ``node_id`` is in *node_ids*.

        Performs a depth-first search through the entire subtree rooted at
        this node.
        """
        results: list[TreeNode] = []
        if self.node_id in node_ids:
            results.append(self)
        for child in self.children:
            results.extend(child.find_nodes_by_ids(node_ids))
        return results

    def has_images(self) -> bool:
        """Return True if this node or any descendant has images."""
        if self.images:
            return True
        return any(child.has_images() for child in self.children)

    def all_nodes_flat(self) -> list[TreeNode]:
        """Return a flat list of every node in the subtree (including self)."""
        nodes: list[TreeNode] = [self]
        for child in self.children:
            nodes.extend(child.all_nodes_flat())
        return nodes
