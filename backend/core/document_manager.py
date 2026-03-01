"""Non-Streamlit document processing logic.

Extracts file hashing, tree caching, and parse-and-index functionality
from the Streamlit sidebar into a reusable module that can be called by
both the Streamlit UI and the FastAPI backend.

All functions are synchronous and do not depend on ``streamlit`` or any
UI framework.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from config.settings import settings
from indexer.node import TreeNode
from indexer.tree_builder import TreeBuilder
from llm.factory import get_llm_provider
from parsers.registry import get_parser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# File hashing
# ---------------------------------------------------------------------------

def compute_file_hash(content: bytes) -> str:
    """Return the MD5 hex digest for the given file content.

    Parameters
    ----------
    content:
        Raw bytes of the file.

    Returns
    -------
    str
        32-character lowercase hex string.
    """
    return hashlib.md5(content).hexdigest()


# ---------------------------------------------------------------------------
# Cache path helpers
# ---------------------------------------------------------------------------

def cache_path(username: str, file_hash: str) -> Path:
    """Return the expected JSON cache path for a given user and file hash.

    The directory layout is::

        {INDEX_DIR}/{username}/{file_hash}.json

    Parameters
    ----------
    username:
        Owner username used as a namespace directory.
    file_hash:
        MD5 hex digest of the original file content.

    Returns
    -------
    Path
        Absolute path to the JSON cache file (may or may not exist yet).
    """
    return Path(settings.INDEX_DIR) / username / f"{file_hash}.json"


# ---------------------------------------------------------------------------
# Cache load / save / delete
# ---------------------------------------------------------------------------

def load_cached_tree(username: str, file_hash: str) -> TreeNode | None:
    """Load a cached tree from disk if it exists, otherwise return ``None``.

    If the cached JSON is corrupt, the file is deleted and ``None`` is
    returned so that the caller can rebuild the index.

    Parameters
    ----------
    username:
        Owner username (cache namespace).
    file_hash:
        MD5 hex digest of the original file content.

    Returns
    -------
    TreeNode | None
        The reconstructed tree, or ``None`` if no valid cache exists.
    """
    path = cache_path(username, file_hash)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return TreeNode.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Cached index is corrupted and will be rebuilt: %s", exc)
        path.unlink(missing_ok=True)
    return None


def save_cached_tree(username: str, file_hash: str, tree: TreeNode) -> None:
    """Persist a tree to the JSON cache on disk.

    Creates the parent directories if they do not exist.

    Parameters
    ----------
    username:
        Owner username (cache namespace).
    file_hash:
        MD5 hex digest of the original file content.
    tree:
        The fully-built document tree to serialize.
    """
    path = cache_path(username, file_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tree.to_json(include_text=True), encoding="utf-8")
    logger.info("Saved cached tree to %s", path)


def delete_cached_tree(username: str, file_hash: str) -> bool:
    """Remove the cached tree file from disk.

    Parameters
    ----------
    username:
        Owner username (cache namespace).
    file_hash:
        MD5 hex digest of the original file content.

    Returns
    -------
    bool
        ``True`` if the file existed and was deleted, ``False`` otherwise.
    """
    path = cache_path(username, file_hash)
    if path.exists():
        path.unlink()
        logger.info("Deleted cached tree at %s", path)
        return True
    return False


# ---------------------------------------------------------------------------
# Parse and index
# ---------------------------------------------------------------------------

def _add_quick_summaries(tree: TreeNode) -> None:
    """Fill in short summaries (first 100 chars of text) for every node in-place."""
    for node in tree.all_nodes_flat():
        if not node.summary and node.text:
            snippet = node.text[:100].replace("\n", " ").strip()
            node.summary = snippet + ("..." if len(node.text) > 100 else "")


def parse_and_index(
    file_path: str,
    file_name: str,
    username: str,
    quick_index: bool = False,
    extract_images: bool = True,
) -> tuple[TreeNode, dict]:
    """Parse a file and build a hierarchical index tree.

    This is the main entry point for document processing.  It determines
    the correct parser from the file extension, parses the document into
    flat sections, and then builds a tree -- optionally generating LLM
    summaries for each node.

    Parameters
    ----------
    file_path:
        Path to the file on disk (typically a temporary upload).
    file_name:
        Original file name (used to derive the extension and doc title).
    username:
        Owner username (used for cache namespace if needed by caller).
    quick_index:
        If ``True``, skip LLM summarisation and instead use the first
        100 characters of each node's text as a quick summary.
    extract_images:
        If ``True``, include extracted images in parsing. Currently
        passed through for future parser configuration.

    Returns
    -------
    tuple[TreeNode, dict]
        A 2-tuple of:

        - **tree** -- the fully-built ``TreeNode`` hierarchy.
        - **metadata** -- a dict with keys ``doc_title``,
          ``root_summary``, ``node_count``, ``image_count``,
          ``page_count``.

    Raises
    ------
    ValueError
        If the file extension is unsupported or the parser returns no
        sections.
    """
    # Determine extension and doc title from file name
    ext = os.path.splitext(file_name)[1].lower()
    doc_title = os.path.splitext(file_name)[0]

    # Parse
    parser = get_parser(ext)
    sections = parser.parse(file_path)

    if not sections:
        raise ValueError(
            "The parser returned no sections. The file may be empty or unsupported."
        )

    # Build tree
    if quick_index:
        builder = TreeBuilder(llm_provider=None)
        tree = builder.build_tree(sections, doc_title)
        _add_quick_summaries(tree)
    else:
        llm = get_llm_provider()
        builder = TreeBuilder(llm)
        tree = builder.build_tree_with_summaries(sections, doc_title)

    # Extract metadata from the tree
    all_nodes = tree.all_nodes_flat()
    node_count = len(all_nodes)
    image_count = sum(len(n.images) for n in all_nodes)

    pages_with_values = [n.end_page for n in all_nodes if n.end_page is not None]
    page_count = max(pages_with_values) if pages_with_values else 0

    metadata = {
        "doc_title": doc_title,
        "root_summary": tree.summary or "",
        "node_count": node_count,
        "image_count": image_count,
        "page_count": page_count,
    }

    return tree, metadata
