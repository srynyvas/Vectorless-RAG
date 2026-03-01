"""Theme engine for the PageIndex RAG Streamlit application.

Provides light and dark mode themes with CSS custom properties,
a sidebar toggle, and reusable HTML component helpers.

Usage in app.py:
    from ui.theme import inject_theme_css, render_theme_toggle
    render_theme_toggle()          # sidebar toggle (call inside sidebar or before)
    inject_theme_css(st.session_state.get("theme", "dark"))
"""

from __future__ import annotations

import streamlit as st


# ---------------------------------------------------------------------------
# CSS custom properties for each theme
# ---------------------------------------------------------------------------

_THEME_VARS: dict[str, dict[str, str]] = {
    "light": {
        # Backgrounds
        "--bg-primary": "#ffffff",
        "--bg-secondary": "#f8f9fb",
        "--bg-tertiary": "#f0f2f5",
        "--bg-card": "#ffffff",
        "--bg-card-hover": "#f5f7fa",
        "--bg-sidebar": "#f4f5f7",
        "--bg-sidebar-card": "#ffffff",
        "--bg-user-bubble": "rgba(26, 115, 232, 0.06)",
        "--bg-assistant-bubble": "#ffffff",
        "--bg-input": "#ffffff",
        "--bg-code": "#f6f8fa",
        "--bg-tooltip": "#1f1f1f",
        "--bg-overlay": "rgba(0, 0, 0, 0.04)",
        "--bg-metric": "rgba(26, 115, 232, 0.05)",
        # Text
        "--text-primary": "#1f1f1f",
        "--text-secondary": "#5f6368",
        "--text-tertiary": "#80868b",
        "--text-inverse": "#ffffff",
        "--text-link": "#1a73e8",
        # Accent / brand
        "--accent-primary": "#1a73e8",
        "--accent-primary-hover": "#1557b0",
        "--accent-primary-subtle": "rgba(26, 115, 232, 0.10)",
        "--accent-secondary": "#7c4dff",
        "--accent-gradient": "linear-gradient(135deg, #1a73e8 0%, #7c4dff 100%)",
        "--accent-gradient-subtle": "linear-gradient(135deg, rgba(26,115,232,0.08) 0%, rgba(124,77,255,0.08) 100%)",
        # Borders
        "--border-primary": "#e0e0e0",
        "--border-secondary": "#eeeeee",
        "--border-focus": "#1a73e8",
        "--border-accent": "#1a73e8",
        # Shadows
        "--shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.04)",
        "--shadow-md": "0 2px 8px rgba(0, 0, 0, 0.06)",
        "--shadow-lg": "0 4px 16px rgba(0, 0, 0, 0.08)",
        "--shadow-card": "0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)",
        # Radius
        "--radius-sm": "6px",
        "--radius-md": "8px",
        "--radius-lg": "12px",
        "--radius-xl": "16px",
        "--radius-pill": "9999px",
        # Status colours
        "--status-success": "#0d9f6e",
        "--status-success-bg": "rgba(13, 159, 110, 0.10)",
        "--status-info": "#1a73e8",
        "--status-info-bg": "rgba(26, 115, 232, 0.10)",
        "--status-warning": "#e37400",
        "--status-warning-bg": "rgba(227, 116, 0, 0.10)",
        "--status-error": "#d93025",
        "--status-error-bg": "rgba(217, 48, 37, 0.10)",
        # Tree depth accent colours (6 levels)
        "--tree-depth-0": "#1a73e8",
        "--tree-depth-1": "#7c4dff",
        "--tree-depth-2": "#0d9f6e",
        "--tree-depth-3": "#e37400",
        "--tree-depth-4": "#d93025",
        "--tree-depth-5": "#80868b",
        # Scrollbar
        "--scrollbar-track": "#f0f2f5",
        "--scrollbar-thumb": "#c4c7cc",
        "--scrollbar-thumb-hover": "#9aa0a6",
        # Header gradient
        "--header-gradient": "linear-gradient(135deg, #1a73e8 0%, #4285f4 50%, #7c4dff 100%)",
    },
    "dark": {
        # Backgrounds
        "--bg-primary": "#0e1117",
        "--bg-secondary": "#161b22",
        "--bg-tertiary": "#1c2129",
        "--bg-card": "#1e1e2e",
        "--bg-card-hover": "#252538",
        "--bg-sidebar": "#13141d",
        "--bg-sidebar-card": "#1e1e2e",
        "--bg-user-bubble": "rgba(124, 138, 255, 0.08)",
        "--bg-assistant-bubble": "#1e1e2e",
        "--bg-input": "#1e1e2e",
        "--bg-code": "#161b22",
        "--bg-tooltip": "#e0e0e0",
        "--bg-overlay": "rgba(255, 255, 255, 0.03)",
        "--bg-metric": "rgba(124, 138, 255, 0.08)",
        # Text
        "--text-primary": "#e0e0e0",
        "--text-secondary": "#9ca3af",
        "--text-tertiary": "#6b7280",
        "--text-inverse": "#0e1117",
        "--text-link": "#7c8aff",
        # Accent / brand
        "--accent-primary": "#7c8aff",
        "--accent-primary-hover": "#9ba6ff",
        "--accent-primary-subtle": "rgba(124, 138, 255, 0.12)",
        "--accent-secondary": "#c084fc",
        "--accent-gradient": "linear-gradient(135deg, #7c8aff 0%, #c084fc 100%)",
        "--accent-gradient-subtle": "linear-gradient(135deg, rgba(124,138,255,0.10) 0%, rgba(192,132,252,0.10) 100%)",
        # Borders
        "--border-primary": "#2d2d3d",
        "--border-secondary": "#232336",
        "--border-focus": "#7c8aff",
        "--border-accent": "#7c8aff",
        # Shadows
        "--shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.20)",
        "--shadow-md": "0 2px 8px rgba(0, 0, 0, 0.30)",
        "--shadow-lg": "0 4px 16px rgba(0, 0, 0, 0.40)",
        "--shadow-card": "0 1px 3px rgba(0, 0, 0, 0.24), 0 1px 2px rgba(0, 0, 0, 0.18)",
        # Radius (identical across themes)
        "--radius-sm": "6px",
        "--radius-md": "8px",
        "--radius-lg": "12px",
        "--radius-xl": "16px",
        "--radius-pill": "9999px",
        # Status colours
        "--status-success": "#34d399",
        "--status-success-bg": "rgba(52, 211, 153, 0.12)",
        "--status-info": "#7c8aff",
        "--status-info-bg": "rgba(124, 138, 255, 0.12)",
        "--status-warning": "#fbbf24",
        "--status-warning-bg": "rgba(251, 191, 36, 0.12)",
        "--status-error": "#f87171",
        "--status-error-bg": "rgba(248, 113, 113, 0.12)",
        # Tree depth accent colours
        "--tree-depth-0": "#7c8aff",
        "--tree-depth-1": "#c084fc",
        "--tree-depth-2": "#34d399",
        "--tree-depth-3": "#fbbf24",
        "--tree-depth-4": "#f87171",
        "--tree-depth-5": "#6b7280",
        # Scrollbar
        "--scrollbar-track": "#161b22",
        "--scrollbar-thumb": "#2d2d3d",
        "--scrollbar-thumb-hover": "#3d3d50",
        # Header gradient
        "--header-gradient": "linear-gradient(135deg, #7c8aff 0%, #a78bfa 50%, #c084fc 100%)",
    },
}


# ---------------------------------------------------------------------------
# CSS variable declaration block builder
# ---------------------------------------------------------------------------

def _build_css_vars(theme: str) -> str:
    """Return a ``:root`` block declaring all CSS custom properties."""
    variables = _THEME_VARS.get(theme, _THEME_VARS["dark"])
    lines = "\n".join(f"    {k}: {v};" for k, v in variables.items())
    return f":root {{\n{lines}\n}}"


# ---------------------------------------------------------------------------
# Core stylesheet (uses var() references only -- theme-agnostic)
# ---------------------------------------------------------------------------

_CORE_CSS = r"""
/* ================================================================
   PageIndex RAG -- Theme Engine (auto-generated)
   ================================================================ */

/* --- Typography ------------------------------------------------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* --- Global transitions ----------------------------------------- */
*, *::before, *::after {
    transition: background-color 0.3s ease,
                border-color 0.3s ease,
                color 0.3s ease,
                box-shadow 0.3s ease;
}

/* --- Main app container ----------------------------------------- */
.stApp {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

/* --- Custom scrollbar ------------------------------------------- */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: var(--scrollbar-track);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb {
    background: var(--scrollbar-thumb);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--scrollbar-thumb-hover);
}

/* Firefox scrollbar */
* {
    scrollbar-width: thin;
    scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);
}

/* ================================================================
   HEADER
   ================================================================ */
header[data-testid="stHeader"] {
    background: var(--header-gradient) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-secondary) !important;
}

/* Style the app title when rendered in the header area */
.stApp h1:first-of-type {
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 700;
    letter-spacing: -0.025em;
}

/* ================================================================
   SIDEBAR
   ================================================================ */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-primary) !important;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.5rem;
}

/* Sidebar headers */
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--text-primary) !important;
    font-weight: 600;
    letter-spacing: -0.01em;
}

/* Sidebar dividers */
[data-testid="stSidebar"] hr {
    border-color: var(--border-secondary) !important;
    margin: 0.75rem 0 !important;
}

/* Sidebar captions & secondary text */
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stCaption {
    color: var(--text-secondary) !important;
    font-size: 0.875rem;
}

/* Sidebar select boxes */
[data-testid="stSidebar"] [data-testid="stSelectbox"] {
    margin-bottom: 0.25rem;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background-color: var(--bg-sidebar-card) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}

/* Sidebar toggle switches */
[data-testid="stSidebar"] [data-testid="stToggle"] label {
    color: var(--text-secondary) !important;
    font-size: 0.875rem;
}

/* ================================================================
   BUTTONS
   ================================================================ */
.stButton > button {
    background-color: var(--accent-primary) !important;
    color: var(--text-inverse) !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1.25rem !important;
    cursor: pointer !important;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.01em;
}
.stButton > button:hover {
    background-color: var(--accent-primary-hover) !important;
    box-shadow: var(--shadow-md) !important;
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: translateY(0);
    box-shadow: var(--shadow-sm) !important;
}

/* Secondary / sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    background-color: var(--bg-sidebar-card) !important;
    color: var(--accent-primary) !important;
    border: 1px solid var(--border-primary) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: var(--accent-primary-subtle) !important;
    border-color: var(--accent-primary) !important;
}

/* Theme toggle button special styling */
.stButton > button[kind="secondary"] {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-primary) !important;
}
.stButton > button[kind="secondary"]:hover {
    background-color: var(--bg-card-hover) !important;
    border-color: var(--accent-primary) !important;
}

/* ================================================================
   CHAT MESSAGES
   ================================================================ */
[data-testid="stChatMessage"] {
    border-radius: var(--radius-lg) !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.75rem !important;
    border: 1px solid var(--border-secondary) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* User message bubble */
[data-testid="stChatMessage"][data-testid-role="user"],
.stChatMessage:has([data-testid="chatAvatarIcon-user"]) {
    background-color: var(--bg-user-bubble) !important;
    border-left: 3px solid var(--accent-primary) !important;
}

/* Assistant message bubble */
[data-testid="stChatMessage"][data-testid-role="assistant"],
.stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) {
    background-color: var(--bg-assistant-bubble) !important;
    border-left: 3px solid var(--accent-secondary) !important;
}

/* Chat message text colour */
[data-testid="stChatMessage"] .stMarkdown p {
    color: var(--text-primary) !important;
    line-height: 1.65;
}

/* Chat input */
[data-testid="stChatInput"] {
    border-color: var(--border-primary) !important;
}
[data-testid="stChatInput"] textarea {
    background-color: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-lg) !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.9375rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--border-focus) !important;
    box-shadow: 0 0 0 2px var(--accent-primary-subtle) !important;
}

/* Chat avatar styling */
[data-testid="stChatMessage"] [data-testid*="chatAvatar"] {
    border-radius: var(--radius-md) !important;
}

/* ================================================================
   EXPANDERS
   ================================================================ */
[data-testid="stExpander"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border-primary) !important;
    border-left: 3px solid var(--accent-primary) !important;
    border-radius: var(--radius-md) !important;
    margin-bottom: 0.5rem !important;
    overflow: hidden;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stExpander"]:hover {
    border-left-color: var(--accent-secondary) !important;
    box-shadow: var(--shadow-md) !important;
}

[data-testid="stExpander"] summary {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.9375rem;
}
[data-testid="stExpander"] summary:hover {
    color: var(--accent-primary) !important;
}

[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    border-top: 1px solid var(--border-secondary) !important;
    padding: 0.75rem 1rem !important;
}

/* Nested expanders get slightly different accent */
[data-testid="stExpander"] [data-testid="stExpander"] {
    border-left-color: var(--accent-secondary) !important;
}

/* ================================================================
   METRICS
   ================================================================ */
[data-testid="stMetric"] {
    background-color: var(--bg-metric) !important;
    border: 1px solid var(--border-secondary) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1rem 1.25rem !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    font-size: 1.5rem !important;
    letter-spacing: -0.02em;
}
[data-testid="stMetricDelta"] {
    font-size: 0.8125rem !important;
    font-weight: 500;
}

/* ================================================================
   FILE UPLOADER
   ================================================================ */
[data-testid="stFileUploader"] {
    background-color: var(--bg-card) !important;
    border-radius: var(--radius-lg) !important;
    padding: 0.25rem !important;
}
[data-testid="stFileUploader"] section {
    border: 2px dashed var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
    padding: 1.5rem 1rem !important;
    background: var(--accent-gradient-subtle) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: var(--accent-primary) !important;
    background: var(--accent-primary-subtle) !important;
}
[data-testid="stFileUploader"] section small {
    color: var(--text-tertiary) !important;
}
[data-testid="stFileUploader"] button {
    background-color: var(--accent-primary) !important;
    color: var(--text-inverse) !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-weight: 500 !important;
}

/* ================================================================
   TEXT INPUTS, TEXT AREAS, SELECT BOXES (general)
   ================================================================ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background-color: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--border-focus) !important;
    box-shadow: 0 0 0 2px var(--accent-primary-subtle) !important;
}

/* Labels */
.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stFileUploader label,
[data-testid="stWidgetLabel"] {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.8125rem !important;
    letter-spacing: 0.01em;
}

/* ================================================================
   TABS
   ================================================================ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--border-primary) !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.5rem 1rem !important;
    background-color: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary) !important;
    background-color: var(--bg-overlay) !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent-primary) !important;
    border-bottom-color: var(--accent-primary) !important;
}

/* ================================================================
   CODE BLOCKS
   ================================================================ */
.stCodeBlock, code, pre {
    background-color: var(--bg-code) !important;
    border: 1px solid var(--border-secondary) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}
.stMarkdown code {
    background-color: var(--bg-code) !important;
    color: var(--accent-primary) !important;
    padding: 0.15em 0.4em !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.85em !important;
    border: 1px solid var(--border-secondary) !important;
}

/* ================================================================
   ALERTS / INFO / WARNING / ERROR / SUCCESS
   ================================================================ */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-secondary) !important;
}
.stAlert [data-testid="stAlertContentInfo"] {
    background-color: var(--status-info-bg) !important;
    color: var(--text-primary) !important;
}

/* ================================================================
   SPINNER / TOAST
   ================================================================ */
.stSpinner > div {
    border-top-color: var(--accent-primary) !important;
}
[data-testid="stToast"] {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-lg) !important;
}

/* ================================================================
   TREE VIEWER -- depth-coded left borders
   ================================================================ */
.pi-tree-item {
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.25rem;
    border-radius: var(--radius-sm);
    background-color: var(--bg-card);
    transition: all 0.15s ease;
}
.pi-tree-item:hover {
    background-color: var(--bg-card-hover);
}
.pi-tree-depth-0 { border-left: 3px solid var(--tree-depth-0); margin-left: 0; }
.pi-tree-depth-1 { border-left: 3px solid var(--tree-depth-1); margin-left: 1rem; }
.pi-tree-depth-2 { border-left: 3px solid var(--tree-depth-2); margin-left: 2rem; }
.pi-tree-depth-3 { border-left: 3px solid var(--tree-depth-3); margin-left: 3rem; }
.pi-tree-depth-4 { border-left: 3px solid var(--tree-depth-4); margin-left: 4rem; }
.pi-tree-depth-5 { border-left: 3px solid var(--tree-depth-5); margin-left: 5rem; }

.pi-tree-title {
    font-weight: 500;
    color: var(--text-primary);
    font-size: 0.875rem;
}
.pi-tree-meta {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    margin-top: 0.125rem;
}

/* ================================================================
   STATUS BADGES (pill-shaped)
   ================================================================ */
.pi-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.65rem;
    border-radius: var(--radius-pill);
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    line-height: 1.4;
    white-space: nowrap;
}
.pi-badge-success {
    background-color: var(--status-success-bg);
    color: var(--status-success);
}
.pi-badge-info {
    background-color: var(--status-info-bg);
    color: var(--status-info);
}
.pi-badge-warning {
    background-color: var(--status-warning-bg);
    color: var(--status-warning);
}
.pi-badge-error {
    background-color: var(--status-error-bg);
    color: var(--status-error);
}

/* ================================================================
   METRIC CARDS (custom HTML)
   ================================================================ */
.pi-metric-card {
    background: var(--bg-metric);
    border: 1px solid var(--border-secondary);
    border-radius: var(--radius-lg);
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease;
}
.pi-metric-card:hover {
    box-shadow: var(--shadow-md);
    border-color: var(--accent-primary);
}
.pi-metric-icon {
    font-size: 1.5rem;
    line-height: 1;
    margin-bottom: 0.125rem;
}
.pi-metric-label {
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-tertiary);
}
.pi-metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    line-height: 1.2;
}

/* ================================================================
   SECTION HEADERS (custom HTML)
   ================================================================ */
.pi-section-header {
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border-secondary);
}
.pi-section-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.01em;
    margin: 0;
    padding: 0;
    line-height: 1.4;
}
.pi-section-subtitle {
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    margin: 0.25rem 0 0 0;
    padding: 0;
    line-height: 1.4;
}

/* ================================================================
   THEME TOGGLE BUTTON (sidebar)
   ================================================================ */
.pi-theme-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    background-color: var(--bg-sidebar-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    margin-bottom: 0.75rem;
    cursor: pointer;
}
.pi-theme-toggle-label {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    font-weight: 500;
}

/* ================================================================
   GENERAL MARKDOWN STYLING
   ================================================================ */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
.stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
    color: var(--text-primary) !important;
    letter-spacing: -0.01em;
}
.stMarkdown p {
    color: var(--text-primary) !important;
    line-height: 1.65;
}
.stMarkdown a {
    color: var(--text-link) !important;
    text-decoration: none !important;
}
.stMarkdown a:hover {
    text-decoration: underline !important;
}
.stMarkdown blockquote {
    border-left: 3px solid var(--accent-primary) !important;
    padding-left: 1rem !important;
    color: var(--text-secondary) !important;
    background-color: var(--bg-overlay) !important;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0 !important;
}
.stMarkdown hr {
    border-color: var(--border-secondary) !important;
}

/* ================================================================
   COLUMNS GAP refinement
   ================================================================ */
[data-testid="column"] {
    padding: 0 0.5rem !important;
}

/* ================================================================
   DATA FRAMES / TABLES
   ================================================================ */
.stDataFrame {
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden;
}
.stDataFrame thead th {
    background-color: var(--bg-tertiary) !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    font-size: 0.8125rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
}
.stDataFrame tbody td {
    color: var(--text-primary) !important;
    border-bottom: 1px solid var(--border-secondary) !important;
}

/* ================================================================
   POPOVER / DROPDOWN MENUS (baseweb)
   ================================================================ */
[data-baseweb="popover"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-lg) !important;
}
[data-baseweb="menu"] {
    background-color: var(--bg-card) !important;
}
[data-baseweb="menu"] li {
    color: var(--text-primary) !important;
}
[data-baseweb="menu"] li:hover {
    background-color: var(--bg-card-hover) !important;
}

/* ================================================================
   FOCUS OUTLINES (accessibility)
   ================================================================ */
*:focus-visible {
    outline: 2px solid var(--accent-primary) !important;
    outline-offset: 2px;
}

/* ================================================================
   DIALOG / MODAL (@st.dialog)
   ================================================================ */
[data-testid="stDialog"] > div {
    background-color: var(--bg-primary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-xl) !important;
    box-shadow: var(--shadow-lg) !important;
}
[data-testid="stDialog"] [data-testid="stDialogDismissBtn"] {
    color: var(--text-secondary) !important;
}
[data-testid="stDialog"] [data-testid="stDialogDismissBtn"]:hover {
    color: var(--text-primary) !important;
    background-color: var(--bg-card-hover) !important;
}
[data-testid="stDialog"] .stMarkdown h1,
[data-testid="stDialog"] .stMarkdown h2,
[data-testid="stDialog"] .stMarkdown h3 {
    color: var(--text-primary) !important;
}
[data-testid="stDialog"] .stCaption {
    color: var(--text-tertiary) !important;
}
/* Slider inside dialog */
[data-testid="stDialog"] [data-testid="stSlider"] {
    color: var(--text-secondary) !important;
}
[data-testid="stDialog"] [data-testid="stSlider"] [data-testid="stThumbValue"] {
    color: var(--accent-primary) !important;
}

/* ================================================================
   CHAT INPUT BOTTOM BAR
   ================================================================ */
/* Ensure the bottom chat bar blends with the theme background */
[data-testid="stBottom"] {
    background-color: var(--bg-primary) !important;
    border-top: 1px solid var(--border-secondary) !important;
}
[data-testid="stBottom"] [data-testid="stChatInput"] {
    background-color: var(--bg-primary) !important;
}

/* Add bottom padding to main content so chat bar doesn't overlap content */
.stApp > [data-testid="stAppViewContainer"] > section.main {
    padding-bottom: 5rem !important;
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inject_theme_css(theme: str = "dark") -> None:
    """Inject the full themed CSS into the Streamlit page.

    Call once per render cycle (typically near the top of your app).

    Args:
        theme: ``"light"`` or ``"dark"``.
    """
    if theme not in _THEME_VARS:
        theme = "dark"

    css_vars = _build_css_vars(theme)
    full_css = f"<style>\n{css_vars}\n{_CORE_CSS}\n</style>"
    st.markdown(full_css, unsafe_allow_html=True)


def render_theme_toggle() -> None:
    """Render a theme toggle button in the sidebar.

    Reads / writes ``st.session_state.theme`` (defaults to ``"dark"``).
    The toggle triggers a Streamlit rerun so that ``inject_theme_css``
    picks up the updated value.
    """
    # Initialise default
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"

    current = st.session_state.theme
    is_dark = current == "dark"

    with st.sidebar:
        icon = "\u2600\ufe0f" if is_dark else "\U0001F319"
        label = "Switch to Light" if is_dark else "Switch to Dark"

        if st.button(f"{icon}  {label}", key="pi_theme_toggle", use_container_width=True):
            st.session_state.theme = "light" if is_dark else "dark"
            st.rerun()


# ---------------------------------------------------------------------------
# HTML component helpers
# ---------------------------------------------------------------------------

_BADGE_COLOUR_MAP: dict[str, str] = {
    "success": "success",
    "green": "success",
    "info": "info",
    "blue": "info",
    "warning": "warning",
    "orange": "warning",
    "error": "error",
    "red": "error",
}


def status_badge(text: str, color: str = "info") -> str:
    """Return an HTML string for a pill-shaped status badge.

    Args:
        text:  The label text.
        color: One of ``"success"``/``"green"``, ``"info"``/``"blue"``,
               ``"warning"``/``"orange"``, ``"error"``/``"red"``.

    Returns:
        An HTML ``<span>`` that can be rendered with
        ``st.markdown(..., unsafe_allow_html=True)``.
    """
    css_class = _BADGE_COLOUR_MAP.get(color.lower(), "info")
    return f'<span class="pi-badge pi-badge-{css_class}">{text}</span>'


def metric_card(label: str, value: str, icon: str = "") -> str:
    """Return an HTML string for a styled metric card.

    Args:
        label: Small uppercase description (e.g. ``"Total Nodes"``).
        value: The prominent metric value (e.g. ``"42"``).
        icon:  An optional emoji or text icon shown above the label.

    Returns:
        An HTML ``<div>`` that can be rendered with
        ``st.markdown(..., unsafe_allow_html=True)``.
    """
    icon_html = f'<div class="pi-metric-icon">{icon}</div>' if icon else ""
    return (
        f'<div class="pi-metric-card">'
        f'  {icon_html}'
        f'  <div class="pi-metric-label">{label}</div>'
        f'  <div class="pi-metric-value">{value}</div>'
        f'</div>'
    )


def section_header(title: str, subtitle: str | None = None) -> str:
    """Return an HTML string for a styled section header.

    Args:
        title:    The main heading text.
        subtitle: An optional muted line below the heading.

    Returns:
        An HTML ``<div>`` that can be rendered with
        ``st.markdown(..., unsafe_allow_html=True)``.
    """
    subtitle_html = (
        f'<p class="pi-section-subtitle">{subtitle}</p>' if subtitle else ""
    )
    return (
        f'<div class="pi-section-header">'
        f'  <p class="pi-section-title">{title}</p>'
        f'  {subtitle_html}'
        f'</div>'
    )
