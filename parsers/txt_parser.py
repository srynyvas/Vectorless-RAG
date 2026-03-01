"""Plain-text parser with heuristic heading detection and paragraph chunking fallback."""

import re
from pathlib import Path

from parsers.base import BaseParser, ParsedSection

# ---------------------------------------------------------------------------
# Heading heuristic patterns
# ---------------------------------------------------------------------------

# ALL-CAPS lines (at least 3 alpha characters, max 120 chars)
_ALLCAPS_RE = re.compile(r"^[A-Z][A-Z0-9 :,\-\u2013\u2014]{2,119}$")

# "Chapter N:", "Section N:", "Part N:" etc.
_CHAPTER_SECTION_RE = re.compile(
    r"^(chapter|section|part|appendix)\s+(\d+|[IVXLCDM]+)\b[:\.\s\-]*",
    re.IGNORECASE,
)

# Markdown-style headings: # Heading, ## Heading, ### Heading, etc.
_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# Default max chunk size (characters) for the paragraph-chunking fallback.
_CHUNK_MAX_CHARS = 3000


def _detect_markdown_headings(lines: list[str]) -> list[tuple[int, str, int]]:
    """Detect Markdown ATX-style headings (# Heading, ## Heading, etc.).

    Returns list of (line_index, heading_text, level).
    """
    headings: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        match = _MARKDOWN_HEADING_RE.match(line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append((i, title, level))
    return headings


def _detect_setext_headings(lines: list[str]) -> list[tuple[int, str, int]]:
    """Detect Setext-style headings (lines followed by === or ---).

    Returns list of (line_index, heading_text, level).
    Level 1 for '===', level 2 for '---'.
    """
    headings: list[tuple[int, str, int]] = []
    for i in range(len(lines) - 1):
        current = lines[i].strip()
        underline = lines[i + 1].strip()
        if not current or len(current) > 120:
            continue
        if underline and len(underline) >= 3:
            if all(c == "=" for c in underline):
                headings.append((i, current, 1))
            elif all(c == "-" for c in underline):
                headings.append((i, current, 2))
    return headings


def _detect_pattern_headings(lines: list[str]) -> list[tuple[int, str, int]]:
    """Detect headings via ALL-CAPS and Chapter/Section patterns.

    Returns list of (line_index, heading_text, level).
    """
    headings: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        if _CHAPTER_SECTION_RE.match(stripped):
            headings.append((i, stripped, 1))
            continue

        if _ALLCAPS_RE.match(stripped):
            # Require that the line is surrounded by blank lines (or is at boundaries)
            prev_blank = (i == 0) or (not lines[i - 1].strip())
            next_blank = (i == len(lines) - 1) or (not lines[i + 1].strip())
            if prev_blank or next_blank:
                headings.append((i, stripped, 1))

    return headings


# ---------------------------------------------------------------------------
# TxtParser
# ---------------------------------------------------------------------------

class TxtParser(BaseParser):
    """Parse plain-text files with heuristic heading detection."""

    def supported_extensions(self) -> list[str]:
        return [".txt"]

    def parse(self, file_path: str) -> list[ParsedSection]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")
        if path.suffix.lower() != ".txt":
            raise ValueError(f"Not a .txt file: {file_path}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")

        lines = content.split("\n")

        # --- Merge all heading detections ------------------------------------
        headings: dict[int, tuple[str, int]] = {}  # line_idx -> (title, level)

        for idx, title, level in _detect_markdown_headings(lines):
            headings[idx] = (title, level)

        for idx, title, level in _detect_setext_headings(lines):
            if idx not in headings:  # markdown ATX takes priority
                headings[idx] = (title, level)

        for idx, title, level in _detect_pattern_headings(lines):
            if idx not in headings:  # setext takes priority over pattern
                headings[idx] = (title, level)

        # Also track setext underline lines so we can skip them in body text
        setext_underline_indices: set[int] = set()
        for idx, _, _ in _detect_setext_headings(lines):
            setext_underline_indices.add(idx + 1)

        # --- Fallback to paragraph chunking if too few headings ---------------
        if len(headings) < 2:
            return self._chunk_by_paragraphs(content)

        # --- Build sections from detected headings ----------------------------
        sorted_indices = sorted(headings.keys())
        sections: list[ParsedSection] = []

        # Preamble (text before first heading)
        first_idx = sorted_indices[0]
        preamble = "\n".join(lines[:first_idx]).strip()
        if preamble:
            sections.append(ParsedSection(
                title="Preamble",
                text=preamble,
                level=0,
            ))

        for pos, heading_line_idx in enumerate(sorted_indices):
            title, level = headings[heading_line_idx]

            # Determine the range of body lines
            start = heading_line_idx + 1
            # Skip setext underline immediately after heading
            if start in setext_underline_indices:
                start += 1

            if pos + 1 < len(sorted_indices):
                end = sorted_indices[pos + 1]
            else:
                end = len(lines)

            body_lines = [
                lines[i]
                for i in range(start, end)
                if i not in setext_underline_indices
            ]
            body_text = "\n".join(body_lines).strip()

            sections.append(ParsedSection(
                title=title,
                text=body_text,
                level=level,
            ))

        return sections

    # ------------------------------------------------------------------
    @staticmethod
    def _chunk_by_paragraphs(
        content: str,
        max_chars: int = _CHUNK_MAX_CHARS,
    ) -> list[ParsedSection]:
        """Fallback: split text into chunks of approximately *max_chars* along
        paragraph boundaries (double newlines).
        """
        paragraphs = re.split(r"\n\s*\n", content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return []

        sections: list[ParsedSection] = []
        chunk_parts: list[str] = []
        chunk_len = 0
        chunk_idx = 1

        for para in paragraphs:
            # If adding this paragraph would exceed the limit, flush first
            if chunk_parts and chunk_len + len(para) + 2 > max_chars:
                sections.append(ParsedSection(
                    title=f"Section {chunk_idx}",
                    text="\n\n".join(chunk_parts),
                    level=1,
                ))
                chunk_idx += 1
                chunk_parts = []
                chunk_len = 0

            chunk_parts.append(para)
            chunk_len += len(para) + 2  # +2 for the "\n\n" separator

        # Flush remaining
        if chunk_parts:
            sections.append(ParsedSection(
                title=f"Section {chunk_idx}",
                text="\n\n".join(chunk_parts),
                level=1,
            ))

        return sections
