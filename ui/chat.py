"""Chat component: premium chat interface with multimodal retrieval details."""
from __future__ import annotations

import base64

import streamlit as st

from llm.factory import get_llm_provider
from retriever.pipeline import RAGPipeline
from ui.theme import section_header, status_badge


def _display_retrieval_details(details: dict) -> None:
    """Render retrieval details in a polished expandable card."""
    with st.expander("\U0001F50D Retrieval Details", expanded=False):
        # Image count badge
        image_count = details.get("image_count", 0)
        if image_count > 0:
            st.markdown(
                status_badge(f"\U0001F5BC\uFE0F {image_count} images used", "info"),
                unsafe_allow_html=True,
            )

        if details.get("reasoning"):
            st.markdown("**Search Reasoning:**")
            st.markdown(f"> {details['reasoning']}")

        if details.get("node_ids"):
            st.markdown("**Selected Sections:**")
            badges_html = " ".join(
                status_badge(nid, "info") for nid in details["node_ids"]
            )
            st.markdown(badges_html, unsafe_allow_html=True)

        # Show images used in context
        if details.get("images"):
            st.markdown("**Images in Context:**")
            img_cols = st.columns(min(len(details["images"]), 3))
            for i, img_dict in enumerate(details["images"][:6]):
                with img_cols[i % 3]:
                    try:
                        img_bytes = base64.b64decode(img_dict["data"])
                        st.image(
                            img_bytes,
                            caption=img_dict.get("caption", ""),
                            use_container_width=True,
                        )
                    except Exception:
                        st.caption("(Image failed to load)")

        if details.get("context"):
            st.markdown("**Context Sent to LLM:**")
            st.text_area(
                "context_preview",
                value=details["context"][:3000],
                height=150,
                disabled=True,
                label_visibility="collapsed",
            )


def render_chat_messages() -> None:
    """Render the chat UI (header, message history) WITHOUT the input box.

    The ``st.chat_input()`` is intentionally omitted so that this function
    can be called inside ``st.columns()`` without layout issues.  The input
    widget lives in ``app.py`` at the main body level instead.
    """
    messages: list[dict] = st.session_state.get("messages", [])
    show_details: bool = st.session_state.get("show_retrieval_details", False)

    # ── Chat header ───────────────────────────────────────────────
    col_header, col_new = st.columns([4, 1])
    with col_header:
        st.markdown(
            section_header("Chat", "Ask questions about your document"),
            unsafe_allow_html=True,
        )
    with col_new:
        if st.button(
            "\U0001F5D1 New Chat",
            key="new_chat_btn",
            use_container_width=True,
        ):
            st.session_state.messages = []
            st.rerun()

    # ── Scrollable message container ──────────────────────────────
    with st.container(height=500):
        # ── Empty state ───────────────────────────────────────────
        if not messages and st.session_state.get("tree") is not None:
            st.markdown(
                "<div style='text-align: center; padding: 2rem; opacity: 0.6;'>"
                "<p style='font-size: 2rem;'>\U0001F4AC</p>"
                "<p>Ask a question about your document to get started.</p>"
                "</div>",
                unsafe_allow_html=True,
            )

        # ── Display message history ───────────────────────────────
        for msg in messages:
            avatar = "\U0001F9D1\u200D\U0001F4BC" if msg["role"] == "user" else "\U0001F916"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])
                if (
                    show_details
                    and msg["role"] == "assistant"
                    and msg.get("retrieval_details")
                ):
                    _display_retrieval_details(msg["retrieval_details"])


def handle_user_query(prompt: str) -> None:
    """Process a user query through the RAG pipeline and update session state.

    Called from ``app.py`` after ``st.chat_input()`` returns a value.
    Appends both the user and assistant messages to ``st.session_state.messages``
    and triggers ``st.rerun()`` so the chat UI refreshes with the new messages.
    """
    tree = st.session_state.get("tree")
    if tree is None:
        st.error("Please upload a document before asking questions.")
        return

    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Run RAG pipeline
    with st.spinner("Searching document..."):
        try:
            provider_name = st.session_state.get("llm_provider", "anthropic")
            llm = get_llm_provider(provider_name)
            pipeline = RAGPipeline(llm)
            result = pipeline.query(tree, prompt)

            answer = result.get("answer", "No answer was generated.")
            retrieval_details = {
                "node_ids": result.get("node_ids", []),
                "reasoning": result.get("reasoning", ""),
                "context": result.get("context", ""),
                "image_count": result.get("image_count", 0),
                "images": result.get("images", []),
            }
        except Exception as exc:
            answer = f"An error occurred: {exc}"
            retrieval_details = {}

    # Append assistant message
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "retrieval_details": retrieval_details,
        }
    )

    st.rerun()
