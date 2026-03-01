"""PageIndex RAG -- Streamlit application entry point.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

# ── Page configuration (must be first Streamlit call) ────────────────────
st.set_page_config(
    page_title="PageIndex RAG",
    page_icon="\U0001F4D1",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.theme import inject_theme_css, render_theme_toggle
from ui.sidebar import render_sidebar
from ui.tree_viewer import render_tree_viewer, show_mind_graph
from ui.chat import render_chat_messages, handle_user_query

# ── Session state initialization ─────────────────────────────────────────
for key, default in [
    ("messages", []),
    ("tree", None),
    ("doc_name", None),
    ("theme", "dark"),
    ("show_doc_panel", True),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Theme injection ──────────────────────────────────────────────────────
inject_theme_css(st.session_state.get("theme", "dark"))

# ── Sidebar (theme toggle + settings + upload) ───────────────────────────
render_theme_toggle()
render_sidebar()

# ── Main content area ────────────────────────────────────────────────────
if st.session_state.tree is not None:
    tree = st.session_state.tree
    show_panel = st.session_state.get("show_doc_panel", True)

    # Action bar: toggle panel + view document map
    col_toggle, col_map, _ = st.columns([1, 1.5, 9.5])
    with col_toggle:
        toggle_label = "\u00ab Hide" if show_panel else "\u00bb Show"
        if st.button(toggle_label, key="toggle_doc_panel", help="Toggle document panel"):
            st.session_state.show_doc_panel = not show_panel
            st.rerun()
    with col_map:
        if st.button("\U0001F4CA Document Map", key="show_mind_graph_btn", help="Interactive mind-graph visualization"):
            show_mind_graph(tree)

    if show_panel:
        col_tree, col_chat = st.columns([1, 2], gap="large")
        with col_tree:
            render_tree_viewer(tree)
        with col_chat:
            render_chat_messages()
    else:
        render_chat_messages()

    # ── Chat input at main body level (must be the LAST element for bottom-docking) ──
    prompt = st.chat_input("Ask a question about the document...")
    if prompt:
        handle_user_query(prompt)
else:
    # ── Empty state ──────────────────────────────────────────────────
    st.markdown("")
    st.markdown("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### \U0001F4D1 PageIndex RAG")
        st.markdown(
            "**Hierarchical document indexing & retrieval-augmented generation**\n\n"
            "Upload a document using the sidebar to get started.\n\n"
            "Supported formats: **PDF**, **Markdown**, **DOCX**, **PPTX**, **TXT**"
        )
