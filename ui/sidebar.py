"""Sidebar component: LLM provider selection, file upload, indexing, and doc info."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import streamlit as st

from config.settings import settings
from indexer.node import TreeNode
from llm.factory import get_llm_provider
from parsers.registry import get_parser, supported_extensions
from ui.theme import metric_card, status_badge, section_header


def _compute_file_hash(content: bytes) -> str:
    """Return the MD5 hex digest for the uploaded file content."""
    return hashlib.md5(content).hexdigest()


def _cache_path(file_hash: str) -> Path:
    """Return the expected JSON cache path for a given file hash."""
    return Path(settings.INDEX_DIR) / f"{file_hash}.json"


def _load_cached_tree(file_hash: str) -> TreeNode | None:
    """Load a cached tree from INDEX_DIR if it exists, otherwise return None."""
    path = _cache_path(file_hash)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return TreeNode.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            st.warning(f"Cached index is corrupted and will be rebuilt: {exc}")
            path.unlink(missing_ok=True)
    return None


def _save_cached_tree(file_hash: str, tree: TreeNode) -> None:
    """Persist a tree to the JSON cache."""
    cache_dir = Path(settings.INDEX_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    _cache_path(file_hash).write_text(tree.to_json(include_text=True), encoding="utf-8")


def _add_quick_summaries(tree: TreeNode) -> None:
    """Fill in short summaries (first 100 chars of text) for every node in-place."""
    for node in tree.all_nodes_flat():
        if not node.summary and node.text:
            snippet = node.text[:100].replace("\n", " ").strip()
            node.summary = snippet + ("..." if len(node.text) > 100 else "")


def _parse_and_build_tree(
    uploaded_file,
    file_hash: str,
    provider_name: str,
    quick_index: bool,
) -> TreeNode:
    """Parse the uploaded file and build the hierarchical index tree.

    Saves the uploaded bytes to a temp file, invokes the appropriate parser,
    then builds the tree (with or without LLM summaries based on the toggle).
    """
    # Determine file extension
    file_name: str = uploaded_file.name
    ext = os.path.splitext(file_name)[1].lower()

    # Save to temp file so parsers can read from disk
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = upload_dir / f"{file_hash}{ext}"
    tmp_path.write_bytes(uploaded_file.getvalue())

    try:
        # Parse
        parser = get_parser(ext)
        sections = parser.parse(str(tmp_path))

        if not sections:
            raise ValueError("The parser returned no sections. The file may be empty or unsupported.")

        # Build tree
        from indexer.tree_builder import TreeBuilder

        doc_title = os.path.splitext(file_name)[0]

        if quick_index:
            # Quick index: no LLM needed -- just build structure + text snippets
            builder = TreeBuilder(llm_provider=None)
            tree = builder.build_tree(sections, doc_title)
            _add_quick_summaries(tree)
        else:
            # Full index: LLM generates summaries for each node
            llm = get_llm_provider(provider_name)
            builder = TreeBuilder(llm)
            tree = builder.build_tree_with_summaries(sections, doc_title)

        return tree
    finally:
        # Clean up the temp file
        tmp_path.unlink(missing_ok=True)


def render_sidebar() -> None:
    """Render the full sidebar: provider selector, uploader, toggles, and doc info."""

    with st.sidebar:
        # ── Section header ────────────────────────────────────────────
        st.markdown(section_header("Settings"), unsafe_allow_html=True)

        # ── LLM provider selector ────────────────────────────────────
        provider_options = ["anthropic", "openai"]
        default_idx = (
            provider_options.index(settings.LLM_PROVIDER)
            if settings.LLM_PROVIDER in provider_options
            else 0
        )
        provider = st.selectbox(
            "LLM Provider",
            options=provider_options,
            index=default_idx,
            key="llm_provider",
        )

        # ── API key status indicators ─────────────────────────────────
        anthropic_key_set = bool(settings.ANTHROPIC_API_KEY)
        openai_key_set = bool(settings.OPENAI_API_KEY)

        key_cols = st.columns(2)
        with key_cols[0]:
            if anthropic_key_set:
                st.markdown(
                    status_badge("Anthropic \u2713", "success"),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    status_badge("Anthropic \u2717", "warning"),
                    unsafe_allow_html=True,
                )
        with key_cols[1]:
            if openai_key_set:
                st.markdown(
                    status_badge("OpenAI \u2713", "success"),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    status_badge("OpenAI \u2717", "warning"),
                    unsafe_allow_html=True,
                )

        st.divider()

        # ── Toggles ──────────────────────────────────────────────────
        st.toggle(
            "Quick index (skip LLM summaries)",
            value=False,
            key="quick_index",
        )
        st.toggle(
            "Show retrieval details",
            value=False,
            key="show_retrieval_details",
        )
        st.toggle(
            "Extract images",
            value=True,
            key="extract_images",
        )

        st.divider()

        # ── File uploader ─────────────────────────────────────────────
        allowed_exts = ["pdf", "md", "markdown", "docx", "pptx", "txt"]
        uploaded_file = st.file_uploader(
            "Upload a document",
            type=allowed_exts,
            key="file_uploader",
        )

        if uploaded_file is not None:
            file_content = uploaded_file.getvalue()
            file_hash = _compute_file_hash(file_content)

            # Detect whether this is a *new* upload (different from current doc)
            is_new = st.session_state.get("_current_file_hash") != file_hash

            if is_new:
                with st.status("Processing document...", expanded=True) as status:
                    try:
                        # Try cache first
                        tree = _load_cached_tree(file_hash)
                        if tree is not None:
                            status.update(label="Loaded from cache!", state="complete")
                            st.toast("Loaded from cache.", icon="\u2705")
                        else:
                            st.write("Parsing document...")
                            # We need to parse and build -- use multi-step progress
                            file_name: str = uploaded_file.name
                            ext = os.path.splitext(file_name)[1].lower()

                            # Save to temp file
                            upload_dir = Path(settings.UPLOAD_DIR)
                            upload_dir.mkdir(parents=True, exist_ok=True)
                            tmp_path = upload_dir / f"{file_hash}{ext}"
                            tmp_path.write_bytes(uploaded_file.getvalue())

                            try:
                                parser = get_parser(ext)
                                sections = parser.parse(str(tmp_path))

                                if not sections:
                                    raise ValueError(
                                        "The parser returned no sections. "
                                        "The file may be empty or unsupported."
                                    )

                                st.write("Building tree structure...")
                                from indexer.tree_builder import TreeBuilder

                                doc_title = os.path.splitext(file_name)[0]
                                quick_index = st.session_state.get("quick_index", False)

                                if quick_index:
                                    builder = TreeBuilder(llm_provider=None)
                                    tree = builder.build_tree(sections, doc_title)
                                    _add_quick_summaries(tree)
                                else:
                                    st.write("Generating AI summaries...")
                                    llm = get_llm_provider(provider)
                                    builder = TreeBuilder(llm)
                                    tree = builder.build_tree_with_summaries(
                                        sections, doc_title
                                    )
                            finally:
                                tmp_path.unlink(missing_ok=True)

                            _save_cached_tree(file_hash, tree)
                            status.update(
                                label="Document indexed!", state="complete"
                            )
                            st.toast("Document indexed successfully.", icon="\u2705")

                        # Update session state
                        st.session_state.tree = tree
                        st.session_state.doc_name = uploaded_file.name
                        st.session_state._current_file_hash = file_hash
                        # Reset chat on new document
                        st.session_state.messages = []

                    except Exception as exc:
                        status.update(label="Processing failed", state="error")
                        st.error(f"Failed to process document: {exc}")

        # ── Document info ─────────────────────────────────────────────
        st.divider()
        st.markdown(
            section_header("Current Document"), unsafe_allow_html=True
        )

        if st.session_state.get("tree") is not None:
            tree: TreeNode = st.session_state.tree
            all_nodes = tree.all_nodes_flat()
            node_count = len(all_nodes)
            image_count = sum(len(n.images) for n in all_nodes)

            # Compute page range
            pages_with_values = [
                n.end_page for n in all_nodes if n.end_page is not None
            ]
            total_pages = max(pages_with_values) if pages_with_values else 0

            doc_name = st.session_state.get("doc_name", "Unknown")
            st.caption(doc_name)

            # Metric cards in a grid
            metric_cols = st.columns(3)
            with metric_cols[0]:
                st.markdown(
                    metric_card("Sections", str(node_count), "\U0001F4C4"),
                    unsafe_allow_html=True,
                )
            with metric_cols[1]:
                st.markdown(
                    metric_card("Images", str(image_count), "\U0001F5BC"),
                    unsafe_allow_html=True,
                )
            with metric_cols[2]:
                st.markdown(
                    metric_card(
                        "Pages",
                        str(total_pages) if total_pages > 0 else "N/A",
                        "\U0001F4D1",
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No document loaded.")
