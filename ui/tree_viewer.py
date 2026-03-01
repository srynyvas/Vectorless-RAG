"""Tree viewer component: interactive collapsible tree with image badges and search."""
from __future__ import annotations

import base64
from io import BytesIO

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from indexer.node import TreeNode
from ui.theme import section_header, status_badge


def _page_range_label(node: TreeNode) -> str:
    """Return a human-readable page range string, or empty if pages are not set."""
    if node.start_page is not None and node.end_page is not None:
        if node.start_page == node.end_page:
            return f"p.{node.start_page}"
        return f"pp.{node.start_page}\u2013{node.end_page}"
    return ""


def _node_icon(node: TreeNode) -> str:
    """Choose icon based on node type."""
    if node.node_id == "root":
        return "\U0001F4D1"
    if node.images:
        return "\U0001F5BC"  # framed picture for nodes with images
    if node.children:
        return "\U0001F4C1"  # folder
    return "\U0001F4C4"  # document


def _count_images_recursive(node: TreeNode) -> int:
    """Count all images in a node and its descendants."""
    count = len(node.images)
    for child in node.children:
        count += _count_images_recursive(child)
    return count


def _render_node(node: TreeNode, depth: int = 0, search_filter: str = "") -> None:
    """Recursively render a tree node with enterprise styling."""
    # Skip nodes that don't match search filter
    if search_filter:
        matches = search_filter.lower() in node.title.lower()
        child_matches = any(
            search_filter.lower() in n.title.lower()
            for n in node.all_nodes_flat()
        )
        if not matches and not child_matches:
            return

    icon = _node_icon(node)
    page_info = _page_range_label(node)
    img_count = len(node.images)

    # Build label
    label_parts = [f"{icon} {node.title}"]
    if page_info:
        label_parts.append(f"  [{page_info}]")
    if img_count > 0:
        label_parts.append(f"  \U0001F5BC\uFE0F {img_count}")
    label = "".join(label_parts)

    if node.children:
        expanded = depth <= 0  # only root expanded by default
        with st.expander(label, expanded=expanded):
            # Node metadata
            meta_parts = [f"`{node.node_id}`"]
            if page_info:
                meta_parts.append(page_info)
            if img_count > 0:
                meta_parts.append(f"{img_count} image(s)")
            st.caption(" | ".join(meta_parts))

            if node.summary:
                st.markdown(f"*{node.summary}*")

            # Show images if any
            if node.images:
                _render_node_images(node.images)

            for child in node.children:
                _render_node(child, depth + 1, search_filter)
    else:
        # Leaf node
        with st.expander(label, expanded=False):
            meta_parts = [f"`{node.node_id}`"]
            if page_info:
                meta_parts.append(page_info)
            st.caption(" | ".join(meta_parts))

            if node.summary:
                st.markdown(f"*{node.summary}*")

            # Show text preview
            if node.text:
                preview = node.text[:300].replace("\n", " ").strip()
                if len(node.text) > 300:
                    preview += "..."
                st.markdown(f"<small>{preview}</small>", unsafe_allow_html=True)

            # Show images
            if node.images:
                _render_node_images(node.images)


def _render_node_images(images: list[dict]) -> None:
    """Display images as a row of thumbnails."""
    cols = st.columns(min(len(images), 3))
    for i, img_dict in enumerate(images[:6]):  # max 6 thumbnails
        with cols[i % 3]:
            try:
                img_bytes = base64.b64decode(img_dict["data"])
                st.image(
                    img_bytes,
                    caption=img_dict.get("caption", ""),
                    use_container_width=True,
                )
            except Exception:
                st.caption("(Image failed to load)")


def render_tree_viewer(tree: TreeNode) -> None:
    """Render the full document structure tree."""
    # Header with stats
    all_nodes = tree.all_nodes_flat()
    total_nodes = len(all_nodes)
    nodes_with_images = sum(1 for n in all_nodes if n.images)
    total_images = sum(len(n.images) for n in all_nodes)

    st.markdown(
        section_header(
            "Document Structure",
            f"{total_nodes} sections | {nodes_with_images} with images | {total_images} total images"
            if total_images > 0
            else f"{total_nodes} sections",
        ),
        unsafe_allow_html=True,
    )

    # Search/filter box
    search = st.text_input(
        "\U0001F50D Search sections",
        key="tree_search",
        placeholder="Filter by section title...",
        label_visibility="collapsed",
    )

    # Render tree
    _render_node(tree, depth=0, search_filter=search)


# ── Mind-Graph Visualization ─────────────────────────────────────────────────

_DEPTH_COLORS_DARK = ["#7c8aff", "#c084fc", "#34d399", "#fbbf24", "#f87171", "#6b7280"]
_DEPTH_COLORS_LIGHT = ["#1a73e8", "#7c4dff", "#0d9f6e", "#e37400", "#d93025", "#80868b"]


def _tree_to_agraph(
    node: TreeNode,
    nodes: list[Node],
    edges: list[Edge],
    depth: int,
    colors: list[str],
    max_depth: int,
) -> None:
    """Recursively convert a TreeNode hierarchy into agraph Node/Edge lists."""
    # Pick icon
    if node.node_id == "root":
        icon = "\U0001F4D1"
    elif node.images:
        icon = "\U0001F5BC"
    elif node.children:
        icon = "\U0001F4C1"
    else:
        icon = "\U0001F4C4"

    # Build label
    title_display = node.title if len(node.title) <= 40 else node.title[:37] + "..."
    label = f"{icon} {title_display}"
    page_info = _page_range_label(node)
    if page_info:
        label += f"\n[{page_info}]"
    img_count = len(node.images)
    if img_count > 0:
        label += f"\n\U0001F5BC {img_count}"

    # Build tooltip
    tooltip_parts = [f"ID: {node.node_id}"]
    if page_info:
        tooltip_parts.append(f"Pages: {page_info}")
    if node.summary:
        summary_preview = node.summary[:150]
        if len(node.summary) > 150:
            summary_preview += "..."
        tooltip_parts.append(f"Summary: {summary_preview}")
    total_images = _count_images_recursive(node)
    if total_images > 0:
        tooltip_parts.append(f"Images: {total_images}")
    tooltip = "\n".join(tooltip_parts)

    # Color from palette by depth
    color_idx = min(depth, len(colors) - 1)
    bg_color = colors[color_idx]

    # Size: root=40, parent=30, leaf=20
    if node.node_id == "root":
        size = 40
    elif node.children:
        size = 30
    else:
        size = 20

    nodes.append(
        Node(
            id=node.node_id,
            label=label,
            size=size,
            shape="box",
            color=bg_color,
            font={"color": "#ffffff", "size": 11},
            title=tooltip,
            level=depth,
        )
    )

    # Recurse into children if within max_depth
    if depth < max_depth:
        edge_color = colors[min(depth + 1, len(colors) - 1)]
        for child in node.children:
            edges.append(
                Edge(
                    source=node.node_id,
                    target=child.node_id,
                    color=edge_color,
                )
            )
            _tree_to_agraph(child, nodes, edges, depth + 1, colors, max_depth)


@st.dialog("\U0001F4CA Document Mind Map", width="large")
def show_mind_graph(tree: TreeNode) -> None:
    """Interactive mind-graph visualization of the document tree."""
    # Determine theme
    theme = st.session_state.get("theme", "dark")
    is_dark = theme == "dark"

    if is_dark:
        colors = _DEPTH_COLORS_DARK
        font_color = "#e0e0e0"
        bg_color = "#0e1117"
        edge_default = "#555555"
    else:
        colors = _DEPTH_COLORS_LIGHT
        font_color = "#202124"
        bg_color = "#ffffff"
        edge_default = "#cccccc"

    # Stats caption
    all_nodes = tree.all_nodes_flat()
    total_sections = len(all_nodes)
    sections_with_images = sum(1 for n in all_nodes if n.images)
    st.caption(
        f"{total_sections} sections | {sections_with_images} with images | Click nodes to inspect"
    )

    # Depth-limit slider
    max_depth = st.slider("Display depth", 1, 6, 3, key="graph_depth")

    # Convert tree to agraph nodes/edges
    nodes: list[Node] = []
    edges: list[Edge] = []
    _tree_to_agraph(tree, nodes, edges, depth=0, colors=colors, max_depth=max_depth)

    # Override font color on all nodes based on theme
    for n in nodes:
        n.font = {"color": font_color, "size": 11}

    # Configure agraph
    config = Config(
        width=900,
        height=500,
        directed=True,
        physics=False,
        hierarchical=True,
        nodeHighlightBehavior=True,
    )

    # Render graph
    selected = agraph(nodes=nodes, edges=edges, config=config)

    # Show selected node details
    if selected:
        matched = tree.find_nodes_by_ids([selected])
        if matched:
            sel_node = matched[0]
            st.markdown(f"**{sel_node.title}**")
            if sel_node.summary:
                st.markdown(f"*{sel_node.summary}*")
            page_info = _page_range_label(sel_node)
            if page_info:
                st.caption(f"Pages: {page_info}")
            sel_img_count = _count_images_recursive(sel_node)
            if sel_img_count > 0:
                st.caption(f"\U0001F5BC {sel_img_count} image(s)")
